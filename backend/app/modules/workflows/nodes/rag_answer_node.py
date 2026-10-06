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

        model_policy = getattr(profile, "model_policy", None) if profile else None
        primary_model = (
            model_policy.primary_model
            if model_policy
            else (config.get("preferred_model_name") or config.get("model"))
        )
        fallback_model = (
            model_policy.fallback_model
            if model_policy
            else (config.get("fallback_model_name") or config.get("fallback_model"))
        )
        thinking_budget = (
            getattr(model_policy, "thinking_budget", 0)
            if model_policy
            else config.get("thinking_budget", 0)
        )
        preferred_provider_id = (
            getattr(model_policy, "preferred_provider_id", None)
            if model_policy
            else config.get("preferred_provider_id")
        )

        ask_req = AskRequest(
            question=query,
            collection_id=collection_id,
            module_code=module_code,
            conversation_id=context.conversation_id,
            tenant_id=context.tenant_id or "tenant_qnu",
            system_prompt=profile.system_prompt if profile else config.get("system_prompt"),
            temperature=model_policy.temperature if model_policy else config.get("temperature", 0.2),
            max_tokens=min(model_policy.max_tokens, 8192) if model_policy else config.get("max_tokens", 2000),
            thinking_budget=thinking_budget,
            preferred_model_name=primary_model,
            preferred_provider_id=preferred_provider_id,
            fallback_model=fallback_model,
            history=context.inputs.get("conversation_history") or context.inputs.get("history"),
            reranker_policy=(
                getattr(getattr(profile, "knowledge_policy", None), "reranker_policy", None)
                if hasattr(getattr(profile, "knowledge_policy", None), "reranker_policy")
                else (config.get("knowledge_policy", {}).get("reranker_policy") if isinstance(config.get("knowledge_policy"), dict) else None)
            ),
        )

        # Universal Agentic Consulting & Artifact Generation
        from app.modules.tools.consulting_dispatcher import consulting_dispatcher

        dispatch_res = await consulting_dispatcher.dispatch(
            module_code=module_code,
            user_message=query,
            history=context.inputs.get("conversation_history"),
            collection_id=collection_id,
            db=context.db,
            preferred_model_name=primary_model,
            fallback_model=fallback_model,
        )
        if dispatch_res.get("has_agentic_guidance"):
            guidance = dispatch_res.get("guidance_context", "")
            if guidance:
                base_prompt = ask_req.system_prompt or ""
                ask_req.system_prompt = f"{base_prompt}\n\n[DỮ LIỆU ĐỐI SOÁT & TƯ VẤN CHUYÊN BIỆT TỪ FACT LAYER]:\n{guidance}"
                context.node_data["guidance_context"] = guidance

        artifacts = dispatch_res.get("artifacts", [])
        if artifacts:
            context.node_data["artifacts"] = artifacts
            context.outputs["artifacts"] = artifacts

        if context.db:
            rag_res = await rag_service.ask(context.db, ask_req)
            answer_text = rag_res.answer
            citations = [c.model_dump() for c in rag_res.citations]
            status = rag_res.status
            suggested_questions = getattr(rag_res, "suggested_questions", [])
            retrieved_contexts = getattr(rag_res, "contexts", [])
            context.node_data["contexts"] = retrieved_contexts
            context.outputs["contexts"] = retrieved_contexts
            facts_used = getattr(rag_res, "facts_used", [])
            if facts_used:
                context.node_data["facts_used"] = facts_used
                fact_lines: list[str] = [
                    "| Thực thể / Ngành | Thuộc tính | Giá trị dữ liệu |",
                    "| --- | --- | --- |",
                ]
                for item in facts_used:
                    if isinstance(item, dict):
                        ent = item.get("entity") or item.get("entity_name") or ""
                        attr = item.get("attr") or item.get("attribute_name") or ""
                        val = item.get("val") or item.get("attribute_value") or ""
                    else:
                        ent = getattr(item, "entity_name", "")
                        attr = getattr(item, "attribute_name", "")
                        val = getattr(item, "attribute_value", "")
                    fact_lines.append(f"| {ent} | {attr} | **{val}** |")
                context.node_data["fact_markdown"] = "\n".join(fact_lines)
        else:
            answer_text = f"Dựa trên tài liệu chính thức của ĐH Quy Nhơn cho câu hỏi: '{query}'."
            citations = []
            status = "answered"
            suggested_questions = []
            retrieved_contexts = []

        context.node_data["rag_answer"] = answer_text
        context.node_data["citations"] = citations
        context.node_data["rag_status"] = status
        context.node_data["suggested_questions"] = suggested_questions

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "answer": answer_text,
                "response": answer_text,
                "citations": citations,
                "status": status,
                "suggested_questions": suggested_questions,
                "artifacts": artifacts,
                "contexts": retrieved_contexts,
            },
        )
