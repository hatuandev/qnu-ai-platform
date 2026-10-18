"""Deterministic serving projection of the standard, never a second RAG engine."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from app.modules.knowledge.normalization.qnu_markdown import (
    QNU_CELL_STATES,
    QnuBlock,
    QnuStructuredDocument,
    cell_state,
    parse_qnu_gfm_table,
)
from app.modules.knowledge.normalization.retrieval_models import (
    SourceUnit,
    TemporalScope,
    UnitManifest,
)
from app.modules.knowledge.normalization.retrieval_units import manifest_digest, validate_manifest
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.source_links import attach_fact_context, build_context_graph

VERSION = "qnu-rag-projection/v1"
TEMPORAL_KEYS = frozenset({"data_years", "academic_year", "effective_from", "effective_to",
                           "event_from", "event_to", "recurrence", "basis_quote"})
MILESTONES = ("effective_from", "effective_to", "event_from", "event_to")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _mapping(value: Any) -> dict:
    return value.model_dump() if hasattr(value, "model_dump") else dict(value or {})


def _declared_temporal(raw: Any, *, block_id: str, level: str, text: str, header: str,
                       issues: list[dict]) -> dict:
    """Validate declared time metadata; a declaration is never server approval."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        issues.append({"code": "TEMPORAL_METADATA_INVALID", "block_id": block_id, "level": level})
        return {"status": "ambiguous", "role": "unknown", "scope_level": level}
    scope: dict[str, Any] = {}
    unsupported: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in TEMPORAL_KEYS:
            unsupported[key] = copy.deepcopy(value)
    if unsupported:
        issues.append({"code": "TEMPORAL_KEY_UNSUPPORTED", "block_id": block_id, "level": level,
                       "keys": sorted(unsupported)})
    years = raw.get("data_years")
    if years is not None:
        if isinstance(years, list) and all(isinstance(year, int) and not isinstance(year, bool) for year in years):
            scope["data_years"] = sorted(set(years))
        else:
            unsupported["data_years"] = copy.deepcopy(years)
            issues.append({"code": "TEMPORAL_DATA_YEARS_INVALID", "block_id": block_id, "level": level})
    for key in MILESTONES:
        if key not in raw:
            continue
        value = raw[key]
        if (isinstance(value, dict) and value.get("precision") in {"day", "month", "year"}
                and "raw" in value and "value" in value):
            scope[key] = copy.deepcopy(value)
        else:
            unsupported[key] = copy.deepcopy(value)
            issues.append({"code": "TEMPORAL_MILESTONE_INVALID", "block_id": block_id, "level": level, "key": key})
    for key in ("academic_year", "recurrence"):
        if key in raw:
            value = raw[key]
            if isinstance(value, (str, dict)):
                scope[key] = copy.deepcopy(value)
            else:
                unsupported[key] = copy.deepcopy(value)
                issues.append({"code": "TEMPORAL_VALUE_UNSUPPORTED", "block_id": block_id, "level": level, "key": key})
    basis = raw.get("basis_quote")
    if basis is not None:
        if isinstance(basis, str) and basis.strip():
            scope["basis_quote"] = basis
        else:
            unsupported["basis_quote"] = copy.deepcopy(basis)
            issues.append({"code": "TEMPORAL_BASIS_INVALID", "block_id": block_id, "level": level})
    if "status" in raw:
        # File metadata cannot certify itself; only the review mechanism can.
        unsupported["status"] = copy.deepcopy(raw["status"])
        issues.append({"code": "TEMPORAL_STATUS_NOT_ACCEPTED", "block_id": block_id, "level": level})
    has_scope = bool(scope.get("data_years") or scope.get("academic_year") or scope.get("recurrence")
                     or any(scope.get(key) for key in MILESTONES))
    if not has_scope:
        if unsupported:
            issues.append({"code": "TEMPORAL_SCOPE_UNRESOLVED", "block_id": block_id, "level": level})
            return {"status": "ambiguous", "role": "unknown", "scope_level": level, "unsupported": unsupported}
        return {}
    basis = scope.get("basis_quote")
    basis_ok = bool(basis and ((text and basis in text) or (header and basis in header)))
    declared_years = set(scope.get("data_years") or [])
    header_years = {int(year) for year in YEAR.findall(header)} if level in {"column", "field"} else set()
    if declared_years and header_years and not declared_years.issubset(header_years):
        basis_ok = False
        issues.append({"code": "TEMPORAL_HEADER_CONFLICT", "block_id": block_id, "level": level})
    if basis_ok and (not declared_years or declared_years.issubset({int(year) for year in YEAR.findall(basis)})):
        status = "proposed"
    else:
        status = "ambiguous"
        issues.append({"code": "TEMPORAL_BASIS_MISSING" if not basis else "TEMPORAL_BASIS_UNSUPPORTED",
                       "block_id": block_id, "level": level})
    role = ("data" if declared_years else "effective" if any(scope.get(key) for key in MILESTONES[:2])
            else "event" if any(scope.get(key) for key in MILESTONES[2:]) else "unknown")
    return {**scope, "status": status, "role": role, "scope_level": level, "unsupported": unsupported}


def _scope_key(scope: dict) -> tuple:
    return tuple((key, json.dumps(scope.get(key), sort_keys=True, ensure_ascii=False))
                 for key in (*TEMPORAL_KEYS, "status", "role", "scope_level", "unsupported"))


def _apply_scope(target: TemporalScope, declared: dict) -> TemporalScope:
    for key in ("data_years", *TEMPORAL_KEYS - {"data_years", "basis_quote"}, "basis_quote",
                "scope_level", "unsupported", "status", "role"):
        if key in declared:
            setattr(target, key, copy.deepcopy(declared[key]))
    target.evidence_quote = declared.get("basis_quote")
    return target


def _aggregate_scopes(scopes: list[dict], *, basis: str, level: str, require_full: bool = False) -> dict:
    """A container row/table never turns one declared year into every cell's year.

    Different cell scopes keep their union at container level and are marked
    ambiguous only when a declaration itself is ambiguous or its basis does not
    contain the declared years. ``require_full`` refuses to summarize a partially
    scoped container: an unknown sibling must not inherit a declared year.
    """
    explicit = [scope for scope in scopes if scope and (
        scope.get("data_years") or scope.get("academic_year") or scope.get("recurrence")
        or any(scope.get(milestone) for milestone in MILESTONES)
        or scope.get("scope_level") not in {None, "unknown"})]
    if not explicit or (require_full and any(not scope for scope in scopes)):
        return {}
    if len({_scope_key(scope) for scope in explicit}) == 1:
        scope = copy.deepcopy(explicit[0])
        scope["scope_level"] = level
        scope["basis_quote"] = scope.get("basis_quote") or basis or None
        return scope
    years = sorted({year for scope in explicit for year in scope.get("data_years") or []})
    roles = {scope.get("role", "unknown") for scope in explicit}
    statuses = {scope.get("status", "unknown") for scope in explicit}
    basis_years = {int(year) for year in YEAR.findall(basis or "")}
    unknown_years = bool(years) and not set(years).issubset(basis_years)
    result: dict[str, Any] = {"data_years": years, "basis_quote": basis or None,
        "status": "verified" if statuses == {"verified"} and not unknown_years
        else "ambiguous" if "ambiguous" in statuses or unknown_years else "proposed",
        "role": "data" if roles == {"data"} else "unknown", "scope_level": level, "unsupported": {}}
    for key in (*MILESTONES, "academic_year", "recurrence"):
        values = [scope.get(key) for scope in explicit if scope.get(key)]
        if not values:
            continue
        if len({json.dumps(value, sort_keys=True, ensure_ascii=False) for value in values}) == 1:
            result[key] = copy.deepcopy(values[0])
        else:
            result["unsupported"][key] = copy.deepcopy(values)
    return result


def _page(block: QnuBlock) -> int | None:
    pages = {location.page for location in block.source_locations}
    return next(iter(pages)) if len(pages) == 1 else None


def _cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def _line(values: list[str]) -> str:
    return "| " + " | ".join(_cell(value) for value in values) + " |"


def _table(block: QnuBlock, rows: list[QnuBlock]) -> tuple[str, list[str], list[list[str]], list[list[str]]]:
    columns = block.attributes.get("columns", [])
    paths = [column["header_path"] for column in columns]
    headers = [" / ".join(path) for path in paths]
    if block.attributes.get("representation") == "records":
        if any(set(row.attributes.get("fields", {})) != {column["id"] for column in columns} for row in rows):
            raise ValueError("Record fields must cover exactly the declared columns")
        values = [[row.attributes["fields"][column["id"]]["raw"] for column in columns] for row in rows]
        text = "\n".join([_line(headers), _line(["---"] * len(headers)), *[_line(row) for row in values]])
        return text, headers, values, paths
    lines = [line for line in block.body.splitlines() if line.strip()]
    if len(lines) < 2:
        if block.body.strip():
            raise ValueError("A nonempty GFM table must contain a header and separator")
        return block.body, [], [], []
    parsed_headers, values = parse_qnu_gfm_table(block.body)
    paths = paths or [[header] for header in parsed_headers]
    headers = [" / ".join(path) for path in paths]
    if parsed_headers not in (headers, [path[-1] if path else "" for path in paths]):
        raise ValueError("GFM headers disagree with declared column paths")
    if len(headers) != len(parsed_headers) or any(len(row) != len(headers) for row in values):
        raise ValueError("GFM table width differs from its columns")
    return "\n".join([_line(headers), _line(["---"] * len(headers)), *[_line(row) for row in values]]), headers, values, paths


def project_document(document: QnuStructuredDocument, reference: dict, metadata: dict) -> tuple[str, dict]:
    """Strip transport metadata, retaining exact block/cell locations and explicit dependencies."""
    parts: list[str] = []
    units: list[SourceUnit] = []
    tables: list[dict] = []
    row_sources: dict[tuple[str, int], QnuBlock] = {}
    row_cells: dict[tuple[str, int], list[dict]] = {}
    row_unit_ids: dict[tuple[str, int], str] = {}
    projection_issues: list[dict] = []
    blocks = {block.id: block for block in document.blocks}
    offset = 0

    def append(block: QnuBlock, body: str, *, container: bool = False) -> SourceUnit | None:
        nonlocal offset
        body = body.strip("\n")
        if not body.strip():
            return None
        if parts:
            offset += 2
        start = offset
        parts.append(body)
        offset += len(body)
        kind = {"section": "heading", "list": "list", "table": "table"}.get(block.type, "paragraph")
        unit = SourceUnit(id=f"qnu:{block.id}", kind=kind, text=body, start=start, end=offset,
            page_number=_page(block), heading_path=block.section_path, is_container=container,
            qnu_block_id=block.id, source_locations=[loc.model_dump() for loc in block.source_locations])
        units.append(unit)
        return unit

    for block in document.blocks:
        if block.type in {"table_row", "derived_index"}:
            continue  # Records are emitted once under their table; indexes are not source evidence.
        if block.type != "table":
            unit = append(block, block.body)
            if unit is not None:
                declared = _declared_temporal(block.attributes.get("temporal"), block_id=block.id,
                    level="block", text=unit.text, header="", issues=projection_issues)
                if declared:
                    _apply_scope(unit.temporal, declared)
            continue
        rows = [row for row in document.blocks if row.parent_id == block.id and row.type == "table_row"]
        representation = block.attributes.get("representation")
        state_source = "declared" if representation == "records" else "derived"
        text, headers, values, paths = _table(block, rows)
        parent = append(block, text, container=True)
        if not parent or not headers:
            continue
        # Row spans come from the known emitted lines, not table/header recognition heuristics.
        lines = list(re.finditer(r"[^\n]+", text))
        header = "\n".join(line.group() for line in lines[:2])
        header_unit = parent.model_copy(deep=True, update={"id": f"{parent.id}:header", "parent_id": parent.id,
            "text": header, "end": parent.start + len(header), "is_container": False, "header_context": header})
        units.append(header_unit)
        declared_columns = [column for column in block.attributes.get("columns") or []
                            if isinstance(column, dict) and isinstance(column.get("id"), str)]
        if len(declared_columns) != len(headers):
            declared_columns = []
        column_defs = [{"id": column["id"], "header_path": column.get("header_path") or paths[index],
                        "temporal": column.get("temporal")} for index, column in enumerate(declared_columns)] or [
            {"id": f"c{index + 1:02d}", "header_path": paths[index], "temporal": None}
            for index in range(len(headers))]
        table_scope = _declared_temporal(block.attributes.get("temporal"), block_id=block.id, level="block",
                                         text=text, header=header, issues=projection_issues)
        column_scopes = [_declared_temporal(column.get("temporal"), block_id=block.id, level="column",
                          text="", header=headers[index], issues=projection_issues)
                         for index, column in enumerate(column_defs)]
        row_scopes = []
        for index, line in enumerate(lines[2:]):
            source = rows[index] if rows else block
            row_id = f"qnu:{source.id}" if rows else f"{parent.id}:row:{index}"
            row_unit = SourceUnit(id=row_id, parent_id=parent.id, kind="table", text=line.group(),
                start=parent.start + line.start(), end=parent.start + line.end(), page_number=_page(source),
                heading_path=block.section_path, header_context=header, qnu_block_id=source.id,
                source_locations=[loc.model_dump() for loc in source.source_locations])
            units.append(row_unit)
            row_declared = _declared_temporal(source.attributes.get("temporal") if rows else None,
                block_id=source.id, level="row", text=line.group(), header=header, issues=projection_issues)
            elements = []
            for column_index, (column_def, value) in enumerate(zip(column_defs, values[index], strict=True)):
                if rows:
                    raw_field = _mapping(source.attributes["fields"][column_def["id"]])
                    field_source = (source.attributes.get("field_sources") or {}).get(column_def["id"])
                    field_origin = (source.attributes.get("field_origins") or {}).get(column_def["id"])
                else:
                    raw_field = {"raw": value, "state": cell_state(value), "normalized": None}
                    field_source = field_origin = None
                state = raw_field.get("state")
                if state not in QNU_CELL_STATES:
                    projection_issues.append({"code": "CELL_STATE_UNAVAILABLE", "block_id": source.id,
                        "table_id": parent.id, "row_index": index, "column_index": column_index})
                    state = "ambiguous"
                normalized = raw_field.get("normalized")
                if state != "present" and normalized is not None:
                    projection_issues.append({"code": "CELL_NORMALIZED_UNSUPPORTED", "block_id": source.id,
                        "table_id": parent.id, "row_index": index, "column_index": column_index})
                    normalized = None  # A non-present state can never carry a numeric value.
                field_declared = _declared_temporal(raw_field.get("temporal"), block_id=source.id, level="field",
                    text=raw_field.get("raw") or "", header=headers[column_index], issues=projection_issues)
                cell_scope = (field_declared or column_scopes[column_index] or row_declared or table_scope)
                header_years = sorted({int(year) for year in YEAR.findall(headers[column_index])})
                header_temporal = ({"data_years": header_years, "basis_quote": headers[column_index],
                    "scope_level": "column", "status": "proposed", "role": "data", "unsupported": {}}
                    if len(header_years) == 1 else None)
                elements.append({"raw": raw_field.get("raw", value), "state": state,
                    "normalized": normalized, "column_id": column_def["id"],
                    "column_index": column_index, "header_path": column_def["header_path"] or paths[column_index],
                    "header": headers[column_index], "field_source": field_source,
                    "field_origin": field_origin, "temporal": copy.deepcopy(cell_scope) if cell_scope else None,
                    "header_temporal": header_temporal, "standard": True, "state_source": state_source})
            row_cells[(parent.id, index)] = elements
            row_scopes.append(_aggregate_scopes([field.get("temporal") for field in elements],
                                                basis=header, level="row", require_full=True))
            if row_scopes[-1]:
                _apply_scope(row_unit.temporal, row_scopes[-1])
            row_unit_ids[(parent.id, index)] = row_id
            row_sources[(parent.id, index)] = source
        header_scope = _aggregate_scopes(column_scopes, basis=header, level="column", require_full=True)
        if header_scope:
            _apply_scope(header_unit.temporal, header_scope)
        table_row_scope = _aggregate_scopes(row_scopes, basis=header, level="block", require_full=True)
        if table_row_scope:
            _apply_scope(parent.temporal, table_row_scope)
        elif table_scope:
            _apply_scope(parent.temporal, table_scope)
        tables.append({"id": parent.id, "headers": headers, "header_paths": paths, "header_rows": [headers],
            "rows": values, "page_number": _page(block), "header_page_number": _page(block),
            "row_fields": [row_cells[(parent.id, index)] for index in range(len(values))],
            "columns": column_defs, "row_unit_ids": [row_unit_ids[(parent.id, index)] for index in range(len(values))],
            "standard": True, "cell_state_source": state_source, "evidence": VERSION})
    canonical = "\n\n".join(parts)
    artifact = build_source_artifact(canonical, document.source.page_count or 0, metadata, context_tables=tables)
    issued = (artifact.get("temporal_metadata") or {}).get("issued_date")
    issued_date = issued.get("value") if isinstance(issued, dict) else None
    if isinstance(issued_date, str) and issued_date:
        for unit in units:
            unit.temporal.issued_date = issued_date  # Document issue date, never a data-year claim.
    by_id = {unit.id: unit for unit in units}
    for unit in units:
        block = blocks[unit.qnu_block_id]
        if unit.parent_id is None and block.parent_id and f"qnu:{block.parent_id}" in by_id:
            parent = by_id[f"qnu:{block.parent_id}"]
            if parent.kind == "heading":
                unit.parent_id = parent.id
        refs = list(block.context_refs)
        if block.parent_id and block.type not in {"table_row", "table"}:
            parent_ref = f"qnu:{block.parent_id}"
            if parent_ref in by_id and by_id[parent_ref].kind != "heading":
                if by_id[parent_ref].is_container and block.type == "note":
                    parent_ref = ""  # A shared table note must not point back to its own header.
                if parent_ref and by_id[parent_ref].is_container:
                    parent_ref += ":header"
                if parent_ref in by_id:
                    unit.context_refs.append(parent_ref)
        if block.type == "table_row" and block.parent_id:
            refs.extend(blocks[block.parent_id].context_refs)
            unit.context_refs.append(f"qnu:{block.parent_id}:header")
        for ref in refs:
            target = f"qnu:{ref}"
            if target in by_id and by_id[target].is_container:
                target += ":header"
            if target not in by_id:
                raise ValueError("Context target has no source content")
            if target == unit.id:
                raise ValueError("A standard block cannot depend on itself")
            unit.context_refs.append(target)
        unit.context_refs = list(dict.fromkeys(unit.context_refs))
    for unit in units:
        unit.temporal.mentioned_years = sorted({int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", unit.text)})
        unit.temporal.heading_years = sorted({int(year) for path in unit.heading_path for year in re.findall(r"\b(?:19|20)\d{2}\b", path)})
        declared = (unit.temporal.scope_level != "unknown" or bool(unit.temporal.unsupported)
                    or bool(unit.temporal.data_years) or bool(unit.temporal.academic_year)
                    or bool(unit.temporal.recurrence)
                    or any(getattr(unit.temporal, key) for key in MILESTONES))
        if not declared:
            unit.temporal.status = "proposed" if unit.temporal.mentioned_years or unit.temporal.heading_years else "unknown"
    manifest = UnitManifest(canonical_hash=hashlib.sha256(canonical.encode()).hexdigest(), units=units)
    validate_manifest(manifest, canonical)
    manifest_hash = manifest_digest(manifest)
    artifact["input_format"] = VERSION
    artifact["unresolved_cell_count"] = sum(field.get("state") in {"ambiguous", "unreadable"}
        for fields in row_cells.values() for field in fields)
    artifact["issues"].extend(projection_issues)
    artifact["issues"].extend({"code": "ambiguous_cell", "table_id": table_id, "row_index": index,
                               "column_index": column}
        for (table_id, index), fields in row_cells.items() if row_sources[(table_id, index)].type == "table"
        for column, field in enumerate(fields) if field["state"] in {"ambiguous", "unreadable"})
    artifact["qnu_input"] = {**reference, "projection_hash": manifest.canonical_hash, "version": VERSION}
    graph = build_context_graph(manifest)
    attach_fact_context(artifact["facts"], manifest, graph)
    for fact in artifact["facts"]:
        raw = fact["raw_data"]
        block = row_sources[(raw["table_id"], raw["row_index"])]
        field = row_cells[(raw["table_id"], raw["row_index"])][raw["column_index"]]
        scope = field.get("temporal")
        raw.update(qnu_block_id=block.id, source_locations=[loc.model_dump() for loc in block.source_locations],
            field_source=field.get("field_source"), field_origin=field.get("field_origin"),
            field_state=field.get("state"), page_number=_page(block),
            source_unit_id=row_unit_ids[(raw["table_id"], raw["row_index"])],
            projection_version=VERSION, unit_manifest_hash=manifest_hash)
        if scope:
            years = list(scope.get("data_years") or [])
            raw["temporal_context"] = {
                "type": "year" if len(years) == 1 else "years" if years else "unknown",
                "year": years[0] if len(years) == 1 else None, "years": years,
                "status": scope.get("status", "unknown"), "role": scope.get("role", "unknown"),
                "scope_level": scope.get("scope_level", "unknown"), "basis_quote": scope.get("basis_quote"),
                "evidence": "declared_temporal",
                **{key: copy.deepcopy(scope[key]) for key in MILESTONES if scope.get(key)},
            }
        else:
            context = dict(raw.get("temporal_context") or {})
            raw["temporal_context"] = {
                **context, "role": context.get("role", "data" if context.get("year") else "unknown"),
                "scope_level": context.get("scope_level", "column" if context.get("year") else "unknown"),
            }
        raw["context_unit_ids"] = graph["links"].get(raw["source_unit_id"], [])
        raw["context_graph_hash"] = graph["digest"]
    artifact["facts"] = [fact for fact in artifact["facts"] if fact["raw_data"].get("field_state") == "present"]
    artifact["retrieval_units"] = manifest.model_dump()
    artifact["unit_manifest_hash"] = manifest_hash
    artifact["context_graph"] = graph
    artifact["fact_set_hash"] = digest(artifact["facts"])
    artifact["derived_indexes"] = [{"type": "table_rows", "table_id": table["id"],
        "members": [unit.id for unit in units if unit.parent_id == table["id"] and not unit.id.endswith(":header")],
        "count": len(table["rows"]), "coverage": "source_table", "input_hash": reference["structured_sha256"]}
        for table in tables]
    artifact["issues"].extend({"code": flag.code, "block_id": block.id, "field_id": flag.field_id}
        for block in document.blocks for flag in block.quality_flags if flag.status == "unresolved")
    explicit_targets = {ref for block in document.blocks for ref in block.context_refs}
    artifact["issues"].extend({"code": "table_note_scope_unresolved", "block_id": block.id}
        for block in document.blocks if block.type == "note" and block.parent_id in blocks
        and blocks[block.parent_id].type == "table" and block.id not in explicit_targets)
    artifact["review"] = {"status": "required"}  # File metadata cannot approve data.
    return canonical, artifact
