"""Source-backed DOCX header roles and representation-independent cell safety."""

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import docx
import pytest
from docx.oxml import OxmlElement

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuSourceInfo,
    QnuSourceLocation,
    QnuStructuredDocument,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.normalization.qnu_projection import project_document
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.services.source_extraction import SourceExtraction, extract_source
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service


def test_extraction_fingerprint_fits_the_persisted_version_contract():
    from app.modules.knowledge.models import KnowledgeSourceRevision
    from app.modules.knowledge.services.source_extraction import EXTRACTION_VERSION

    assert EXTRACTION_VERSION != "layout-v15-qnu-serving"
    assert len(EXTRACTION_VERSION) <= KnowledgeSourceRevision.__table__.c.normalizer_version.type.length


def _header(row, enabled=True):
    flag = OxmlElement("w:tblHeader")
    if not enabled:
        from docx.oxml.ns import qn

        flag.set(qn("w:val"), "0")
    row._tr.get_or_add_trPr().append(flag)


def _table(document, values, header_rows=0):
    table = document.add_table(rows=len(values), cols=len(values[0]))
    for index, (row, values_row) in enumerate(zip(table.rows, values)):
        for cell, value in zip(row.cells, values_row):
            cell.text = value
        if index < header_rows:
            _header(row)
    return table


async def _extract(document):
    stream = io.BytesIO()
    document.save(stream)
    content = stream.getvalue()
    parsed = await get_document_parser("docx").parse(content, "fixture.docx")
    preview = SourceExtraction(parsed.raw_text, 1, pages=[{
        "page_number": 1, "extracted_text": parsed.raw_text, "alignment_text": parsed.raw_text,
    }])
    parser = SimpleNamespace(parse=AsyncMock(return_value=parsed))
    with patch("app.modules.knowledge.services.source_extraction.get_document_parser", return_value=parser), \
         patch("app.modules.knowledge.services.ingestion_service.IngestionService._convert_office_to_pdf", AsyncMock(return_value=b"preview")), \
         patch("app.modules.knowledge.services.source_extraction.extract_pdf", AsyncMock(return_value=preview)):
        result = await extract_source(AsyncMock(), content, "fixture.docx", "docx", "standard", None, "tenant")
    return result.qnu_document


def _project(model):
    return project_document(model, {"structured_sha256": "b" * 64}, {})[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [[["Alpha", "North"], ["2", "South"]], [["2025", "2026"], ["0", "001"]]])
async def test_headerless_docx_preserves_every_row_without_trusting_docling_flags(values):
    document = docx.Document()
    _table(document, values)
    model = await _extract(document)
    table = next(b for b in model.blocks if b.type == "table")
    artifact = _project(model)
    assert artifact["derived_indexes"][0]["count"] == 2
    assert all(c["header_path"] == [] for c in table.attributes["columns"])
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)
    assert table.source_data["header_rows"] == 0
    assert table.source_data["cells"][0]["column_header"] is True  # Raw engine proposal was not rewritten.
    rows = [b for b in model.blocks if b.type == "table_row"]
    assert [r.attributes["fields"]["c01"]["raw"] for r in rows] == [v[0] for v in values]


@pytest.mark.asyncio
async def test_explicit_docx_header_rows_include_numeric_and_second_level_headers():
    document = docx.Document()
    _table(document, [["2025", "2026"], ["Score", "Quota"], ["0", "001"]], header_rows=2)
    model = await _extract(document)
    table = next(b for b in model.blocks if b.type == "table")
    assert [c["header_path"] for c in table.attributes["columns"]] == [["2025", "Score"], ["2026", "Quota"]]
    rows = [b for b in model.blocks if b.type == "table_row"]
    assert len(rows) == 1 and rows[0].attributes["fields"]["c01"]["raw"] == "0"


@pytest.mark.asyncio
async def test_explicit_false_header_does_not_authorize_consuming_the_first_row():
    document = docx.Document()
    table = _table(document, [["Alpha", "North"], ["2", "South"]])
    _header(table.rows[0], enabled=False)
    artifact = _project(await _extract(document))
    assert artifact["derived_indexes"][0]["count"] == 2


@pytest.mark.asyncio
async def test_header_only_docx_preserves_header_paths_without_creating_data():
    document = docx.Document()
    _table(document, [["2025", "2026"], ["Score", "Quota"]], header_rows=2)
    model = await _extract(document)
    assert validate_qnu_markdown(render_qnu_markdown(model, document_id="fixture", revision_id="rev")).ok
    assert _project(model)["derived_indexes"][0]["count"] == 0
    assert [c["header_path"] for c in model.blocks[0].attributes["columns"]] == [["2025", "Score"], ["2026", "Quota"]]


@pytest.mark.asyncio
async def test_duplicate_table_content_with_different_roles_does_not_guess_source_association():
    document = docx.Document()
    values = [["Alpha", "North"], ["2", "South"]]
    _table(document, values)
    _table(document, values, header_rows=1)
    model = await _extract(document)
    assert sum(index["count"] for index in _project(model)["derived_indexes"]) == 4
    assert all(any(f.code == "table_header_unresolved" for f in b.quality_flags)
               for b in model.blocks if b.type == "table")


def _gfm(value):
    table = QnuBlock(id="t", type="table", source_locations=[QnuSourceLocation(page=1, locator="source/table")],
                     attributes={"representation": "gfm"},
                     body=f"| Mã ngành | Tên ngành | Chỉ tiêu |\n| --- | --- | --- |\n| 7480101 | Alpha | {value} |")
    return QnuStructuredDocument(title="Fixture", source=QnuSourceInfo(filename="fixture.pdf"), blocks=[table])


@pytest.mark.parametrize("marker", ["–", "-", "/"])
def test_gfm_ambiguous_cells_never_become_facts_or_pass_whole_document_approval(marker):
    artifact = _project(_gfm(marker))
    assert artifact["unresolved_cell_count"] == 1
    assert not any(f["attribute_name"] == "Chỉ tiêu" for f in artifact["facts"])
    revision = SimpleNamespace(parse_provenance={"standard_required": True})
    with pytest.raises(AppException) as error:
        source_ingestion_service._apply_review_decision(SimpleNamespace(), revision, artifact,
                                                      "approved", "Checked source", "actor")
    assert error.value.code == "QNU_UNRESOLVED_CELLS"


@pytest.mark.parametrize("value", ["0", "25", ""])
def test_gfm_present_and_blank_cells_keep_their_meaning(value):
    artifact = _project(_gfm(value))
    assert artifact["unresolved_cell_count"] == 0
    facts = [f for f in artifact["facts"] if f["attribute_name"] == "Chỉ tiêu"]
    assert len(facts) == bool(value)
    if value:
        assert facts[0]["attribute_value"] == value
        assert facts[0]["raw_data"]["field_state"] == "present"
        assert facts[0]["raw_data"]["source_unit_id"] == "qnu:t:row:0"


@pytest.mark.asyncio
async def test_real_docx_gfm_marker_is_blocked_even_with_explicit_header():
    document = docx.Document()
    _table(document, [["Mã ngành", "Tên ngành", "Chỉ tiêu"], ["7480101", "Alpha", "–"],
                      ["7480102", "Beta", "0"]], header_rows=1)
    artifact = _project(await _extract(document))
    assert artifact["unresolved_cell_count"] == 1
    assert [f["attribute_value"] for f in artifact["facts"] if f["attribute_name"] == "Chỉ tiêu"] == ["0"]


def test_explicit_record_state_is_not_overwritten_by_gfm_marker_defaults():
    model = _gfm("–")
    table = model.blocks[0]
    table.body = ""
    table.attributes = {"representation": "records", "columns": [
        {"id": "c1", "header_path": ["Mã ngành"]}, {"id": "c2", "header_path": ["Tên ngành"]},
        {"id": "c3", "header_path": ["Chỉ tiêu"]}]}
    row = QnuBlock(id="r", parent_id="t", type="table_row", source_locations=table.source_locations,
                   context_refs=["n"], body="Row", attributes={"fields": {
                       "c1": {"raw": "7480101", "state": "present"}, "c2": {"raw": "Alpha", "state": "present"},
                       "c3": {"raw": "–", "state": "not_applicable"}}})
    note = QnuBlock(id="n", type="note", source_locations=table.source_locations,
                    body='The symbol "–" explicitly means not applicable.')
    model.blocks.extend([row, note])
    artifact = _project(model)
    assert artifact["unresolved_cell_count"] == 0
    assert artifact["tables"][0]["row_fields"][0][2]["state"] == "not_applicable"
    assert not any(f["attribute_name"] == "Chỉ tiêu" for f in artifact["facts"])
