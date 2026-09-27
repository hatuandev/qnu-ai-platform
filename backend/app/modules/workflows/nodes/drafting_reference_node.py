"""Analyze optional drafting references through structural invariants."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.nodes.drafting_contracts import normalize_text
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

_LIST_PREFIX_RE = re.compile(r"^\s*(?:[-–—•]|\d+[.)]|[A-Za-zĐđ][.)])\s+")
_BASIS_LINE_RE = re.compile(r"^\s*căn\s+cứ\b", re.IGNORECASE)


def _flatten_reference(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_reference(item))
        return flattened
    if isinstance(value, dict):
        flattened = []
        for item in value.values():
            flattened.extend(_flatten_reference(item))
        return flattened
    return []


def _looks_like_heading(line: str) -> bool:
    letters = [character for character in line if character.isalpha()]
    if not letters or len(line) > 140:
        return False
    uppercase_ratio = sum(character.isupper() for character in letters) / len(letters)
    return uppercase_ratio >= 0.7


class DraftingReferenceNodeHandler(BaseNodeHandler):
    """Create a compact structural profile from optional user-provided references."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        port_inputs = context.node_inputs.get(node_spec.id, {})
        raw_reference = (
            port_inputs.get("reference")
            or context.inputs.get("reference_context")
            or context.inputs.get("reference_documents")
        )
        fragments = [
            text for item in _flatten_reference(raw_reference) if (text := normalize_text(item))
        ]
        reference_text = "\n\n".join(fragments)
        lines = [line.strip() for line in reference_text.splitlines() if line.strip()]
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", reference_text) if part.strip()]
        list_count = sum(bool(_LIST_PREFIX_RE.match(line)) for line in lines)
        heading_count = sum(_looks_like_heading(line) for line in lines)
        basis_count = sum(bool(_BASIS_LINE_RE.match(line)) for line in lines)
        word_count = len(re.findall(r"\w+", reference_text, flags=re.UNICODE))
        max_characters = max(
            1000,
            min(
                int((node_spec.config or {}).get("max_reference_characters", 16000)),
                32000,
            ),
        )

        if not reference_text:
            recommended_profile = "adaptive"
        elif word_count <= 550 and len(paragraphs) <= 14:
            recommended_profile = "compact_narrative"
        else:
            recommended_profile = "reference_led"

        profile = {
            "has_reference": bool(reference_text),
            "reference_text": reference_text[:max_characters],
            "recommended_profile": recommended_profile,
            "signals": {
                "word_count": word_count,
                "paragraph_count": len(paragraphs),
                "heading_count": heading_count,
                "list_item_count": list_count,
                "basis_paragraph_count": basis_count,
            },
        }
        context.node_data["drafting_reference_profile"] = profile
        logger.info(
            "Drafting reference [%s]: present=%s profile=%s words=%d",
            node_spec.id,
            bool(reference_text),
            recommended_profile,
            word_count,
        )
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"reference_profile": profile},
        )
