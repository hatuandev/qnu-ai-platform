"""PDF Standard sidecar: physical provenance, raw OCR, tables and safe revision reuse."""

from __future__ import annotations

import copy
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pymupdf
import pytest

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuSourceLocation,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.parsers.pdf_evidence import capture_native_page, reading_order
from app.modules.knowledge.parsers.pdf_inspector import PDFInspectionResult
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document
from app.modules.knowledge.parsers.pdf_tables import (
    html_table,
    native_table,
    ocr_table,
    table_blocks,
)
from app.modules.knowledge.services.qnu_docx_artifacts import (
    build_qnu_markdown_artifact,
    rebuild_qnu_markdown_for_revision,
)
from app.modules.knowledge.services.source_extraction import SourceExtraction, extract_source
from app.modules.ocr.schemas import OCRExtractResponse, OCRPageResult
from app.modules.ocr.service import OCRService


@pytest.fixture(autouse=True)
def no_remote_inspection():
    with patch("app.modules.knowledge.parsers.inspector_process.inspect_pdf_safely",
               AsyncMock(return_value=PDFInspectionResult())), patch(
            "app.modules.knowledge.services.source_extraction.prepare_header_rescue", return_value=None):
        yield


def make_pdf(*kinds):
    with pymupdf.open() as doc:
        for kind in kinds:
            page = doc.new_page()
            if kind == "text":
                page.insert_text((50, 70), "Digital source with zero 0 and year 2026.")
            elif kind == "scan":
                with pymupdf.open() as image:
                    image.new_page().insert_text((50, 70), "Scanned source")
                    page.insert_image(page.rect, stream=image[0].get_pixmap().tobytes("png"))
        return doc.tobytes()


@pytest.mark.asyncio
async def test_pdf_default_header_rescue_stays_on_internal_paddleocr():
    with patch("app.modules.knowledge.services.source_extraction.prepare_header_rescue", return_value={"crop": True}), patch(
        "app.modules.knowledge.services.source_extraction.rescue_header", AsyncMock()
    ) as rescue:
        await extract_source(AsyncMock(), make_pdf("text"), "source.pdf", "pdf", "standard", None, "tenant")
    assert rescue.await_args.args[3] == "paddleocr"


def empty_native(number=1):
    return {"page": number, "page_label": None, "width": 100, "height": 100,
            "rotation": 0, "bbox_space": "pymupdf_unrotated_points", "layout": {"blocks": []},
            "tables": [], "images": [], "table_errors": []}


def native_text(text, bbox, size=11):
    return {"bbox": bbox, "lines": [{"spans": [{"text": text, "size": size}]}]}


def model(pages):
    return build_pdf_document({"pages": pages}, filename="fixture.pdf", sha256="a" * 64)


def validate(document):
    report = validate_qnu_markdown(render_qnu_markdown(document, document_id="binding", revision_id="revision"))
    assert report.ok, [e.model_dump() for e in report.errors]


@pytest.mark.asyncio
async def test_digital_pdf_builds_standard_without_ocr():
    content = make_pdf("text")
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", AsyncMock()) as ocr:
        result = await extract_source(AsyncMock(), content, "digital.pdf", "pdf", "standard", None, "tenant")
    ocr.assert_not_awaited()
    assert result.qnu_build_error is None
    validate(result.qnu_document)
    assert any("zero 0" in b.body for b in result.qnu_document.blocks)
    location = result.qnu_document.blocks[0].source_locations[0]
    assert location.page == 1 and location.bbox and location.bbox_space == "pymupdf_unrotated_points"
    assert result.pdf_evidence["source_sha256"] == hashlib.sha256(content).hexdigest()


def test_raw_native_evidence_is_not_limited_to_ui_sixty_blocks():
    with pymupdf.open() as doc:
        page = doc.new_page(width=600, height=2500)
        for i in range(75):
            page.insert_text((20, 30 + i * 30), f"Raw block {i:03d}")
        evidence = capture_native_page(page)
    assert len(evidence["layout"]["blocks"]) == 75
    document = model([{"page": 1, "native": evidence}])
    assert len(document.blocks) == 75
    assert "074" in document.blocks[-1].body


def test_xy_order_reads_columns_not_alternating_rows():
    items = [{"text": text, "bbox": box} for text, box in [
        ("L1", [0, 10, 40, 20]), ("R1", [60, 10, 100, 20]),
        ("L2", [0, 30, 40, 40]), ("R2", [60, 30, 100, 40])]]
    assert [i["text"] for i in reading_order(items)] == ["L1", "L2", "R1", "R2"]


def test_html_multi_level_headers_and_spans_keep_raw_zero_and_blank():
    html = ('<table><tr><th rowspan="2">Code</th><th colspan="2">2026</th></tr>'
            '<tr><th>Quota</th><th>Score</th></tr><tr><td>00123</td><td>0</td><td></td></tr>'
            '<tr><td colspan="2">Group</td><td>—</td></tr></table>')
    parsed = html_table(html)
    assert parsed["raw_html"] == html and parsed["header_depth"] == 2
    blocks = table_blocks(parsed, block_id="table", parent_id=None, location=QnuSourceLocation(page=2, locator="raw:table"),
                          section_path=[], engine="paddle")
    assert blocks[0].attributes["columns"][1]["header_path"] == ["2026", "Quota"]
    fields = blocks[1].attributes["fields"]
    assert fields["c01"]["raw"] == "00123" and fields["c02"]["raw"] == "0"
    assert fields["c03"]["state"] == "blank"
    assert blocks[-1].attributes["field_origins"]["c02"]["column_id"] == "c01"
    document = model([{"page": 1, "native": empty_native()}, {"page": 2, "native": empty_native(2)}]); document.blocks = blocks
    validate(document)


def test_headerless_ocr_table_keeps_first_data_row_and_marks_uncertainty():
    parsed = html_table("<table><tr><td>001</td><td>0</td></tr></table>")
    blocks = table_blocks(parsed, block_id="table", parent_id=None, location=QnuSourceLocation(page=1), section_path=[], engine="ocr")
    assert blocks[1].attributes["fields"]["c01"]["raw"] == "001"
    assert blocks[0].quality_flags[0].code == "table_header_unresolved"


def test_native_merged_cell_uses_geometry_and_keeps_raw_null():
    raw = {"matrix": [["Name", "Value"], ["Group", None], ["001", "0"]],
           "cell_boxes": [[[0, 0, 50, 10], [50, 0, 100, 10]], [[0, 10, 100, 20], None],
                          [[0, 20, 50, 30], [50, 20, 100, 30]]],
           "header": {"names": ["Name", "Value"], "external": False}}
    parsed = native_table(raw)
    assert parsed["grid"][1][1]["raw"] == "Group"
    assert parsed["grid"][1][1]["origin"] == [1, 0]
    assert parsed["raw_native"]["matrix"][1][1] is None
    blocks = table_blocks(parsed, block_id="t", parent_id=None, location=QnuSourceLocation(page=1, bbox_space="points"), section_path=[], engine="native")
    group = next(block for block in blocks if block.type == "table_row"
                 and block.attributes["fields"]["c01"]["raw"] == "Group")
    assert group.attributes["field_sources"]["c02"]["bbox"] == [0, 10, 100, 20]
    assert group.attributes["field_origins"]["c02"]["column_id"] == "c01"


@pytest.mark.parametrize("text", ["<table><tr><td rowspan='0'>x</td></tr></table>",
                                "<table><tr><td>x</td></tr></table><table><tr><td>y</td></tr></table>",
                                "<table><tr><td><table><tr><td>x</td></tr></table></td></tr></table>"])
def test_unsupported_html_is_not_silently_repaired(text):
    assert html_table(text) is None


def test_raw_markdown_table_block_has_explicit_header_and_keeps_values():
    table = ocr_table("| Code | Value |\n| --- | --- |\n| 0001 | 0 |")
    assert table["grid"][1][0]["raw"] == "0001" and table["header_depth"] == 1


@pytest.mark.asyncio
async def test_mixed_ocr_pages_map_back_to_original_physical_pages():
    raw = {"markdown": {"text": "RAW scan 0001"}, "prunedResult": {"width": 100, "height": 100,
           "parsing_res_list": [{"block_label": "text", "block_content": "RAW scan 0001", "block_bbox": [10, 10, 80, 20]}]}}
    response = OCRExtractResponse(filename="selected.pdf", success=True, engine_used="paddle", total_pages=1,
        overall_confidence=0, latency_ms=1, raw_text="cleaned scan",
        pages=[OCRPageResult(page_number=1, extracted_text="cleaned scan", confidence=0, word_count=2, line_count=1)],
        raw_evidence={"provider_response": {"result": {"layoutParsingResults": [raw]}}})
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", AsyncMock(return_value=response)) as ocr:
        result = await extract_source(AsyncMock(), make_pdf("blank", "text", "scan"), "mixed.pdf", "pdf", "standard", None, "tenant")
    assert result.qnu_build_error is None
    validate(result.qnu_document)
    scan = next(b for b in result.qnu_document.blocks if "RAW scan" in b.body)
    assert scan.source_locations[0].page == 3
    assert result.pdf_evidence["ocr_page_map"] == [{"local": 1, "physical": 3}]
    assert "cleaned scan" in result.raw_text  # Existing serving path stays independent.
    assert len(pymupdf.open(stream=ocr.call_args.kwargs["content"], filetype="pdf")) == 1
    assert "raw_evidence" not in response.model_dump()


def test_conflicting_native_and_ocr_regions_keep_one_primary_and_alternative():
    native = empty_native()
    native["layout"]["blocks"] = [native_text("Quota 55", [10, 10, 90, 20])]
    page = {"page": 1, "native": native, "ocr_selected": True, "engine_used": "paddle", "raw_ocr_available": True,
            "ocr_raw_page": {"prunedResult": {"width": 100, "height": 100, "parsing_res_list": [
                {"block_label": "text", "block_content": "Quota 50", "block_bbox": [10, 10, 90, 20]}]}}}
    document = model([page])
    assert len(document.blocks) == 1
    assert document.blocks[0].body == "Quota 50"
    assert document.blocks[0].source_data["alternatives"][0]["text"] == "Quota 55"
    assert document.document_meta["content_status"] == "needs_review"


def test_duplicate_native_ocr_is_not_a_second_source():
    native = empty_native(); native["layout"]["blocks"] = [native_text("Same 55", [10, 10, 90, 20])]
    document = model([{"page": 1, "native": native, "ocr_selected": True, "engine_used": "paddle", "raw_ocr_available": True,
                       "ocr_raw_page": {"prunedResult": {"width": 100, "height": 100, "parsing_res_list": [
                           {"block_label": "text", "block_content": "Same 55", "block_bbox": [10, 10, 90, 20]}]}}}])
    assert len(document.blocks) == 1 and not document.blocks[0].quality_flags


def test_similar_tables_are_not_merged_just_because_headers_match():
    pages = []
    for number in [1, 2]:
        native = empty_native(number)
        native["tables"] = [{"bbox": [10, 40, 90, 60], "matrix": [["Code", "Value"], ["001", "0"]],
                             "cell_boxes": [], "header": {"names": ["Code", "Value"], "external": False}}]
        pages.append({"page": number, "native": native})
    document = model(pages)
    tables = [b for b in document.blocks if b.type == "table"]
    assert len(tables) == 2
    assert all("continuation_candidate" not in b.attributes for b in tables)
    assert {b.source_locations[0].page for b in document.blocks} == {1, 2}


@pytest.mark.asyncio
async def test_raw_ocr_is_preserved_before_cleaner_and_excluded_from_api():
    raw = {"engine_used": "paddle", "total_pages": 1, "raw_text": "Raw 001", "overall_confidence": 0,
           "raw_payload": {"original": "Raw 001"}, "pages": [{"page_number": 1, "extracted_text": "Raw 001",
               "confidence": 0, "word_count": 2, "line_count": 1, "layout_pruned": {"source": "raw"}}]}
    db = AsyncMock(); db.add = MagicMock()
    # Avoid constructing default OCR adapters (which discover remote clients) in this unit test.
    service = object.__new__(OCRService)
    service.default_engine = "paddle"
    with patch("app.modules.ocr.cleaner.post_process_ocr_output", return_value=("Clean", [
        {**raw["pages"][0], "extracted_text": "Clean"}])):
        response = await service._build_response(session=db, result_dict=raw, filename="fixture.pdf",
            tenant_id="tenant", start_time=0, fallback_triggered=False)
    assert response.raw_evidence["pages"][0]["extracted_text"] == "Raw 001"
    assert response.raw_evidence["provider_response"] == {"original": "Raw 001"}
    assert response.raw_text == "Clean" and "raw_evidence" not in response.model_dump()


@pytest.mark.asyncio
async def test_pdf_storage_and_reuse_verify_both_structured_and_raw_hashes():
    document = model([{"page": 1, "native": empty_native()}])
    extraction = SourceExtraction("serving", 1, qnu_document=document, pdf_evidence={"source": "raw"})
    stored = {}
    async def save(path, data):
        stored[path] = data
    with patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", side_effect=save), \
         patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.exists", side_effect=lambda p: p in stored), \
         patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.get", side_effect=lambda p: stored.get(p)):
        artifact = await build_qnu_markdown_artifact(extraction=extraction, document_id="bnd", revision_id="rev1", title=None, snapshot_path="snapshots/test")
        assert artifact["status"] == "ready"
        assert json.loads(stored[artifact["raw_evidence"]["path"]]) == {"source": "raw"}
        for key, hash_key in [("path", "sha256"), ("structured_path", "structured_sha256")]:
            assert hashlib.sha256(stored[artifact[key]]).hexdigest() == artifact[hash_key]
        reused = await rebuild_qnu_markdown_for_revision(artifact, document_id="bnd", revision_id="rev2", snapshot_path="snapshots/test")
        assert reused["status"] == "ready" and b'"rev2"' in stored[reused["path"]]
        stored[artifact["raw_evidence"]["path"]] = b"tampered"
        before = copy.deepcopy(stored)
        rejected = await rebuild_qnu_markdown_for_revision(artifact, document_id="bnd", revision_id="rev3", snapshot_path="snapshots/test")
        assert rejected["reason"] == "pdf_evidence_integrity_failed" and stored == before


@pytest.mark.asyncio
async def test_failed_pdf_builder_still_saves_raw_evidence_not_ready_md():
    extraction = SourceExtraction("", 1, pdf_evidence={"raw": "intact"}, qnu_build_error="ValueError")
    with patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", AsyncMock()) as save:
        artifact = await build_qnu_markdown_artifact(extraction=extraction, document_id="b", revision_id="r", title=None, snapshot_path="snapshot")
    assert artifact["status"] == "failed" and artifact["raw_evidence"]["sha256"]
    assert "path" not in artifact and save.await_count == 1


@pytest.mark.asyncio
async def test_pdf_download_handler_serves_the_revision_artifact_without_reparse():
    from app.modules.knowledge.router import download_source_qnu_markdown

    actor = MagicMock(tenant_id="tenant", workspace_id="workspace")
    artifact = {"status": "ready", "path": "snapshot/test.md", "structured_path": "snapshot/test.json"}
    with patch("app.modules.knowledge.router.source_ingestion_service.get_qnu_markdown_artifact",
               AsyncMock(return_value=artifact)) as resolve, patch(
            "app.core.storage.storage_service.get", AsyncMock(return_value=b"verified pdf markdown")):
        response = await download_source_qnu_markdown("collection", "binding", "revision", "md", AsyncMock(), actor)
    assert response.body == b"verified pdf markdown"
    assert "revision.qnu-rag-v1.md" in response.headers["content-disposition"]
    assert resolve.await_args.kwargs["revision_id"] == "revision"


@pytest.mark.asyncio
async def test_native_real_grid_preserves_atomic_cell_boxes():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        for x in [50, 200, 350]:
            page.draw_line((x, 100), (x, 190))
        for y in [100, 130, 160, 190]:
            page.draw_line((50, y), (350, y))
        for row, values in enumerate([["Code", "Quota"], ["0001", "0"], ["0002", "12"]]):
            for col, value in enumerate(values):
                page.insert_text((60 + col * 150, 120 + row * 30), value)
        content = pdf.tobytes()
    with patch("app.modules.knowledge.services.source_extraction.OCRService.extract_document", AsyncMock()) as ocr:
        result = await extract_source(AsyncMock(), content, "grid.pdf", "pdf", "standard", None, "tenant")
    ocr.assert_not_awaited()
    assert result.qnu_build_error is None
    validate(result.qnu_document)
    rows = [b for b in result.qnu_document.blocks if b.type == "table_row"]
    assert any(row.attributes["fields"]["c01"]["raw"] == "0001" for row in rows)
    cell = next(row for row in rows if row.attributes["fields"]["c01"]["raw"] == "0001")
    source = cell.attributes["field_sources"]["c01"]
    assert source["page"] == 1 and source["bbox"] == [50, 130, 200, 160]


def test_footnote_links_require_unique_explicit_marker_on_same_page():
    native = empty_native()
    native["layout"]["blocks"] = [native_text("Condition [1] is mandatory.", [10, 20, 90, 30]),
                                     native_text("[1] Only when all conditions hold.", [10, 90, 90, 95], size=8)]
    document = model([{"page": 1, "native": native}])
    note = next(b for b in document.blocks if b.type == "note")
    assert document.blocks[0].context_refs == [note.id]
    validate(document)


def test_continuation_at_page_edges_is_only_a_review_candidate():
    pages = []
    for number, box in [(1, [10, 80, 90, 99]), (2, [10, 1, 90, 20])]:
        native = empty_native(number)
        native["tables"] = [{"bbox": box, "matrix": [["Code", "Value"], ["001", "0"]],
                             "cell_boxes": [], "header": {"names": ["Code", "Value"], "external": False}}]
        pages.append({"page": number, "native": native})
    document = model(pages)
    tables = [b for b in document.blocks if b.type == "table"]
    assert len(tables) == 2
    assert tables[1].attributes["continuation_candidate"]["block_id"] == tables[0].id
    assert any(f.code == "table_continuation_needs_review" for f in tables[1].quality_flags)
    validate(document)


def test_header_rescue_proposal_preserves_crop_and_raw_not_a_verified_fact():
    page = {"page": 1, "native": empty_native(), "header_rescue": {
        "audit": {"accepted_lines": ["Number 123"], "bbox": [0, 0, 100, 40], "engine": "paddle"},
        "raw": {"provider_response": {"original": "Number 123"}}}}
    document = model([page])
    block = document.blocks[0]
    assert block.source_data["raw"]["provider_response"]["original"] == "Number 123"
    assert block.source_locations[0].bbox == [0, 0, 100, 40]
    assert block.attributes["location_precision"] == "crop_region"
    assert block.quality_flags[0].code == "header_rescue_needs_review"
    assert document.document_meta["content_status"] == "needs_review"
    validate(document)


def test_vector_geometry_is_retained_without_inventing_its_text():
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.draw_rect((100, 100, 200, 200), fill=(0.5, 0.5, 0.5))
        evidence = capture_native_page(page)
    json.dumps(evidence)
    assert evidence["drawings"][0]["rect"] == [100, 100, 200, 200]
    document = model([{"page": 1, "native": evidence}])
    assert document.blocks[0].type == "figure" and document.blocks[0].body == ""
    assert document.blocks[0].quality_flags[0].code == "visual_content_untranscribed"


@pytest.mark.asyncio
async def test_derivative_capture_error_does_not_break_existing_serving_extraction():
    with patch("app.modules.knowledge.parsers.pdf_evidence.capture_native_page", side_effect=ValueError("fixture")):
        result = await extract_source(AsyncMock(), make_pdf("text"), "text.pdf", "pdf", "standard", None, "tenant")
    assert "Digital source" in result.raw_text
    assert result.qnu_document is None and result.qnu_build_error == "ValueError"
    assert result.pdf_evidence["pages"][0]["native"]["capture_error"] == "ValueError"


def test_grid_rulings_and_junction_dots_are_not_untranscribed_visual_regions():
    native = empty_native()
    native["drawings"] = [
        {"rect": [10, 20, 90, 20.5], "width": 0.5, "type": "s", "items": [("l", (10, 20), (90, 20))]},
        {"rect": [28.4, 49.7, 28.9, 50.2], "fill": [0, 0, 0], "type": "f",
         "items": [("re", pymupdf.Rect(28.4, 49.7, 28.9, 50.2))]},
        # A filled rectangle has no stroke width: its own short side is the thickness of the rule.
        {"rect": [10, 95, 90, 96.2], "fill": [0, 0, 0], "type": "f", "items": [("re", pymupdf.Rect(10, 95, 90, 96.2))]},
        {"rect": [10, 60, 60, 90], "fill": [0.5, 0.5, 0.5], "type": "f", "items": [("re", pymupdf.Rect(10, 60, 60, 90))]},
    ]
    document = model([{"page": 1, "native": native}])
    figures = [block for block in document.blocks if block.type == "figure"]
    assert [block.source_data["raw"]["rect"] for block in figures] == [[10, 60, 60, 90]]
    assert document.document_meta["visual_classification"] == {
        "ruling_strokes_in_source": 3, "visual_regions_retained": 1, "symbol_legend_definitions": 0}
    validate(document)


def test_competing_table_reconstructions_publish_the_one_carrying_the_evidence():
    native = empty_native()
    native["tables"] = [{"bbox": [0, 0, 100, 100], "matrix": [["", ""], ["", ""], ["", ""]],
                         "cell_boxes": [], "header": {"names": [], "external": False}}]
    page = {"page": 1, "native": native, "ocr_selected": True, "engine_used": "paddle", "raw_ocr_available": True,
            "ocr_raw_page": {"prunedResult": {"width": 100, "height": 100, "parsing_res_list": [
                {"block_label": "table", "block_bbox": [5, 10, 95, 80],
                 "block_content": "<table><tr><td>Ref</td><td>Name</td></tr><tr><td>01</td><td>Alpha</td></tr></table>"}]}}}
    document = model([page])
    tables = [block for block in document.blocks if block.type == "table"]
    rows = [block for block in document.blocks if block.type == "table_row"]
    assert len(tables) == 1 and len(rows) == 2
    assert all("Alpha" in row.body or "Name" in row.body for row in rows)
    assert tables[0].source_data["alternatives"][0]["table"]["grid"][0][0]["unresolved"] is True
    assert any(flag.code == "native_ocr_conflict" for flag in tables[0].quality_flags)
    validate(document)


def _headerless_ocr_page(with_labels: bool, label_box: list[float]) -> dict:
    native = empty_native()
    if with_labels:
        native["layout"]["blocks"] = [native_text("Ref Name", label_box)]
    return {"page": 1, "native": native, "ocr_selected": True, "engine_used": "paddle", "raw_ocr_available": True,
            "ocr_raw_page": {"prunedResult": {"width": 100, "height": 100, "parsing_res_list": [
                {"block_label": "table", "block_bbox": [5, 10, 95, 80],
                 "block_content": "<table><tr><td>Ref</td><td>Name</td></tr>"
                                  "<tr><td>01</td><td>Alpha</td></tr></table>"}]}}}


def test_ocr_header_proposal_requires_the_digital_layer_to_repeat_every_label_in_that_band():
    document = model([_headerless_ocr_page(True, [5, 10, 95, 20])])
    table = next(block for block in document.blocks if block.type == "table")
    assert any(flag.code == "native_header_needs_review" for flag in table.quality_flags)
    assert any(flag.code == "table_header_unresolved" for flag in table.quality_flags)
    assert table.source_data["table"]["header_proposal"]["basis"] == "native_text_layer_corroboration"
    assert table.source_data["table"]["header_proposal"]["labels"] == ["Ref", "Name"]
    rows = [block for block in document.blocks if block.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Ref"
    assert rows[1].attributes["fields"]["c01"]["raw"] == "01"
    validate(document)

    for page in (_headerless_ocr_page(False, [0, 0, 0, 0]), _headerless_ocr_page(True, [5, 60, 95, 70])):
        document = model([page])
        unresolved = next(block for block in document.blocks if block.type == "table")
        assert any(flag.code == "table_header_unresolved" for flag in unresolved.quality_flags)
        assert unresolved.source_data["table"].get("header_proposal") is None
        assert len([block for block in document.blocks if block.type == "table_row"]) == 2


def test_dash_cell_is_evidence_only_when_the_document_itself_defines_the_symbol():
    legend = 'Ký hiệu "–": value not collected for this row.'
    html = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"

    def page(with_legend: bool) -> dict:
        native = empty_native()
        native["layout"]["blocks"] = ([native_text(legend, [10, 90, 90, 95])] if with_legend else [])
        blocks = [{"block_label": "table", "block_bbox": [5, 10, 95, 80], "block_content": html}]
        if with_legend:
            blocks.append({"block_label": "text", "block_bbox": [10, 90, 90, 95], "block_content": legend})
        return {"page": 1, "native": native, "ocr_selected": True, "engine_used": "paddle",
                "raw_ocr_available": True, "ocr_raw_page": {"prunedResult": {"width": 100, "height": 100,
                                                                            "parsing_res_list": blocks}}}

    defined = model([page(True)])
    row = next(block for block in defined.blocks if block.type == "table_row" and block.attributes["fields"]["c01"]["raw"] == "01")
    assert row.attributes["fields"]["c02"] == {"raw": "–", "state": "present", "normalized": None}
    flag = next(f for f in row.quality_flags if f.code == "cell_symbol_defined")
    assert flag.status == "resolved" and flag.field_id == "c02"
    assert row.context_refs == flag.related_block_ids
    assert defined.document_meta["visual_classification"]["symbol_legend_definitions"] == 1
    validate(defined)

    undefined = model([page(False)])
    row = next(block for block in undefined.blocks if block.type == "table_row"
               and block.attributes["fields"]["c01"]["raw"] == "01")
    assert row.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in row.quality_flags)
    assert not [f for f in row.quality_flags if f.code == "cell_symbol_defined"]
    validate(undefined)


def test_native_continuation_data_rows_are_not_promoted_to_headers():
    raw = {
        "matrix": [
            ["42", "7510605", "Logistics và Quản lý chuỗi cung ứng", "16", "19", "650", "16"],
            ["43", "7520116", "Kỹ thuật cơ khí động lực", "15", "18", "600", "15"],
        ],
        "cell_boxes": [],
        "header": {
            "names": ["42", "7510605", "Logistics và Quản lý chuỗi cung ứng", "16", "19", "650", "16"],
            "external": False,
        },
    }
    parsed = native_table(raw)
    assert parsed["header_depth"] == 0
    blocks = table_blocks(
        parsed,
        block_id="p0006_b0001",
        parent_id=None,
        location=QnuSourceLocation(page=6, bbox_space="points"),
        section_path=[],
        engine="native",
    )
    assert len(blocks) == 3
    data_rows = [b for b in blocks if b.type == "table_row"]
    assert len(data_rows) == 2
    assert data_rows[0].attributes["fields"]["c01"]["raw"] == "42"
    assert data_rows[1].attributes["fields"]["c01"]["raw"] == "43"
    assert any(flag.code == "table_header_unresolved" for flag in blocks[0].quality_flags)


def test_ocr_header_proposal_does_not_consume_numeric_data_rows():
    native = empty_native()
    native["layout"]["blocks"] = [native_text("001 12 002 15", [5, 10, 95, 20])]
    html = "<table><tr><td>001</td><td>12</td></tr><tr><td>002</td><td>15</td></tr></table>"
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100,
                "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [5, 10, 95, 80], "block_content": html}
                ],
            }
        },
    }
    doc = model([page])
    table = next(b for b in doc.blocks if b.type == "table")
    rows = [b for b in doc.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "001"
    assert rows[1].attributes["fields"]["c01"]["raw"] == "002"
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)


def test_symbol_legends_respect_page_scope_and_do_not_leak_cross_page():
    legend_p1 = 'Ký hiệu "–": không xét tuyển.'
    legend_p2 = 'Ký hiệu "–": chưa có dữ liệu.'
    html_p1 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"
    html_p2 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>02</td><td>–</td></tr></table>"
    html_p3 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>03</td><td>–</td></tr></table>"

    def make_page(p: int, legend: str | None, html: str) -> dict:
        native = empty_native(p)
        if legend:
            native["layout"]["blocks"] = [native_text(legend, [10, 90, 90, 95])]
        blocks = [{"block_label": "table", "block_bbox": [5, 10, 95, 80], "block_content": html}]
        if legend:
            blocks.append({"block_label": "text", "block_bbox": [10, 90, 90, 95], "block_content": legend})
        return {
            "page": p,
            "native": native,
            "ocr_selected": True,
            "engine_used": "paddle",
            "raw_ocr_available": True,
            "ocr_raw_page": {
                "prunedResult": {"width": 100, "height": 100, "parsing_res_list": blocks}
            },
        }

    doc = model([
        make_page(1, legend_p1, html_p1),
        make_page(2, legend_p2, html_p2),
        make_page(3, None, html_p3),
    ])

    r1 = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    r2 = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "02")
    r3 = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "03")

    # Page 1 must use legend 1
    assert r1.attributes["fields"]["c02"]["state"] == "present"
    flag1 = next(f for f in r1.quality_flags if f.code == "cell_symbol_defined")
    assert "không xét tuyển" in flag1.detail
    assert r1.attributes["symbol_definitions"]["c02"]["line"] == legend_p1

    # Page 2 must use legend 2, NOT legend 1
    assert r2.attributes["fields"]["c02"]["state"] == "present"
    flag2 = next(f for f in r2.quality_flags if f.code == "cell_symbol_defined")
    assert "chưa có dữ liệu" in flag2.detail
    assert r2.attributes["symbol_definitions"]["c02"]["line"] == legend_p2

    # Page 3 has no legend and conflicting document definitions -> MUST be ambiguous
    assert r3.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r3.quality_flags)
    assert not [f for f in r3.quality_flags if f.code == "cell_symbol_defined"]


def test_native_and_ocr_table_without_header_evidence_preserves_all_rows_at_depth_zero():
    # 1. Native table with names: []
    raw1 = {
        "matrix": [["Alpha", "North"], ["Beta", "South"]],
        "cell_boxes": [],
        "header": {"names": [], "external": False},
    }
    parsed1 = native_table(raw1)
    assert parsed1["header_depth"] == 0
    blocks1 = table_blocks(
        parsed1,
        block_id="t1",
        parent_id=None,
        location=QnuSourceLocation(page=1, bbox_space="points"),
        section_path=[],
        engine="native",
    )
    rows1 = [b for b in blocks1 if b.type == "table_row"]
    assert len(rows1) == 2
    assert rows1[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows1[1].attributes["fields"]["c01"]["raw"] == "Beta"
    assert any(f.code == "table_header_unresolved" for f in blocks1[0].quality_flags)

    # 2. Native table with names: ["Alpha", "North"] but no structural evidence
    raw2 = {
        "matrix": [["Alpha", "North"], ["Beta", "South"]],
        "cell_boxes": [],
        "header": {"names": ["Alpha", "North"], "external": False},
    }
    parsed2 = native_table(raw2)
    assert parsed2["header_depth"] == 0
    blocks2 = table_blocks(
        parsed2,
        block_id="t2",
        parent_id=None,
        location=QnuSourceLocation(page=1, bbox_space="points"),
        section_path=[],
        engine="native",
    )
    rows2 = [b for b in blocks2 if b.type == "table_row"]
    assert len(rows2) == 2
    assert rows2[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert any(f.code == "table_header_unresolved" for f in blocks2[0].quality_flags)

    # 3. OCR table with plain td elements
    parsed_ocr = html_table("<table><tr><td>Alpha</td><td>North</td></tr><tr><td>Beta</td><td>South</td></tr></table>")
    assert parsed_ocr["header_depth"] == 0
    blocks_ocr = table_blocks(
        parsed_ocr,
        block_id="t3",
        parent_id=None,
        location=QnuSourceLocation(page=1, bbox_space="percent"),
        section_path=[],
        engine="ocr",
    )
    rows_ocr = [b for b in blocks_ocr if b.type == "table_row"]
    assert len(rows_ocr) == 2
    assert rows_ocr[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert any(f.code == "table_header_unresolved" for f in blocks_ocr[0].quality_flags)


def test_native_external_headers_and_internal_header_proposals():
    # 1. External header evidence
    raw_ext = {
        "matrix": [["Alpha", "North"], ["Beta", "South"]],
        "header": {"names": ["Col A", "Col B"], "external": True},
    }
    parsed_ext = native_table(raw_ext)
    assert parsed_ext["header_depth"] == 0
    assert parsed_ext["external_headers"] == ["Col A", "Col B"]
    blocks_ext = table_blocks(
        parsed_ext,
        block_id="t_ext",
        parent_id=None,
        location=QnuSourceLocation(page=1, bbox_space="points"),
        section_path=[],
        engine="native",
    )
    assert [c["header_path"] for c in blocks_ext[0].attributes["columns"]] == [["Col A"], ["Col B"]]
    rows_ext = [b for b in blocks_ext if b.type == "table_row"]
    assert len(rows_ext) == 2
    assert rows_ext[0].attributes["fields"]["c01"]["raw"] == "Alpha"

    # 2. An engine bounding box and a gap remain a proposal, not a row-role annotation.
    raw_bbox = {
        "matrix": [["Ref", "Score"], ["01", "100"]],
        "cell_boxes": [[[10, 10, 50, 20], [50, 10, 90, 20]], [[10, 25, 50, 35], [50, 25, 90, 35]]],
        "header": {"names": ["Ref", "Score"], "bbox": [10, 10, 90, 20], "external": False},
    }
    parsed_bbox = native_table(raw_bbox)
    assert parsed_bbox["header_depth"] == 0
    assert parsed_bbox["header_proposal"]["labels"] == ["Ref", "Score"]
    blocks_bbox = table_blocks(
        parsed_bbox,
        block_id="t_bbox",
        parent_id=None,
        location=QnuSourceLocation(page=1, bbox_space="points"),
        section_path=[],
        engine="native",
    )
    assert [c["header_path"] for c in blocks_bbox[0].attributes["columns"]] == [[], []]
    rows_bbox = [b for b in blocks_bbox if b.type == "table_row"]
    assert len(rows_bbox) == 2
    assert rows_bbox[0].attributes["fields"]["c01"]["raw"] == "Ref"
    assert rows_bbox[1].attributes["fields"]["c01"]["raw"] == "01"

    # 3. A proposed multi-level header also preserves every row until reviewed.
    raw_multi = {
        "matrix": [["H1", "H2"], ["Sub1", "Sub2"], ["01", "100"]],
        "header": {"names": ["H1", "H2"], "external": False},
        "proposed_header_depth": 2,
    }
    parsed_multi = native_table(raw_multi)
    assert parsed_multi["header_depth"] == 0
    assert parsed_multi["header_proposal"]["depth"] == 2
    assert len(parsed_multi["grid"]) == 3


def test_symbol_legends_unrelated_pages_do_not_leak_single_document_legend():
    legend_p1 = 'Ký hiệu "–": không đủ điều kiện.'
    html_p1 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"
    html_p2 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>02</td><td>–</td></tr></table>"

    def make_page(p: int, legend: str | None, html: str) -> dict:
        native = empty_native(p)
        if legend:
            native["layout"]["blocks"] = [native_text(legend, [10, 85, 90, 95])]
        blocks = [{"block_label": "table", "block_bbox": [10, 30, 90, 70], "block_content": html}]
        if legend:
            blocks.append({"block_label": "text", "block_bbox": [10, 85, 90, 95], "block_content": legend})
        return {
            "page": p,
            "native": native,
            "ocr_selected": True,
            "engine_used": "paddle",
            "raw_ocr_available": True,
            "ocr_raw_page": {
                "prunedResult": {"width": 100, "height": 100, "parsing_res_list": blocks}
            },
        }

    doc = model([
        make_page(1, legend_p1, html_p1),
        make_page(2, None, html_p2),
    ])

    r1 = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    r2 = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "02")

    # Page 1 table resolves dash
    assert r1.attributes["fields"]["c02"]["state"] == "present"
    flag1 = next(f for f in r1.quality_flags if f.code == "cell_symbol_defined")
    assert "không đủ điều kiện" in flag1.detail

    # Page 2 table has NO continuation relation and no legend -> MUST remain ambiguous
    assert r2.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r2.quality_flags)
    assert not [f for f in r2.quality_flags if f.code == "cell_symbol_defined"]
    legend_block_p1 = next(b for b in doc.blocks if b.type in {"text", "note"} and "không đủ điều kiện" in b.body)
    assert legend_block_p1.id not in r2.context_refs


def test_symbol_legends_same_page_conflicting_definitions_remain_ambiguous():
    legend1 = 'Ký hiệu "–": không xét tuyển.'
    legend2 = 'Ký hiệu "–": chưa có dữ liệu.'
    html = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"

    native = empty_native(1)
    native["layout"]["blocks"] = [
        native_text(legend1, [10, 80, 90, 85]),
        native_text(legend2, [10, 86, 90, 91]),
    ]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100,
                "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [10, 10, 90, 75], "block_content": html},
                    {"block_label": "text", "block_bbox": [10, 80, 90, 85], "block_content": legend1},
                    {"block_label": "text", "block_bbox": [10, 86, 90, 91], "block_content": legend2},
                ],
            }
        },
    }

    doc = model([page])
    r = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    assert r.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r.quality_flags)
    assert not [f for f in r.quality_flags if f.code == "cell_symbol_defined"]


def test_symbol_legends_same_page_duplicate_same_meaning_resolves():
    legend1 = 'Ký hiệu "–": không xét tuyển.'
    legend2 = 'Ký hiệu "–": không xét tuyển.'
    html = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"

    native = empty_native(1)
    native["layout"]["blocks"] = [
        native_text(legend1, [10, 80, 90, 85]),
        native_text(legend2, [10, 86, 90, 91]),
    ]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100,
                "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [10, 10, 90, 75], "block_content": html},
                    {"block_label": "text", "block_bbox": [10, 80, 90, 85], "block_content": legend1},
                    {"block_label": "text", "block_bbox": [10, 86, 90, 91], "block_content": legend2},
                ],
            }
        },
    }

    doc = model([page])
    r = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    assert r.attributes["fields"]["c02"]["state"] == "present"
    assert any(f.code == "cell_symbol_defined" and f.field_id == "c02" for f in r.quality_flags)


def test_symbol_legends_continuation_candidate_preserves_evidence_but_keeps_symbols_ambiguous():
    legend_p1 = 'Ký hiệu "–": không xét tuyển.'
    html_p1 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"
    html_p2 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>02</td><td>–</td></tr></table>"

    page1 = {
        "page": 1,
        "native": {**empty_native(1), "layout": {"blocks": [native_text(legend_p1, [10, 86, 90, 92])]}},
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [10, 30, 90, 85], "block_content": html_p1},
                    {"block_label": "text", "block_bbox": [10, 86, 90, 92], "block_content": legend_p1},
                ],
            }
        },
    }
    page2 = {
        "page": 2,
        "native": empty_native(2),
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [10, 10, 90, 70], "block_content": html_p2},
                ],
            }
        },
    }

    doc = model([page1, page2])
    t2 = next(b for b in doc.blocks if b.type == "table" and b.source_locations[0].page == 2)
    assert any(f.code == "table_continuation_needs_review" for f in t2.quality_flags)
    assert t2.attributes["continuation_candidate"]["basis"] == "inferred_geometry"
    r2 = next(b for b in doc.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "02")
    assert r2.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r2.quality_flags)
    assert not [f for f in r2.quality_flags if f.code == "cell_symbol_defined"]


@pytest.mark.asyncio
async def test_queue_reparse_inline_is_not_enqueued_by_reconciler_or_worker():
    from app.modules.jobs.models import JobRecord
    from app.modules.jobs.service import jobs_service
    from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
    from app.modules.knowledge.services.source_reparse import queue_reparse
    from app.workers.tasks import task_knowledge_source_reparse

    mock_binding = MagicMock(spec=KnowledgeBinding)
    mock_rev = MagicMock(spec=KnowledgeSourceRevision)
    mock_rev.id = "rev_base_1"
    mock_rev.revision_no = 1
    mock_rev.origin_document_id = "doc_1"
    mock_rev.origin_file_hash = "h" * 64
    mock_rev.snapshot_storage_path = "snapshots/s.pdf"
    mock_rev.snapshot_metadata = {}
    mock_binding.active_source_revision = mock_rev

    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=1), scalar_one_or_none=MagicMock(return_value=None)))

    with patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()), \
         patch("app.modules.knowledge.services.source_ingestion_service.source_ingestion_service.get_source", AsyncMock(return_value=mock_binding)), \
         patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()), \
         patch("app.modules.knowledge.services.source_reparse.enqueue_arq_job", AsyncMock()) as mock_source_enqueue:

        # 1. Inline reparse reservation
        await queue_reparse(
            session, "col_1", "src_1", "standard", None, "tenant", "workspace", dispatch=False
        )
        assert session.add.call_count >= 2
        job_inline = next(call.args[0] for call in session.add.call_args_list if isinstance(call.args[0], JobRecord))
        assert job_inline.dispatch_status == "inline"
        mock_source_enqueue.assert_not_called()

        # 2. Query-sensitive reconciliation fake session
        job_pending_failed_broker = JobRecord(
            id="job_pending_rec_1",
            job_type="knowledge_source_reparse",
            status="queued",
            dispatch_status="pending",
            cancel_requested=False,
            error="Redis broker down on initial dispatch",
        )
        job_cancelled = JobRecord(
            id="job_cancelled_1",
            job_type="knowledge_source_reparse",
            status="queued",
            dispatch_status="pending",
            cancel_requested=True,
        )

        class QuerySensitiveFakeSession:
            def __init__(self, candidates: list[JobRecord]):
                self.candidates = candidates
                self.committed = False

            async def execute(self, stmt):
                where_clauses = stmt._where_criteria
                has_dispatch_pending_filter = any(
                    getattr(c, "left", None) is not None
                    and getattr(c.left, "name", None) == "dispatch_status"
                    and getattr(c, "right", None) is not None
                    and getattr(c.right, "value", None) == "pending"
                    for c in where_clauses
                )
                matched = []
                for j in self.candidates:
                    if has_dispatch_pending_filter:
                        if j.status == "queued" and j.dispatch_status == "pending" and not j.cancel_requested:
                            matched.append(j)
                    else:
                        if j.status == "queued" and not j.cancel_requested:
                            matched.append(j)
                res = MagicMock()
                res.scalars.return_value.all.return_value = matched
                return res

            async def commit(self):
                self.committed = True

        fake_reconcile_db = QuerySensitiveFakeSession([job_inline, job_pending_failed_broker, job_cancelled])

        with patch("app.modules.jobs.service.enqueue_arq_job", AsyncMock(return_value="arq_rec_123")) as mock_jobs_enqueue:
            dispatched = await jobs_service.reconcile_pending_dispatches(fake_reconcile_db)

            assert dispatched == 1
            assert job_pending_failed_broker.dispatch_status == "dispatched"
            assert job_pending_failed_broker.arq_job_id == "arq_rec_123"
            assert job_pending_failed_broker.error is None
            mock_jobs_enqueue.assert_awaited_once_with(
                "task_knowledge_source_reparse",
                "job_pending_rec_1",
                broker_job_id="job_pending_rec_1:attempt:0",
            )

            assert job_inline.dispatch_status == "inline"
            mock_source_enqueue.assert_not_called()

        # 3. Worker task with ARQ worker context (job_try in ctx) must skip inline reserved job
        with patch("app.workers.tasks._load_job", AsyncMock(return_value=job_inline)):
            res = await task_knowledge_source_reparse({"redis": MagicMock(), "job_try": 1}, job_inline.id)
            assert res["status"] in ("skipped", "cancelled")


def test_native_table_engine_bbox_does_not_prove_header_role_even_with_separation():
    # Matrix with text words in both rows, engine proposes header.names and header.bbox
    # but cell boxes show contiguous grid without physical separation
    table_data = {
        "matrix": [["Alpha", "North"], ["Beta", "South"]],
        "cell_boxes": [
            [[0, 0, 50, 10], [50, 0, 100, 10]],
            [[0, 10, 50, 20], [50, 10, 100, 20]],
        ],
        "proposed_header_depth": 1,
        "header": {
            "external": False,
            "names": ["Alpha", "North"],
            "bbox": [0, 0, 100, 10],
        },
    }
    parsed = native_table(table_data)
    assert parsed["header_depth"] == 0

    location = QnuSourceLocation(page=1, locator="pdf:page:1/native/table/0")
    blocks = table_blocks(parsed, block_id="p0001_b0001", parent_id=None,
                          location=location, section_path=[], engine="pymupdf")
    assert any(f.code == "table_header_unresolved" for f in blocks[0].quality_flags)
    row_blocks = [b for b in blocks if b.type == "table_row"]
    assert len(row_blocks) == 2
    assert row_blocks[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert row_blocks[1].attributes["fields"]["c01"]["raw"] == "Beta"

    # Whitespace cannot establish a header role either.
    separated_table = copy.deepcopy(table_data)
    separated_table["cell_boxes"][1] = [[0, 15, 50, 25], [50, 15, 100, 25]]
    parsed_sep = native_table(separated_table)
    assert parsed_sep["header_depth"] == 0
    assert parsed_sep["header_proposal"]["labels"] == ["Alpha", "North"]


def test_ocr_native_agreement_preserves_unverified_row_end_to_end_in_builder():
    html = "<table><tr><td>Alpha</td><td>North</td></tr><tr><td>Beta</td><td>South</td></tr></table>"
    native = empty_native(1)
    # Native text layer repeats the OCR text in row 0
    native["layout"]["blocks"] = [native_text("Alpha North", [5, 10, 95, 20])]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [5, 10, 95, 80], "block_content": html},
                ],
            }
        },
    }
    document = model([page])
    table = next(b for b in document.blocks if b.type == "table")
    # Header proposal is retained for review
    assert table.source_data["table"]["header_proposal"]["basis"] == "native_text_layer_corroboration"
    assert table.source_data["table"]["header_proposal"]["labels"] == ["Alpha", "North"]
    assert any(f.code == "native_header_needs_review" for f in table.quality_flags)
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)
    # Both rows are preserved as table_row blocks; unverified row is NOT consumed
    rows = [b for b in document.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows[1].attributes["fields"]["c01"]["raw"] == "Beta"
    validate(document)


def test_symbol_legends_two_independent_same_page_tables_do_not_leak_legend():
    legend_text = 'Ký hiệu "–": không xét tuyển.'
    html1 = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"
    html2 = "<table><tr><td>Item</td><td>Value</td></tr><tr><td>10</td><td>–</td></tr></table>"

    native = empty_native(1)
    # Legend is placed immediately below Table 1 [10, 10, 90, 40], at [10, 42, 90, 48]
    native["layout"]["blocks"] = [native_text(legend_text, [10, 42, 90, 48])]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [10, 10, 90, 40], "block_content": html1},
                    {"block_label": "text", "block_bbox": [10, 42, 90, 48], "block_content": legend_text},
                    {"block_label": "table", "block_bbox": [10, 55, 90, 85], "block_content": html2},
                ],
            }
        },
    }
    document = model([page])
    r1 = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    r2 = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "10")

    # Table 1 (adjacent to legend) resolves symbol:
    assert r1.attributes["fields"]["c02"]["state"] == "present"
    flag1 = next(f for f in r1.quality_flags if f.code == "cell_symbol_defined")
    assert "không xét tuyển" in flag1.detail

    # Table 2 (independent, not adjacent) MUST remain ambiguous:
    assert r2.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r2.quality_flags)
    assert not [f for f in r2.quality_flags if f.code == "cell_symbol_defined"]
    legend_block = next(b for b in document.blocks if b.type in {"text", "note"} and "không xét tuyển" in b.body)
    assert legend_block.id in r1.context_refs
    assert legend_block.id not in r2.context_refs
    validate(document)


def test_native_table_mixed_numeric_row1_does_not_consume_row0_without_independent_evidence():
    # Matrix with text row 0 and mixed/numeric row 1, empty cell_boxes, engine header names equal row 0
    table_data = {
        "id": "native_table_0",
        "bbox": [0, 0, 100, 100],
        "matrix": [["Alpha", "North"], ["2", "South"]],
        "cell_boxes": [],
        "proposed_header_depth": 1,
        "header": {
            "external": False,
            "names": ["Alpha", "North"],
            "bbox": None,
        },
    }
    # 1. Direct unit verification: header_depth must be 0 without independent evidence
    parsed = native_table(table_data)
    assert parsed["header_depth"] == 0

    # 2. Full builder verification
    native = empty_native(1)
    native["tables"] = [table_data]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": False,
        "engine_used": "pymupdf",
    }
    document = model([page])
    table = next(b for b in document.blocks if b.type == "table")
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)

    # First-row record identity must be preserved and not consumed as header
    rows = [b for b in document.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows[0].attributes["fields"]["c02"]["raw"] == "North"
    assert rows[1].attributes["fields"]["c01"]["raw"] == "2"
    assert rows[1].attributes["fields"]["c02"]["raw"] == "South"
    validate(document)


def test_ocr_table_mixed_numeric_row1_does_not_consume_row0_in_full_builder():
    html = "<table><tr><td>Alpha</td><td>North</td></tr><tr><td>2</td><td>South</td></tr></table>"
    native = empty_native(1)
    native["layout"]["blocks"] = [native_text("Alpha North", [0, 0, 100, 10])]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [0, 0, 100, 100], "block_content": html},
                ],
            }
        },
    }
    document = model([page])
    table = next(b for b in document.blocks if b.type == "table")
    # Proposal is retained for reviewer inspection
    assert table.source_data["table"]["header_proposal"]["basis"] == "native_text_layer_corroboration"
    assert table.source_data["table"]["header_proposal"]["labels"] == ["Alpha", "North"]
    assert any(f.code == "native_header_needs_review" for f in table.quality_flags)
    assert any(f.code == "table_header_unresolved" for f in table.quality_flags)

    # Both rows are preserved as table_row blocks; first-row record identity is preserved
    rows = [b for b in document.blocks if b.type == "table_row"]
    assert len(rows) == 2
    assert rows[0].attributes["fields"]["c01"]["raw"] == "Alpha"
    assert rows[0].attributes["fields"]["c02"]["raw"] == "North"
    assert rows[1].attributes["fields"]["c01"]["raw"] == "2"
    assert rows[1].attributes["fields"]["c02"]["raw"] == "South"
    validate(document)


def test_symbol_legends_side_by_side_tables_shared_legend_tie_abstains():
    legend_text = 'Ký hiệu "–": không xét tuyển.'
    html_a = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"
    html_b = "<table><tr><td>Item</td><td>Value</td></tr><tr><td>10</td><td>–</td></tr></table>"

    native = empty_native(1)
    # Full-width shared legend at [0, 65, 100, 70]
    native["layout"]["blocks"] = [native_text(legend_text, [0, 65, 100, 70])]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [0, 30, 40, 60], "block_content": html_a},
                    {"block_label": "table", "block_bbox": [60, 30, 100, 60], "block_content": html_b},
                    {"block_label": "text", "block_bbox": [0, 65, 100, 70], "block_content": legend_text},
                ],
            }
        },
    }
    document = model([page])
    r_a = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    r_b = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "10")

    # Symmetric / equal-distance case: tie must abstain; both fields remain ambiguous
    assert r_a.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r_a.quality_flags)
    assert not [f for f in r_a.quality_flags if f.code == "cell_symbol_defined"]

    assert r_b.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r_b.quality_flags)
    assert not [f for f in r_b.quality_flags if f.code == "cell_symbol_defined"]

    legend_block = next(b for b in document.blocks if b.type in {"text", "note"} and "không xét tuyển" in b.body)
    assert legend_block.id not in r_a.context_refs
    assert legend_block.id not in r_b.context_refs
    validate(document)


def test_symbol_legends_positive_uniquely_adjacent_table_resolves():
    legend_text = 'Ký hiệu "–": không xét tuyển.'
    html = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"

    native = empty_native(1)
    # Legend uniquely placed immediately below Table 1 [10, 10, 90, 40], at [10, 42, 90, 48]
    native["layout"]["blocks"] = [native_text(legend_text, [10, 42, 90, 48])]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [10, 10, 90, 40], "block_content": html},
                    {"block_label": "text", "block_bbox": [10, 42, 90, 48], "block_content": legend_text},
                ],
            }
        },
    }
    document = model([page])
    r = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    assert r.attributes["fields"]["c02"]["state"] == "present"
    flag = next(f for f in r.quality_flags if f.code == "cell_symbol_defined")
    assert "không xét tuyển" in flag.detail
    legend_block = next(b for b in document.blocks if b.type in {"text", "note"} and "không xét tuyển" in b.body)
    assert legend_block.id in r.context_refs
    validate(document)


def test_symbol_legends_nearby_table_in_another_column_does_not_interfere():
    legend_text = 'Ký hiệu "–": giá trị cột trái.'
    html_left = "<table><tr><td>Ref</td><td>Score</td></tr><tr><td>01</td><td>–</td></tr></table>"
    html_right = "<table><tr><td>Item</td><td>Value</td></tr><tr><td>10</td><td>–</td></tr></table>"

    native = empty_native(1)
    # Legend is in left column [0, 52, 45, 56], immediately below Table 1 [0, 10, 45, 50]
    native["layout"]["blocks"] = [native_text(legend_text, [0, 52, 45, 56])]
    page = {
        "page": 1,
        "native": native,
        "ocr_selected": True,
        "engine_used": "paddle",
        "raw_ocr_available": True,
        "ocr_raw_page": {
            "prunedResult": {
                "width": 100, "height": 100,
                "parsing_res_list": [
                    {"block_label": "table", "block_bbox": [0, 10, 45, 50], "block_content": html_left},
                    {"block_label": "text", "block_bbox": [0, 52, 45, 56], "block_content": legend_text},
                    {"block_label": "table", "block_bbox": [55, 10, 100, 50], "block_content": html_right},
                ],
            }
        },
    }
    document = model([page])
    r_left = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "01")
    r_right = next(b for b in document.blocks if b.type == "table_row" and b.attributes["fields"]["c01"]["raw"] == "10")

    # Table 1 (left column) uniquely wins Legend 1
    assert r_left.attributes["fields"]["c02"]["state"] == "present"
    flag_left = next(f for f in r_left.quality_flags if f.code == "cell_symbol_defined")
    assert "giá trị cột trái" in flag_left.detail

    # Table 2 (right column) has no horizontal overlap with Legend 1; must NOT interfere and stays ambiguous
    assert r_right.attributes["fields"]["c02"]["state"] == "ambiguous"
    assert any(f.code == "ambiguous_cell" and f.field_id == "c02" for f in r_right.quality_flags)
    assert not [f for f in r_right.quality_flags if f.code == "cell_symbol_defined"]

    legend_block = next(b for b in document.blocks if b.type in {"text", "note"} and "giá trị cột trái" in b.body)
    assert legend_block.id in r_left.context_refs
    assert legend_block.id not in r_right.context_refs
    validate(document)
