"""Stage-two source contracts: exact spans, conservative semantics, OCR failure."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.normalization.retrieval_units import resolve_unit_manifest, unit_chunks
from app.modules.knowledge.services.source_artifact import (
    add_layout_issues,
    build_source_artifact,
    cell_context,
)

EXCERPT = (Path(__file__).parent / "fixtures/rag_floor_121_excerpt.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("header", ["Phương thức xét kết quả học tập THPT", "Phương thức xét điểm thi TN. THPT"])
def test_composite_column_is_not_mislabeled_as_cutoff_or_method_id(header):
    assert cell_context(header)["attribute_code"] is None


def test_precise_existing_column_meaning_is_preserved():
    assert cell_context("Điểm trúng tuyển 2025 (THPT)")["attribute_code"] == "cutoff_score"
    assert cell_context("Phương thức")["attribute_code"] == "admission_method"


def test_rows_link_to_exact_intro_header_and_trailing_notes_without_inventing_year():
    # A structural continuation needs the last ordinal, not merely equal column counts.
    markdown = EXCERPT.replace("\n\n<!-- Trang 2 -->", "\n| 5 | 7140206 | Group C | 19 | – | – | 19 | C |\n\n<!-- Trang 2 -->")
    markdown += "\n\nGhi chú:\n\n1. Điều kiện A áp dụng cho nhóm nêu trong văn bản.\n\n2. Ký hiệu – có nghĩa như chú giải."
    artifact = build_source_artifact(markdown, 2, {})
    graph = artifact["context_graph"]
    manifest = resolve_unit_manifest(markdown, artifact)
    by_id = {unit.id: unit for unit in manifest.units}
    rows = [unit for unit in manifest.units if not unit.is_container and "7140209" in unit.text]
    linked = graph["links"][rows[0].id]
    assert any("năm 2026" in by_id[item].text for item in linked)
    assert any("Phương thức xét" in by_id[item].text for item in linked)
    assert any("Điều kiện A" in by_id[item].text for item in linked)
    assert rows[0].temporal.data_years == []
    for unit in by_id.values():
        assert markdown[unit.start:unit.end] == unit.text
    chunks = unit_chunks(manifest, context_graph=graph)
    row = next(chunk for chunk in chunks if "7140209" in chunk["content"])
    assert "Phương thức xét điểm thi TN. THPT: 20" in row["content"]
    assert row["metadata"]["context_unit_ids"] == linked
    assert "Điều kiện A" not in row["content"]  # parent refs, not whole-book duplication


def test_context_links_never_cross_independent_table_sections():
    first, second = EXCERPT.split("<!-- Trang 2 -->")
    artifact = build_source_artifact(first + "\n\n# Một bảng độc lập\n\n<!-- Trang 2 -->" + second, 2, {})
    manifest = resolve_unit_manifest(first + "\n\n# Một bảng độc lập\n\n<!-- Trang 2 -->" + second, artifact)
    row = next(unit for unit in manifest.units if not unit.is_container and "7140209" in unit.text)
    by_id = {unit.id: unit for unit in manifest.units}
    assert not any("năm 2026" in by_id[item].text for item in artifact["context_graph"]["links"][row.id])


def test_context_graph_tampering_is_rejected():
    from app.modules.knowledge.services.source_links import validate_context_graph

    artifact = build_source_artifact(EXCERPT, 2, {})
    manifest = resolve_unit_manifest(EXCERPT, artifact)
    graph = artifact["context_graph"]
    graph["canonical_hash"] = "another source"
    with pytest.raises(ValueError):
        validate_context_graph(graph, manifest)


def test_numbered_post_table_context_spans_pages_but_stops_at_new_section():
    markdown = EXCERPT.split("<!-- Trang 2 -->")[0]
    markdown += "\n\n1. Điều kiện thứ nhất còn tiếp\n\n<!-- Trang 2 -->\ntrên trang tiếp theo."
    markdown += "\n\n2. Điều kiện thứ hai.\n\nKý hiệu ‘–’: không xét tuyển."
    markdown += "\n\nNơi nhận:\n\nMột nội dung không phải chú giải."
    artifact = build_source_artifact(markdown, 2, {})
    manifest = resolve_unit_manifest(markdown, artifact)
    row = next(unit for unit in manifest.units if not unit.is_container and "7140114" in unit.text)
    by_id = {unit.id: unit for unit in manifest.units}
    linked = [by_id[ref] for ref in artifact["context_graph"]["links"][row.id]]
    assert any("trên trang tiếp theo" in unit.text and unit.page_number == 2 for unit in linked)
    assert any("Ký hiệu" in unit.text for unit in linked)
    assert not any("Nơi nhận" in unit.text or "Một nội dung" in unit.text for unit in linked)
    assert row.id not in artifact["context_graph"]["links"][row.id]


def test_non_numbered_rows_link_facts_without_inventing_physical_page():
    markdown = "| Tên ngành | Điểm chuẩn 2024 |\n| --- | --- |\n| Entity A | 15 |"
    artifact = build_source_artifact(markdown, 1, {})
    manifest = resolve_unit_manifest(markdown, artifact)
    fact = artifact["facts"][0]
    row = next(unit for unit in manifest.units if unit.id == fact["raw_data"]["source_unit_id"])
    assert row.page_number is None
    assert row.text == "| Entity A | 15 |"
    assert "Điểm chuẩn 2024: 15" in artifact["context_graph"]["row_projections"][row.id]


def test_repeated_unrelated_rows_do_not_get_arbitrary_fact_pointer():
    table = "| Tên ngành | Điểm chuẩn 2024 |\n| --- | --- |\n| Entity A | 15 |"
    artifact = build_source_artifact(table + "\n\n# Bảng khác\n\n" + table, 1, {})
    assert artifact["facts"]
    assert all("source_unit_id" not in fact["raw_data"] for fact in artifact["facts"])


def test_old_stored_manifests_keep_their_digest_and_can_be_read():
    from app.modules.knowledge.normalization.retrieval_units import manifest_digest

    artifact = build_source_artifact(EXCERPT, 2, {})
    artifact.pop("context_graph", None)
    manifest = resolve_unit_manifest(EXCERPT, artifact)
    assert manifest_digest(manifest) == artifact["unit_manifest_hash"]


@pytest.mark.asyncio
async def test_metadata_ocr_failure_is_observable_and_preserves_native_table():
    from app.modules.knowledge.services.header_rescue import rescue_header

    original = EXCERPT
    page = {"page_number": 1, "extracted_text": original, "engine_used": "native"}
    prepared = {"content": b"rendered test crop", "missing": ["document_number", "issued_date"],
                "bbox": [0, 0, 100, 100]}
    with patch("app.modules.knowledge.services.header_rescue.OCRService.extract_document",
               AsyncMock(side_effect=AppException("OCR unavailable", code="OCR_PROVIDER_UNAVAILABLE", status_code=503))):
        await rescue_header(AsyncMock(), page, prepared, None, "tenant")
    assert page["extracted_text"] == original
    assert page["metadata_rescue"]["status"] == "unavailable"
    artifact = build_source_artifact(original, 2, {})
    add_layout_issues(artifact, [page])
    assert artifact["review"]["status"] == "required"
    assert any(issue["code"] == "METADATA_OCR_REVIEW" for issue in artifact["issues"])


@pytest.mark.asyncio
async def test_ocr_header_adds_only_supported_fields_without_replacing_table():
    from types import SimpleNamespace

    from app.modules.knowledge.services.header_rescue import rescue_header

    page = {"page_number": 1, "extracted_text": EXCERPT, "engine_used": "native"}
    prepared = {"content": b"test crop", "missing": ["document_number", "issued_date"], "bbox": [0, 0, 100, 100]}
    ocr = SimpleNamespace(success=True, engine_used="configured-test-engine",
        pages=[SimpleNamespace(extracted_text="Số: 121/TB-HĐTS\nGia Lai, ngày 09 tháng 7 năm 2026\nUnrelated OCR paragraph")])
    with patch("app.modules.knowledge.services.header_rescue.OCRService.extract_document", AsyncMock(return_value=ocr)) as call:
        await rescue_header(AsyncMock(), page, prepared, None, "tenant")
    assert EXCERPT in page["extracted_text"]
    assert "Unrelated OCR paragraph" not in page["extracted_text"]
    assert "121/TB-HĐTS" in page["extracted_text"]
    assert page["metadata_rescue"]["status"] == "proposed"
    assert call.call_args.kwargs["engine_name"] == "auto"
    assert call.call_args.kwargs["session"] is not None


@pytest.mark.asyncio
async def test_header_ocr_accepts_only_structural_spacing_repairs_and_keeps_raw_observation():
    from types import SimpleNamespace

    from app.modules.knowledge.services.header_rescue import rescue_header

    observed = "Số: 121 /TB-HDTS\nGia Lai, ngày 09 tháng7 năm 2026\nUnrelated OCR paragraph"
    page = {"page_number": 1, "extracted_text": EXCERPT, "engine_used": "native"}
    prepared = {"content": b"test crop", "missing": ["document_number", "issued_date"], "bbox": [0, 0, 100, 100]}
    ocr = SimpleNamespace(success=True, engine_used="paddleocr_vl",
                          pages=[SimpleNamespace(extracted_text=observed)])
    with patch("app.modules.knowledge.services.header_rescue.OCRService.extract_document", AsyncMock(return_value=ocr)):
        await rescue_header(AsyncMock(), page, prepared, "paddleocr", "tenant")
    assert page["metadata_rescue"]["status"] == "proposed"
    assert "Số: 121/TB-HDTS" in page["extracted_text"]  # no invented accent correction
    assert "ngày 09 tháng 7 năm 2026" in page["extracted_text"]
    assert "Unrelated OCR paragraph" not in page["extracted_text"]
    assert page["metadata_rescue"]["ocr_text"] == observed


@pytest.mark.asyncio
async def test_cited_document_date_is_not_compared_as_the_native_issue_date():
    from types import SimpleNamespace

    from app.modules.knowledge.services.header_rescue import rescue_header

    original = "Số: /TB-HĐTS\nGia Lai, ngày tháng năm 2026\n\nCăn cứ Thông tư ngày 15 tháng 02 năm 2026 của Bộ.\n\n" + EXCERPT
    page = {"page_number": 1, "extracted_text": original, "engine_used": "native"}
    prepared = {"content": b"test crop", "missing": ["document_number", "issued_date"], "bbox": [0, 0, 100, 100]}
    ocr = SimpleNamespace(success=True, engine_used="paddleocr_vl", pages=[SimpleNamespace(
        extracted_text="Số: 121/TB-HDTS\nGia Lai, ngày 09 tháng 7 năm 2026")])
    with patch("app.modules.knowledge.services.header_rescue.OCRService.extract_document", AsyncMock(return_value=ocr)):
        await rescue_header(AsyncMock(), page, prepared, "paddleocr", "tenant")
    assert page["metadata_rescue"]["status"] == "proposed"
    assert page["extracted_text"].endswith(original)


def test_complete_native_header_never_requests_rescue():
    from app.modules.knowledge.services.header_rescue import prepare_header_rescue

    page = {"extracted_text": "Số: 121/TB-HĐTS\nGia Lai, ngày 09 tháng 7 năm 2026\n" + EXCERPT}
    # Invalid binary proves no renderer/provider is needed for a complete native header.
    assert prepare_header_rescue(b"not needed", page) is None


def test_empty_header_crop_requires_review_instead_of_breaking_native_extraction():
    import pymupdf

    from app.modules.knowledge.services.header_rescue import prepare_header_rescue

    page = {"extracted_text": "Số: /TB-HĐTS", "blocks": [{"type": "table", "coordinates": {"top": 0}}]}
    with pymupdf.open() as document:
        document.new_page()
        assert prepare_header_rescue(document.tobytes(), page) is None
    assert page["metadata_rescue"]["error_code"] == "HEADER_CROP_EMPTY"
    artifact = build_source_artifact(page["extracted_text"], 1, {})
    add_layout_issues(artifact, [page])
    assert artifact["review"]["status"] == "required"


@pytest.mark.asyncio
@pytest.mark.parametrize("ocr_text, status", [
    ("Số: 122/TB-HĐTS\nGia Lai, ngày 09 tháng 7 năm 2026", "conflict"),
    ("No complete administrative fields", "incomplete"),
])
async def test_uncertain_header_never_overwrites_native_fields(ocr_text, status):
    from types import SimpleNamespace

    from app.modules.knowledge.services.header_rescue import rescue_header
    from app.modules.knowledge.services.source_pages import normalize_source_pages

    original = "Số: 121/TB-HĐTS\n" + EXCERPT
    page = {"page_number": 1, "extracted_text": original, "engine_used": "native"}
    prepared = {"content": b"test crop", "missing": ["issued_date"], "bbox": [0, 0, 100, 100]}
    ocr = SimpleNamespace(success=True, engine_used="configured-test-engine",
                          pages=[SimpleNamespace(extracted_text=ocr_text)])
    parent_db = AsyncMock()
    with patch("app.modules.knowledge.services.header_rescue.OCRService.extract_document", AsyncMock(return_value=ocr)) as call:
        await rescue_header(parent_db, page, prepared, "configured-engine", "tenant")
    assert page["metadata_rescue"]["status"] == status
    assert page["extracted_text"] == original
    assert call.call_args.kwargs["session"] is not parent_db
    parent_db.commit.assert_not_awaited()
    assert call.call_args.kwargs["engine_name"] == "configured-engine"
    _, manifest = normalize_source_pages(original, 1, [page])
    assert manifest[0]["metadata_rescue"] == page["metadata_rescue"]


@pytest.mark.asyncio
async def test_real_docx_merged_header_keeps_distinct_data_year_paths():
    from io import BytesIO

    from docx import Document

    from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser

    document = Document()
    document.add_paragraph("Văn bản ban hành năm 2026")
    table = document.add_table(rows=3, cols=5)
    for index, label in enumerate(["STT", "Tên ngành", "2024", "", "2025"]):
        table.cell(0, index).text = label
    table.cell(0, 2).merge(table.cell(0, 3))
    for index, label in enumerate(["STT", "Tên ngành", "A", "B", "A"]):
        table.cell(1, index).text = label
    for index, label in enumerate(["1", "Entity", "15", "18", "20"]):
        table.cell(2, index).text = label
    stream = BytesIO()
    document.save(stream)
    # Actual Office backend and HTML span projection; no fake parser or model response.
    parsed = await DoclingOfficeParser("docx").parse(stream.getvalue(), "merged.docx")
    assert parsed.metadata["parser"] == "docling"
    artifact = build_source_artifact(parsed.raw_text, 1, {})
    manifest = resolve_unit_manifest(parsed.raw_text, artifact)
    row = next(unit for unit in manifest.units if not unit.is_container and "Entity" in unit.text)
    projection = artifact["context_graph"]["row_projections"][row.id]
    assert "2024 / A: 15" in projection
    assert "2024 / B: 18" in projection
    assert "2025 / A: 20" in projection
    assert "2026" not in projection
    assert parsed.raw_text[row.start:row.end] == row.text
    assert row.temporal.data_years == []  # issue year is not data applicability
