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
        config = node_spec.config or {}
        profile_tools = (
            getattr(context.assistant_profile, "tools", None)
            if context.assistant_profile
            else None
        )
        profile_requires_approval = getattr(
            profile_tools, "human_approval_required", True
        )
        requires_approval = bool(
            config.get("required", profile_requires_approval)
        )
        is_approved = context.inputs.get("is_approved", False)

        if not requires_approval:
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output={"approval_skipped": True, "reason": "assistant_policy"},
            )

        if not is_approved:
            draft = context.node_data.get("draft")
            preview = None
            missing_fields: list[str] = []
            if isinstance(draft, dict):
                preview = {
                    "title": draft.get("title"),
                    "document_type": draft.get("document_type_label")
                    or draft.get("document_type"),
                    "ast": draft.get("ast"),
                }
                missing_fields = list(draft.get("missing_fields") or [])
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="paused_for_approval",
                output={
                    "checkpoint": node_spec.id,
                    "action_required": config.get(
                        "description", "Cần cán bộ chuyên môn phê duyệt trước khi ban hành."
                    ),
                    "pending_approval": True,
                    "preview": preview,
                    "missing_fields": missing_fields,
                },
            )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"approved_by": context.inputs.get("approved_by", "admin")},
        )
