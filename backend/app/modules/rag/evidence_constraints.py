"""Role-specific numeric proof; dates/identifiers never establish data season."""

import re
from datetime import date
from typing import Literal

from app.modules.rag.evidence_validation import YEAR, number_values

ConstraintRole = Literal["value_constraint", "current_value", "method_identity", "data_year", "document_year", "event_year"]
DATE = re.compile(r"(?<!\w)\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}(?!\w)")
IDENTIFIER = re.compile(r"(?<!\w)\d+(?:/\d+)?/[A-ZĐ][\w/-]*", re.IGNORECASE)
URL_SHAPE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)


def location_pointer_gap(claims: list[dict], intent: str | None, attribute: str | None = None) -> bool:
    """A where-answer pointing at another notice without quoting any path is incomplete.

    Token shapes only (URL vs document identifier); never borrows a generic
    portal address for a notice-specific path and never invents a locator.
    The planner labels intents freely, so match the stable role substrings
    instead of one exact label.
    """
    label = f"{intent or ''} {attribute or ''}".casefold()
    if ("location" not in label and "địa điểm" not in label) or not claims:
        return False
    quotes = [ref.get("quote") or "" for claim in claims for ref in claim.get("references") or []]
    if any(URL_SHAPE.search(quote) for quote in quotes):
        return False
    return any(IDENTIFIER.search(quote) for quote in quotes)


def current_value_numbers(text: str) -> set:
    """Exclude syntactically cited document metadata, not operational deadlines.

    An earlier cited value is comparison background only in this explicitly
    audited role. Threshold/date/formula conditions use the strict default role.
    """
    clauses = re.split(r"[,;]\s+(?!\d)", text)
    dated = []
    for clause in clauses:
        matches = list(DATE.finditer(clause))
        if not IDENTIFIER.search(clause) or len(matches) != 1:
            continue
        parts = list(map(int, re.split(r"[/.-]", matches[0].group())))
        try:
            issued = date(parts[2], parts[1], parts[0])
        except ValueError:
            continue
        dated.append((clause, issued))
    latest = max((issued for _, issued in dated), default=None)
    retained = []
    for clause in clauses:
        old = next((issued for candidate, issued in dated if candidate == clause), None)
        if old is not None and latest is not None and old < latest:
            continue
        retained.append(DATE.sub("", IDENTIFIER.sub("", clause)) if old else clause)
    return number_values(" ".join(retained))


def data_year_values(text: str) -> set[int]:
    # Structural exclusions only: no domain-specific dictionary or filename.
    return {int(year) for year in YEAR.findall(IDENTIFIER.sub("", DATE.sub("", text)))}


def retained_condition(role: ConstraintRole, reference: dict, claims: list[dict], years: list[int]) -> bool:
    """Semantic audit decides the role; deterministic proof still binds its value."""
    if not claims:
        return False
    if role in {"value_constraint", "current_value", "method_identity"}:
        values = set().union(*(number_values(claim["text"]) for claim in claims))
        # Do not remove years from numeric conditions: deadlines need dates AND hours.
        if role == "method_identity":
            # Alphanumeric method aliases keep their digits in the same role.
            # Do not equate these digits with thresholds, dates or quantities.
            from decimal import Decimal

            values.update(Decimal(match[1]) for claim in claims for match in
                          re.finditer(r"\b[A-Za-z]+(\d+)\b", claim["text"]))
            evidence = re.sub(r"\b\d+[A-Z]+\b", "", reference["quote"])
            return number_values(evidence).issubset(values)
        needed = current_value_numbers(reference["quote"]) if role == "current_value" else number_values(reference["quote"])
        year_values = {value for value in needed if value in years}
        if role == "current_value" and year_values:
            # The year still requires actual attached source-scope proof.
            if not retained_condition("data_year", reference, claims, list(map(int, year_values))):
                return False
            needed -= year_values
        return needed.issubset(values)
    wanted = set(years)
    evidence = data_year_values(reference["quote"]) if role == "data_year" else {int(y) for y in YEAR.findall(reference["quote"])}
    needed = wanted.intersection(evidence)
    if not needed:
        return False
    for claim in claims:
        supported = set()
        for ref in claim["references"]:
            scope = ref.get("temporal_scope") or {}
            if scope.get("status") == "verified" and scope.get("role") == "data":
                if role == "data_year" and scope.get("data_years") and not needed.intersection(scope["data_years"]):
                    return False
                supported.update(scope.get("data_years") or [])
            supported.update(data_year_values(ref["quote"]) if role == "data_year" else
                             (int(y) for y in YEAR.findall(ref["quote"])))
        body_years = data_year_values(claim["text"]) if role == "data_year" else set()
        # A same-source season header cannot overwrite explicit historical body data.
        if not needed.issubset(supported) or (body_years and not body_years.intersection(needed)):
            return False
    return True
