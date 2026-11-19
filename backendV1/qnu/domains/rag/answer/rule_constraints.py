"""Structured Rule Constraints & Negation Cards for QNU RAG (Slice 5).

Prevents quantized models from overlooking negative conditions, exclusions,
or prohibitions in regulation text by extracting and formatting a 4-part Negation Card:
1. applies_to
2. preconditions
3. exceptions
4. prohibitions

Adheres strictly to AGENTS.md Invariants:
- Never truncates across rule_constraints blocks in context packing.
- Enforces strict negative and exclusion discipline.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from qnu.domains.rag.answer.schemas import EvidenceSource

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;\n])\s+")

_APPLIES_PATTERNS = [
    re.compile(r"\b(?:áp dụng cho|đối với|dành cho|phạm vi áp dụng|đối tượng áp dụng)\s+([^.,;\n]+)", re.IGNORECASE),
]

_PRECONDITION_PATTERNS = [
    re.compile(r"\b(?:điều kiện|yêu cầu|phải có|đạt từ|ngưỡng bảo đảm|ngưỡng đầu vào)\s+([^.;\n]+)", re.IGNORECASE),
]

_EXCEPTION_PATTERNS = [
    re.compile(r"\b(?:trừ trường hợp|ngoại lệ|ngoại trừ|riêng đối với|cho phép|được miễn)\s+([^.;\n]+)", re.IGNORECASE),
]

_PROHIBITION_PATTERNS = [
    re.compile(r"\b(?:không được|không áp dụng|không cho phép|nghiêm cấm|loại trừ|bị hủy|không chấp nhận)\s+([^.;\n]+)", re.IGNORECASE),
]


class RuleConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applies_to: str = Field(..., min_length=1)
    preconditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    prohibitions: list[str] = Field(default_factory=list)


def format_rule_constraints(rc: RuleConstraints) -> str:
    """Format RuleConstraints into a clearly delineated Negation Card."""
    lines = ["[RÀNG BUỘC QUY CHẾ]"]
    lines.append(f"- Phạm vi áp dụng: {rc.applies_to}")
    if rc.preconditions:
        lines.append(f"- Điều kiện bắt buộc: {'; '.join(rc.preconditions)}")
    if rc.exceptions:
        lines.append(f"- Ngoại lệ: {'; '.join(rc.exceptions)}")
    if rc.prohibitions:
        lines.append(f"- Điều cấm / Loại trừ: {'; '.join(rc.prohibitions)}")
    lines.append("[/RÀNG BUỘC QUY CHẾ]")
    return "\n".join(lines)


def extract_rule_constraints_from_text(text: str, default_scope: str = "Quy chế chung") -> RuleConstraints | None:
    """Extract rule constraints from regulation text using pattern matching."""
    if not text or len(text.strip()) < 10:
        return None

    applies_to: str | None = None
    preconditions: list[str] = []
    exceptions: list[str] = []
    prohibitions: list[str] = []

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]

    for sentence in sentences:
        for p in _APPLIES_PATTERNS:
            m = p.search(sentence)
            if m and not applies_to:
                applies_to = m.group(1).strip()

        for p in _PRECONDITION_PATTERNS:
            m = p.search(sentence)
            if m:
                preconditions.append(m.group(0).strip())

        for p in _EXCEPTION_PATTERNS:
            m = p.search(sentence)
            if m:
                exceptions.append(m.group(0).strip())

        for p in _PROHIBITION_PATTERNS:
            m = p.search(sentence)
            if m:
                prohibitions.append(m.group(0).strip())

    if not (preconditions or exceptions or prohibitions):
        return None

    return RuleConstraints(
        applies_to=applies_to or default_scope,
        preconditions=list(dict.fromkeys(preconditions))[:5],
        exceptions=list(dict.fromkeys(exceptions))[:5],
        prohibitions=list(dict.fromkeys(prohibitions))[:5],
    )


def extract_constraints_for_sources(
    sources: list[EvidenceSource],
) -> list[dict[str, Any]]:
    """Extract constraints from evidence sources (from structure or text)."""
    results: list[dict[str, Any]] = []
    for s in sources:
        rc: RuleConstraints | None = None
        if s.structure and "rule_constraints" in s.structure:
            try:
                rc = RuleConstraints.model_validate(s.structure["rule_constraints"])
            except Exception:
                rc = None

        if rc is None and s.text:
            rc = extract_rule_constraints_from_text(s.text, default_scope=s.evidence_id)

        if rc:
            results.append(
                {
                    "evidence_id": s.evidence_id,
                    "constraints": rc.model_dump(mode="json"),
                    "card_text": format_rule_constraints(rc),
                }
            )
    return results
