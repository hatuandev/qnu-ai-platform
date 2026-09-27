"""Extract Fields Node Handler — Parses Structured Directives for Drafting & Exam Matrix."""

from __future__ import annotations

import logging
import unicodedata

from app.modules.document_types.catalog import DOCUMENT_TYPE_CATALOG, normalize_document_type_code
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
            context.node_inputs.get(node_spec.id, {}).get("text")
            or context.node_data.get("normalized_query")
            or context.node_data.get("user_message")
            or context.inputs.get("message", "")
        )

        extracted_fields = {
            "raw_text": user_message,
            "target_format": "markdown",
        }

        # Heuristic detection for common drafting types
        lower_msg = unicodedata.normalize("NFC", str(user_message)).casefold()
        # A request can mention several document types, especially when its
        # legal basis cites a Quyết định while asking for a Tờ trình. The
        # requested type normally appears first, so select the earliest catalog
        # occurrence and use the longest name only as a tie-breaker.
        candidates = [
            (position, -len(definition["name"]), definition["code"])
            for definition in DOCUMENT_TYPE_CATALOG
            if (position := lower_msg.find(definition["name"].casefold())) >= 0
        ]
        detected_code = min(candidates)[2] if candidates else None
        extracted_fields["doc_type"] = detected_code
        extracted_fields["document_type_code"] = normalize_document_type_code(detected_code)
        extracted_fields["document_type_status"] = "classified" if detected_code else "unclassified"

        context.node_data["extracted_fields"] = extracted_fields

        logger.info(
            "ExtractFields [%s]: detected doc_type=%s",
            node_spec.id,
            extracted_fields["doc_type"],
        )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"fields": extracted_fields, "extracted_fields": extracted_fields},
        )
