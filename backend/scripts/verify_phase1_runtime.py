"""Live phase-1 verification; no reset, reindex or publication."""

import asyncio
import json
import uuid
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import LLMUsageLog
from app.modules.modelops.services.model_runtime_resolver import model_runtime_resolver
from app.modules.rag.fusion import FusionCandidate
from app.modules.rag.reranker import reranker_client
from app.modules.workflows.models import WorkflowExecution


async def main():
    base = "http://localhost:8001/platform/v1alpha1"
    result = {}
    async with httpx.AsyncClient(timeout=120, trust_env=False) as client:
        assistant_response = await client.get(f"{base}/assistants/admissions")
        assistant_response.raise_for_status()
        assistant = assistant_response.json()
        policy = assistant["config"]["knowledge_policy"]["reranker_policy"]
        async with AsyncSessionFactory() as db:
            runtime = await model_runtime_resolver.resolve(db, "reranker",
                preferred_provider_id=policy["provider_id"], preferred_model_name=policy["model_name"])
        error = None
        try:
            candidates = [FusionCandidate(str(i), "test", content, 0.01) for i, content in enumerate([
                "Trường thông báo lịch đăng ký xét tuyển đại học.",
                "Kết quả tuyển sinh và điểm chuẩn ngành đào tạo.",
                "Dự báo thời tiết có mưa vào buổi chiều."])]
            ranked = await reranker_client._rerank_vllm_or_generic("Lịch đăng ký xét tuyển đại học", candidates, runtime, 3)
            assert len(ranked) == 3 and all(c.relevance_score is not None for c in ranked)
            result["reranker"] = {"provider_id": runtime.provider_id, "model": runtime.model_name,
                "endpoint": runtime.api_base_url, "scores": [{"id": c.chunk_id, "score": c.relevance_score} for c in ranked]}
        except Exception as exc:
            error = exc
            raise
        finally:
            await reranker_client._finish_runtime_key(runtime, error)
        readiness = await client.get(f"{base}/assistants/admissions/readiness")
        readiness.raise_for_status()
        result["readiness"] = readiness.json()
        conversation = f"eval416_{uuid.uuid4().hex[:12]}"
        response = await client.post(f"{base}/assistants/admissions/chat", json={
            "message": "Số điện thoại tư vấn tuyển sinh của Trường Đại học Quy Nhơn là gì?",
            "conversation_id": conversation, "stream": False})
        result["chat"] = {"http_status": response.status_code, "conversation_id": conversation,
                          "response": response.json()}
        async with AsyncSessionFactory() as db:
            usage = (await db.execute(select(LLMUsageLog).where(LLMUsageLog.conversation_id == conversation))).scalars().all()
            result["served_models"] = [{"provider": u.provider, "model": u.model_name,
                                        "fallback": u.is_fallback, "status": u.status} for u in usage]
            execution_id = response.json().get("execution_id")
            execution = await db.get(WorkflowExecution, execution_id) if execution_id else None
            result["workflow"] = {"id": execution_id, "status": execution.status if execution else None,
                                  "nodes": execution.node_execution_count if execution else None}
    Path("storage/phase1_416_live.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
