"""Resolve the same persisted evidence policy for direct RAG and assistant DAG."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.evidence_policy import EvidencePolicy
from app.core.exceptions import AppException
from app.modules.rag.schemas import AskRequest


async def resolve_evidence_request(db: AsyncSession, req: AskRequest) -> tuple[AskRequest, EvidencePolicy]:
    runtime = req.runtime_policy or {}
    if not runtime:
        from app.modules.knowledge.models import KnowledgeCollection

        try:
            collection = await db.get(KnowledgeCollection, req.collection_id)
        except Exception as exc:
            raise AppException("Không thể đọc chính sách chứng cứ của kho tri thức.",
                code="EVIDENCE_POLICY_UNAVAILABLE", status_code=503) from exc
        metadata = getattr(collection, "collection_metadata", None)
        if not isinstance(metadata, dict) or not metadata.get("evidence_answers_enabled"):
            return req, EvidencePolicy()
        if collection.tenant_id != req.tenant_id or collection.workspace_id != req.workspace_id:
            raise AppException("Không thể xác nhận chính sách chứng cứ trong phạm vi truy cập.",
                code="EVIDENCE_POLICY_UNAVAILABLE", status_code=503)
        # Lazy import avoids the assistant/RAG package initialization cycle.
        from app.modules.assistants.models import AssistantModel

        try:
            record = (await db.execute(select(AssistantModel).where(
                AssistantModel.code == (req.assistant_code or collection.module_code),
                AssistantModel.collection_id == req.collection_id,
                AssistantModel.tenant_id == req.tenant_id,
                AssistantModel.is_active.is_(True)))).scalar_one_or_none()
        except Exception as exc:
            raise AppException("Không thể đọc cấu hình chứng cứ của trợ lý.",
                code="EVIDENCE_POLICY_UNAVAILABLE", status_code=503) from exc
        if record is None or not isinstance(record.config, dict):
            raise AppException("Không thể xác nhận chính sách chứng cứ của trợ lý cho kho này.", code="EVIDENCE_POLICY_UNAVAILABLE", status_code=503)
        if record is not None and isinstance(record.config, dict):
            runtime = record.config
            if not EvidencePolicy.model_validate((runtime.get("knowledge_policy") or {}).get("evidence_policy") or {}).enabled:
                raise AppException("Kho yêu cầu chứng cứ nhưng trợ lý chưa có chính sách kiểm chứng hợp lệ.",
                    code="EVIDENCE_POLICY_UNAVAILABLE", status_code=503)
            models = runtime.get("model_policy") or {}
            req = req.model_copy(update={
                "runtime_policy": runtime, "assistant_code": record.code,
                "assistant_revision": record.updated_at.isoformat(),
                "preferred_provider_id": req.preferred_provider_id or models.get("preferred_provider_id"),
                "preferred_model_name": req.preferred_model_name or models.get("primary_model"),
                "fallback_provider_id": req.fallback_provider_id or models.get("fallback_provider_id"),
                "fallback_model": req.fallback_model or models.get("fallback_model"),
                "max_tokens": models.get("max_tokens", req.max_tokens),
                "reranker_policy": req.reranker_policy or (runtime.get("knowledge_policy") or {}).get("reranker_policy"),
            })
    raw = (runtime.get("knowledge_policy") or {}).get("evidence_policy") or {}
    return req, EvidencePolicy.model_validate(raw)


def assistant_scope(req: AskRequest) -> dict:
    """Persisted scope disambiguates the target institution; never supplies facts."""
    scope = (req.runtime_policy or {}).get("persona_scope") or {}
    return {"persona": str(scope.get("persona") or "")[:2000],
            "allowed_topics": [str(topic)[:200] for topic in (scope.get("allowed_topics") or [])[:20]]}


def no_answer_message(req: AskRequest) -> str:
    guardrails = (req.runtime_policy or {}).get("guardrails") or {}
    return guardrails.get("no_answer_message") or (
        "Trong nguồn đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho thông tin bạn hỏi. "
        "Vui lòng liên hệ đơn vị phụ trách của Trường Đại học Quy Nhơn để được xác nhận.")
