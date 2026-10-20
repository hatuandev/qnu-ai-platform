"""Conversation interpretation is not source evidence or collection authorization."""
import re
from typing import Literal

from pydantic import Field

from app.modules.rag.evidence_schemas import StrictContract

Intent = Literal['SOCIAL', 'ASSISTANT_META', 'KNOWLEDGE', 'KNOWLEDGE_FOLLOWUP', 'MIXED', 'CLARIFICATION']


class ContextReferent(StrictContract):
    field: Literal['topic', 'institution', 'program', 'program_code', 'calendar_year', 'academic_year', 'audience']
    value: str = Field(min_length=1, max_length=200)
    source_turn: int = Field(ge=-1, le=7, description='-1 is the current user; otherwise previous_questions index')
    quote: str = Field(min_length=1, max_length=500)


class IntentDecision(StrictContract):
    intent: Intent
    requires_rag: bool
    requires_context: bool = False
    classification_method: Literal['rule', 'model', 'fallback']
    reason_code: str
    confidence: float | None = Field(default=None, ge=0, le=1)


def validate_referents(references: list[ContextReferent], current: str, previous: list[str], rewritten: str) -> bool:
    """Only exact user quotations authorize inherited scope; never assistant assertions."""
    if not references:
        return False
    fields: dict[str, str] = {}
    for reference in references:
        if reference.source_turn >= len(previous):
            return False
        source = current if reference.source_turn == -1 else previous[reference.source_turn]
        if reference.quote not in source or reference.value not in reference.quote or reference.value not in rewritten:
            return False
        if reference.field in fields and fields[reference.field] != reference.value:
            return False
        fields[reference.field] = reference.value
        marker = {'program': r'\b(?:ngành|chương trình|program)\s+(?!(?:đó|này|ấy|trước|kia)\b)',
                  'institution': r'\b(?:trường|institution)\s+(?!(?:đó|này|ấy|trước|kia)\b)'}.get(reference.field)
        if marker and reference.source_turn >= 0:
            later = [*previous[reference.source_turn + 1:], current]
            if any(re.search(marker, turn, re.IGNORECASE) and reference.value not in turn for turn in later):
                return False
    return True
