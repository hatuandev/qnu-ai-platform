"""Output Chat Node Handler — Formats final response payload."""

from __future__ import annotations

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


class OutputChatNodeHandler(BaseNodeHandler):
    """Produces the final assistant message for the conversation."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        output_template = config.get("output_template")

        if output_template:
            # Predefined static or greeting template
            final_answer = output_template
            citations = []
            status = "answered"
        else:
            # Derived from upstream RAG / LLM node
            final_answer = (
                context.node_data.get("rag_answer")
                or context.node_data.get("llm_content")
                or "Trợ lý QNU đã xử lý xong yêu cầu của bạn."
            )
            citations = context.node_data.get("citations", [])
            status = context.node_data.get("rag_status", "answered")

        context.outputs["answer"] = final_answer
        context.outputs["citations"] = citations
        context.outputs["status"] = status

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "answer": final_answer,
                "citations": citations,
                "status": status,
            },
        )
