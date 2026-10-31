"""Atomic source units: one text block, or one data row of a parsed table.

Ownership is always expressed over these units so a part can never take half a row
or share a row with another part.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Unit:
    document_index: int
    page_index: int
    page_number: int
    block_index: int
    ocr_run_id: str
    evidence_id: str
    kind: str
    row_index: int | None = None
    header_rows: tuple[int, ...] = ()


def header_row_indexes(rows: list[list[dict]]) -> tuple[int, ...]:
    leading = 0
    for row in rows:
        if not row or not all(cell.get("header") for cell in row):
            break
        leading += 1
    if leading == len(rows):
        return ()
    return tuple(range(leading))


def build_units(documents: list[dict]) -> list[Unit]:
    """One unit per text block, or per data row of a parsed table; never a half row."""
    units: list[Unit] = []
    for document_index, document in enumerate(documents):
        for page_index, page in enumerate(document["pages"]):
            for block_index, block in enumerate(page["blocks"]):
                table = block.get("table")
                rows = table.get("rows") if table and table.get("status") == "parsed" else None
                headers = header_row_indexes(rows) if rows else ()
                data_rows = [index for index in range(len(rows or [])) if index not in headers]
                common = {
                    "document_index": document_index,
                    "page_index": page_index,
                    "page_number": page["page_number"],
                    "block_index": block_index,
                    "ocr_run_id": document["ocr_run_id"],
                    "evidence_id": block["evidence_id"],
                }
                if data_rows:
                    units.extend(
                        Unit(**common, kind="table_row", row_index=row, header_rows=headers)
                        for row in data_rows
                    )
                else:
                    units.append(Unit(**common, kind="block"))
    return units


def _block_ref(unit: Unit) -> dict:
    return {
        "kind": "block",
        "ocr_run_id": unit.ocr_run_id,
        "page": unit.page_number,
        "evidence_id": unit.evidence_id,
    }


def owned_refs(units: list[Unit]) -> tuple[dict, ...]:
    """Group consecutive table-row units; ownership stays per source row."""
    refs: list[dict] = []
    table: dict | None = None
    for unit in units:
        if unit.kind == "block":
            table = None
            refs.append(_block_ref(unit))
            continue
        key = (unit.ocr_run_id, unit.page_number, unit.evidence_id)
        if table is None or table["_key"] != key:
            table = {
                "_key": key,
                "kind": "table_rows",
                "ocr_run_id": unit.ocr_run_id,
                "page": unit.page_number,
                "evidence_id": unit.evidence_id,
                "rows": [],
                "header_rows": list(unit.header_rows),
            }
            refs.append(table)
        table["rows"].append(unit.row_index)
    for ref in refs:
        ref.pop("_key", None)
    return tuple(refs)


def ref_key(ref: dict) -> tuple:
    return (
        ref["ocr_run_id"],
        ref["page"],
        ref["evidence_id"],
        ref["kind"],
        tuple(ref.get("rows", ())),
    )


# Kept for callers written against the previous private name.
_ref_key = ref_key
