"""Deterministic span, number and request-context invariants."""

import hashlib
import json
import re
import unicodedata
from decimal import Decimal

from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, QuoteReference

VERSION = "evidence-claims-v1"
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
REQUEST_YEAR = re.compile(r"(?<![\d_./-])(?:19|20)\d{2}(?![\w./])")
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


def _is_scope_header_text(text: str) -> bool:
    first = text.strip().splitlines()[0] if text.strip() else ""
    letters = [c for c in first if c.isalpha()]
    return bool(letters and all(c.isupper() for c in letters)) or first.lstrip().startswith("#")


MATH_GLYPH = re.compile(r"[\U0001D400-\U0001D7FF]")


def formula_legend_gap(claims: list[dict], blocks: list[EvidenceBlock], intent: str | None, attribute: str | None) -> bool:
    """A quoted formula without its neighbouring legend is not yet usable.

    When the plan asks for a formula and an accepted claim quotes formula
    glyphs, every other member of that claim's structural run group (variable
    legend, conditions) must also be cited. Shape and structure only.
    """
    from app.modules.rag.evidence_dependencies import dependency_groups

    label = f"{intent or ''} {attribute or ''}".casefold()
    if "formula" not in label and "công thức" not in label:
        return False
    cited = {ref.get("block_id") for claim in claims for ref in claim.get("references") or []}
    groups = dependency_groups(blocks)
    for claim in claims:
        references = claim.get("references") or []
        if not references or not any(MATH_GLYPH.search(ref.get("quote") or "") for ref in references):
            continue
        members = groups.get(references[0].get("block_id") or "", [references[0]])
        # A bare intro line ("Trong đó:") carries no formula content itself;
        # the legend members after it are what must be cited.
        if any(member.id not in cited and not member.text.strip().endswith(":") for member in members):
            return True
    return False


def group_single_row_gap(claims: list[dict], entity: str | None) -> list[str]:
    """A lone table row proves only its own entity, never a whole group.

    Returns display names of the evidenced rows when the answer holds no
    group-wide (canonical, non-header) policy claim and no row matches the
    requested entity. Pure metadata shapes only, no domain vocabulary.
    """
    if not entity or not claims:
        return []
    for claim in claims:
        references = claim.get("references") or []
        if not references:
            continue
        if references[0].get("origin") == "canonical" and not _is_scope_header_text(claim.get("text") or ""):
            return []
    display: list[str] = []
    for claim in claims:
        references = claim.get("references") or []
        name = references[0].get("entity_name") or "" if references else ""
        if normalized_label(entity) == normalized_label(name):
            return []
        if name and name not in display:
            display.append(name)
    return display[:3]


def row_entities_supported(claim: str, references: list[dict]) -> bool:
    for ref in references:
        if ref.get("origin") != "reviewed_fact":
            continue
        entity = normalized_label(ref.get("entity_name") or "")
        if not entity or entity not in normalized_label(claim) or entity not in normalized_label(ref["quote"]):
            return False
    return True


def _source_locations(block: EvidenceBlock) -> list[dict]:
    raw = block.fact_context.get("source_locations") if isinstance(block.fact_context, dict) else None
    if raw is None:
        return []
    from app.modules.knowledge.normalization.qnu_markdown import QnuSourceLocation

    if not isinstance(raw, list):
        raise TypeError("Source locations must be a list")
    locations, seen = [], set()
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("page"), bool):
            raise TypeError("Boolean is not a source page")
        location = QnuSourceLocation.model_validate(item).model_dump()
        if not any(location.get(key) is not None for key in ("page", "page_label", "locator", "bbox")):
            continue
        if location["page"] is not None and location["page"] < 1:
            raise ValueError("Source page must be a positive integer")
        key = json.dumps(location, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            locations.append(location)
    return locations


def _source_pages(locations: list[dict], page_number: int | None) -> list[int]:
    pages = []
    for location in locations:
        page = location.get("page")
        if isinstance(page, int) and not isinstance(page, bool) and page >= 1 and page not in pages:
            pages.append(page)
    if pages:
        return pages
    return [page_number] if isinstance(page_number, int) and page_number >= 1 else []


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
    locations = _source_locations(block)
    from app.modules.rag.source_row_context import table_row_context

    table_row = table_row_context(block)
    return {"block_id": block.id, "quote": quote,
            **({'table_row': table_row} if table_row else {}),
            "binding_id": block.binding_id, "index_revision_id": block.index_revision_id,
            "source_revision_id": block.source_revision_id, "page_number": block.page_number,
            "title": block.title, "section": block.section,
            "canonical_hash": block.canonical_hash,
            "origin": block.origin, "fact_id": block.fact_id,
            "temporal_scope": block.temporal_scope.model_dump(),
            "entity_name": block.fact_context.get("entity_name") if block.origin == "reviewed_fact" else None,
            "record_label": block.record_label, "record_path": block.record_path,
            "source_locations": locations, "source_pages": _source_pages(locations, block.page_number),
            "start": block.start + local if block.origin == "canonical" else None,
            "end": block.start + local + len(quote) if block.origin == "canonical" else None}


def validate_plan_years(plan: QueryPlan, question: str, history: list, default_year: int | None) -> None:
    explicit = request_years(question)
    allowed = set(explicit)
    if not explicit and plan.uses_history:
        allowed |= {y for h in history[-4:] for y in request_years(str(h.get("content", "")))}
    if not explicit and default_year:
        allowed.add(default_year)
    planned = set(plan.years + plan.document_years + plan.event_years)
    if planned - allowed or (explicit and not explicit.issubset(planned)):
        raise ValueError("Planner changed the requested temporal scope")
    query_years = {y for text in [plan.query, *plan.search_queries] for y in request_years(text)}
    if query_years - planned:
        raise ValueError("Search variant invented a year")


def request_years(text: str) -> set[int]:
    """Literal candidates, not year roles. Attached prose is allowed; codes are not.

    An uppercase/alphanumeric prefix may be an identifier, so require clarification
    rather than borrowing its digits. Source-year validation is intentionally unchanged.
    """
    result = {int(m[1]) for m in re.finditer(
        r'(?<![\w./])\d{1,2}[/.-]\d{1,2}[/.-]((?:19|20)\d{2})(?![\w./])', text)}
    for match in REQUEST_YEAR.finditer(text):
        prefix = re.search(r'[\w-]+$', text[:match.start()])
        if prefix and (any(c.isdigit() or c in '_-' for c in prefix[0]) or prefix[0].isupper()):
            continue
        result.add(int(match[0]))
    for match in re.finditer(r'(?<![\d_./-])((?:19|20)\d{2})\s*([-–/])\s*((?:19|20)\d{2})(?![\w./])', text):
        prefix = re.search(r'[\w-]+$', text[:match.start()])
        if prefix and (any(c.isdigit() or c in '_-' for c in prefix[0]) or prefix[0].isupper()):
            continue
        start, end = int(match[1]), int(match[3])
        result.update((start, end))
        if match[2] != '/' and 0 <= end - start < 10:
            result.update(range(start, end + 1))
    return result


def evidence_digest(bindings: list[dict]) -> str:
    return hashlib.sha256(json.dumps(bindings, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def location_pages(locations: list[dict] | None) -> list[int] | None:
    pages = [location["page"] for location in locations or [] if isinstance(location, dict)
             and isinstance(location.get("page"), int) and not isinstance(location["page"], bool)
             and location["page"] >= 1]
    return list(dict.fromkeys(pages)) or None


def citation_pages(reference: dict) -> list[int] | None:
    """Bound pages win; locator-only sources never get an invented page."""
    pages = reference.get("source_pages")
    if pages is None:
        locations = reference.get("source_locations")
        pages = location_pages(locations) or []
        if not pages and not locations and reference.get("page_number") is not None:
            pages = [reference["page_number"]]
    return list(pages) or None


def citation_locations(reference: dict) -> list[dict] | None:
    return list(reference.get("source_locations") or []) or None


def temporal_references_supported(claim: dict, years: list[int]) -> bool:
    from app.modules.knowledge.normalization.retrieval_models import (
        TemporalScope,
        temporal_is_compatible,
    )
    from app.modules.rag.evidence_constraints import data_year_values

    body_years = data_year_values(claim.get("text") or "")
    if years and body_years and not body_years.intersection(years):
        return False
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
    years = decision.get("requested", {}).get("years") or []
    historical_year = None
    if decision.get("historical_reference") or decision.get("reason") == "HISTORICAL_REFERENCE_ONLY":
        from app.modules.rag.evidence_historical import (
            historical_claim_supported,
            validate_historical_label,
        )

        historical_year = validate_historical_label(decision, answer)
        if historical_year is None:
            return False
        years = [historical_year]
    for claim in bindings:
        refs = claim.get("references") or []
        if (not refs or not same_source(refs) or not claim.get("verified")
                or not temporal_references_supported(claim, years)
                or historical_year is not None and not historical_claim_supported(claim, historical_year)
                or not numbers_supported(claim["text"], [r["quote"] for r in refs])
                or not row_entities_supported(claim["text"], refs)):
            return False
        for ref in refs:
            if not any(all(c.get(key) == ref.get(key) for key in (
                "binding_id", "index_revision_id", "source_revision_id", "page_number", "quote")) for c in citations):
                return False
    return True
