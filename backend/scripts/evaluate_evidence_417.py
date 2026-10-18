"""Independent live evaluation from the already extracted FAQ fixture.

Expected answers are stored only in the report, never sent to the assistant.
No upload, OCR, publication, reset or source mutations.
"""

import argparse
import asyncio
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import LLMUsageLog
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.retriever import hybrid_retriever
from scripts.evaluate_admissions_412 import read_trace, save_result


async def evaluate(args):
    fixture = json.loads(Path("storage/admissions_eval412_run2.json").read_text(encoding="utf-8"))
    selected = set(map(int, args.ids.split(","))) if args.ids else None
    cases = [c for c in fixture["cases"] if selected is None or c["id"] in selected]
    output = Path(args.output)
    code_files = sorted([*Path("app/modules/rag").glob("evidence_*.py"),
        Path("app/core/evidence_policy.py"), Path("app/modules/rag/service.py"),
        Path("app/modules/rag/router.py"), Path("app/modules/rag/schemas.py"),
        Path("app/modules/workflows/nodes/citation_guard_node.py"),
        Path("app/modules/workflows/nodes/no_answer_node.py"),
        Path("app/modules/workflows/nodes/output_chat_node.py")])
    code_files += [Path("app/modules/workflows/service.py"), Path("app/modules/workflows/execution_audit.py"),
                   Path("app/modules/workflows/nodes/rag_answer_node.py")]
    code_files += [Path("app/modules/assistants/runtime.py"),
                   Path("app/modules/assistants/services/assistant_chat_service.py"),
                   Path("app/modules/assistants/services/assistant_rag_chat.py")]
    code_fingerprint = hashlib.sha256(b"".join(p.read_bytes() for p in code_files)).hexdigest()
    report = json.loads(output.read_text(encoding="utf-8")) if args.resume and output.exists() else {
        "started_at": datetime.now(UTC).isoformat(), "document": fixture["document"],
        "document_sha256": fixture["document_sha256"], "cases": cases, "results": [],
        "method": "Original independent questions; expected answers never included in requests; statuses are not accuracy."}
    if report.get("code_fingerprint") not in (None, code_fingerprint):
        raise ValueError("Cannot resume results from a different evidence runtime")
    report["code_fingerprint"] = code_fingerprint
    async with httpx.AsyncClient(timeout=130, trust_env=False) as client:
        response = await client.get(args.base + "/assistants/admissions")
        response.raise_for_status()
        assistant = response.json()
        report["assistant"] = assistant
        async with AsyncSessionFactory() as db:
            snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant["collection_id"])
            blocks = await load_published_blocks(db, snapshot)
            report["publication"] = {"snapshot": snapshot.model_dump(mode="json"), "fingerprint": snapshot.cache_fingerprint(),
                "sources": list({b.source_revision_id: {"binding": b.binding_id, "index": b.index_revision_id,
                    "source": b.source_revision_id, "title": b.title, "hash": b.canonical_hash} for b in blocks}.values())}
        config_fingerprint = hashlib.sha256(json.dumps(assistant["config"], sort_keys=True).encode()).hexdigest()
        if report.get("configuration_fingerprint") not in (None, config_fingerprint):
            raise ValueError("Cannot resume after an assistant configuration change")
        report["configuration_fingerprint"] = config_fingerprint
        completed = {(r["id"], r["route"]) for r in report["results"]}
        save_result(output, report)
        for case in cases:
            for route in args.routes.split(","):
                if (case["id"], route) in completed:
                    continue
                start = time.monotonic()
                conversation = f"eval417_{uuid.uuid4().hex[:16]}"
                item = {"id": case["id"], "question": case["question"], "route": route, "conversation_id": conversation}
                try:
                    if route in {"dag", "chat"}:
                        endpoint = "/assistants/admissions/chat"
                        body = {"message": case["question"], "conversation_id": conversation}
                    else:
                        endpoint = "/rag/ask"
                        body = {"question": case["question"], "collection_id": assistant["collection_id"],
                            "module_code": "admissions", "assistant_code": "admissions",
                            "retrieval_snapshot": snapshot.model_dump(mode="json"), "conversation_id": conversation}
                    result = await client.post(args.base + endpoint, json=body)
                    item.update(http=result.status_code, response=result.json())
                    if item["response"].get("execution_id"):
                        item["trace"] = await read_trace(item["response"]["execution_id"])
                except httpx.ConnectError as exc:
                    item.update(error=f"{type(exc).__name__}: {exc}",
                        elapsed_seconds=round(time.monotonic() - start, 2), failure_kind="service_connection")
                    report["results"].append(item)
                    report.update(interrupted_at=datetime.now(UTC).isoformat(),
                        interruption_reason="Service connection unavailable; remaining cases were not attempted.")
                    save_result(output, report)
                    print(json.dumps({"stopped": True, "id": case["id"], "error": item["error"]}), flush=True)
                    await engine.dispose()
                    return
                except Exception as exc:
                    item["error"] = f"{type(exc).__name__}: {exc}"
                item["elapsed_seconds"] = round(time.monotonic() - start, 2)
                async with AsyncSessionFactory() as db:
                    usage = (await db.execute(select(LLMUsageLog).where(LLMUsageLog.conversation_id == conversation))).scalars().all()
                    item["served_models"] = [{"provider": u.provider, "model": u.model_name, "fallback": u.is_fallback,
                        "status": u.status, "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
                        "latency_ms": u.latency_ms, "cost_usd": u.cost_usd} for u in usage]
                report["results"].append(item)
                save_result(output, report)
                print(json.dumps({"id": case["id"], "route": route, "http": item.get("http"),
                    "status": item.get("response", {}).get("status"), "error": item.get("error"),
                    "seconds": item["elapsed_seconds"]}), flush=True)
                if (item.get("response", {}).get("error_code") or item.get("response", {}).get("code")) in {"QUOTA_EXCEEDED", "TENANT_BLOCKED"}:
                    report.update(interrupted_at=datetime.now(UTC).isoformat(),
                        interruption_reason="Tenant policy blocked the run; remaining cases were not attempted.")
                    save_result(output, report)
                    await engine.dispose()
                    return
        final = await client.get(args.base + "/assistants/admissions")
        final.raise_for_status()
        report["configuration_unchanged"] = final.json()["updated_at"] == assistant["updated_at"]
        async with AsyncSessionFactory() as db:
            final_snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant["collection_id"])
            report["publication_unchanged"] = final_snapshot.cache_fingerprint() == snapshot.cache_fingerprint()
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["code_unchanged"] = code_fingerprint == hashlib.sha256(b"".join(p.read_bytes() for p in code_files)).hexdigest()
        save_result(output, report)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids")
    parser.add_argument("--routes", default="dag")
    parser.add_argument("--output", default="storage/admissions_eval417.json")
    parser.add_argument("--base", default="http://localhost:8001/platform/v1alpha1")
    parser.add_argument("--resume", action="store_true")
    asyncio.run(evaluate(parser.parse_args()))
