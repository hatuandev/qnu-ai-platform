"""Chat Input Node Handler — Sanitizes and extracts incoming user query."""

from __future__ import annotations

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


class ChatInputNodeHandler(BaseNodeHandler):
    """Processes incoming chat question from user."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        raw_message = (
            context.inputs.get("message")
            or context.inputs.get("query")
            or context.inputs.get("prompt")
            or ""
        )
        config = node_spec.config or {}

        if config.get("trim", True):
            raw_message = raw_message.strip()

        max_len = config.get("max_length", 10000)
        cleaned_message = raw_message[:max_len]

        context.node_data["user_message"] = cleaned_message
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"message": cleaned_message},
        )
