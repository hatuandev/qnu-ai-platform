"""Safe capability audit / real whole-document API generation in an owned test DB.

No review/apply endpoints, shared configuration writes, migrations or publication.
Raw model output stays inside the temporary runtime and is excluded from exports.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import logging
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.chat_capabilities import load_chat_capabilities


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


async def main(args):
    state = json.loads(args.state.read_text(encoding="utf-8"))
    configured = make_url(settings.DATABASE_URL)
    runtime = Path(state["runtime"]).resolve()
    assert settings.ENVIRONMENT == "test" and configured.host in {"127.0.0.1", "localhost", "::1"}
    assert configured.database == state["name"] and configured.database.startswith("qnu_test_context548_")
    assert settings.STORAGE_DRIVER == "local" and Path(settings.LOCAL_STORAGE_PATH).resolve().is_relative_to(runtime)
    assert args.output.resolve().is_relative_to(runtime)
    args.output.mkdir(parents=True, exist_ok=False)
    async with AsyncSessionFactory() as db:
        owner = (await db.execute(text("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"))).scalar()
        assert owner == "context548:" + state["nonce"]
        rows = (await db.scalars(select(ModelProviderConfig))).all()
        audit = []
        for row in rows:
            if row.id == "system_model_defaults": continue
            models = set((row.extra_config or {}).get("chat_request_contracts", {}))
            models.update([row.model_name] if row.model_name else [])
            audit.append({"provider_id": row.id, "endpoint_sha256": hashlib.sha256((row.api_base_url or "").encode()).hexdigest(),
                "models": {model: {key: value for key, value in load_chat_capabilities(row.extra_config, model, row.api_base_url).items()
                    if key in {"json_schema_supported", "json_object_supported", "token_parameter", "temperature_supported"}} for model in sorted(models)}})
        write(args.output/"capabilities.json", {"source": "existing ModelOps registry; test copy from read-only source", "providers": audit,
            "native_schema_enforcement": "NOT_ESTABLISHED by a successful response"})
    if args.action == "capabilities": return 0
    if args.action == "chat": return await probe_chat(args)
    return await api_document(args)


async def probe_chat(args):
    from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
    from app.modules.modelops.service import modelops_service
    from app.modules.modelops.services.model_catalog_service import model_catalog_service
    async with AsyncSessionFactory() as db:
        defaults = (await model_catalog_service.get_system_model_defaults(db)).defaults
        provider_id, model_name = defaults.default_chat_provider_id, defaults.default_chat_model
        if args.chat_model:
            matches = [item for item in defaults.chat_combo_chain if item.model_name == args.chat_model and item.is_active]
            assert len(matches) == 1, "Need one active model in the existing configured chain"
            provider_id, model_name = matches[0].provider_id, matches[0].model_name
        response = await modelops_service.generate(db, LLMGenerateRequest(
            messages=[ChatMessage(role="user", content=args.chat_message)],
            preferred_provider_id=provider_id, preferred_model_name=model_name,
            max_tokens=args.chat_max_tokens, temperature=0, thinking_budget=0))
        passed = bool(response.content.strip()) and response.finish_reason == "stop" and not response.is_fallback and response.provider_id == provider_id and response.requested_model == model_name
        report = {"status": "PROVIDER_RESPONDED", "scope": "minimal chat only; not semantic extraction",
            "requested_model": model_name, "model": response.model, "provider_id": response.provider_id,
            "is_fallback": response.is_fallback, "finish_reason": response.finish_reason,
            "prompt_tokens": response.prompt_tokens, "completion_tokens": response.completion_tokens,
            "latency_ms": response.latency_ms, "response_sha256": hashlib.sha256(response.content.encode()).hexdigest(),
            "returned_exact_ok": response.content.strip() == "OK", "fallback_configured_for_this_probe": False,
            "requested_max_tokens": args.chat_max_tokens, "checks_passed": passed,
            "source_applied": False, "human_approved": False, "exit_code": 0 if passed else 1}
        write(args.output/"report.json", report)
        print(json.dumps(report))
        return report["exit_code"]


async def api_document(args):
    import httpx
    from verify_semantic_modelops import run_proposal

    from app.core.database import get_db
    from app.core.exceptions import AppException
    from app.main import app
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.knowledge.models import (
        KnowledgeBinding,
        KnowledgeCollection,
        KnowledgeSourceRevision,
    )
    from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
    from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
    from app.modules.knowledge.services.qnu_docx_artifacts import build_qnu_markdown_artifact
    from app.modules.knowledge.services.qnu_serving import prepare_standard_revision
    from app.modules.knowledge.services.source_extraction import SourceExtraction
    from app.modules.modelops.service import modelops_service
    from app.modules.modelops.services.output_contract import contract_schemas, schema_hash

    fixture = ROOT/"docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx"
    data = fixture.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    assert checksum == "58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274"
    parsed = await DoclingOfficeParser("docx").parse(data, fixture.name)
    document = build_qnu_structured_document(parsed.docling_document, filename=fixture.name, sha256=checksum,
        header_evidence=parsed.docx_header_evidence, source_evidence=parsed.docx_source_evidence)
    async with AsyncSessionFactory() as db:
        collection = KnowledgeCollection(name="JSON contract549 SYNTHETIC TEST", module_code="json549_"+uuid4().hex[:12])
        db.add(collection); await db.flush()
        binding = KnowledgeBinding(collection_id=collection.id, status="pending")
        db.add(binding); await db.flush()
        revision = KnowledgeSourceRevision(id="ks_rev_"+uuid4().hex[:12], binding_id=binding.id, revision_no=1,
            origin_document_id="SYNTHETIC-json549", origin_file_hash=checksum, snapshot_storage_path=f"snapshots/{collection.id}/{binding.id}/source.docx",
            snapshot_metadata={}, parse_provenance={}, status="review_required")
        reference = await build_qnu_markdown_artifact(extraction=SourceExtraction(parsed.raw_text, 0,
            qnu_document=document, office_resources=parsed.docx_source_evidence["resources"]), document_id=binding.id,
            revision_id=revision.id, title=None, snapshot_path=revision.snapshot_storage_path)
        assert reference["status"] == "ready"
        revision.snapshot_metadata = {"qnu_markdown": reference}
        await prepare_standard_revision(revision)
        db.add(revision); await db.commit(); await db.refresh(revision)
        collection_id, binding_id, revision_id = collection.id, binding.id, revision.id
        artifact = copy.deepcopy(revision.parse_provenance["structured_artifact"])
    original_generate = modelops_service.generate
    original_send = httpx.AsyncClient.send
    http_errors = []
    async def observed_send(client, request, **kwargs):
        response = await original_send(client, request, **kwargs)
        if request.url.path.endswith("/chat/completions") and response.status_code >= 400:
            await response.aread()
            try: error = response.json().get("error", {})
            except (ValueError, AttributeError): error = {}
            message = str(error.get("message", "")) if isinstance(error, dict) else ""
            # Numeric window diagnostics only; never persist arbitrary echoed text.
            http_errors.append({"status": response.status_code,
                "endpoint_sha256": hashlib.sha256(str(request.url).encode()).hexdigest(),
                "model": json.loads(request.content).get("model"),
                "body_sha256": hashlib.sha256(response.content).hexdigest(),
                "maximum_context_tokens": next(iter(re.findall(r"maximum context length is (\d+)", message)), None),
                "input_tokens": next(iter(re.findall(r"prompt contains (?:at least )?(\d+) input tokens", message)), None),
                "input_tokens_is_lower_bound": "prompt contains at least" in message})
        return response
    attempts = []
    async def observed_generate(db, request):
        packet = json.loads(request.messages[1].content)
        item = {"logical_call": len(attempts)+1, "packet_sha256": schema_hash(packet), "context_id": packet["context_id"],
            "source": packet["source"], "requested_contract": request.output_contract.model_dump(),
            "schema_sha256": schema_hash(contract_schemas(request.output_contract.name)[1])}
        attempts.append(item)
        try:
            response = await original_generate(db, request)
            item.update(provider=response.provider, model=response.model, output_contract=response.output_contract,
                metadata=response.response_metadata, finish_reason=response.finish_reason, attempt_trace=response.attempt_trace,
                prompt_tokens=response.prompt_tokens, completion_tokens=response.completion_tokens, latency_ms=response.latency_ms)
            write(args.output/f"response-{len(attempts)}.json", {"content": response.content, "trace": item})
            return response
        except AppException as exc:
            item.update(error_code=exc.code, details=exc.details)
            raise
    async def test_db():
        async with AsyncSessionFactory() as db: yield db
    async def test_generation_actor():
        return AuthActor(actor_id="TEST-generation549", username="TEST-generation549", permissions=["ai.knowledge.update", "ai.knowledge.view"])
    async def invoke(target):
        path = f"/platform/v1alpha1/knowledge/collections/{collection_id}/sources/{binding_id}/revisions/{revision_id}/semantic-proposals"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(path)
        if response.status_code != 200:
            body = response.json()
            raise AppException("API verification did not produce a proposal", code=body.get("code", "API_GENERATION_FAILED"),
                status_code=response.status_code, details=body.get("details", {}))
        async with AsyncSessionFactory() as db:
            revision = await db.get(KnowledgeSourceRevision, revision_id)
            target.update(copy.deepcopy(revision.parse_provenance["structured_artifact"]))
        return target["semantic_annotations"]
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_actor] = test_generation_actor
    modelops_service.generate = observed_generate
    httpx.AsyncClient.send = observed_send
    started = time.perf_counter()
    try:
        code, report = await run_proposal(artifact, invoke)
    finally:
        modelops_service.generate = original_generate
        httpx.AsyncClient.send = original_send
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_actor, None)
    report.update(real_provider=True, scope="document", api_auth="TEST generation actor in isolated ASGI application; no human review", fixture_sha256=checksum,
        logical_calls=len(attempts), packets_seen=len({item["context_id"] for item in attempts}), attempts=attempts,
        elapsed_ms=(time.perf_counter()-started)*1000, http_error_diagnostics=http_errors, exit_code=code)
    write(args.output/"report.json", report)
    if code != 1: write(args.output/"proposal.json", artifact["semantic_annotations"])
    print(json.dumps({"status": report["status"], "calls": len(attempts), "exit_code": code}))
    return code


if __name__ == "__main__":
    logging.getLogger().handlers = [logging.NullHandler()]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capabilities", "api", "chat"])
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chat-message", default="Return only OK. This is a connection test.")
    parser.add_argument("--chat-max-tokens", type=int, default=512)
    parser.add_argument("--chat-model", help="Optional active model from the copied configured chain; no default changes")
    args = parser.parse_args()
    async def execute():
        try: return await main(args)
        except Exception as exc:
            result = {"status": "BLOCKED", "stage": "verification_setup", "error_type": type(exc).__name__,
                "code": getattr(exc, "code", None), "source_applied": False, "human_approved": False, "exit_code": 1}
            if args.output.is_dir(): write(args.output/"report.json", result)
            print(json.dumps(result))
            return 1
        finally: await engine.dispose()
    code = asyncio.run(execute())
    raise SystemExit(code)
