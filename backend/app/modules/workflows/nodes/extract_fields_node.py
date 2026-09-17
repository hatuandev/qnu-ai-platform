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
            context.node_data.get("user_message")
            or context.inputs.get("message", "")
        )

        extracted_fields = {
            "raw_text": user_message,
            "target_format": "markdown",
        }

        # Heuristic detection for common drafting types
        lower_msg = unicodedata.normalize("NFC", str(user_message)).casefold()
        detected_code = next(
            (
                definition["code"]
                for definition in sorted(
                    DOCUMENT_TYPE_CATALOG, key=lambda definition: len(definition["name"]), reverse=True
                )
                if definition["name"].casefold() in lower_msg
            ),
            None,
        )
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
            output={"extracted_fields": extracted_fields},
        )
