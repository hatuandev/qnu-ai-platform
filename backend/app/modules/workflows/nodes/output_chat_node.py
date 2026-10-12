"""Output Chat Node Handler — Formats final response payload."""

from __future__ import annotations

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.nodes.routed_inputs import routed_payload, routed_text
from app.modules.workflows.schemas import WorkflowNodeSpec


class OutputChatNodeHandler(BaseNodeHandler):
    """Produces the final assistant message for the conversation."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        output_template = config.get("output_template")
        payload = routed_payload(context, node_spec.id)
        has_wired_answer = any(
            key in payload for key in ("answer", "response", "content", "grounded", "input")
        )
        has_wired_answer = has_wired_answer or any(
            key != "input" for key in context.node_inputs.get(node_spec.id, {})
        )

        if output_template:
            # Predefined static or greeting template
            final_answer = output_template
            citations = []
            status = "answered"
        elif has_wired_answer:
            final_answer = routed_text(
                context, node_spec.id, ("answer", "response", "content", "grounded"), ""
            )
            citations = payload.get("citations", [])
            status = payload.get("status", "answered")
        else:
            # Derived from upstream RAG / LLM node
            final_answer = (
                context.node_data.get("rag_answer")
                or context.node_data.get("llm_content")
                or "Trợ lý QNU đã xử lý xong yêu cầu của bạn."
            )
            citations = context.node_data.get("citations", [])
            status = context.node_data.get(
                "assistant_status",
                context.node_data.get("rag_status", "answered"),
            )

        warnings = (
            payload.get("warnings", [])
            if has_wired_answer
            else context.node_data.get("artifact_warnings", [])
        )
        if warnings:
            final_answer = f"{final_answer}\n\nLưu ý: {'; '.join(warnings)}"

        suggested_questions = (
            payload.get("suggested_questions", [])
            if has_wired_answer
            else (
                context.node_data.get("suggested_questions")
                or context.outputs.get("suggested_questions")
                or []
            )
        )
        artifacts = (
            payload.get("artifacts", [])
            if has_wired_answer
            else (context.node_data.get("artifacts") or context.outputs.get("artifacts", []))
        )
        decision = context.node_data.get("answer_decision")
        if decision:
            # A downstream template/model cannot replace a fact-bound decision.
            final_answer = decision["answer"]
            status = "answered" if decision["status"] == "supported" else "insufficient_context"
            citations = context.node_data.get("citations", []) if status == "answered" else []
            context.outputs["answer_decision"] = decision
        context.outputs["answer"] = final_answer
        context.outputs["citations"] = citations
        context.outputs["status"] = status
        context.outputs["suggested_questions"] = suggested_questions
        if has_wired_answer:
            context.outputs["contexts"] = payload.get("contexts", [])
            context.outputs["facts_used"] = payload.get("facts_used", [])
            context.outputs["missing_fields"] = payload.get("missing_fields", [])
        if artifacts or has_wired_answer:
            context.outputs["artifacts"] = artifacts

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "answer": final_answer,
                "answer_decision": decision,
                "citations": citations,
                "status": status,
                "artifacts": artifacts,
                "missing_fields": context.outputs.get("missing_fields", []),
                "warnings": warnings,
                "suggested_questions": suggested_questions,
            },
        )
