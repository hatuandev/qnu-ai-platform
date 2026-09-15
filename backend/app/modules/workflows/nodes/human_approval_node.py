"""Human Approval Node Handler — Enforces Human-in-the-Loop checkpoints."""

from __future__ import annotations

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec


class HumanApprovalNodeHandler(BaseNodeHandler):
    """Halts execution until human supervisor provides approval token."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        is_approved = context.inputs.get("is_approved", False)
        config = node_spec.config or {}

        if not is_approved:
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="paused_for_approval",
                output={
                    "checkpoint": node_spec.id,
                    "action_required": config.get(
                        "description", "Cần cán bộ chuyên môn phê duyệt trước khi ban hành."
                    ),
                    "pending_approval": True,
                },
            )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"approved_by": context.inputs.get("approved_by", "admin")},
        )
