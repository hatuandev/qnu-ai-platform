"""Resolve scope only against authorized, sealed units of the current publication.

Unknown stays unknown. A missing hard-filter result never triggers a wider search.
This conservative planner uses explicit catalog values, not a second LLM or a
hand-maintained university dictionary. Years with multiple roles require clarification.
"""

import itertools
import json
import re
import unicodedata

from sqlalchemy import select

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.domains.knowledge.metadata import (
    MetadataFilter,
    matches_metadata,
    merge_scope,
    scope_conflicts,
)
from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict

VERSION = "qnu.catalog-scope/v2"


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def mentions(query: str, value) -> bool:
    return (
        re.search(r"(?<!\w)" + re.escape(normalize(str(value))) + r"(?!\w)", normalize(query))
        is not None
    )


def clarify(field: str, values) -> None:
    field = {"program": "ngành/chương trình", "intake": "khóa/đợt", "data_year": "năm dữ liệu"}.get(
        field, field
    )
    options = "; ".join(str(v) for v in sorted(values, key=str)[:12])
    raise Conflict(
        f"Cần làm rõ phạm vi {field}: {options}. Vui lòng chọn hoặc nêu rõ các phạm vi cần so sánh.",
        code="answer_scope_clarification_required",
    )


def matched_values(query: str, values) -> list:
    text = normalize(query)
    occurrences = [
        (value, match.span())
        for value in values
        for match in re.finditer(r"(?<!\w)" + re.escape(normalize(str(value))) + r"(?!\w)", text)
    ]
    # A longer exact label wins only at the same position. An explicit second
    # mention of the short label still counts as a distinct requested scope.
    return [
        v
        for v in values
        if any(
            value == v
            and not any(
                other != value and start <= span[0] and end >= span[1] and (start, end) != span
                for other, (start, end) in occurrences
            )
            for value, span in occurrences
        )
    ]


def year_choices(query: str, catalog: dict) -> dict:
    choices = {}
    labeled = re.findall(
        r"(?:\bnăm(?: dữ liệu| ban hành)?|\byear)\s*[:=]?\s*"
        r"([12]\d{3}(?:(?:\s*(?:,|và|and)\s*)(?:năm\s+|year\s+)?[12]\d{3})*)(?!\d)",
        query,
        re.IGNORECASE,
    )
    years = sorted({int(y) for group in labeled for y in re.findall(r"[12]\d{3}", group)})
    roles = [key for key in ("data_year", "issued_year") if catalog[key]]
    for year in years:
        explicit = [
            key
            for key, label in (
                ("data_year", r"năm dữ liệu|data year"),
                ("issued_year", r"năm ban hành|issued year"),
            )
            if re.search(r"(?:" + label + r")\s*[:=]?\s*" + str(year) + r"\b", query, re.IGNORECASE)
        ]
        if not explicit and not roles:
            continue
        if not explicit and len(roles) != 1:
            clarify("vai trò năm", ["năm dữ liệu", "năm ban hành"])
        for role in explicit or roles:
            choices.setdefault(role, []).append(year)
    return choices


def catalog_attributes(structures: list[dict]) -> dict:
    catalog: dict[str, dict] = {}
    for structure in structures:
        for annotation in structure.get("retrieval_metadata", []):
            for key, value in (annotation["values"].get("attributes") or {}).items():
                typed_value = (type(value) if isinstance(value, (str, bool)) else int, value)
                catalog.setdefault(key, {})[typed_value] = value
    return {key: list(values.values()) for key, values in sorted(catalog.items())}


def attribute_scope(query: str, catalog: dict) -> dict:
    text = normalize(query)
    selected = {}
    for label, values in catalog.items():
        label_pattern = (
            r"(?<!\w)"
            + re.escape(normalize(label))
            + r"(?!\w)\s*(?:(?P<explicit>[:=])\s*|là\b\s*)?"
        )
        selectors = list(re.finditer(label_pattern, text))
        if not selectors:
            continue
        by_label = {}
        for value in values:
            if isinstance(value, bool):
                literal = json.dumps(value)
            elif isinstance(value, float) and value.is_integer():
                literal = str(int(value))
            else:
                literal = str(value)
            by_label.setdefault(normalize(literal), []).append(value)
        options = "|".join(re.escape(key) for key in sorted(by_label, key=len, reverse=True))
        value_pattern = re.compile(r"(?:" + options + r")(?!\w|[.,]\d)")
        join_pattern = re.compile(r"\s*(?:,|và\b|hoặc\b|với\b)\s*")
        found = set()
        for selector in selectors:
            match = value_pattern.match(text, selector.end())
            if match is None and selector["explicit"]:
                clarify(label, values)
            while match:
                found.add(match[0])
                join = join_pattern.match(text, match.end())
                match = value_pattern.match(text, join.end()) if join else None
        matches = [value for key in found for value in by_label[key]]
        overview = re.search(r"\b(?:liệt kê|tất cả|các|những|nào|list|all|overview)\b", text)
        if len(matches) > 1 or (not matches and not overview):
            clarify(label, values)
        if matches:
            selected[label] = matches[0]
    if len(selected) > 20:
        raise Conflict("Câu hỏi có quá nhiều thuộc tính.", code="query_scope_too_large")
    return selected


def resolve(
    query: str, fixed: MetadataFilter, structures: list[dict]
) -> tuple[str, list[MetadataFilter], dict]:
    """Return a disjunction of conjunctive scopes, without weakening fixed filters."""
    units = [a["values"] for s in structures for a in s.get("retrieval_metadata", [])]
    catalog = {
        key: sorted({u[key] for u in units if u.get(key) is not None}, key=str)
        for key in ("program", "intake", "data_year", "issued_year")
    }
    chosen = {key: matched_values(query, catalog[key]) for key in ("program", "intake")}
    # Numeric counts, scores or course codes are not years merely because they
    # contain four digits. Require a year label, including for unknown years.
    chosen.update(year_choices(query, catalog))
    base = fixed.model_dump(mode="json", exclude_none=True)
    attributes = attribute_scope(query, catalog_attributes(structures))
    if attributes:
        requested = {"attributes": attributes}
        if scope_conflicts(base, requested):
            raise Conflict("Câu hỏi mâu thuẫn với phạm vi đã chọn.", code="answer_scope_conflict")
        base = merge_scope(base, requested)
        if len(base["attributes"]) > 20:
            raise Conflict("Câu hỏi có quá nhiều thuộc tính.", code="query_scope_too_large")
    # Disambiguate glossary within the explicit question scope, not across
    # unrelated programs/years of the authorized collection.
    preliminary = {**base, **{k: v[0] for k, v in chosen.items() if len(v) == 1}}
    definitions = {}
    for structure in structures:
        if not matches_metadata(structure, MetadataFilter.model_validate(preliminary)):
            continue
        for d in structure.get("search_context", {}).get("glossary", []):
            if mentions(query, d["alias"]):
                definitions.setdefault(d["alias"], set()).add(d["expansion"])
    expansions = []
    for alias, values in sorted(definitions.items()):
        if len(values) != 1:
            clarify(alias, values)
        expansions.append(next(iter(values)))
    expanded = query + ("\n" + " | ".join(expansions) if expansions else "")
    if len(expanded) > 8000:
        raise Conflict("Mở rộng truy vấn vượt ngân sách.", code="query_scope_too_large")
    for key in ("program", "intake"):
        chosen[key] = matched_values(expanded, catalog[key])
    for key, values in chosen.items():
        if (
            key in base
            and values
            and any(normalize(str(v)) != normalize(str(base[key])) for v in values)
        ):
            raise Conflict("Câu hỏi mâu thuẫn với phạm vi đã chọn.", code="answer_scope_conflict")
    keys = [key for key, values in chosen.items() if values and key not in base]
    if sum(len(chosen[key]) > 1 for key in keys) > 1:
        clarify("cặp phạm vi", ["nêu riêng ngành/khóa/năm cho từng ý hỏi"])
    combinations = list(itertools.product(*(chosen[k] for k in keys)))
    if len(combinations) > 32:
        raise Conflict("Câu hỏi có quá nhiều phạm vi.", code="query_scope_too_large")
    filters = [
        MetadataFilter.model_validate({**base, **dict(zip(keys, values, strict=True))})
        for values in combinations
    ]
    # Ask before selecting an arbitrary program/intake from parallel regulations.
    # Explicit list/comparison requests may legitimately span multiple units.
    overview = re.search(
        r"\b(?:so sánh|compare|liệt kê|list|tất cả|all|tổng quan|overview)\b", query, re.IGNORECASE
    )
    narrowed = [
        u
        for u in units
        if any(matches_metadata({"retrieval_metadata": [{"values": u}]}, f) for f in filters)
    ]
    if not overview:
        for key in ("program", "intake", "data_year"):
            values = {u[key] for u in narrowed if u.get(key)}
            if key not in base and not chosen.get(key) and len(values) > 1:
                clarify(key, values)
    return (
        expanded,
        filters,
        {
            "version": VERSION,
            "filters": [f.model_dump(mode="json", exclude_none=True) for f in filters],
            "catalog_sha256": digest(structures),
            "alias_count": len(expansions),
        },
    )


async def verified_structures(db, run, allowed, sealed):
    rows = (
        await db.execute(
            select(IndexChunk.id, IndexChunk.structure)
            .where(
                IndexChunk.run_id == run.id,
                IndexChunk.input_id.in_([b.id for b in allowed]),
            )
            .order_by(IndexChunk.id)
            .limit(get_settings().INDEX_MAX_CHUNKS + 1)
        )
    ).all()
    if len(rows) > get_settings().INDEX_MAX_CHUNKS:
        raise Conflict("Danh mục phạm vi vượt ngân sách.", code="index_scope_too_large")
    proofs = {c["id"]: c["structure_sha256"] for c in sealed["chunks"]}
    for identifier, structure in rows:
        if digest(structure) != proofs.get(identifier):
            raise Conflict("Metadata khác manifest đã ghim.", code="index_metadata_changed")
    return [structure or {} for _, structure in rows]


async def plan(db, run, allowed, sealed, query, fixed):
    return resolve(query, fixed, await verified_structures(db, run, allowed, sealed))


def result_scopes(result, fallback):
    plans = result.trace.get("facets", [result.trace])
    return [
        MetadataFilter.model_validate(f)
        for p in plans
        for f in p.get("scope_resolution", {}).get("filters", [])
    ] or [fallback]
