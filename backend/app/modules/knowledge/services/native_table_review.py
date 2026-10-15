"""Build a table-only native correction and persist an isolated human-review revision."""

import copy
import hashlib
import json
import re
from datetime import UTC, datetime

import pymupdf
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.parsers.native_headers import native_header_matrix
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.source_pages import canonical_pages
from app.modules.knowledge.services.table_context import extract_context_tables

VERSION = "native-table-review-v1"


def comparable(value: str) -> str:
    return " ".join(value.replace("<br>", " ").split())


def extract_native_evidence(content: bytes) -> tuple[list[dict], int]:
    tables = []
    numeric_cells = 0
    with pymupdf.open(stream=content, filetype="pdf") as document:
        for page in document:
            words = page.get_text("words")
            for table in page.find_tables().tables:
                matrix, depth = native_header_matrix(table)
                if not matrix or any(not header for header in matrix[0]):
                    raise ValueError("Native header geometry is unresolved")
                cells = []
                for row_index, row in enumerate(matrix[1:]):
                    boxes = table.rows[row_index + depth].cells
                    for column, value in enumerate(row):
                        box = boxes[column]
                        if value and box is None:
                            raise ValueError("Data cell has no unique geometry")
                        if box and re.fullmatch(r"\d+(?:[.,]\d+)?%?", value):
                            visible = "".join(word[4] for word in words
                                if box[0] <= (word[0] + word[2]) / 2 < box[2]
                                and box[1] <= (word[1] + word[3]) / 2 < box[3])
                            if visible != value.replace(" ", ""):
                                raise ValueError("Numeric cell does not match independently located PDF words")
                            numeric_cells += 1
                        cells.append({"row_index": row_index, "column_index": column,
                                      "value": value, "bbox": list(box) if box else None})
                tables.append({"page_number": page.number + 1, "headers": matrix[0],
                    "rows": matrix[1:], "bbox": list(table.bbox), "cells": cells,
                    "header_depth": depth})
    return tables, numeric_cells


def table_markdown(table: dict) -> str:
    def line(row: list[str]) -> str:
        return "| " + " | ".join(value.replace("|", "\\|").replace("\n", "<br>") for value in row) + " |"
    return "\n".join([line(table["headers"]), line(["---"] * len(table["headers"])),
                      *(line(row) for row in table["rows"])])


def replace_tables_only(markdown: str, native: list[dict], page_count: int) -> tuple[str, list[dict]]:
    existing = extract_context_tables(markdown, page_count)
    if len(existing) != len(native):
        raise ValueError("Native and canonical table inventories differ; review manually")
    pages = {page["page_number"]: page["markdown_content"] for page in canonical_pages(markdown, page_count)}
    edits = []
    for old, new in zip(existing, native, strict=True):
        if old["page_number"] != new["page_number"] or len(old["rows"]) != len(new["rows"]):
            raise ValueError("Page/row inventory differs; automatic table replacement is unsafe")
        headers = [comparable(value) for value in new["headers"]]
        if len(set(headers)) != len(headers):
            raise ValueError("Native column identity is ambiguous")
        columns = [headers.index(comparable(header)) for header in old["headers"]]
        if any(comparable(value) != comparable(new["rows"][row][columns[col]])
               for row, values in enumerate(old["rows"]) for col, value in enumerate(values)):
            raise ValueError("Existing cells disagree with native source; review manually")
        if len(old["headers"]) == len(headers):
            continue  # Already correct tables and surrounding prose stay byte-identical.
        page_text = pages[old["page_number"]]
        if markdown.count(page_text) != 1:
            raise ValueError("Page location is ambiguous")
        page_start = markdown.index(page_text)
        lines = page_text.splitlines(keepends=True)
        start = page_start + sum(map(len, lines[:old["line_number"] - 1]))
        end = page_start + sum(map(len, lines[:old["end_line_number"]]))
        suffix = "\n" if markdown[start:end].endswith("\n") else ""
        edits.append({"start": start, "end": end, "page_number": old["page_number"],
                      "old_columns": len(old["headers"]), "new_columns": len(headers),
                      "replacement": table_markdown(new) + suffix})
    result = markdown
    for edit in reversed(edits):
        result = result[:edit["start"]] + edit["replacement"] + result[edit["end"]:]
    return result, edits


async def create_native_table_draft(db: AsyncSession, *, collection_id: str, source_id: str,
        base_revision_id: str, tenant_id: str, workspace_id: str, content: bytes) -> KnowledgeSourceRevision:
    from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
    from app.modules.knowledge.services.source_reparse import ensure_source_idle, lock_source

    await lock_source(db, source_id)
    binding = await source_ingestion_service.get_source(db, collection_id, source_id, tenant_id, workspace_id)
    await ensure_source_idle(db, source_id)
    base = await db.get(KnowledgeSourceRevision, base_revision_id)
    digest = hashlib.sha256(content).hexdigest()
    if base is None or base.binding_id != binding.id or base.origin_file_hash != digest:
        raise AppException("Tệp/bản nguồn không khớp phạm vi đã chọn.", code="NATIVE_REVIEW_SOURCE_MISMATCH", status_code=409)
    if binding.active_source_revision_id != base.id:
        raise AppException("Bản nguồn hiện tại đã thay đổi.", code="NATIVE_REVIEW_BASE_CHANGED", status_code=409)
    # Native PDF work is local; no OCR, model, storage write or publication calls.
    import asyncio

    native, count = await asyncio.to_thread(extract_native_evidence, content)
    markdown, edits = replace_tables_only(base.canonical_markdown or "", native, len(base.page_manifest))
    if not edits:
        raise AppException("Bảng đã đầy đủ; không tạo bản trùng.", code="NATIVE_REVIEW_NO_CHANGE", status_code=409)
    artifact = build_source_artifact(markdown, len(base.page_manifest), base.citation_metadata, native)
    for fact in artifact["facts"]:
        raw = fact["raw_data"]
        matches = [table for table in native if table["page_number"] == raw["page_number"]]
        if len(matches) == 1:
            cells = [cell for cell in matches[0]["cells"] if cell["row_index"] == raw["row_index"]
                     and cell["column_index"] == raw["column_index"] and comparable(cell["value"]) == comparable(raw["raw_value"])]
            if len(cells) == 1:
                raw["native_cell_bbox"] = cells[0]["bbox"]
                raw["origin_file_hash"] = digest
    artifact["fact_set_hash"] = hashlib.sha256(json.dumps(
        artifact["facts"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    artifact["issues"].append({"code": "NATIVE_TABLE_HUMAN_REVIEW_REQUIRED", "pages": [edit["page_number"] for edit in edits]})
    artifact["review"] = {"status": "required"}
    number = (await db.execute(select(func.max(KnowledgeSourceRevision.revision_no)).where(
        KnowledgeSourceRevision.binding_id == binding.id))).scalar_one() or 0
    # A repeated run against the same active base must not create duplicate drafts.
    key = hashlib.sha256(f"{VERSION}:{binding.id}:{base.id}:{digest}".encode()).hexdigest()
    duplicate = (await db.execute(select(KnowledgeSourceRevision.id).where(
        KnowledgeSourceRevision.binding_id == binding.id, KnowledgeSourceRevision.artifact_key == key))).scalar_one_or_none()
    if duplicate:
        raise AppException("Đã có bản bảng chờ duyệt này.", code="NATIVE_REVIEW_ALREADY_EXISTS", status_code=409)
    values = {col.key: copy.deepcopy(getattr(base, col.key)) for col in KnowledgeSourceRevision.__table__.columns
              if col.key not in {"id", "revision_no", "created_at", "updated_at"}}
    values.update(status="review_required", canonical_markdown=markdown,
        canonical_hash=hashlib.sha256(markdown.encode()).hexdigest(), artifact_key=key,
        failure_code=None, failure_detail=None, created_by="codex-assisted-native-review",
        normalizer_version=VERSION, finished_at=datetime.now(UTC), lock_version=1,
        quality_report={"overall_status": "warning", "structured_review_required": True,
                        "structured_issues": artifact["issues"]},
        parse_provenance={**copy.deepcopy(base.parse_provenance or {}), "structured_artifact": artifact,
            "edited_from_revision_id": base.id, "native_table_review": {"version": VERSION,
                "numeric_cells_verified": count, "changes": [{k: v for k, v in edit.items() if k != "replacement"} for edit in edits]}})
    changed = {edit["page_number"] for edit in edits}
    for page in values["page_manifest"]:
        if page.get("page") in changed:
            page["layout_text_alignment"] = "stale"
            page["chars"] = len(next(item["markdown_content"] for item in canonical_pages(markdown, len(base.page_manifest))
                                     if item["page_number"] == page["page"]))
    revision = KnowledgeSourceRevision(**values, revision_no=number + 1)
    db.add(revision)
    await db.flush()
    return revision  # Caller owns the transaction. No existing binding/index is changed.
