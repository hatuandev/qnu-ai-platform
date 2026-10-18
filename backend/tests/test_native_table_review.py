"""Merged native headers must not erase populated child columns or publish drafts."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pymupdf
import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.models import CanonicalCell, CanonicalRow, SourceSpan
from app.modules.knowledge.normalization.table_reconstructor import clean_table_columns
from app.modules.knowledge.parsers.native_headers import native_header_matrix
from app.modules.knowledge.parsers.pdf_parser import _normalize_raw_table_rows
from app.modules.knowledge.services.native_table_review import (
    create_native_table_draft,
    extract_native_evidence,
    replace_tables_only,
    table_markdown,
)


def native_pdf():
    document = pymupdf.open()
    page = document.new_page(width=600, height=400)
    xs = [30 + 70 * col for col in range(8)]
    ys = [40 + 30 * row for row in range(6)]
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    for col, x in enumerate(xs):
        page.draw_line((x, ys[0] if col in (0, 1, 4, 7) else ys[1]), (x, ys[-1]))
    for col, label in ((0, "Percent"), (1, "G01"), (4, "G02")):
        page.insert_text((xs[col] + 4, ys[0] + 20), label, fontsize=9)
    for col, label in enumerate(("Percent", "S", "T", "U", "S", "T", "U")):
        page.insert_text((xs[col] + 4, ys[1] + 20), label, fontsize=9)
    for row in range(3):
        for col in range(7):
            page.insert_text((xs[col] + 4, ys[row + 2] + 20), f"{100-row}%" if col == 0 else str(10 * row + col), fontsize=9)
    return document


def test_native_group_headers_keep_every_populated_column():
    with native_pdf() as document:
        table = document[0].find_tables().tables[0]
        matrix, depth = native_header_matrix(table)
        _, headers, data = _normalize_raw_table_rows(matrix)
        assert depth == 2
        assert headers[1:4] == ["G01 / S", "G01 / T", "G01 / U"]
    rows = [CanonicalRow(row_id=str(i), cells=[CanonicalCell(raw_value=value,
        source_span=SourceSpan(page_number=1)) for value in row]) for i, row in enumerate(data)]
    cleaned, _ = clean_table_columns(headers, rows)
    assert len(cleaned) == 7


def test_populated_unnamed_column_is_not_a_visual_spacer():
    headers = ["Row", "Group", "", "Tail"]
    row = CanonicalRow(row_id="r", cells=[CanonicalCell(raw_value=value,
        source_span=SourceSpan(page_number=1)) for value in ("1", "2", "3", "4")])
    cleaned, rows = clean_table_columns(headers, [row])
    assert cleaned == headers
    assert [cell.raw_value for cell in rows[0].cells] == ["1", "2", "3", "4"]


def correction_fixture():
    with native_pdf() as document:
        content = document.tobytes()
    native, _ = extract_native_evidence(content)
    old = {**native[0], "headers": [native[0]["headers"][i] for i in (0, 1, 4)],
           "rows": [[row[i] for i in (0, 1, 4)] for row in native[0]["rows"]]}
    markdown = "<!-- Trang 1 -->\nBefore unchanged.\n\n" + table_markdown(old) + "\n\nAfter unchanged."
    return content, native, markdown


def test_table_only_replacement_preserves_every_other_character():
    content, native, markdown = correction_fixture()
    revised, edits = replace_tables_only(markdown, native, 1)
    assert len(edits) == 1 and edits[0]["new_columns"] == 7
    edit = edits[0]
    assert revised[:edit["start"]] == markdown[:edit["start"]]
    assert revised.endswith(markdown[edit["end"]:])
    assert extract_native_evidence(content)[1] == 21
    assert replace_tables_only(revised, native, 1)[1] == []


@pytest.mark.parametrize("corruption", ["value", "page", "row", "header"])
def test_conflicting_existing_table_must_not_be_silently_replaced(corruption):
    _, native, markdown = correction_fixture()
    if corruption == "value":
        native[0]["rows"][0][1] = "999"
    elif corruption == "page":
        native[0]["page_number"] = 2
    elif corruption == "row":
        native[0]["rows"].pop()
    else:
        native[0]["headers"][2] = native[0]["headers"][1]
    with pytest.raises(ValueError):
        replace_tables_only(markdown, native, 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [None, "hash", "binding", "base", "duplicate", "db"])
async def test_revision_creation_is_isolated_review_required_and_fails_closed(error):
    content, _, markdown = correction_fixture()
    base = KnowledgeSourceRevision(id="base", binding_id="binding", revision_no=2,
        origin_document_id="doc", origin_file_hash=hashlib.sha256(content).hexdigest(),
        snapshot_storage_path="original.pdf", canonical_markdown=markdown,
        canonical_hash=hashlib.sha256(markdown.encode()).hexdigest(), page_manifest=[{"page": 1, "chars": len(markdown)}],
        snapshot_metadata={"qnu_markdown": {"document_id": "binding", "revision_id": "base", "status": "ready",
                                            "path": "snapshots/collection/binding/hash.docx.aa.qnu-rag-v1.md"}},
        status="ready")
    binding = SimpleNamespace(id="binding", active_source_revision_id="base", active_index_revision_id="index")
    db = AsyncMock()
    db.add = lambda revision: None
    db.get.return_value = base
    db.execute.side_effect = [SimpleNamespace(scalar_one=lambda: 2),
                              SimpleNamespace(scalar_one_or_none=lambda: "duplicate" if error == "duplicate" else None)]
    if error == "hash":
        base.origin_file_hash = "bad"
    elif error == "binding":
        base.binding_id = "other"
    elif error == "base":
        binding.active_source_revision_id = "new-base"
    elif error == "db":
        db.get.side_effect = RuntimeError("DB down")
    with (patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()),
          patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()),
          patch("app.modules.knowledge.services.source_ingestion_service.source_ingestion_service.get_source", AsyncMock(return_value=binding))):
        if error:
            with pytest.raises(RuntimeError if error == "db" else AppException):
                await create_native_table_draft(db, collection_id="collection", source_id="binding",
                    base_revision_id="base", tenant_id="tenant", workspace_id="workspace", content=content)
            db.flush.assert_not_awaited()
        else:
            revision = await create_native_table_draft(db, collection_id="collection", source_id="binding",
                base_revision_id="base", tenant_id="tenant", workspace_id="workspace", content=content)
            assert revision.status == "review_required" and revision.revision_no == 3
            assert revision.parse_provenance["structured_artifact"]["review"]["status"] == "required"
            assert revision.canonical_hash != base.canonical_hash
            assert base.canonical_markdown == markdown and base.status == "ready"
            assert binding.active_source_revision_id == "base" and binding.active_index_revision_id == "index"
            # The base standard file must not be served as this draft's artifact.
            marker = revision.snapshot_metadata["qnu_markdown"]
            assert marker["status"] == "unavailable" and marker["reason"] == "superseded_revision_content"
            assert marker["revision_id"] == revision.id and marker["superseded_revision_id"] == "base"
            assert "path" not in marker and revision.parse_provenance["qnu_markdown"] == marker
            assert base.snapshot_metadata["qnu_markdown"]["status"] == "ready"
        db.commit.assert_not_awaited()  # The caller controls commit/rollback.
