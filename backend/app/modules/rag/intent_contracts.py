"""Conversation interpretation is not source evidence or collection authorization."""
import re
from typing import Literal

from pydantic import Field

from app.modules.rag.evidence_schemas import StrictContract

Intent = Literal['SOCIAL', 'ASSISTANT_META', 'KNOWLEDGE', 'KNOWLEDGE_FOLLOWUP', 'MIXED', 'CLARIFICATION']


class ContextReferent(StrictContract):
    field: Literal['topic', 'source', 'source_locator', 'metric', 'institution', 'program', 'program_code',
                   'calendar_year', 'academic_year', 'publication_year', 'effective_year',
                   'event_year', 'data_year', 'audience']
    value: str = Field(min_length=1, max_length=200,
        description='One contiguous literal value from the quoted user turn; never a synthesized label')
    source_turn: int = Field(ge=-1, le=7, description='-1 is the current user; otherwise previous_questions index')
    quote: str = Field(min_length=1, max_length=500,
        description='Exact contiguous user quotation containing the complete literal value')


class IntentDecision(StrictContract):
    intent: Intent
    requires_rag: bool
    requires_context: bool = False
    classification_method: Literal['rule', 'model', 'fallback']
    reason_code: str
    confidence: float | None = Field(default=None, ge=0, le=1)


def validate_referents(references: list[ContextReferent], current: str, previous: list[str], rewritten: str) -> bool:
    """Only exact user quotations authorize inherited scope; never assistant assertions."""
    return not referent_errors(references, current, previous, rewritten)


def _in_rewrite(reference: ContextReferent, rewritten: str) -> bool:
    # This compares a derived query, not source quotations. Codes and source
    # addresses remain case-sensitive; no synonyms, punctuation or accents change.
    value = ' '.join(reference.value.split())
    text = ' '.join(rewritten.split())
    if reference.field not in {'program_code', 'source'}:
        value, text = value.casefold(), text.casefold()
    return bool(re.search(r'(?<!\w)' + re.escape(value) + r'(?!\w)', text))


def referent_errors(references: list[ContextReferent], current: str, previous: list[str],
                    rewritten: str) -> list[dict]:
    """Safe validation codes, without copying rejected queries or user quotations into logs."""
    if not references:
        return [{'code': 'MISSING_REFERENCES'}]
    errors = []
    for index, reference in enumerate(references):
        def reject(code: str, index: int = index, field: str = reference.field) -> None:
            errors.append({'index': index, 'field': field, 'code': code})

        if reference.source_turn >= len(previous):
            reject('INVALID_SOURCE_TURN')
            continue
        source = current if reference.source_turn == -1 else previous[reference.source_turn]
        if reference.quote not in source:
            reject('QUOTE_NOT_IN_USER_TURN')
        if reference.value not in reference.quote:
            reject('VALUE_NOT_IN_QUOTE')
        if not _in_rewrite(reference, rewritten):
            reject('VALUE_NOT_IN_STANDALONE_QUERY')
        if reference.field.endswith('_year'):
            from app.modules.rag.conversation_time import times
            role = reference.field.removesuffix('_year')
            candidates = [t for t in times(source, reference.source_turn) if reference.value in t.value]
            quoted = times(reference.quote, reference.source_turn)
            if candidates and not any(t.role == role for t in candidates):
                reject('TEMPORAL_REFERENCE_ROLE_MISMATCH')
            elif len({t.role for t in candidates}) > 1 and not any(t.role == role for t in quoted):
                reject('TEMPORAL_REFERENCE_AMBIGUOUS')
    # Set membership, supersession and source association are validated from user
    # syntax, never by treating two values of the same role as an automatic conflict.
    from app.modules.rag.conversation_scope import referent_set_errors
    errors.extend(referent_set_errors(references, current, previous))
    return errors
