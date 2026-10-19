"""Bounded, proposal-only real ModelOps verification on an authorized synthetic DOCX.

Default workflow mode exits 2 while human review is pending. --proposal-only
exits 0 ONLY for successful proposal generation/validation, never end-to-end PASS.
No source DB rows, active pointers, approvals or provider configuration are written.
ModelOps's ordinary usage/quota/key health accounting remains in effect.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine
from app.core.storage import LocalStorageDriver, storage_service
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.services.qnu_serving import input_reference, load_document
from app.modules.knowledge.services.semantic_annotations import (
    SemanticAnnotations,
    _digest,
    _validated_copy,
    propose_source_semantics,
    semantic_input_hash,
)
from app.modules.knowledge.services.semantic_store import semantic_fingerprint
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.model_catalog_service import model_catalog_service


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


class SafeDiagnostics(logging.Handler):
    def __init__(self):
        super().__init__()
        self.failures: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        if str(record.msg).startswith("model_inference_failed") and isinstance(record.args, tuple):
            provider, model, diagnostics = record.args
            allowed = {key: diagnostics.get(key) for key in ("error_type", "http_status", "reason")}
            kind = str(allowed["error_type"])
            allowed["category"] = ("timeout" if "Timeout" in kind else "connection" if "Connect" in kind
                                   else allowed["reason"])
            self.failures.append({"provider_id": provider, "model": model, **allowed})


async def run_proposal(artifact: dict, invoke, *, proposal_only: bool = False) -> tuple[int, dict]:
    """Same workflow contract for real calls and explicitly labeled test adapters."""
    before = semantic_fingerprint(artifact)
    original_policy = copy.deepcopy(artifact.get("source_policy"))
    report = {"stages": {"provider": "NOT_RUN", "response_complete": "NOT_RUN", "json_syntax": "NOT_RUN", "selector_schema": "NOT_RUN", "evidence_binding": "NOT_RUN", "context_expansion": "NOT_RUN", "proposal": "NOT_RUN", "human_review": "NOT_RUN", "apply": "NOT_RUN",
                          "persist_reload": "NOT_RUN", "projection_chunks": "NOT_RUN"},
              "source_applied": False, "human_approved": False, "end_to_end": "INCOMPLETE"}
    try:
        proposal = await invoke(artifact)
        if (proposal.get("status") not in {"proposed", "empty"}
                or proposal.get("proposal_hash") != _digest({k: v for k, v in proposal.items() if k != "proposal_hash"})
                or proposal.get("input_hash") != semantic_input_hash(artifact)):
            raise ValueError("Invalid proposal envelope")
        _validated_copy(artifact, SemanticAnnotations.model_validate(proposal["annotations"]))
        if semantic_fingerprint(artifact) != before:
            # Context policy is a derived blocker for a pending proposal, not an
            # applied semantic edit. Compare the effective payload independently.
            comparable = copy.deepcopy(artifact)
            comparable["source_policy"] = original_policy
            if semantic_fingerprint(comparable) != before:
                raise ValueError("Proposal mutated effective data")
        report.update(status="WAITING_FOR_REVIEW", proposal_hash=proposal["proposal_hash"],
                      model=proposal["model"], counts={key: len(value) for key, value in proposal["annotations"].items()})
        from app.modules.knowledge.services.semantic_context_review import proposal_summary
        summary = proposal_summary(proposal)
        report["context_summary"] = summary
        status = "WAITING_FOR_CONTEXT" if summary["requires_more_context"] else "WAITING_FOR_REVIEW"
        report.update(status=status)
        report["stages"].update(proposal="PASS", human_review=status)
        report["stages"].update(provider="PASS", selector_schema="PASS", evidence_binding="PASS")
        runs = (proposal.get("model") or {}).get("runs", [])
        report["stages"].update(response_complete="PASS" if runs and all(run.get("finish_reason") == "stop" for run in runs) else "UNKNOWN",
            json_syntax="PASS")
        return (0 if proposal_only and not summary["requires_more_context"] else 2), report
    except Exception as exc:
        report.update(status="BLOCKED", error_code=getattr(exc, "code", type(exc).__name__))
        if getattr(exc, "code", "").startswith("MODEL_OUTPUT_") or getattr(exc, "code", "") == "MODEL_RESPONSE_PROTOCOL_ERROR":
            report["provider_failure"] = exc.details
        if getattr(exc, "code", None) in {"SEMANTIC_RUN_DEADLINE", "SEMANTIC_CALL_DEADLINE"}:
            report["failure_category"] = exc.code
            report["stages"]["proposal"] = "FAIL"
            return 1, report
        if getattr(exc, "code", None) in {"SEMANTIC_EVIDENCE_INVALID", "SEMANTIC_OUTPUT_INVALID"}:
            report["output_validation"] = exc.details
            report["provider_inference"] = "PASS"
            report["stages"].update(provider="PASS", selector_schema="FAIL" if exc.code == "SEMANTIC_OUTPUT_INVALID" else "PASS",
                evidence_binding="NOT_RUN" if exc.code == "SEMANTIC_OUTPUT_INVALID" else "FAIL")
            stage = exc.details.get("stage")
            report["stages"]["response_complete"] = "FAIL" if stage in {"refusal", "response_incomplete"} else "PASS"
            report["stages"]["json_syntax"] = "FAIL" if stage == "json_syntax" else "NOT_RUN" if stage in {"refusal", "response_incomplete"} else "PASS"
            if stage in {"refusal", "response_incomplete", "json_syntax"}:
                report["stages"]["selector_schema"] = "NOT_RUN"
        if getattr(exc, "code", None) == "SEMANTIC_CONTEXT_INCOMPLETE":
            report["context_incomplete"] = exc.details
            report["provider_inference"] = "PASS" if exc.details.get("model") else "NOT_RUN"
            if exc.details.get("model") and exc.details.get("stage") == "context_expansion":
                report["stages"].update(provider="PASS", json_syntax="PASS", selector_schema="PASS", context_expansion="FAIL")
                report["stages"]["response_complete"] = "PASS" if exc.details["model"].get("finish_reason") == "stop" else "UNKNOWN"
        report["failure_category"] = ("invalid_output_or_evidence" if getattr(exc, "code", None) in {"SEMANTIC_EVIDENCE_INVALID", "SEMANTIC_OUTPUT_INVALID"} else
                                      "context_budget_or_missing_evidence" if getattr(exc, "code", None) == "SEMANTIC_CONTEXT_INCOMPLETE" else
                                      "timeout" if isinstance(exc, TimeoutError) else
                                      "invalid_output_or_evidence" if isinstance(exc, (ValueError, KeyError, TypeError))
                                      else "provider_or_configuration")
        report["stages"]["proposal"] = "FAIL"
        # No exception strings, provider bodies or model text in diagnostics.
        return 1, report


async def main(args) -> int:
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"status": "BLOCKED", "real_provider": True, "environment": settings.ENVIRONMENT,
              "command": sys.argv, "cwd": str(Path.cwd()), "source_applied": False, "human_approved": False}
    try:
        if settings.ENVIRONMENT not in {"development", "dev", "local", "test", "testing", "staging"}:
            raise ValueError("Verification environment not authorized")
        source_hash = hashlib.sha256(args.docx.read_bytes()).hexdigest()
        report["fixture_sha256"] = source_hash
        if source_hash != args.expected_sha256:
            raise ValueError("Fixture checksum mismatch")
        saved = json.loads((args.input / "projection.json").read_text(encoding="utf-8"))
        reference = {**saved["qnu_input"], "status": "ready"}
        snapshot_path = reference["path"].split("." + reference["sha256"])[0]
        driver = LocalStorageDriver(str(args.output / "objects"))
        for file, key in (("standard.md", "path"), ("standard.json", "structured_path")):
            await driver.save(reference[key], (args.input / file).read_bytes())
        structured = json.loads((args.input / "standard.json").read_text(encoding="utf-8"))
        raw_evidence = structured.get("document_meta", {}).get("raw_evidence")
        if raw_evidence:
            path = raw_evidence["path"]
            if not path.startswith(snapshot_path + ".") or ".." in path or "\\" in path:
                raise ValueError("Unsafe raw resource reference")
            raw = args.raw_resources.read_bytes() if args.raw_resources else await storage_service.get(path)
            if raw is None or hashlib.sha256(raw).hexdigest() != raw_evidence["sha256"]:
                raise ValueError("Original office resource checksum mismatch")
            await driver.save(path, raw)
        document = await load_document(reference, binding_id=reference["document_id"], revision_id=reference["revision_id"],
                                       origin_hash=source_hash, snapshot_path=snapshot_path, storage=driver)
        # Rebuild through CURRENT projection code; never use a saved answer/gold proposal.
        canonical, artifact = await asyncio.to_thread(project_document, document, input_reference(reference), {})
        (args.output / "canonical.md").write_text(canonical, encoding="utf-8", newline="\n")
        write_json(args.output / "before.json", artifact)
        async with AsyncSessionFactory() as db:
            defaults = (await model_catalog_service.get_system_model_defaults(db)).defaults
            public = (await db.execute(select(ModelProviderConfig.id, ModelProviderConfig.provider_type,
                ModelProviderConfig.model_name, ModelProviderConfig.is_active, ModelProviderConfig.timeout_seconds))).mappings().all()
            report["configuration"] = {"source": "ModelOps DB system defaults; no overrides",
                "preferred_model": defaults.default_chat_model, "preferred_provider": defaults.default_chat_provider_id,
                "chat_mode": defaults.default_chat_mode,
                "chat_chain": [{"provider_id": item.provider_id, "model": item.model_name, "is_active": item.is_active}
                               for item in defaults.chat_combo_chain],
                "providers": [dict(row) for row in public], "deadline_policy": "shared SemanticContextPolicy; no outer timeout override",
                "max_top_level_calls": args.max_calls, "scope": "selected_tables" if args.target_table else "document",
                "transport_retry": "existing ModelOps shared retry budget (1)",
                "fallback": "existing configured routes only; no fallback override",
                "authorization": "user authorized synthetic fixture proposal; configured ModelOps credentials"}
            selected = next((dict(row) for row in public if row["id"] == defaults.default_chat_provider_id), None)
            if selected is not None and not selected["is_active"]:
                report["configuration_blocker"] = "preferred_provider_disabled"
        diagnostics = SafeDiagnostics()
        logger = logging.getLogger("app.modules.modelops.services.inference_service")
        logger.addHandler(diagnostics)
        async def invoke(target):
            async with AsyncSessionFactory() as db:
                async def observe(kind, data):
                    await asyncio.to_thread(write_json, args.output / f"{kind}-{data['call']}.json", data)
                return await propose_source_semantics(db, target, "tenant_qnu", document=document,
                    target_table_ids=args.target_table or None, observer=observe,
                    context_policy={"max_calls": args.max_calls, "max_packet_bytes": args.max_packet_bytes})
        try:
            code, result = await run_proposal(artifact, invoke, proposal_only=args.proposal_only)
        finally:
            logger.removeHandler(diagnostics)
        report.update(result, failures=diagnostics.failures)
        if report.get("configuration_blocker") and code == 1 and not diagnostics.failures:
            report["failure_category"] = "configuration"
            report["provider_inference"] = "NOT_RUN: configured preferred provider disabled"
        if code != 1:
            write_json(args.output / "proposal.json", copy.deepcopy(artifact["semantic_annotations"]))
            write_json(args.output / "pending-projection.json", artifact)
            write_json(args.output / "policy.json", {"mode": "strict", "publication_enabled": False,
                                                      "reason": "pending human review; no source persistence"})
            from app.modules.knowledge.services.semantic_evidence import source_identity
            responses = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(args.output.glob("response-*.json"))]
            checkpoint = {"status": report["status"], "source": source_identity(artifact),
                "fixture_sha256": source_hash, "proposal_hash": report["proposal_hash"],
                "input_hash": artifact["semantic_annotations"]["input_hash"], "scope": report["context_summary"]["scope"],
                "target_table_ids": args.target_table, "human_approved": False, "source_applied": False,
                "files": {name: hashlib.sha256((args.output/name).read_bytes()).hexdigest()
                    for name in ("proposal.json", "pending-projection.json", "policy.json")},
                "calls": [{key: response.get(key) for key in ("call", "context_id", "packet_sha256", "schema_hash",
                    "selector_contract", "selector_version", "policy_sha256", "policy")} for response in responses],
                "continuation": "Review this exact pending proposal using existing source-bound decisions; never regenerate it to resume or auto-approve. This is an offline checkpoint, not an application job."}
            write_json(args.output / "checkpoint.json", checkpoint)
    except Exception as exc:
        code = 1
        report.update(error_code=getattr(exc, "code", type(exc).__name__))
        reason = (getattr(exc, "details", None) or {}).get("reason")
        if reason:
            report["validation_reason"] = reason
    finally:
        await engine.dispose()
    report["exit_code"] = code
    write_json(args.output / "report.json", report)
    print(json.dumps(report, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    # Suppress arbitrary provider logs; collect only allowlisted metadata above.
    logging.getLogger().handlers = [logging.NullHandler()]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Authorized offline standard pair directory")
    parser.add_argument("--docx", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True, help="New offline dossier directory")
    parser.add_argument("--raw-resources", type=Path, help="Explicit original Office resource archive, checksum verified")
    parser.add_argument("--proposal-only", action="store_true")
    parser.add_argument("--target-table", action="append", help="Explicit table IDs to analyze; dossier records selected scope")
    parser.add_argument("--max-calls", type=int, default=24, help="Per-run bound, never changes persisted ModelOps defaults")
    parser.add_argument("--max-packet-bytes", type=int, default=48000)
    raise SystemExit(asyncio.run(main(parser.parse_args())))
