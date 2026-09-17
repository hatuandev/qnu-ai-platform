"""Extract Fields Node Handler — Parses Structured Directives for Drafting & Exam Matrix."""

from __future__ import annotations

import logging

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


class ExtractFieldsNodeHandler(BaseNodeHandler):
    """Extracts structured document or exam specification fields from raw user instructions."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        user_message = (
            context.node_data.get("user_message")
            or context.inputs.get("message", "")
        )

        extracted_fields = {
            "raw_text": user_message,
            "target_format": "markdown",
        }

        # Heuristic detection for common drafting types
        lower_msg = user_message.lower()
        if "quyết định" in lower_msg:
            extracted_fields["doc_type"] = "decision"
        elif "tờ trình" in lower_msg:
            extracted_fields["doc_type"] = "submission"
        elif "thông báo" in lower_msg:
            extracted_fields["doc_type"] = "notice"
        elif "công văn" in lower_msg:
            extracted_fields["doc_type"] = "official_dispatch"
        else:
            extracted_fields["doc_type"] = "general_draft"

        context.node_data["extracted_fields"] = extracted_fields

        logger.info(
            "ExtractFields [%s]: detected doc_type=%s",
            node_spec.id,
            extracted_fields["doc_type"],
        )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"extracted_fields": extracted_fields},
        )
