"""Live smoke evaluation: read publication state; exercise RAG and assistant DAG.

No reparse, publish, configuration writes or deletions. Chat may create its normal
conversation/trace/usage/cache records. Outputs JSON lines, no credentials.
"""

import asyncio
import json
import sys

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.workflows.models import WorkflowNodeExecution

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8001/platform/v1alpha1"


def emit(data):
    print(json.dumps(data, ensure_ascii=False), flush=True)


async def main():
    async with httpx.AsyncClient(timeout=100, trust_env=False) as client:
        assistant = (await client.get(BASE + "/assistants/admissions")).json()
        collection_id = assistant["collection_id"]
        async with AsyncSessionFactory() as db:
            bindings = list((await db.execute(select(KnowledgeBinding).where(
                KnowledgeBinding.collection_id == collection_id,
                KnowledgeBinding.status == "active",
            ))).scalars().all())
            for binding in bindings:
                revision = await db.get(KnowledgeSourceRevision, binding.active_source_revision_id)
                artifact = (revision.parse_provenance or {}).get("structured_artifact", {})
                emit({"kind": "source", "binding": binding.id, "index": binding.active_index_revision_id,
                      "title": (revision.snapshot_metadata or {}).get("title"), "revision": revision.id,
                      "artifact_version": artifact.get("version"), "draft_facts": len(artifact.get("facts", []))})
                for term in ("4800", "4.800", "IELTS", "7480201", "02/7", "cảnh báo học tập"):
                    text = revision.canonical_markdown or ""
                    start = text.casefold().find(term.casefold())
                    if start >= 0:
                        emit({"kind": "evidence", "binding": binding.id, "term": term,
                              "excerpt": text[max(0, start - 150):start + 650]})
        questions = [
            ("quota", "Tổng chỉ tiêu tuyển sinh đại học năm 2026 là bao nhiêu?"),
            ("ielts", "IELTS 6.0 được quy đổi thành bao nhiêu điểm tiếng Anh khi xét tuyển năm 2026?"),
            ("cutoffs", "Điểm chuẩn ngành Công nghệ thông tin năm 2024 và năm 2025 theo kết quả thi THPT là bao nhiêu?"),
            ("registration", "Thời gian đăng ký xét tuyển đại học năm 2026 là từ ngày nào đến ngày nào?"),
            ("missing", "Điểm chuẩn chính thức ngành Công nghệ thông tin năm 2026 là bao nhiêu?"),
            ("greeting", "Chào bạn!"),
        ]
        if len(sys.argv) > 1:
            requested = set(sys.argv[1].split(","))
            questions = [item for item in questions if item[0] in requested]
        if len(sys.argv) > 1 and "training" in requested:
            questions.append(("training", "Theo Điều 19 quy chế đào tạo đại học áp dụng từ K48, điều kiện cảnh báo học tập mức 1 là gì?"))
        reranker = assistant.get("config", {}).get("knowledge_policy", {}).get("reranker_policy")
        for case, question in questions:
            for route in ("rag", "dag"):
                try:
                    endpoint = "/rag/ask" if route == "rag" else "/assistants/admissions/chat"
                    body = {"collection_id": collection_id, "question": question, "module_code": "admissions",
                            "reranker_policy": reranker} if route == "rag" else {"message": question}
                    response = await client.post(BASE + endpoint, json=body)
                    data = response.json()
                    emit({"kind": "result", "case": case, "route": route, "http": response.status_code,
                          "status": data.get("status"), "answer": data.get("answer"),
                          "contexts": len(data.get("contexts", [])), "citations": [{key: cite.get(key) for key in (
                              "title", "page_number", "binding_id", "index_revision_id", "source_revision_id")}
                              for cite in data.get("citations", [])],
                          "latency_ms": data.get("latency_ms"), "execution_id": data.get("execution_id"),
                          "conversation_id": data.get("conversation_id"), "error": data.get("detail")})
                    if data.get("execution_id"):
                        async with AsyncSessionFactory() as db:
                            nodes = list((await db.execute(select(WorkflowNodeExecution).where(
                                WorkflowNodeExecution.execution_id == data["execution_id"],
                            ))).scalars().all())
                            emit({"kind": "trace", "case": case, "nodes": [{"node": node.node_id,
                                  "type": node.node_type, "status": node.status, "latency_ms": node.latency_ms,
                                  "next_node": (node.output_data or {}).get("next_node"),
                                  "contexts_count": len((node.output_data or {}).get("contexts", [])),
                                  "answer_status": (node.output_data or {}).get("status"),
                                  "is_grounded": (node.output_data or {}).get("is_grounded"),
                                  "unsupported_numbers": (node.output_data or {}).get("unsupported_numbers"),
                                  "normalized_query": (node.output_data or {}).get("normalized_query")} for node in nodes]})
                except Exception as exc:
                    emit({"kind": "error", "case": case, "route": route, "type": type(exc).__name__, "message": str(exc)})


if __name__ == "__main__":
    asyncio.run(main())
