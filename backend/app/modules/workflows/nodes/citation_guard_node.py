"""Citation Policy Guardrail Node Handler — Enforces Anti-Hallucination & Groundedness."""

from __future__ import annotations

import logging

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)


class CitationGuardNodeHandler(BaseNodeHandler):
    """Verifies that generated answers contain legitimate citations from QNU official documents."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        config = node_spec.config or {}
        require_citation = config.get("require_citation_for_answer", True)
        accepted_statuses = config.get("accepted_statuses", ["answered", "success"])
        invalid_route = config.get("invalid_route", "ungrounded")

        rag_status = context.node_data.get("rag_status") or context.outputs.get("status", "answered")
        citations = context.node_data.get("citations") or context.outputs.get("citations", [])
        answer_text = context.node_data.get("rag_answer") or context.outputs.get("answer", "")

        is_grounded = True

        # Check 1: Status must be valid
        if rag_status not in accepted_statuses:
            is_grounded = False

        # Check 2: Answer must not be empty
        if not answer_text or not answer_text.strip():
            is_grounded = False

        # Check 3: If citations required, verify non-empty citations
        if require_citation and len(citations) == 0:
            is_grounded = False

        # If answer itself declares insufficient context, treat as ungrounded
        if ("chưa có trong" in answer_text.lower() or "không tìm thấy" in answer_text.lower()) and len(citations) == 0:
            is_grounded = False

        context.node_data["is_grounded"] = is_grounded
        selected_port = "grounded" if is_grounded else invalid_route

        logger.info(
            "CitationGuard [%s]: is_grounded=%s, citations=%d, port=%s",
            node_spec.id,
            is_grounded,
            len(citations),
            selected_port,
        )

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "is_grounded": is_grounded,
                "citations_count": len(citations),
                "port": selected_port,
            },
            selected_port=selected_port,
        )
