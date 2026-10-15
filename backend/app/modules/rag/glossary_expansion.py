"""Collection glossary expansion for weighted retrieval.

Single-hop, directed aliases only: a user phrase helps retrieve its target
term, never the reverse, and targets are never re-matched. Expansion only
creates search candidates; it never filters evidence, quotes, facts or plans.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pydantic import TypeAdapter, ValidationError

from app.modules.knowledge.glossary_schemas import GlossaryScope
from app.modules.rag.evidence_validation import number_values
from app.modules.rag.query_expansion import SearchQuery, normalized_query

logger = logging.getLogger(__name__)

MAX_GLOSSARY_MATCHES = 2
MAX_TARGET_TOKENS = 12
GLOSSARY_LEXICAL_WEIGHT = 0.3
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
ALNUM_RUN = re.compile(r"[A-Za-z]+\d+|\d+[A-Za-z]+")
SCOPE_ADAPTER = TypeAdapter(GlossaryScope)


@dataclass(frozen=True)
class GlossaryMatch:
    alias_id: str
    entry_version: int
    phrase: str
    term: str


@dataclass
class GlossaryExpansion:
    enabled: bool
    settings_version: int
    matches: list[GlossaryMatch] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)

    def trace(self, weights: dict[str, float] | None = None) -> dict:
        return {
            "enabled": self.enabled,
            "settings_version": self.settings_version,
            "matches": [{"alias_id": match.alias_id, "entry_version": match.entry_version,
                         "phrase": match.phrase, "term": match.term,
                         "weight": (weights or {}).get(match.term)} for match in self.matches],
            "skipped": list(self.skipped),
            "limits": {"max_matches": MAX_GLOSSARY_MATCHES, "max_target_tokens": MAX_TARGET_TOKENS,
                       "lexical_weight": GLOSSARY_LEXICAL_WEIGHT},
        }


def _phrase_pattern(phrase: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)")


def _scope_allows(scope: dict, plan_years: list[int] | None,
                  plan_method: str | None, plan_entity: str | None,
                  question: str = "") -> str | None:
    """Return None when the structured scope applies, else a skip reason.

    Only exact matches count; unknown scope keys or unverifiable dimensions
    mean the scope is unclear and the alias is skipped. Free-text notes are
    never used as filter conditions.
    """
    if isinstance(scope, dict) and set(scope) - {"years", "methods", "entities"}:
        return "unclear_scope"
    try:
        scope = SCOPE_ADAPTER.validate_python(scope)
    except ValidationError:
        return "invalid_scope"
    if not scope:
        return None
    allowed_keys = {"years", "methods", "entities"}
    if any(key not in allowed_keys for key in scope):
        return "unclear_scope"
    years = scope.get("years") or []
    if years and (not plan_years or not set(plan_years).intersection(int(year) for year in years)):
        return "scope_mismatch"
    def dimension_matches(values: list[str], resolved: str | None) -> bool:
        if resolved:
            return normalized_query(resolved) in {normalized_query(value) for value in values}
        # The fact/hybrid branch has no semantic planner. Only accept a scope
        # label literally present in the original question; never infer one.
        return any(_phrase_pattern(normalized_query(value)).search(normalized_query(question))
                   for value in values)

    methods = scope.get("methods") or []
    if methods and not dimension_matches(methods, plan_method):
        return "scope_mismatch"
    entities = scope.get("entities") or []
    if entities and not dimension_matches(entities, plan_entity):
        return "scope_mismatch"
    return None


def _protected_target(target: str) -> str | None:
    """Alias targets must not smuggle numbers, years or codes into retrieval."""
    cleaned = target.strip()
    if not cleaned or len(cleaned.split()) > MAX_TARGET_TOKENS:
        return "oversized_target"
    if number_values(cleaned):
        return "protected_numeric"
    if ALNUM_RUN.search(cleaned) or YEAR_PATTERN.search(cleaned):
        return "protected_numeric"
    return None


def match_glossary(question: str, entries: list,
                   plan_years: list[int] | None = None,
                   plan_method: str | None = None,
                   plan_entity: str | None = None) -> tuple[list[GlossaryMatch], list[dict]]:
    """Match approved aliases against word boundaries, longest phrase first."""
    normalized = normalized_query(question)
    candidates = []
    skipped: list[dict] = []
    for entry in entries:
        phrase = normalized_query(getattr(entry, "user_phrase", "") or "")
        target = (getattr(entry, "target_term", "") or "").strip()
        if not phrase or not target:
            continue
        spans = [match.span() for match in _phrase_pattern(phrase).finditer(normalized)]
        if spans:
            stored_scope = getattr(entry, "scope", None)
            reason = _scope_allows({} if stored_scope is None else stored_scope,
                                   plan_years, plan_method, plan_entity, question)
            if reason:
                skipped.append({"phrase": phrase, "reason": reason})
                continue
            candidates.append((phrase, target, entry, spans))
    # Group by phrase: one phrase mapping to several distinct targets is
    # ambiguous (all skipped); identical aliases keep the first in-scope entry.
    groups: dict[str, list] = {}
    for candidate in sorted(candidates, key=lambda item: (-len(item[0]), item[3][0][0])):
        groups.setdefault(candidate[0], []).append(candidate)
    matches: list[GlossaryMatch] = []
    used_spans: list[tuple[int, int]] = []

    def overlaps(span: tuple[int, int]) -> bool:
        return any(span[0] < end and start < span[1] for start, end in used_spans)

    for phrase, group in groups.items():
        targets = {normalized_query(target) for _, target, _, _ in group}
        if len(targets) > 1:
            for _, _, entry, _ in group:
                skipped.append({"phrase": getattr(entry, "user_phrase", phrase),
                                "reason": "conflicting_targets"})
            continue
        _, target, _, spans = group[0]
        if any(overlaps(span) for span in spans):
            continue
        evaluated = []
        for _, _, entry, _ in group:
            protected = _protected_target(target)
            if protected is not None:
                evaluated.append((entry, protected))
                continue
            evaluated.append((entry, None))
        passed = next((entry for entry, reason in evaluated if reason is None), None)
        if passed is None:
            skipped.append({"phrase": getattr(group[0][2], "user_phrase", phrase),
                            "reason": evaluated[-1][1] if evaluated else "match_limit"})
            continue
        for entry, reason in evaluated:
            if entry is not passed:
                skipped.append({"phrase": getattr(entry, "user_phrase", phrase),
                                "reason": reason or "duplicate_alias"})
        if len(matches) >= MAX_GLOSSARY_MATCHES:
            skipped.append({"phrase": getattr(passed, "user_phrase", phrase), "reason": "match_limit"})
            continue
        used_spans.extend(spans)
        matches.append(GlossaryMatch(alias_id=getattr(passed, "id", ""),
                                     entry_version=int(getattr(passed, "version", 0) or 0),
                                     phrase=phrase, term=target))
    return matches, skipped


def expand_question(question: str, matches: list[GlossaryMatch]) -> list[SearchQuery]:
    """Build natural-text glossary queries; the original question stays intact."""
    return [SearchQuery(f"{question} · {match.term}", question, "glossary") for match in matches]


async def resolve_glossary_queries(db, collection_id: str, question: str,
                                   plan_years: list[int] | None = None,
                                   plan_method: str | None = None,
                                   plan_entity: str | None = None) -> tuple[list[SearchQuery], dict]:
    """Load, match and expand in one step for retrieval call sites.

    Returns ([SearchQuery, ...], trace). Disabled/missing settings, a missing
    session, empty matches or a store without the glossary tables all fall
    back to the baseline ([], disabled trace); genuine DB failures raise
    RFC 7807.
    """
    if db is None:
        return [], GlossaryExpansion(enabled=False, settings_version=0).trace()
    from app.modules.knowledge.services.glossary_service import glossary_service

    version = await glossary_service.glossary_cache_version(db, collection_id)
    if version <= 0:
        return [], GlossaryExpansion(enabled=False, settings_version=0).trace()
    entries = await glossary_service.load_approved_terms(db, collection_id)
    matches, skipped = match_glossary(question, entries, plan_years=plan_years,
                                       plan_method=plan_method, plan_entity=plan_entity)
    queries = expand_question(question, matches)
    expansion = GlossaryExpansion(enabled=True, settings_version=version,
                                  matches=matches, skipped=skipped)
    weights = {match.term: GLOSSARY_LEXICAL_WEIGHT for match in matches}
    return queries, expansion.trace(weights)
