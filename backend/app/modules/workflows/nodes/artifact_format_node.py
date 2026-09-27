"""Resolve user-requested artifact formats for administrative draft output."""

from __future__ import annotations

from app.core.exceptions import AppException
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

_ALLOWED_FORMATS = frozenset({"docx", "pdf"})


class ArtifactFormatNodeHandler(BaseNodeHandler):
    """Normalize and validate DOCX/PDF output selection before the export node."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        requested = context.inputs.get("format") or config.get("default_format", "docx,pdf")
        if isinstance(requested, str):
            formats = [item.strip().lower() for item in requested.split(",") if item.strip()]
        elif isinstance(requested, list):
            formats = [str(item).strip().lower() for item in requested if str(item).strip()]
        else:
            formats = ["docx", "pdf"]

        if not formats or "both" in formats:
            formats = ["docx", "pdf"]
        unsupported = sorted(set(formats) - _ALLOWED_FORMATS)
        if unsupported:
            raise AppException(
                "Trợ lý soạn thảo hiện chỉ xuất được DOCX và PDF.",
                code="drafting_format_not_supported",
                status_code=422,
                details={"unsupported_formats": unsupported},
            )

        normalized = list(dict.fromkeys(formats))
        context.node_data["artifact_formats"] = normalized
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"formats": normalized},
        )
