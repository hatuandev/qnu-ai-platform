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
    event_years,
    matches_metadata,
    merge_scope,
    scope_conflicts,
)
from qnu.domains.knowledge.publication.evidence import digest
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict

VERSION = "qnu.catalog-scope/v8"

# A bare four-digit year only scopes when the catalog proves that year and the
# surrounding text is neither a count nor part of a date/code range.
BARE_YEAR = re.compile(r"(?<![\w/\-])(?<!\d\.)([12]\d{3})(?![\w/\-])(?!\.\d)")
COUNT_BEFORE = re.compile(r"\b(?:có|gồm|khoảng|hơn|gần|đạt|chừng)\s+$", re.IGNORECASE)


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


def _bare_years(query: str, catalog: dict) -> list[int]:
    found = set()
    for match in BARE_YEAR.finditer(query):
        year = int(match.group(1))
        if not 1900 <= year <= 2100 or COUNT_BEFORE.search(query[: match.start()]):
            continue
        if any(year in (catalog.get(role) or []) for role in ("data_year", "issued_year")):
            found.add(year)
    return sorted(found)


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
        inferred = [role for role in roles if year in catalog[role]] or roles
        if not explicit and not inferred:
            continue
        if not explicit and len(inferred) != 1:
            clarify("vai trò năm", ["năm dữ liệu", "năm ban hành"])
        for role in explicit or inferred:
            choices.setdefault(role, []).append(year)
    for year in _bare_years(query, catalog):
        if year in years:
            continue
        present = [role for role in roles if year in catalog[role]]
        if len(present) > 1:
            clarify("vai trò năm", ["năm dữ liệu", "năm ban hành"])
        choices.setdefault(present[0], []).append(year)
    return choices


def catalog_attributes(structures: list[dict]) -> dict:
    """Attribute vocabulary, expanding '; '-joined list values into elements."""
    catalog: dict[str, dict] = {}
    for structure in structures:
        for annotation in structure.get("retrieval_metadata", []):
            for key, value in (annotation["values"].get("attributes") or {}).items():
                typed_value = (type(value) if isinstance(value, (str, bool)) else int, value)
                catalog.setdefault(key, {})[typed_value] = value
    expanded = {}
    for key, values in sorted(catalog.items()):
        elements: dict[tuple[type, object], object] = {}
        for value in values.values():
            parts = value.split(";") if isinstance(value, str) else [value]
            for part in parts:
                part = part.strip() if isinstance(part, str) else part
                if part != "":
                    elements.setdefault((str if isinstance(part, str) else type(part), part), part)
        expanded[key] = list(elements.values())
    return expanded


def catalog_sets(structures: list[dict]) -> dict[str, set[frozenset[str]]]:
    """Stored comma lists as order-insensitive sets, for request matching."""
    sets: dict[str, set[frozenset[str]]] = {}
    for structure in structures:
        for annotation in structure.get("retrieval_metadata", []):
            for key, value in (annotation["values"].get("attributes") or {}).items():
                if not isinstance(value, str):
                    continue
                for item in value.split(";"):
                    parts = tuple(part for part in (normalize(p) for p in item.split(",")) if part)
                    if len(parts) > 1:
                        sets.setdefault(key, set()).add(frozenset(parts))
    return sets


SELECTION_CUE = re.compile(r"\bnào\b|\bliệt\s+kê\b|\bdanh\s+sách\b|\bkể\s+tên\b")


def _run_value(text: str, start: int, parts: dict[str, str]) -> str | None:
    """Greedy list run of known elements; a truncated run selects nothing."""
    options = "|".join(re.escape(key) for key in sorted(parts, key=len, reverse=True))
    pattern = re.compile(r"\s*(" + options + r")(?!\w|[.,]\d)")
    join = re.compile(r"\s*(?:,|và\b|hoặc\b|với\b)\s*")
    found, match, end = [], pattern.match(text, start), start
    while match:
        found.append(parts[match[1]])
        end = match.end()
        separator = join.match(text, end)
        match = pattern.match(text, separator.end()) if separator else None
    if len(found) < 2:
        return None
    look = text[end:].lstrip()
    if look and (look[0].isalnum() or look[0] in ",;_"):
        return None
    return ", ".join(found)


def attribute_scope(query: str, catalog: dict, sets: dict) -> dict:
    text = normalize(query)
    selected = {}
    for label, values in catalog.items():
        folded = normalize(label)
        label_pattern = (
            r"(?<!\w)"
            + re.escape(folded)
            + r"(?!\w)\s*(?:(?P<explicit>[:=])\s*|là\b\s*)?"
        )
        selectors = list(re.finditer(label_pattern, text))
        parts = {}
        if label in sets:
            for value in values:
                for part in (str(value).split(", ") if isinstance(value, str) else []):
                    parts.setdefault(normalize(part), part)
        selected_value = None
        if parts:
            starts = [selector.end() for selector in selectors]
            if not selectors and SELECTION_CUE.search(text):
                words = folded.split()
                for size in range(len(words) - 1, 1, -1):
                    prefix = re.escape(" ".join(words[:size]))
                    for match in re.finditer(r"(?<!\w)" + prefix + r"(?!\w)", text):
                        position = match.end()
                        for word in words[size:]:
                            step = re.match(
                                r"\s+" + re.escape(word) + r"(?!\w)", text[position:]
                            )
                            if step is None:
                                break
                            position += step.end()
                        starts.append(position)
            for start in starts:
                value = _run_value(text, start, parts)
                if value and frozenset(normalize(p) for p in value.split(", ")) in sets[label]:
                    selected_value = value
                    break
        if selected_value is not None:
            selected[label] = selected_value
            continue
        # A label mentioned without an assigned catalog value names the topic,
        # not a scope selector: "số điện thoại" must not scope to an attribute
        # labeled "Số", and "tổng quan" questions select a value only when named.
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
        if len(matches) > 1:
            clarify(label, values)
        if matches:
            selected[label] = matches[0]
    if len(selected) > 20:
        raise Conflict("Câu hỏi có quá nhiều thuộc tính.", code="query_scope_too_large")
    return selected


def _intakes(values: dict) -> set[str]:
    # Intakes named only by schedule events still index the source for retrieval;
    # they are not document-wide scope and never force a clarification alone.
    found = {values["intake"]} if values.get("intake") is not None else set()
    for event in values.get("events") or []:
        if isinstance(event, dict) and event.get("intake"):
            found.add(event["intake"])
    return found


def scheduled_scope(
    query: str, units: list[dict], intakes: list[str], fixed: MetadataFilter
) -> dict:
    """Temporal questions select a proven event and its calendar year."""
    text = normalize(query)
    if re.search(r"\bnăm (?:ban hành|dữ liệu)\b", text):
        return {}
    cues = {
        "registration_deadline": r"\b(?:đăng ký|nhận hồ sơ|nộp hồ sơ)\b",
        "exam_date": r"\b(?:ngày thi|lịch thi|tổ chức thi)\b",
        "result_date": r"\b(?:công bố kết quả|thông báo kết quả|công bố điểm chuẩn)\b",
        "fee_deadline": r"\b(?:nộp|đóng|thanh toán) (?:lệ phí|phí)\b",
        "enrollment_confirmation": r"\bxác nhận nhập học\b",
    }
    if not re.search(r"\b(?:hạn|lịch|thời gian|khi nào|ngày nào|bao giờ|mấy giờ)\b", text):
        return {}
    kinds = [kind for kind, pattern in cues.items() if re.search(pattern, text)]
    if len(kinds) != 1:
        return {}
    kind = kinds[0]
    events = [e for values in units for e in values.get("events") or [] if e.get("kind") == kind]
    if not events:
        return {}
    years = sorted({year for event in events for year in event_years(event)})
    chosen = year_choices(query, {"data_year": years, "issued_year": []}).get("data_year", [])
    scope = {"event_kind": [kind], "event_year": chosen}
    intake_scope = {normalize(item) for item in intakes}
    year_scope = set(chosen)
    methods = {
        event["method"]
        for event in events
        if event.get("method")
        and (not year_scope or year_scope & event_years(event))
        and (not intake_scope or normalize(event.get("intake") or "") in intake_scope)
    }
    if kind == "registration_deadline" and len(methods) > 1:
        method = matching_event_method(text, methods, fixed.event_method)
        if method:
            scope["event_method"] = [method]
    return scope


def matching_event_method(query: str, methods: set[str], fixed: str | None) -> str | None:
    def named(method: str) -> bool:
        value = normalize(method)
        owner = re.search(r"\bcủa\s+.+?(?=\s+https?://|$)", value)
        url = re.search(r"https?://([^/\s]+)", value)
        return (
            mentions(query, value)
            or bool(owner and mentions(query, owner[0]))
            or bool(url and mentions(query, url[1]))
        )

    selected = [method for method in sorted(methods) if named(method)]
    if len(selected) == 1:
        return selected[0]
    if fixed:
        return None
    if not re.search(r"\b(?:so sánh|cả hai|tất cả các kênh|các kênh)\b", query):
        clarify("kênh đăng ký", methods)
    return None


def resolve(
    query: str, fixed: MetadataFilter, structures: list[dict]
) -> tuple[str, list[MetadataFilter], dict]:
    """Return a disjunction of conjunctive scopes, without weakening fixed filters."""
    units = [a["values"] for s in structures for a in s.get("retrieval_metadata", [])]
    catalog = {
        key: sorted({u[key] for u in units if u.get(key) is not None}, key=str)
        for key in ("program", "data_year", "issued_year")
    }
    catalog["intake"] = sorted({value for u in units for value in _intakes(u)}, key=str)
    chosen = {key: matched_values(query, catalog[key]) for key in ("program", "intake")}
    # Unlabeled numbers qualify only when they occur in the catalog and aren't counts.
    chosen.update(
        scheduled_scope(
            query, units, chosen["intake"] or ([fixed.intake] if fixed.intake else []), fixed
        )
        or year_choices(query, catalog)
    )
    base = fixed.model_dump(mode="json", exclude_none=True)
    attributes = attribute_scope(query, catalog_attributes(structures), catalog_sets(structures))
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
        for key in ("program", "intake"):
            values = {u[key] for u in narrowed if u.get(key)}
            if key not in base and not chosen.get(key) and len(values) > 1:
                clarify(key, values)
        # A multi-year column inside one publication is answerable reading, not a
        # scope choice; ask only when separate issued documents cover those years.
        if "data_year" not in base and not chosen.get("data_year") and not chosen.get("event_kind"):
            years = {u["data_year"] for u in narrowed if u.get("data_year")}
            issued = {u.get("issued_year") for u in narrowed if u.get("data_year")}
            if len(years) > 1 and len(issued) != 1:
                clarify("data_year", years)
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
    scopes = [
        scope
        for plan in plans
        for scope in (plan.get("collection_scopes") or [plan.get("scope_resolution") or {}])
    ]
    return [
        MetadataFilter.model_validate(f) for scope in scopes for f in scope.get("filters", [])
    ] or [fallback]
