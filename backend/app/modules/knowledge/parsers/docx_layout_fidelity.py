"""Verify literal table coverage against native OOXML, without assigning semantic roles.

An untyped column or full-width merged cell is usable only as a source literal.
No group membership, numeric fact or header role is inferred from its text.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from io import BytesIO

from docx import Document
from docx.oxml.ns import qn

from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument

VERSION = "docx-native-layout/v1"


def _text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n"))


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _native(content: bytes) -> list[dict]:
    tables = []
    for index, table in enumerate(Document(BytesIO(content)).tables):
        grid = [[_text(c.text) for c in row.cells] for row in table.rows]
        origins: dict[object, list[tuple[int, int]]] = {}
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                origins.setdefault(cell._tc, []).append((ri, ci))
        cells = []
        for coordinates in origins.values():
            rs, cs = zip(*coordinates, strict=True)
            r0, c0, r1, c1 = min(rs), min(cs), max(rs) + 1, max(cs) + 1
            if len(coordinates) != (r1 - r0) * (c1 - c0):
                break  # Nonrectangular/incomplete coverage cannot certify a grid.
            cells.append({"row_start": r0, "row_end": r1, "col_start": c0, "col_end": c1, "text": grid[r0][c0]})
        else:
            flags = []
            for row in table.rows:
                tr = row._tr.trPr
                flag = tr.find(qn("w:tblHeader")) if tr is not None else None
                flags.append(flag is not None and flag.get(qn("w:val"), "1") not in {"0", "false", "off"})
            depth = next((i for i, enabled in enumerate(flags) if not enabled), len(flags))
            tables.append({"locator": f"word/document.xml/table/{index + 1}", "grid": grid,
                           "cells": sorted(cells, key=lambda c: (c["row_start"], c["col_start"])), "header_rows": depth})
    return tables


def _matched_table(block, native: list[dict], rows: list) -> dict | None:
    data = block.source_data or {}
    cells = [{k: cell.get(k) for k in ("row_start", "row_end", "col_start", "col_end", "text")}
             for cell in data.get("cells", [])]
    cells.sort(key=lambda c: (c["row_start"], c["col_start"]))
    # Header roles cannot disambiguate the very source association being proved.
    matches = [n for n in native if n["cells"] == cells]
    if len(matches) != 1:
        return None
    source = matches[0]
    if source["header_rows"] != data.get("header_rows"):
        return None
    grid = source["grid"]
    if (len(grid) != data.get("num_rows") or any(len(r) != data.get("num_cols") for r in grid)
            or len(rows) != len(grid) - source["header_rows"]):
        return None
    for row, expected in zip(rows, grid[source["header_rows"]:], strict=True):
        fields = row.attributes.get("fields", {})
        if list(fields) != [f"c{i + 1:02d}" for i in range(len(expected))]:
            return None
        if [f.get("raw") for f in fields.values()] != expected:
            return None
    return source


def preserve_native_layout(document: QnuStructuredDocument, content: bytes) -> None:
    """Only replace role-dependent fields after every native cell/span is accounted for."""
    if hashlib.sha256(content).hexdigest() != document.source.sha256:
        return
    native = _native(content)
    for table in (b for b in document.blocks if b.type == "table"):
        rows = [b for b in document.blocks if b.type == "table_row" and b.parent_id == table.id]
        source = _matched_table(table, native, rows)
        if source is None or not rows:
            continue
        untyped = source["header_rows"] == 0
        table.attributes["native_layout"] = {"version": VERSION, "source_sha256": document.source.sha256,
            "locator": source["locator"], "grid_sha256": _digest(source), "semantic_roles_verified": False}
        if untyped:
            table.attributes["column_roles"] = "unknown"
            for flag in table.quality_flags:
                if flag.code == "table_header_unresolved":
                    flag.status = "literal_only"
        for index, row in enumerate(rows, source["header_rows"]):
            merged = any(c["row_start"] == index and c["row_end"] == index + 1 and c["col_start"] == 0
                         and c["col_end"] == len(source["grid"][index]) for c in source["cells"]) and len(source["grid"][index]) > 1
            if merged:
                row.attributes["row_role"] = "source_merged_literal"
                row.body = source["grid"][index][0]
                row.quality_flags = [f for f in row.quality_flags if f.code != "spanning_row_needs_review"]
            if untyped or merged:
                row.attributes["interpretation"] = "literal_only"
                for field in row.attributes["fields"].values():
                    if field["state"] == "present":
                        field.update(state="ambiguous", normalized=None)


def verify_native_layout(document: QnuStructuredDocument, content: bytes) -> None:
    """Recompute native proof and literal-only restrictions before chunk/index/publication."""
    if not any(b.attributes.get("native_layout") for b in document.blocks):
        return
    expected = document.model_copy(deep=True)
    preserve_native_layout(expected, content)
    native = _native(content)
    for table in (b for b in document.blocks if b.attributes.get("native_layout")):
        rows = [b for b in document.blocks if b.type == "table_row" and b.parent_id == table.id]
        source = _matched_table(table, native, rows)
        if source is None or table.attributes["native_layout"].get("grid_sha256") != _digest(source):
            raise ValueError("DOCX_NATIVE_LAYOUT_MISMATCH")
    for actual, checked in zip(document.blocks, expected.blocks, strict=True):
        if actual.model_dump() != checked.model_dump():
            raise ValueError("DOCX_LITERAL_RESTRICTION_MISMATCH")
