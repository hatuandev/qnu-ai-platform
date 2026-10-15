"""Six fresh chat controls for the published 2025 handbook; no source mutations."""

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
from scripts.evaluate_admissions_412 import save_result

CASES = [
    {"id": 2001, "question": "Theo cẩm nang tuyển sinh năm 2025, ngành Sư phạm Toán học học bao lâu và ra trường có thể làm công việc gì?"},
    {"id": 2002, "question": "Theo cẩm nang tuyển sinh năm 2025, ngành Kỹ thuật phần mềm học bao lâu và có những cơ hội việc làm nào?"},
    {"id": 2003, "question": "Năm 2025, ngành Sư phạm Lịch sử có những tổ hợp môn xét tuyển nào?"},
    {"id": 2004, "question": "Theo cẩm nang tuyển sinh năm 2025, xét học bạ sử dụng kết quả lớp nào?"},
    {"id": 2005, "question": "Năm 2026 xét học bạ của QNU chỉ dùng điểm lớp 12 như cẩm nang 2025 có đúng không?"},
    {"id": 2006, "question": "Có thể dùng các tổ hợp môn trong cẩm nang tuyển sinh QNU năm 2025 để khẳng định chắc chắn tổ hợp xét tuyển năm 2026 không?"},
]


def runtime_fingerprint():
    paths = sorted(Path("app/modules/rag").glob("evidence_*.py"))
    paths += [Path(path) for path in [
        "app/core/evidence_policy.py", "app/modules/rag/service.py",
        "app/modules/rag/schemas.py", "app/modules/rag/retriever.py",
        "app/modules/assistants/services/assistant_chat_service.py",
        "app/modules/assistants/services/assistant_rag_chat.py",
    ]]
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


async def evaluate(output):
    report = {"started_at": datetime.now(UTC).isoformat(), "cases": CASES, "results": [],
              "method": "Fresh handbook and year controls; chat requests contain questions only, no expected answers."}
    report["code_fingerprint"] = runtime_fingerprint()
    try:
        async with httpx.AsyncClient(timeout=130, trust_env=False) as client:
            url = "http://localhost:8001/platform/v1alpha1/assistants/admissions"
            response = await client.get(url)
            response.raise_for_status()
            assistant = response.json()
            report["assistant"] = {key: assistant[key] for key in ["collection_id", "tenant_id", "updated_at"]}
            report["configuration_fingerprint"] = hashlib.sha256(json.dumps(assistant["config"], sort_keys=True).encode()).hexdigest()
            async with AsyncSessionFactory() as db:
                snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
                blocks = await load_published_blocks(db, snapshot)
            report["publication"] = {"snapshot": snapshot.model_dump(mode="json"), "fingerprint": snapshot.cache_fingerprint(),
                "sources": list({block.source_revision_id: {"source": block.source_revision_id, "title": block.title,
                    "binding": block.binding_id, "index": block.index_revision_id, "hash": block.canonical_hash} for block in blocks}.values())}
            save_result(output, report)
            for case in CASES:
                conversation = "eval447_" + uuid.uuid4().hex[:16]
                item = {**case, "route": "chat", "conversation_id": conversation}
                started = time.monotonic()
                try:
                    response = await client.post(url + "/chat", json={"message": case["question"], "conversation_id": conversation})
                    item.update(http=response.status_code, response=response.json())
                except httpx.HTTPError as exc:
                    item.update(error=str(exc), failure_kind="infrastructure")
                item["elapsed_seconds"] = round(time.monotonic() - started, 2)
                async with AsyncSessionFactory() as db:
                    usage = (await db.execute(select(LLMUsageLog).where(LLMUsageLog.conversation_id == conversation))).scalars().all()
                item["served_models"] = [{"model": row.model_name, "provider": row.provider, "fallback": row.is_fallback,
                    "status": row.status, "prompt_tokens": row.prompt_tokens, "completion_tokens": row.completion_tokens,
                    "latency_ms": row.latency_ms} for row in usage]
                report["results"].append(item)
                save_result(output, report)
                decision = (item.get("response") or {}).get("answer_decision") or {}
                print(json.dumps({"id": case["id"], "http": item.get("http"), "status": decision.get("status"),
                    "seconds": item["elapsed_seconds"], "error": item.get("error")}), flush=True)
                if item.get("error") or item.get("http", 0) >= 500:
                    report["interruption_reason"] = "Infrastructure request failed; remaining controls not attempted."
                    break
            response = await client.get(url)
            response.raise_for_status()
            final = response.json()
            report["configuration_unchanged"] = hashlib.sha256(json.dumps(final["config"], sort_keys=True).encode()).hexdigest() == report["configuration_fingerprint"]
            async with AsyncSessionFactory() as db:
                after = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
            report["publication_unchanged"] = after.cache_fingerprint() == snapshot.cache_fingerprint()
            report["code_unchanged"] = runtime_fingerprint() == report["code_fingerprint"]
            report["finished_at"] = datetime.now(UTC).isoformat()
            save_result(output, report)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("storage/admissions_eval447_camnang6.json"))
    asyncio.run(evaluate(parser.parse_args().output))
