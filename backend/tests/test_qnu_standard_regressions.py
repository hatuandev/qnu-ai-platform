"""Behavioral regressions for the four conformance findings from review 532."""

import io
from unittest.mock import AsyncMock, patch

import docx
import pytest
from docx.oxml import OxmlElement

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuQualityFlag,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document


async def _model(document, split=None, gap=False):
    stream = io.BytesIO()
    document.save(stream)
    parsed = await get_document_parser("docx").parse(stream.getvalue(), "fixture.docx")
    markdown = parsed.raw_text
    if split:
        cut = markdown.index(split)
        ranges = [(1, 0, cut), (2, cut + (1 if gap else 0), len(markdown))]
    else:
        ranges = [(1, 0, len(markdown))]
    return build_qnu_structured_document(
        parsed.docling_document, filename="fixture.docx", sha256="a" * 64,
        header_evidence=parsed.docx_header_evidence,
        projection_markdown=markdown, page_ranges=ranges, render_page_count=len(ranges),
    )


def _report(model):
    return validate_qnu_markdown(render_qnu_markdown(model, document_id="fixture", revision_id="rev"))


def _project(model):
    return project_document(model, {"structured_sha256": "b" * 64}, {})[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("gap", [False, True])
async def test_paragraph_uses_its_entire_span_and_abstains_over_a_gap(gap):
    document = docx.Document()
    document.add_paragraph(" ".join(f"word{i}" for i in range(20)))
    model = await _model(document, "word12", gap)
    block = model.blocks[0]
    if gap:
        assert [loc.page for loc in block.source_locations] == [None]
        assert model.document_meta["page_mapping"]["status"] == "partial"
        assert any(flag.code == "page_unresolved" for flag in block.quality_flags)
    else:
        assert [loc.page for loc in block.source_locations] == [1, 2]
        assert model.document_meta["page_mapping"]["status"] == "aligned"
    assert _report(model).ok


@pytest.mark.asyncio
async def test_repeated_paragraph_on_different_pages_remains_unlocated():
    document = docx.Document()
    document.add_paragraph("Repeated statement with an exception.")
    document.add_paragraph("Between the two statements.")
    document.add_paragraph("Repeated statement with an exception.")
    model = await _model(document, "Between")
    repeated = [b for b in model.blocks if b.body.startswith("Repeated")]
    assert len(repeated) == 2
    assert all([loc.page for loc in b.source_locations] == [None] for b in repeated)
    assert model.document_meta["page_mapping"]["status"] == "partial"


@pytest.mark.asyncio
async def test_nonlexical_content_cannot_make_page_mapping_look_aligned():
    document = docx.Document()
    document.add_paragraph("— / †")
    model = await _model(document)
    assert model.document_meta["page_mapping"]["status"] == "partial"
    assert model.blocks[0].source_locations[0].page is None
    assert any(f.code == "page_unresolved" for f in model.blocks[0].quality_flags)


@pytest.mark.asyncio
@pytest.mark.parametrize("split", [None, "Beta"])
async def test_simple_table_has_correct_row_pages_without_borrowing_the_header_page(split):
    document = docx.Document()
    table = document.add_table(rows=3, cols=2)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row, values in zip(table.rows, [["Name", "Value"], ["Alpha", "0"], ["Beta", "2"]]):
        for cell, value in zip(row.cells, values):
            cell.text = value
    model = await _model(document, split)
    table_block = next(b for b in model.blocks if b.type == "table")
    assert table_block.attributes["representation"] == ("records" if split else "gfm")
    artifact = _project(model)
    units = artifact["retrieval_units"]["units"]
    beta = next(u for u in units if "Beta" in u["text"] and not u["is_container"])
    assert beta["page_number"] == (2 if split else 1)
    assert model.document_meta["page_mapping"]["status"] == "aligned"
    assert _report(model).ok


@pytest.mark.asyncio
async def test_single_column_records_keep_data_and_zero_as_rows():
    document = docx.Document()
    table = document.add_table(rows=3, cols=1)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for row, value in zip(table.rows, ["Item", "entry " * 26, "0"]):
        row.cells[0].text = value
    model = await _model(document)
    rows = [b for b in model.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "entry " * 26
    assert rows[1].attributes["fields"]["c01"] == {"raw": "0", "state": "present", "normalized": None}
    assert not any(b.type == "note" for b in model.blocks)
    assert _report(model).ok


@pytest.mark.asyncio
async def test_spanning_body_cell_keeps_row_fields_and_origin_until_role_is_known():
    document = docx.Document()
    table = document.add_table(rows=3, cols=2)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    table.cell(0, 0).text, table.cell(0, 1).text = "Group", "Value"
    table.cell(1, 0).merge(table.cell(1, 1)).text = "Only applies to group A."
    table.cell(2, 0).text, table.cell(2, 1).text = "B", "2"
    model = await _model(document)
    rows = [b for b in model.blocks if b.type == "table_row"]
    assert len(rows) == 2
    spanning = rows[0]
    assert spanning.attributes["row_role"] == "spanning_row_unclassified"
    assert spanning.attributes["fields"]["c02"]["raw"] == "Only applies to group A."
    assert spanning.attributes["field_origins"]["c02"]["block_id"] == spanning.id
    assert any(f.code == "spanning_row_needs_review" for f in spanning.quality_flags)
    assert _report(model).ok


@pytest.mark.parametrize("scope", ["none", "row", "table"])
def test_table_notes_only_enter_explicitly_declared_scope(scope):
    loc = [QnuSourceLocation(page=1, locator="fixture/table")]
    table = QnuBlock(id="t", type="table", source_locations=loc,
                     context_refs=["n"] if scope == "table" else [],
                     attributes={"representation": "records", "columns": [{"id": "c", "header_path": ["Value"]}]})
    rows = [QnuBlock(id=key, parent_id="t", type="table_row", source_locations=loc,
                     context_refs=["n"] if scope == "row" and key == "a" else [], body=value,
                     attributes={"fields": {"c": {"raw": value, "state": "present", "normalized": None}}})
            for key, value in [("a", "A"), ("b", "B")]]
    note = QnuBlock(id="n", parent_id="t", type="note", source_locations=loc, body="Only applies where explicitly linked.")
    model = QnuStructuredDocument(title="Fixture", source=QnuSourceInfo(filename="fixture.pdf"), blocks=[table, *rows, note])
    artifact = _project(model)
    units = {u["id"]: u for u in artifact["retrieval_units"]["units"]}
    assert ("qnu:n" in units["qnu:a"]["context_refs"]) == (scope != "none")
    assert ("qnu:n" in units["qnu:b"]["context_refs"]) == (scope == "table")
    assert artifact["derived_indexes"][0]["count"] == 2
    assert any(issue["code"] == "table_note_scope_unresolved" for issue in artifact["issues"]) == (scope == "none")


def _document(block):
    return QnuStructuredDocument(title="Fixture", source=QnuSourceInfo(filename="fixture.pdf", sha256="a" * 64), blocks=[block])


@pytest.mark.parametrize("body", ["Not a table.", "| A | B |\n| -- | --- |\n| 1 | 2 |", "| A | B |\n| --- | --- |\n| 1 |"])
def test_malformed_gfm_cannot_pass_the_standard_gate(body):
    block = QnuBlock(id="t", type="table", source_locations=[QnuSourceLocation(page=1)],
                     attributes={"representation": "gfm"}, body=body)
    report = _report(_document(block))
    assert not report.ok
    assert any(e.code == "table_gfm_invalid" for e in report.errors)


def test_unsupported_table_representation_returns_a_structured_error():
    block = QnuBlock(id="t", type="table", source_locations=[QnuSourceLocation(page=1)],
                     attributes={"representation": "unknown"}, body="Content")
    assert any(e.code == "table_representation_invalid" for e in _report(_document(block)).errors)


def test_gfm_declared_headers_must_agree_with_the_body():
    block = QnuBlock(id="t", type="table", source_locations=[QnuSourceLocation(page=1)],
                     attributes={"representation": "gfm", "columns": [{"id": "c", "header_path": ["Quota"]}]},
                     body="| Score |\n| --- |\n| 10 |")
    assert any(e.code == "table_gfm_invalid" for e in _report(_document(block)).errors)


@pytest.mark.parametrize("flagged", [False, True])
@pytest.mark.parametrize("locations", [[], [QnuSourceLocation()], [QnuSourceLocation(locator="  ")]])
def test_missing_source_locations_require_an_explicit_warning(flagged, locations):
    flags = [QnuQualityFlag(code="source_location_unverified", detail="Source location is unknown.")] if flagged else []
    block = QnuBlock(id="p", type="text", body="Source text", source_locations=locations, quality_flags=flags)
    report = _report(_document(block))
    assert report.ok == flagged
    if not flagged:
        assert any(e.code == "block_location_unverified" for e in report.errors)


def test_invalid_warning_status_cannot_cover_a_missing_location():
    block = QnuBlock(id="p", type="text", body="Source text", quality_flags=[
        QnuQualityFlag(code="source_location_unverified", status="unknown", detail="Unknown location.")])
    assert any(e.code == "block_quality_flag_invalid" for e in _report(_document(block)).errors)


@pytest.mark.parametrize("outer_pipes", [True, False])
def test_valid_gfm_keeps_escaped_pipes_zero_and_empty_cells(outer_pipes):
    body = "| Name | Value | Extra |\n| :--- | ---: | --- |\n| A\\|B | 0 | X |\n| C | | Y |"
    if not outer_pipes:
        body = "\n".join(line[1:-1].strip() for line in body.splitlines())
    block = QnuBlock(id="t", type="table", source_locations=[QnuSourceLocation(page=1)],
                     attributes={"representation": "gfm"}, body=body)
    assert _report(_document(block)).ok
    artifact = _project(_document(block))
    assert artifact["derived_indexes"][0]["count"] == 2


@pytest.mark.asyncio
async def test_artifact_gate_rejects_invalid_gfm_before_any_storage_write():
    block = QnuBlock(id="t", type="table", source_locations=[QnuSourceLocation(page=1)],
                     attributes={"representation": "gfm"}, body="Not a GFM table.")
    with patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.exists", AsyncMock(return_value=False)), \
         patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", AsyncMock()) as save:
        result = await save_qnu_document(_document(block), document_id="fixture", revision_id="rev", snapshot_path="fixture.pdf")
    assert result["status"] == "failed" and result["reason"] == "validation_failed"
    save.assert_not_awaited()
