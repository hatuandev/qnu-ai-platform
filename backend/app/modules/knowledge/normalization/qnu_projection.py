"""Deterministic serving projection of the standard, never a second RAG engine."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuStructuredDocument,
    parse_qnu_gfm_table,
)
from app.modules.knowledge.normalization.retrieval_models import SourceUnit, UnitManifest
from app.modules.knowledge.normalization.retrieval_units import manifest_digest, validate_manifest
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.source_links import attach_fact_context, build_context_graph

VERSION = "qnu-rag-projection/v1"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


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
            append(block, block.body)
            continue
        rows = [row for row in document.blocks if row.parent_id == block.id and row.type == "table_row"]
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
        for index, line in enumerate(lines[2:]):
            source = rows[index] if rows else block
            row_id = f"qnu:{source.id}" if rows else f"{parent.id}:row:{index}"
            units.append(SourceUnit(id=row_id, parent_id=parent.id, kind="table", text=line.group(),
                start=parent.start + line.start(), end=parent.start + line.end(), page_number=_page(source),
                heading_path=block.section_path, header_context=header, qnu_block_id=source.id,
                source_locations=[loc.model_dump() for loc in source.source_locations]))
            row_sources[(parent.id, index)] = source
        tables.append({"id": parent.id, "headers": headers, "header_paths": paths, "header_rows": [headers],
            "rows": values, "page_number": _page(block), "header_page_number": _page(block),
            "evidence": VERSION})
    canonical = "\n\n".join(parts)
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
        unit.temporal.status = "proposed" if unit.temporal.mentioned_years or unit.temporal.heading_years else "unknown"
    manifest = UnitManifest(canonical_hash=hashlib.sha256(canonical.encode()).hexdigest(), units=units)
    validate_manifest(manifest, canonical)
    artifact = build_source_artifact(canonical, document.source.page_count or 0, metadata, context_tables=tables)
    artifact["input_format"] = VERSION
    artifact["unresolved_cell_count"] = sum(field.get("state") in {"ambiguous", "unreadable"}
        for block in document.blocks for field in block.attributes.get("fields", {}).values())
    artifact["qnu_input"] = {**reference, "projection_hash": manifest.canonical_hash, "version": VERSION}
    graph = build_context_graph(manifest)
    attach_fact_context(artifact["facts"], manifest, graph)
    for fact in artifact["facts"]:
        raw = fact["raw_data"]
        block = row_sources[(raw["table_id"], raw["row_index"])]
        column = blocks[block.parent_id].attributes["columns"][raw["column_index"]] if block.type == "table_row" else None
        if column:
            key = column["id"]
            raw.update(qnu_block_id=block.id, source_locations=[loc.model_dump() for loc in block.source_locations],
                field_source=block.attributes.get("field_sources", {}).get(key),
                field_origin=block.attributes.get("field_origins", {}).get(key),
                field_state=block.attributes["fields"][key]["state"], page_number=_page(block),
                source_unit_id=f"qnu:{block.id}")
            raw["context_unit_ids"] = graph["links"].get(raw["source_unit_id"], [])
            raw["context_graph_hash"] = graph["digest"]
    artifact["facts"] = [fact for fact in artifact["facts"] if fact["raw_data"].get("field_state", "present") == "present"]
    artifact["retrieval_units"] = manifest.model_dump()
    artifact["unit_manifest_hash"] = manifest_digest(manifest)
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
