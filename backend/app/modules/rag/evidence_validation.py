"""Deterministic span, number and request-context invariants."""

import hashlib
import json
import re
import unicodedata
from decimal import Decimal

from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, QuoteReference

VERSION = "evidence-claims-v1"
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
NUMBER = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*(?!\d)(?![.,]\d)")


def number_values(text: str) -> set[Decimal | str]:
    values = set()
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    for match in NUMBER.finditer(text):
        raw = match.group()
        if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", raw):
            raw = re.sub(r"[.,]", "", raw)
        elif raw.count(".") + raw.count(",") > 1:
            values.add("exact:" + raw)  # Phone/compound identifiers cannot borrow individual digits.
            continue
        values.add(Decimal(raw.replace(",", ".")))
    return values


def numbers_supported(claim: str, quotes: list[str]) -> bool:
    evidence = set().union(*(number_values(quote) for quote in quotes))
    return number_values(claim).issubset(evidence)


def same_source(references: list[dict]) -> bool:
    return len({(r["binding_id"], r["index_revision_id"], r["source_revision_id"]) for r in references}) == 1


def normalized_label(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def row_entities_supported(claim: str, references: list[dict]) -> bool:
    for ref in references:
        if ref.get("origin") != "reviewed_fact":
            continue
        entity = normalized_label(ref.get("entity_name") or "")
        if not entity or entity not in normalized_label(claim) or entity not in normalized_label(ref["quote"]):
            return False
    return True


def bind_quote(reference: QuoteReference, blocks: dict[str, EvidenceBlock]) -> dict:
    block = blocks.get(reference.block_id)
    if not block:
        raise ValueError("Quote must be an exact substring of its identified source block")
    quote = reference.quote
    if quote not in block.text:
        # Reflowed whitespace is the only permitted repair. Return the original
        # source span, never the model's modified text, and reject ambiguous matches.
        pieces = list(re.finditer(r"\s+|\S", block.text))
        normalized = "".join(" " if p.group().isspace() else p.group() for p in pieces)
        wanted = re.sub(r"\s+", " ", quote)
        matches = list(re.finditer(re.escape(wanted), normalized))
        if len(matches) != 1:
            raise ValueError("Quote must match one unambiguous source span")
        match = matches[0]
        quote = block.text[pieces[match.start()].start():pieces[match.end() - 1].end()]
    local = block.text.index(quote)
    return {"block_id": block.id, "quote": quote,
            "binding_id": block.binding_id, "index_revision_id": block.index_revision_id,
            "source_revision_id": block.source_revision_id, "page_number": block.page_number,
            "title": block.title, "section": block.section,
            "canonical_hash": block.canonical_hash,
            "origin": block.origin, "fact_id": block.fact_id,
            "temporal_scope": block.temporal_scope.model_dump(),
            "entity_name": block.fact_context.get("entity_name") if block.origin == "reviewed_fact" else None,
            "start": block.start + local if block.origin == "canonical" else None,
            "end": block.start + local + len(quote) if block.origin == "canonical" else None}


def validate_plan_years(plan: QueryPlan, question: str, history: list, default_year: int | None) -> None:
    explicit = {int(y) for y in YEAR.findall(question)}
    for match in re.finditer(r"\b((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})\b", question):
        start, end = map(int, match.groups())
        if 0 <= end - start < 10:
            explicit.update(range(start, end + 1))
    allowed = set(explicit)
    if not explicit and plan.uses_history:
        allowed |= {int(y) for h in history[-4:] for y in YEAR.findall(str(h.get("content", "")))}
    if not explicit and default_year:
        allowed.add(default_year)
    planned = set(plan.years + plan.document_years + plan.event_years)
    if planned - allowed or (explicit and not explicit.issubset(planned)):
        raise ValueError("Planner changed the requested temporal scope")
    query_years = {int(y) for text in [plan.query, *plan.search_queries] for y in YEAR.findall(text)}
    if query_years - planned:
        raise ValueError("Search variant invented a year")


def evidence_digest(bindings: list[dict]) -> str:
    return hashlib.sha256(json.dumps(bindings, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def temporal_references_supported(claim: dict, years: list[int]) -> bool:
    from app.modules.knowledge.normalization.retrieval_models import (
        TemporalScope,
        temporal_is_compatible,
    )

    return all(temporal_is_compatible(TemporalScope.model_validate(ref.get("temporal_scope") or {}), years)
               for ref in claim["references"])


def validate_decision_integrity(decision: dict, answer: str, citations: list[dict]) -> bool:
    bindings = decision.get("claim_bindings") or []
    if decision.get("version") != VERSION or decision.get("answer") != answer:
        return False
    if decision.get("evidence_digest") != evidence_digest(bindings):
        return False
    if decision.get("status") not in {"supported", "partial"} or not bindings:
        return False
    for claim in bindings:
        refs = claim.get("references") or []
        if (not refs or not same_source(refs) or not claim.get("verified")
                or not temporal_references_supported(claim, decision.get("requested", {}).get("years") or [])
                or not numbers_supported(claim["text"], [r["quote"] for r in refs])
                or not row_entities_supported(claim["text"], refs)):
            return False
        for ref in refs:
            if not any(all(c.get(key) == ref.get(key) for key in (
                "binding_id", "index_revision_id", "source_revision_id", "page_number", "quote")) for c in citations):
                return False
    return True
