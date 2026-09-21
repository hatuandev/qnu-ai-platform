"""RAG Answer Node Handler — Queries Hybrid RAG and Fact Layer."""

from __future__ import annotations

import logging

from app.core.exceptions import AppException
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

# Official collections kept for backward compatibility with the 5 seeded workflows.
# New assistants must provide explicit collection_id via profile or node config.
OFFICIAL_MODULE_COLLECTIONS: dict[str, str] = {
    "admissions": "col_admissions",
    "regulations": "col_regulations",
    "library": "col_library",
    "drafting": "col_drafting",
    "question_bank": "col_question_bank",
}


class RAGAnswerNodeHandler(BaseNodeHandler):
    """Executes RAG Pipeline to retrieve facts and generate verified response."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        query = (
            context.node_data.get("normalized_query")
            or context.node_data.get("user_message")
            or context.inputs.get("message", "")
        )
        config = node_spec.config or {}

        profile = context.assistant_profile
        module_code = (
            config.get("module_code")
            or (profile.assistant_code if profile else None)
            or "general"
        )
        collection_id = (profile.collection_id if profile else None) or config.get(
            "collection_id"
        )
        if not collection_id:
            fallback_collection = OFFICIAL_MODULE_COLLECTIONS.get(module_code)
            if fallback_collection:
                logger.debug(
                    "RAG node '%s' using conventional collection '%s' for module '%s'",
                    node_spec.id,
                    fallback_collection,
                    module_code,
                )
                collection_id = fallback_collection
        if not collection_id:
            raise AppException(
                "Node RAG thiếu collection_id. Hãy gắn kho tri thức cho trợ lý hoặc cấu hình collection_id trên node.",
                code="workflow_missing_collection",
                status_code=422,
                details={"node_id": node_spec.id, "workflow_id": context.workflow_id},
            )

        primary_model = (
            profile.model_policy.primary_model
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else None
        )
        fallback_model = (
            profile.model_policy.fallback_model
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else None
        )
        thinking_budget = (
            getattr(profile.model_policy, "thinking_budget", 0)
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else config.get("thinking_budget", 0)
        )

        ask_req = AskRequest(
            question=query,
            collection_id=collection_id,
            module_code=module_code,
            conversation_id=context.conversation_id,
            tenant_id=context.tenant_id or "tenant_qnu",
            system_prompt=profile.system_prompt if profile else config.get("system_prompt"),
            temperature=profile.model_policy.temperature if profile else config.get("temperature", 0.2),
            max_tokens=min(profile.model_policy.max_tokens, 8192) if profile else config.get("max_tokens", 2000),
            thinking_budget=thinking_budget,
            preferred_model_name=primary_model,
            fallback_model=fallback_model,
            history=context.inputs.get("conversation_history"),
        )

        if context.db:
            rag_res = await rag_service.ask(context.db, ask_req)
            answer_text = rag_res.answer
            citations = [c.model_dump() for c in rag_res.citations]
            status = rag_res.status
            suggested_questions = getattr(rag_res, "suggested_questions", [])
        else:
            answer_text = f"Dựa trên tài liệu chính thức của ĐH Quy Nhơn cho câu hỏi: '{query}'."
            citations = []
            status = "answered"
            suggested_questions = []

        context.node_data["rag_answer"] = answer_text
        context.node_data["citations"] = citations
        context.node_data["rag_status"] = status
        context.node_data["suggested_questions"] = suggested_questions

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "answer": answer_text,
                "citations": citations,
                "status": status,
                "suggested_questions": suggested_questions,
            },
        )
