"""Sequential live admissions evaluation (82 questions, 4 phases); test-only.

Reads the frozen 82-question fixture, sends each question as a fresh chat
conversation with its own X-Correlation-ID, and saves every result
immediately. No expected answers are sent. No retries. HTTP errors are
recorded and the run continues; only a lost connection stops the run with a
checkpoint. Application behavior is never modified by this script.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import LLMUsageLog, ModelProviderConfig, ProviderApiKey
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.retriever import hybrid_retriever
from scripts.evaluate_admissions_412 import save_result

FIXTURE = Path("storage/admissions_eval412_run2.json")
PHASES = {1: range(1, 21), 2: range(21, 41), 3: range(41, 61), 4: range(61, 83)}


def code_fingerprint() -> str:
    files = sorted([*Path("app/modules/rag").glob("evidence_*.py"),
        Path("app/core/evidence_policy.py"), Path("app/modules/rag/service.py"),
        Path("app/modules/rag/router.py"), Path("app/modules/rag/schemas.py"),
        Path("app/modules/workflows/service.py"), Path("app/modules/workflows/execution_audit.py"),
        Path("app/modules/workflows/nodes/rag_answer_node.py")])
    files += [Path("app/modules/assistants/runtime.py"),
              Path("app/modules/assistants/services/assistant_chat_service.py"),
              Path("app/modules/assistants/services/assistant_rag_chat.py")]
    return hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest()


def git_dirty_files() -> list[str]:
    try:
        out = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=no"],
                             capture_output=True, text=True, timeout=60, check=False)
        return sorted(line[3:] for line in out.stdout.splitlines() if line.strip())
    except Exception as exc:
        return [f"git-status-unavailable: {type(exc).__name__}"]


async def provider_inventory() -> list[dict]:
    async with AsyncSessionFactory() as db:
        providers = (await db.execute(select(ModelProviderConfig))).scalars().all()
        keys = (await db.execute(select(ProviderApiKey))).scalars().all()
    by_provider: dict[str, list] = {}
    for key in keys:
        by_provider.setdefault(key.provider_id, []).append(key)
    inventory = []
    for provider in providers:
        active = [k for k in by_provider.get(provider.id, []) if k.is_active]
        inventory.append({"id": provider.id, "name": provider.name,
                          "provider_type": provider.provider_type, "is_active": provider.is_active,
                          "timeout_seconds": provider.timeout_seconds,
                          "active_key_count": len(active),
                          "active_key_statuses": sorted({k.status for k in active})})
    return inventory


async def evaluate(args: argparse.Namespace) -> None:
    raw = FIXTURE.read_text(encoding="utf-8")
    fixture = json.loads(raw)
    if args.ids:
        wanted = set(args.ids)
    else:
        wanted = set(PHASES[args.phase])
    cases = [c for c in fixture["cases"] if c["id"] in wanted]
    if len(cases) != len(wanted):
        raise ValueError(f"Fixture covers {len(cases)}/{len(wanted)} requested ids")
    output = Path(args.output)
    report = json.loads(output.read_text(encoding="utf-8")) if args.resume and output.exists() else {
        "started_at": datetime.now(UTC).isoformat(),
        "fixture": str(FIXTURE), "fixture_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "phase": args.phase, "requested_ids": sorted(wanted),
        "cases": cases, "results": [],
        "method": "Sequential fresh chat conversations; expected answers never sent; statuses are not accuracy."}
    report["code_fingerprint"] = code_fingerprint()
    report["git_dirty_files"] = git_dirty_files()
    base = args.base
    try:
        async with httpx.AsyncClient(timeout=140, trust_env=False) as client:
            response = await client.get(base + "/assistants/admissions")
            response.raise_for_status()
            assistant = response.json()
            report["assistant"] = {k: assistant[k] for k in ("collection_id", "tenant_id", "updated_at")}
            report["configuration_fingerprint"] = hashlib.sha256(
                json.dumps(assistant["config"], sort_keys=True).encode()).hexdigest()
            report["model_policy"] = (assistant["config"] or {}).get("model_policy")
            report["evidence_policy"] = ((assistant["config"] or {}).get("knowledge_policy") or {}).get("evidence_policy")
            report["provider_inventory"] = await provider_inventory()
            async with AsyncSessionFactory() as db:
                snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
                    db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
                blocks = await load_published_blocks(db, snapshot)
                report["publication"] = {
                    "snapshot_id": snapshot.snapshot_id,
                    "fingerprint": snapshot.cache_fingerprint(),
                    "sources": sorted({b.source_revision_id for b in blocks}),
                    "block_count": len(blocks)}
            save_result(output, report)
            print(json.dumps({"preflight": {"sources": len(report["publication"]["sources"]),
                "providers": len(report["provider_inventory"]),
                "git_dirty": len(report["git_dirty_files"])}}, ensure_ascii=True), flush=True)
            completed = {r["id"] for r in report["results"]}
            save_result(output, report)
            for case in cases:
                if case["id"] in completed:
                    continue
                conversation = f"{args.prefix}_{uuid.uuid4().hex[:16]}"
                correlation = f"{args.prefix}-q{case['id']}-{uuid.uuid4().hex[:8]}"
                item = {"id": case["id"], "question": case["question"], "route": "chat",
                        "conversation_id": conversation, "correlation_id": correlation,
                        "started_at": datetime.now(UTC).isoformat()}
                started = time.monotonic()
                try:
                    result = await client.post(base + "/assistants/admissions/chat",
                        json={"message": case["question"], "conversation_id": conversation},
                        headers={"X-Correlation-ID": correlation})
                    item.update(http=result.status_code, response=result.json(),
                        echoed_correlation_id=result.headers.get("X-Correlation-ID", "không thu thập được"),
                        server_process_time_ms=result.headers.get("X-Process-Time-Ms", "không thu thập được"))
                    payload = item["response"] if isinstance(item["response"], dict) else {}
                    item["rag_direct"] = payload.get("execution_id") is None
                except httpx.ConnectError as exc:
                    item.update(error=f"{type(exc).__name__}: {exc}", failure_kind="infrastructure-connection")
                    item["ended_at"] = datetime.now(UTC).isoformat()
                    item["elapsed_seconds"] = round(time.monotonic() - started, 2)
                    report["results"].append(item)
                    report.update(finished_at=datetime.now(UTC).isoformat(),
                        interruption_reason="Connection lost; checkpoint saved, remaining questions not attempted.")
                    save_result(output, report)
                    print(json.dumps({"stopped": True, "id": case["id"], "error": item["error"]}), flush=True)
                    await engine.dispose()
                    return
                except httpx.TimeoutException as exc:
                    item.update(error=f"{type(exc).__name__}: {exc}", failure_kind="infrastructure-timeout")
                except Exception as exc:
                    item.update(error=f"{type(exc).__name__}: {exc}", failure_kind="technical")
                item["ended_at"] = datetime.now(UTC).isoformat()
                item["elapsed_seconds"] = round(time.monotonic() - started, 2)
                try:
                    async with AsyncSessionFactory() as db:
                        usage = (await db.execute(select(LLMUsageLog).where(
                            LLMUsageLog.conversation_id == conversation))).scalars().all()
                        item["served_models"] = [{"provider": u.provider, "model": u.model_name,
                            "fallback": u.is_fallback, "status": u.status, "prompt_tokens": u.prompt_tokens,
                            "completion_tokens": u.completion_tokens, "latency_ms": u.latency_ms,
                            "cost_usd": u.cost_usd} for u in usage]
                except Exception as exc:
                    item["usage_error"] = f"{type(exc).__name__}: {exc}"
                report["results"].append(item)
                save_result(output, report)
                decision = ((item.get("response") or {}) if isinstance(item.get("response"), dict) else {}).get("answer_decision") or {}
                print(json.dumps({"id": case["id"], "http": item.get("http"),
                    "status": ((item.get("response") or {}) if isinstance(item.get("response"), dict) else {}).get("status"),
                    "decision": decision.get("status"), "reason": decision.get("reason"),
                    "rag_direct": item.get("rag_direct"), "error": item.get("error"),
                    "seconds": item["elapsed_seconds"]}, ensure_ascii=True), flush=True)
            final = await client.get(base + "/assistants/admissions")
            final.raise_for_status()
            report["configuration_unchanged"] = hashlib.sha256(
                json.dumps(final.json()["config"], sort_keys=True).encode()).hexdigest() == report["configuration_fingerprint"]
            async with AsyncSessionFactory() as db:
                after = await hybrid_retriever.resolve_retrieval_snapshot(
                    db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
                report["publication_unchanged"] = after.cache_fingerprint() == report["publication"]["fingerprint"]
            report["code_unchanged"] = code_fingerprint() == report["code_fingerprint"]
            report["finished_at"] = datetime.now(UTC).isoformat()
            save_result(output, report)
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        save_result(output, report)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4], default=1)
    parser.add_argument("--ids", type=int, nargs="*")
    parser.add_argument("--output", type=Path, default=Path("storage/admissions_eval453_phase1_20.json"))
    parser.add_argument("--base", default="http://localhost:8001/platform/v1alpha1")
    parser.add_argument("--prefix", default="eval453")
    parser.add_argument("--resume", action="store_true")
    asyncio.run(evaluate(parser.parse_args()))
