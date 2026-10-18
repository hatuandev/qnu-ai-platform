"""Tests for DOCX → QNU RAG Markdown v1.0: builder, renderer, validator and artifacts."""

from __future__ import annotations

import asyncio
import io
import json
import re
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import docx

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import (
    QnuIssue,
    QnuValidationReport,
    parse_qnu_markdown,
    render_qnu_markdown,
    validate_qnu_markdown,
)
from app.modules.knowledge.parsers import get_document_parser
from app.modules.knowledge.parsers.docling_structure import (
    build_qnu_structured_document,
    map_unit_to_page,
)
from app.modules.knowledge.services.qnu_docx_artifacts import (
    QNU_MARKDOWN_RENDERER_VERSION,
    build_qnu_markdown_artifact,
    rebuild_qnu_markdown_for_revision,
)
from app.modules.knowledge.services.source_extraction import (
    SourceExtraction,
    align_office_markdown,
    extract_source,
)
from app.modules.knowledge.services.source_ingestion_service import (
    compute_sha256,
    source_ingestion_service,
)

DOC_ID = "bnd_test000001"
REV_ID = "ks_rev_test0001"
SHA = "a" * 64


def _parse_docx(content: bytes, name: str = "fixture.docx"):
    return asyncio.run(get_document_parser("docx").parse(content, name))


async def _parse_docx_async(content: bytes, name: str = "fixture.docx"):
    return await get_document_parser("docx").parse(content, name)


def _model(parsed, page_ranges=None):
    return build_qnu_structured_document(
        parsed.docling_document,
        filename="fixture.docx",
        sha256=SHA,
        projection_markdown=parsed.raw_text,
        page_ranges=page_ranges or [],
        render_sha256=None,
        render_page_count=None,
    )


def _fixture_structure() -> bytes:
    doc = docx.Document()
    doc.add_heading("QUY CHẾ ĐÀO TẠO", level=1)
    doc.add_paragraph("Đoạn mở đầu trước danh sách.")
    doc.add_heading("Điều 1. Phạm vi áp dụng", level=2)
    doc.add_paragraph("Đoạn thân giữa hai tiêu đề.")
    doc.add_paragraph("Ngành Kỹ thuật phần mềm", style="List Bullet")
    doc.add_paragraph("Ngành Trí tuệ nhân tạo", style="List Bullet")
    doc.add_paragraph("Đoạn kết sau danh sách.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _fixture_tables() -> bytes:
    doc = docx.Document()
    doc.add_heading("Bảng chỉ tiêu tuyển sinh", level=1)
    table = doc.add_table(rows=6, cols=4)
    headers = ["TT", "Mã ngành", "Tên ngành", "Chỉ tiêu"]
    for index, value in enumerate(headers):
        table.rows[0].cells[index].text = value
    rows = [
        ["1", "7480107", "Trí tuệ nhân tạo", "55"],
        ["2", "0102030405", "Kỹ thuật phần mềm", "0"],
        ["3", "7480106", "", "12"],
    ]
    for row_index, values in enumerate(rows, start=1):
        for col_index, value in enumerate(values):
            table.rows[row_index].cells[col_index].text = value
    merged = table.rows[4].cells[1].merge(table.rows[4].cells[2])
    table.rows[4].cells[0].text = "4"
    merged.text = "Kỹ thuật số (nhóm ngành)"
    table.rows[4].cells[3].text = "20"
    note = table.rows[5].cells[0].merge(table.rows[5].cells[3])
    note.text = "Ghi chú: số liệu có thể điều chỉnh sau khi có kết quả."
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _fixture_specials() -> bytes:
    doc = docx.Document()
    doc.add_heading("Ký tự đặc biệt và placeholder", level=1)
    doc.add_paragraph("Giá trị có ký tự * _ | # ` và dấu ngoặc [ ].")
    doc.add_paragraph("<!-- rag:block -->")
    doc.add_paragraph("Mẫu {{ ten_nganh }} không được phép lọt vào tệp.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestQnuDocxBuilder(unittest.TestCase):
    def test_structure_headings_paragraphs_and_lists(self) -> None:
        parsed = _parse_docx(_fixture_structure())
        model = _model(parsed)

        types = [block.type for block in model.blocks]
        self.assertIn("section", types)
        self.assertIn("text", types)
        self.assertIn("list", types)
        sections = [block for block in model.blocks if block.type == "section"]
        # DOCX "Heading 1" is mapped by Docling to markdown depth 2 and the standard mirrors it.
        self.assertEqual(sections[0].body, "## QUY CHẾ ĐÀO TẠO")
        self.assertEqual(sections[1].body, "### Điều 1. Phạm vi áp dụng")
        self.assertEqual(sections[1].parent_id, sections[0].id)
        list_block = next(block for block in model.blocks if block.type == "list")
        self.assertIn("Kỹ thuật phần mềm", list_block.body)
        self.assertIn("Trí tuệ nhân tạo", list_block.body)
        for block in model.blocks:
            self.assertTrue(block.id)
        text_blocks = [block for block in model.blocks if block.type == "text"]
        self.assertEqual(
            {block.parent_id for block in text_blocks},
            {sections[0].id, sections[1].id},
        )
        self.assertEqual(text_blocks[0].parent_id, sections[0].id)
        self.assertEqual(text_blocks[-1].parent_id, sections[1].id)

        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        report = validate_qnu_markdown(rendered)
        self.assertTrue(report.ok, [error.detail for error in report.errors])
        self.assertIn("# QUY CHẾ ĐÀO TẠO", rendered)

    def test_table_cells_states_zero_and_leading_zero(self) -> None:
        parsed = _parse_docx(_fixture_tables())
        model = _model(parsed)

        table = next(block for block in model.blocks if block.type == "table")
        self.assertEqual(table.attributes.get("representation"), "records")
        rows = [block for block in model.blocks if block.type == "table_row"]
        self.assertGreaterEqual(len(rows), 3)
        raws = [
            field["raw"]
            for block in rows
            for field in (block.attributes.get("fields") or {}).values()
        ]
        self.assertIn("0102030405", raws)
        zero_fields = [
            field
            for block in rows
            for field in (block.attributes.get("fields") or {}).values()
            if field.get("raw") == "0"
        ]
        self.assertTrue(zero_fields)
        self.assertEqual(zero_fields[0]["state"], "present")
        blank_fields = [
            field
            for block in rows
            for field in (block.attributes.get("fields") or {}).values()
            if field["state"] == "blank"
        ]
        self.assertTrue(blank_fields)
        spanning = next(block for block in rows if "Ghi chú" in block.body)
        self.assertEqual(spanning.attributes["row_role"], "spanning_row_unclassified")
        self.assertTrue(any(flag.code == "spanning_row_needs_review" for flag in spanning.quality_flags))
        self.assertEqual(len(spanning.attributes["fields"]), 4)
        self.assertTrue(all(block.parent_id == table.id for block in rows))

        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        report = validate_qnu_markdown(rendered)
        self.assertTrue(report.ok, [error.detail for error in report.errors])
        self.assertIn("0102030405", rendered)
        self.assertIn("0", rendered)

    def test_merged_cells_keep_field_origins(self) -> None:
        parsed = _parse_docx(_fixture_tables())
        model = _model(parsed)

        rows = [block for block in model.blocks if block.type == "table_row"]
        origins = [
            origin
            for block in rows
            for origin in (block.attributes.get("field_origins") or {}).values()
        ]
        self.assertTrue(origins)
        self.assertTrue(all(origin["basis"] == "merged_cell" for origin in origins))
        for origin in origins:
            self.assertIn("block_id", origin)
            self.assertIn("column_id", origin)

    def test_special_characters_markers_and_template_placeholders(self) -> None:
        parsed = _parse_docx(_fixture_specials())
        model = _model(parsed)

        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        report = validate_qnu_markdown(rendered)
        self.assertTrue(report.ok, [error.detail for error in report.errors])
        self.assertNotIn("{{", rendered)
        self.assertIn("&#123;&#123;", rendered)
        self.assertIn("template_placeholder", rendered)
        self.assertIn("&lt;!-- rag:block", rendered)
        parsed_md = parse_qnu_markdown(rendered)
        self.assertEqual(len(parsed_md.blocks), len(model.blocks))
        self.assertIn("{{ ten_nganh }}", model.model_dump_json())
        marker_blocks = [block for block in model.blocks if "rag:block" in block.body]
        self.assertTrue(marker_blocks)

    def test_page_mapping_unavailable_is_honest(self) -> None:
        parsed = _parse_docx(_fixture_structure())
        model = _model(parsed, page_ranges=[])
        self.assertTrue(all(location.page is None for block in model.blocks for location in block.source_locations))
        mapping = model.document_meta["page_mapping"]
        self.assertEqual(mapping["status"], "unavailable")
        self.assertIsNone(mapping["kind"])
        self.assertIsNone(mapping["render_sha256"])

    def test_align_office_markdown_returns_page_ranges(self) -> None:
        pages = [
            {"page_number": 1, "extracted_text": "Heading First paragraph"},
            {"page_number": 2, "extracted_text": "Second paragraph"},
        ]
        ranges = align_office_markdown("# Heading\nFirst paragraph\n\nSecond paragraph", pages)
        self.assertEqual([page for page, _, _ in ranges], [1, 2])
        self.assertTrue(all(0 <= start < end for _, start, end in ranges))


class TestQnuDocxArtifacts(unittest.IsolatedAsyncioTestCase):
    async def test_artifact_saved_content_addressed_and_validated(self) -> None:
        parsed = await _parse_docx_async(_fixture_structure())
        extraction = SourceExtraction("", 0)
        extraction.qnu_document = _model(parsed)
        saved: dict[str, bytes] = {}

        async def fake_exists(path: str) -> bool:
            return path in saved

        async def fake_save(path: str, content: bytes) -> None:
            saved[path] = content

        with (
            patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.exists", fake_exists),
            patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", fake_save),
        ):
            artifact = await build_qnu_markdown_artifact(
                extraction=extraction,
                document_id=DOC_ID,
                revision_id=REV_ID,
                title="Quy chế đào tạo",
                snapshot_path="snapshots/col/bnd/hash_fixture.docx",
            )

        self.assertEqual(artifact["status"], "ready")
        self.assertEqual(artifact["renderer_version"], QNU_MARKDOWN_RENDERER_VERSION)
        self.assertTrue(artifact["sha256"] in artifact["path"])
        self.assertTrue(artifact["structured_sha256"] in artifact["structured_path"])
        markdown_bytes = saved[artifact["path"]]
        report = validate_qnu_markdown(markdown_bytes.decode("utf-8"))
        self.assertTrue(report.ok, [error.detail for error in report.errors])
        self.assertIn("Quy chế đào tạo", markdown_bytes.decode("utf-8"))
        self.assertIn(REV_ID, markdown_bytes.decode("utf-8"))
        structured = json.loads(saved[artifact["structured_path"]].decode("utf-8"))
        self.assertEqual(structured["schema_version"], "qnu-rag-markdown/1.0")

    async def test_artifact_failure_is_recorded_not_silently_partial(self) -> None:
        parsed = await _parse_docx_async(_fixture_structure())
        extraction = SourceExtraction("", 0)
        extraction.qnu_document = _model(parsed)
        broken = QnuValidationReport(
            ok=False, errors=[QnuIssue(code="block_id_duplicate", detail="Trùng ID.", block_id="s001")]
        )
        with (
            patch("app.modules.knowledge.services.qnu_docx_artifacts.validate_qnu_markdown", return_value=broken),
            patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", new_callable=AsyncMock) as save_mock,
        ):
            artifact = await build_qnu_markdown_artifact(
                extraction=extraction,
                document_id=DOC_ID,
                revision_id=REV_ID,
                title=None,
                snapshot_path="snapshots/col/bnd/hash_fixture.docx",
            )

        self.assertEqual(artifact["status"], "failed")
        self.assertEqual(artifact["reason"], "validation_failed")
        self.assertFalse(artifact["validation"]["ok"])
        self.assertNotIn("path", artifact)
        save_mock.assert_not_called()

    async def test_extract_source_docx_populates_qnu_document_and_page_hints(self) -> None:
        content = _fixture_tables()
        parsed = await _parse_docx_async(content)
        preview_pages = [
            {
                "page_number": 1,
                "extracted_text": parsed.raw_text,
                "alignment_text": parsed.raw_text,
                "engine_used": "native",
                "blocks": [],
            }
        ]
        fake_preview = SourceExtraction(parsed.raw_text, 1, preview_pages, engine_used="native")
        with (
            patch(
                "app.modules.knowledge.services.ingestion_service.IngestionService._convert_office_to_pdf",
                AsyncMock(return_value=b"%PDF-preview"),
            ),
            patch(
                "app.modules.knowledge.services.source_extraction.extract_pdf",
                AsyncMock(return_value=fake_preview),
            ),
        ):
            extraction = await extract_source(
                AsyncMock(), content, "fixture.docx", "docx", "standard", None, "tenant_qnu"
            )

        self.assertIsNotNone(extraction.qnu_document)
        self.assertIn("<!-- Trang 1 -->", extraction.raw_text)
        pages = {
            location.page
            for block in extraction.qnu_document.blocks
            for location in block.source_locations
            if location.page is not None
        }
        self.assertEqual(pages, {1})
        mapping = extraction.qnu_document.document_meta["page_mapping"]
        self.assertEqual(mapping["status"], "aligned")
        self.assertEqual(mapping["render_page_count"], 1)

    async def test_fallback_without_docling_document_is_unavailable(self) -> None:
        extraction = SourceExtraction("plain text", 1)
        extraction.qnu_document = None
        extraction.engine_used = "native_fallback"
        artifact = await build_qnu_markdown_artifact(
            extraction=extraction,
            document_id=DOC_ID,
            revision_id=REV_ID,
            title=None,
            snapshot_path="snapshots/col/bnd/hash_fixture.docx",
        )
        self.assertEqual(artifact["status"], "unavailable")
        self.assertEqual(artifact["reason"], "docling_document_unavailable")
        self.assertEqual(artifact["engine_used"], "native_fallback")


def _fixture_sibling_headings() -> bytes:
    doc = docx.Document()
    doc.add_heading("PHAN A. QUY DINH CHUNG", level=1)
    doc.add_paragraph("Mo dau phan A.")
    doc.add_heading("A1. Dieu 1 pham vi", level=2)
    doc.add_paragraph("Than dieu 1.")
    doc.add_heading("A2. Dieu 2 doi tuong", level=2)
    doc.add_paragraph("Than dieu 2.")
    doc.add_heading("A2a. Khoan 1 dieu 2", level=3)
    doc.add_paragraph("Than khoan 1.")
    doc.add_heading("PHAN B. HINH THUC XU LY", level=1)
    doc.add_heading("B7. Phu luc kem theo", level=4)
    doc.add_paragraph("Noi dung phu luc.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _fixture_multi_page_table() -> bytes:
    doc = docx.Document()
    doc.add_heading("Bang chi tieu nhieu trang", level=1)
    table = doc.add_table(rows=11, cols=3)
    for index, value in enumerate(["Ma", "Ten nganh", "Chi tieu"]):
        table.rows[0].cells[index].text = value
    for row_index in range(1, 10):
        values = [f"MT{row_index:02d}", f"Nganh so {row_index}", f"{row_index * 5}"]
        for col_index, value in enumerate(values):
            table.rows[row_index].cells[col_index].text = value
    merged = table.rows[10].cells[0].merge(table.rows[10].cells[1])
    merged.text = "MT10 nhom nganh"
    table.rows[10].cells[2].text = "40"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _split_projection(markdown: str, cut_line: int) -> tuple[list[tuple[int, int, int]], dict[int, str]]:
    """Split the projection at a line boundary and hand the halves to the render-page aligner."""
    lines = markdown.splitlines()
    first, second = "\n".join(lines[:cut_line]), "\n".join(lines[cut_line:])
    pages = [
        {"page_number": 1, "extracted_text": first, "alignment_text": first},
        {"page_number": 2, "extracted_text": second, "alignment_text": second},
    ]
    return align_office_markdown(markdown, pages), {1: first, 2: second}


def _split_projection_at(markdown: str, cut: int) -> tuple[list[tuple[int, int, int]], dict[int, str]]:
    """Split the projection inside a line so one unit really occupies two render pages."""
    first, second = markdown[:cut], markdown[cut:]
    pages = [
        {"page_number": 1, "extracted_text": first, "alignment_text": first},
        {"page_number": 2, "extracted_text": second, "alignment_text": second},
    ]
    return align_office_markdown(markdown, pages), {1: first, 2: second}


def _pages_by_locator(block) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for location in block.source_locations:
        grouped.setdefault(location.locator, []).append(location.page)
    return {locator: sorted(pages, key=lambda page: (page is None, page)) for locator, pages in grouped.items()}



class TestQnuUnitPageMapping(unittest.TestCase):
    """The whole match decides the pages: start alone would pin a wrapped unit to page one."""

    MARKDOWN = "Alpha beta gamma delta\nSecond line here."
    RANGES = [(1, 0, 11), (2, 11, 40)]

    def test_unit_wrapping_the_boundary_keeps_every_page_it_covers(self) -> None:
        pages, cursor, state = map_unit_to_page("Alpha beta gamma delta", self.RANGES, 0, self.MARKDOWN)
        self.assertEqual(pages, [1, 2])
        self.assertEqual(state, "spanning")
        self.assertEqual(cursor, 22)

    def test_units_confined_to_one_page_keep_their_own_page(self) -> None:
        first, _, state_first = map_unit_to_page("Alpha beta", self.RANGES, 0, self.MARKDOWN)
        self.assertEqual((first, state_first), ([1], "matched"))
        second, cursor, state_second = map_unit_to_page("Second line here", self.RANGES, 22, self.MARKDOWN)
        self.assertEqual((second, state_second, cursor), ([2], "matched", 39))

    def test_gap_inside_the_span_stays_unknown(self) -> None:
        gapped = [(1, 0, 11), (2, 15, 40)]
        pages, cursor, state = map_unit_to_page("Alpha beta gamma delta", gapped, 0, self.MARKDOWN)
        self.assertEqual((pages, state), ([], "ambiguous"))
        self.assertEqual(cursor, 0)

    def test_span_reaching_past_the_pinned_region_stays_unknown(self) -> None:
        for partial in ([(1, 0, 5), (2, 25, 40)], [(1, 5, 40)]):
            with self.subTest(partial=partial):
                pages, _, state = map_unit_to_page("Alpha beta gamma delta", partial, 0, self.MARKDOWN)
                self.assertEqual((pages, state), ([], "ambiguous"))

    def test_repeats_on_different_pages_remain_ambiguous(self) -> None:
        markdown = "Alpha beta gamma delta\nSecond line here.\nAlpha beta gamma delta\nend."
        ranges = [(1, 0, 41), (2, 41, len(markdown))]
        pages, _, state = map_unit_to_page("Alpha beta gamma delta", ranges, 0, markdown)
        self.assertEqual((pages, state), ([], "ambiguous"))

    def test_match_behind_the_cursor_is_never_reused_as_a_page(self) -> None:
        pages, cursor, state = map_unit_to_page("Alpha beta gamma delta", self.RANGES, 25, self.MARKDOWN)
        self.assertEqual((pages, cursor, state), ([], 25, "out_of_order"))

    def test_without_projection_or_text_the_unit_is_unavailable(self) -> None:
        self.assertEqual(map_unit_to_page("Alpha beta", [], 0, self.MARKDOWN), ([], 0, "unavailable"))
        self.assertEqual(map_unit_to_page("", self.RANGES, 0, self.MARKDOWN), ([], 0, "unavailable"))
        self.assertEqual(
            map_unit_to_page("Zeta eta theta", self.RANGES, 0, self.MARKDOWN), ([], 0, "absent")
        )


class TestQnuHeadingHierarchy(unittest.TestCase):
    def _by_title(self, model):
        return {
            re.sub(r"^#+\s+", "", block.body): block for block in model.blocks if block.type == "section"
        }

    def test_same_level_headings_are_siblings_not_parent_child(self) -> None:
        model = _model(_parse_docx(_fixture_sibling_headings()))
        titles = self._by_title(model)
        a = titles["PHAN A. QUY DINH CHUNG"]
        a1 = titles["A1. Dieu 1 pham vi"]
        a2 = titles["A2. Dieu 2 doi tuong"]
        a2a = titles["A2a. Khoan 1 dieu 2"]
        b = titles["PHAN B. HINH THUC XU LY"]
        b7 = titles["B7. Phu luc kem theo"]

        self.assertIsNone(a.parent_id)
        self.assertEqual(a1.parent_id, a.id)
        self.assertEqual(a2.parent_id, a.id)
        self.assertEqual(a2a.parent_id, a2.id)
        self.assertIsNone(b.parent_id)
        self.assertEqual(b7.parent_id, b.id)

        depths = {title: re.match(r"^(#+)\s", block.body).group(1) for title, block in titles.items()}
        self.assertEqual(depths["PHAN A. QUY DINH CHUNG"], "##")
        self.assertEqual(depths["A2. Dieu 2 doi tuong"], "###")
        self.assertEqual(depths["A2a. Khoan 1 dieu 2"], "####")

        self.assertEqual(a2a.section_path, ["PHAN A. QUY DINH CHUNG", "A2. Dieu 2 doi tuong", "A2a. Khoan 1 dieu 2"])
        self.assertEqual(b.section_path, ["PHAN B. HINH THUC XU LY"])
        self.assertEqual(b7.section_path, ["PHAN B. HINH THUC XU LY", "B7. Phu luc kem theo"])

    def test_bodies_after_headings_follow_the_open_section(self) -> None:
        model = _model(_parse_docx(_fixture_sibling_headings()))
        titles = self._by_title(model)
        parents = {block.body: block.parent_id for block in model.blocks if block.type == "text"}
        self.assertEqual(parents["Mo dau phan A."], titles["PHAN A. QUY DINH CHUNG"].id)
        self.assertEqual(parents["Than dieu 2."], titles["A2. Dieu 2 doi tuong"].id)
        self.assertEqual(parents["Than khoan 1."], titles["A2a. Khoan 1 dieu 2"].id)
        self.assertEqual(parents["Noi dung phu luc."], titles["B7. Phu luc kem theo"].id)
        self.assertEqual(
            next(block.section_path for block in model.blocks if block.body == "Than khoan 1."),
            ["PHAN A. QUY DINH CHUNG", "A2. Dieu 2 doi tuong", "A2a. Khoan 1 dieu 2"],
        )

        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        report = validate_qnu_markdown(rendered)
        self.assertTrue(report.ok, [error.detail for error in report.errors])


class TestQnuMultiPageUnits(unittest.TestCase):
    def test_table_rows_take_the_page_of_their_own_render_position(self) -> None:
        parsed = _parse_docx(_fixture_multi_page_table())
        cut = next(
            index
            for index, line in enumerate(parsed.raw_text.splitlines())
            if line.lstrip().startswith("| MT06")
        )
        ranges, page_texts = _split_projection(parsed.raw_text, cut)
        model = _model(parsed, page_ranges=ranges)

        rows = [block for block in model.blocks if block.type == "table_row"]
        self.assertEqual(len(rows), 10)
        pages = [block.source_locations[0].page for block in rows]
        self.assertIn(1, pages)
        self.assertIn(2, pages)
        self.assertNotEqual(pages, [1] * len(pages))
        self.assertEqual(pages, sorted(pages, key=lambda page: (page is None, page)))

        for block, page in zip(rows, pages, strict=True):
            code = next(
                field["raw"]
                for field in block.attributes["fields"].values()
                if str(field["raw"]).startswith("MT")
            )
            self.assertIsNotNone(page, f"{code} phai dinh vi duoc trong ban render")
            self.assertIn(code, page_texts[page])
            self.assertNotIn(code, page_texts[2 if page == 1 else 1])

        mapping = model.document_meta["page_mapping"]
        self.assertEqual(mapping["status"], "aligned")
        self.assertEqual(mapping["kind"], "pdf_preview_render")

    def test_list_items_map_to_their_own_page(self) -> None:
        parsed = _parse_docx(_fixture_structure())
        cut = next(
            index
            for index, line in enumerate(parsed.raw_text.splitlines())
            if "Trí tuệ nhân tạo" in line
        )
        ranges, page_texts = _split_projection(parsed.raw_text, cut)
        model = _model(parsed, page_ranges=ranges)
        list_block = next(block for block in model.blocks if block.type == "list")
        self.assertEqual([location.page for location in list_block.source_locations], [1, 2])
        self.assertIn("Kỹ thuật phần mềm", page_texts[1])
        self.assertNotIn("Kỹ thuật phần mềm", page_texts[2])
        self.assertIn("Trí tuệ nhân tạo", page_texts[2])
        self.assertEqual(model.document_meta["page_mapping"]["status"], "aligned")

    def test_list_item_wrapping_a_boundary_keeps_both_pages(self) -> None:
        parsed = _parse_docx(_fixture_structure())
        ranges, _ = _split_projection_at(parsed.raw_text, parsed.raw_text.index("mềm"))
        model = _model(parsed, page_ranges=ranges)
        list_block = next(block for block in model.blocks if block.type == "list")

        by_locator = _pages_by_locator(list_block)
        wrapped = [pages for pages in by_locator.values() if len(pages) > 1]
        self.assertEqual(wrapped, [[1, 2]])
        self.assertEqual(sum(1 for pages in by_locator.values() if pages == [2]), 1)
        self.assertEqual(model.stats["unit_states"]["spanning"], 1)
        self.assertEqual(model.stats["unmapped_units"], 0)
        mapping = model.document_meta["page_mapping"]
        self.assertEqual(mapping["status"], "aligned")
        self.assertEqual(mapping["kind"], "pdf_preview_render")
        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        report = validate_qnu_markdown(rendered)
        self.assertTrue(report.ok, [error.detail for error in report.errors])

    def test_table_row_wrapping_a_boundary_keeps_both_pages(self) -> None:
        parsed = _parse_docx(_fixture_multi_page_table())
        offset = parsed.raw_text.index("Nganh so 5")
        ranges, page_texts = _split_projection_at(parsed.raw_text, offset)
        model = _model(parsed, page_ranges=ranges)
        rows = [block for block in model.blocks if block.type == "table_row"]

        def row_by_code(code: str):
            return next(
                block
                for block in rows
                if any(str(field["raw"]).startswith(code) for field in block.attributes["fields"].values())
            )

        wrapped = row_by_code("MT05")
        self.assertEqual([location.page for location in wrapped.source_locations], [1, 2])
        self.assertEqual(len({location.locator for location in wrapped.source_locations}), 1)
        self.assertIn("MT05", page_texts[1])
        self.assertEqual([location.page for location in row_by_code("MT01").source_locations], [1])
        self.assertEqual([location.page for location in row_by_code("MT10").source_locations], [2])
        self.assertEqual(model.stats["unit_states"]["spanning"], 1)
        self.assertEqual(model.document_meta["page_mapping"]["status"], "aligned")
        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        self.assertTrue(validate_qnu_markdown(rendered).ok)

    def test_unproven_units_stay_unknown_with_a_flag_not_a_guessed_page(self) -> None:
        parsed = _parse_docx(_fixture_multi_page_table())
        partial = [(1, 0, max(1, len(parsed.raw_text) // 4))]
        model = _model(parsed, page_ranges=partial)
        rows = [block for block in model.blocks if block.type == "table_row"]
        pages = {block.source_locations[0].page for block in rows}
        self.assertIsNone(next((page for page in pages if page is None), "missing"))
        self.assertEqual(model.document_meta["page_mapping"]["status"], "partial")
        table = next(block for block in model.blocks if block.type == "table")
        flag = next(flag for flag in table.quality_flags if flag.code == "page_unresolved")
        self.assertTrue(flag.related_block_ids)
        self.assertTrue(all(location.locator for block in rows for location in block.source_locations))
        rendered = render_qnu_markdown(model, document_id=DOC_ID, revision_id=REV_ID)
        self.assertIn("page_unresolved", rendered)


class TestQnuTableRelationValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        parsed = _parse_docx(_fixture_tables())
        cls.markdown = render_qnu_markdown(
            _model(parsed), document_id=DOC_ID, revision_id=REV_ID
        )

    def _row_fence(self, row_id: str = "r001") -> str:
        fences = re.findall(r"<!-- rag:block\nid: \"r\d+\".*?<!-- /rag:block -->", self.markdown, re.DOTALL)
        return next(fence for fence in fences if fence.startswith(f'<!-- rag:block\nid: "{row_id}"'))

    def _tampered(self, row_id: str, attributes_yaml: str) -> str:
        fence = self._row_fence(row_id)
        head = fence.split("attributes:")[0]
        replacement = head + "attributes:" + attributes_yaml + "\nquality_flags: []\n-->\n**TT:** 1\n<!-- /rag:block -->"
        return self.markdown.replace(fence, replacement, 1)

    def test_valid_merged_table_still_passes(self) -> None:
        report = validate_qnu_markdown(self.markdown)
        self.assertTrue(report.ok, [error.detail for error in report.errors])
        self.assertIn("field_origins", self.markdown)

    def test_field_outside_parent_columns_is_rejected(self) -> None:
        text = self._tampered(
            "r001",
            '\n  fields:\n    c01:\n      raw: "1"\n      state: "present"\n      normalized: null\n'
            '    c99:\n      raw: "x"\n      state: "present"\n      normalized: null',
        )
        report = validate_qnu_markdown(text)
        self.assertFalse(report.ok)
        self.assertIn("table_field_unknown_column", {error.code for error in report.errors})

    def test_broken_origins_are_rejected(self) -> None:
        cases = {
            "block_id khong ton tai": '      basis: "merged_cell"\n      block_id: "zz9"\n      column_id: "c02"',
            "column_id ngoai bang": '      basis: "merged_cell"\n      block_id: "t001"\n      column_id: "c77"',
            "ngoai pham vi bang": '      basis: "merged_cell"\n      block_id: "s001"\n      column_id: "c01"',
            "basis khong ho tro": '      basis: "guess"\n      block_id: "t001"\n      column_id: "c01"',
        }
        for label, origin_body in cases.items():
            with self.subTest(label):
                text = self._tampered(
                    "r001",
                    "\n  field_origins:\n    c01:\n" + origin_body
                    + '\n  fields:\n    c01: {raw: "1", state: present, normalized: null}',
                )
                report = validate_qnu_markdown(text)
                self.assertFalse(report.ok)
                codes = {error.code for error in report.errors}
                self.assertIn("table_field_origin_invalid", codes)

    def test_origin_without_matching_field_is_rejected(self) -> None:
        text = self._tampered(
            "r001",
            '\n  field_origins:\n    c88:\n      basis: "merged_cell"\n      block_id: "t001"\n      column_id: "c01"\n'
            '  fields:\n    c01: {raw: "1", state: present, normalized: null}',
        )
        report = validate_qnu_markdown(text)
        self.assertFalse(report.ok)
        self.assertIn("table_field_origin_invalid", {error.code for error in report.errors})

    def test_row_without_table_parent_is_rejected(self) -> None:
        fence = self._row_fence("r001")
        text = self.markdown.replace(fence, fence.replace('parent_id: "t001"', 'parent_id: "s001"', 1), 1)
        report = validate_qnu_markdown(text)
        self.assertFalse(report.ok)
        self.assertIn("table_row_parent_invalid", {error.code for error in report.errors})

    def test_wrongly_typed_metadata_yields_structured_errors(self) -> None:
        payloads = {
            "fields la chuoi": '\n  fields: "khong phai mapping"',
            "field_origins la danh sach": '\n  fields:\n    c01: {raw: "1", state: present, normalized: null}\n  field_origins: []',
            "origin la chuoi": '\n  fields:\n    c01: {raw: "1", state: present, normalized: null}\n  field_origins:\n    c01: "t001/c01"',
            "table thieu columns": None,
        }
        for label, yaml_body in payloads.items():
            with self.subTest(label):
                if yaml_body is None:
                    text = self.markdown.replace('    - id: "c01"\n      header_path:\n        - "TT"', '    - idx: "c01"', 1)
                else:
                    text = self._tampered("r001", yaml_body)
                report = validate_qnu_markdown(text)
                self.assertFalse(report.ok)
                self.assertTrue(report.errors)

    def test_unhashable_or_non_iterable_metadata_is_a_finding_not_a_crash(self) -> None:
        cases = {
            "type la danh sach": ('type: "table_row"', "type: []", "block_type_invalid"),
            "state la danh sach": ('state: "present"', "state: []", "table_field_state_invalid"),
            "basis la danh sach": ('basis: "merged_cell"', "basis: []", "table_field_origin_invalid"),
            "context_refs la so": ("context_refs: []", "context_refs: 42", "block_attribute_invalid"),
            "section_path la so": (
                'section_path:\n  - "Bảng chỉ tiêu tuyển sinh"\ncontext_refs: []',
                "section_path: 42\ncontext_refs: []",
                "block_attribute_invalid",
            ),
            "review_status la danh sach": (
                'review_status: "unreviewed"',
                "review_status: []",
                "review_status_invalid",
            ),
        }
        for label, (marker, replacement, code) in cases.items():
            with self.subTest(label):
                self.assertIn(marker, self.markdown)
                report = validate_qnu_markdown(self.markdown.replace(marker, replacement, 1))
                self.assertFalse(report.ok)
                self.assertIn(code, {error.code for error in report.errors})

    def test_unhashable_metadata_key_is_a_parse_finding_not_a_type_error(self) -> None:
        fence = self._row_fence("r001")
        head, _, tail = fence.partition("-->\n")
        text = self.markdown.replace(fence, head + "? {a: 1}\n: key\n-->\n" + tail, 1)
        report = validate_qnu_markdown(text)
        self.assertFalse(report.ok)
        self.assertIn("block_metadata_yaml_error", {error.code for error in report.errors})

    def test_zero_blank_and_leading_zero_values_remain_valid(self) -> None:
        rows = [block for block in parse_qnu_markdown(self.markdown).blocks if block.metadata.get("type") == "table_row"]
        raws = {field["raw"] for block in rows for field in block.metadata["attributes"]["fields"].values()}
        self.assertIn("0102030405", raws)
        self.assertIn("0", raws)
        states = {field["state"] for block in rows for field in block.metadata["attributes"]["fields"].values()}
        self.assertIn("blank", states)
        self.assertTrue(validate_qnu_markdown(self.markdown).ok)


def _result(value):
    response = MagicMock()
    response.scalar_one_or_none.return_value = value
    response.scalars.return_value.first.return_value = value
    return response


class TestQnuArtifactRevisionIdentity(unittest.IsolatedAsyncioTestCase):
    """A standard file belongs to exactly one revision; inherited metadata must not revive it."""

    SNAPSHOT = "snapshots/col/bnd/hash_fixture.docx"

    @staticmethod
    def _structured_content(document) -> bytes:
        """The same serialization the artifact writer uses, so fixture checksums are real."""
        return (
            json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

    def _ready(self, revision_id: str, content: bytes = b"structured companion fixture\n") -> dict:
        structured_sha = compute_sha256(content)
        return {
            "schema_version": "qnu-rag-markdown/1.0",
            "renderer_version": QNU_MARKDOWN_RENDERER_VERSION,
            "document_id": "bnd_stale",
            "revision_id": revision_id,
            "status": "ready",
            "path": f"{self.SNAPSHOT}.{'a' * 64}.qnu-rag-v1.md",
            "sha256": "b" * 64,
            "structured_path": f"{self.SNAPSHOT}.{structured_sha}.qnu-doc-v1.json",
            "structured_sha256": structured_sha,
        }

    async def _rebuild(self, shared: dict, stored: dict[str, bytes]) -> dict:
        async def fake_get(path: str) -> bytes | None:
            return stored.get(path)

        async def fake_exists(path: str) -> bool:
            return path in stored

        async def fake_save(path: str, content: bytes) -> None:
            stored[path] = content

        with (
            patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.get", fake_get),
            patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.exists", fake_exists),
            patch("app.modules.knowledge.services.qnu_docx_artifacts.storage_service.save", fake_save),
        ):
            return await rebuild_qnu_markdown_for_revision(
                shared, document_id="bnd_stale", revision_id="ks_rev_new", snapshot_path=self.SNAPSHOT
            )

    def _revision(self, **metadata) -> KnowledgeSourceRevision:
        raw = "<!-- Trang 1 -->\nNoi dung goc can hieu dinh."
        return KnowledgeSourceRevision(
            id="ks_rev_old",
            binding_id="bnd_stale",
            revision_no=1,
            origin_document_id="doc_01",
            origin_file_hash="hash_01",
            canonical_markdown=raw,
            canonical_hash=compute_sha256(raw),
            status="ready",
            page_manifest=[{"page": 1, "extracted_markdown": "Noi dung goc can hieu dinh."}],
            **metadata,
        )

    async def _edit(self, rev: KnowledgeSourceRevision) -> KnowledgeSourceRevision:
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [_result(rev), _result(1)]
        with (
            patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=KnowledgeBinding(
                id="bnd_stale", collection_id="col", status="active"))),
            patch("app.modules.knowledge.services.source_reparse.lock_source", AsyncMock()),
            patch("app.modules.knowledge.services.source_reparse.ensure_source_idle", AsyncMock()),
        ):
            return await source_ingestion_service.update_revision_content(
                db, "col", "bnd_stale", rev.id,
                "<!-- Trang 1 -->\nNoi dung sau khi can bo hieu dinh.",
                actor_id="editor", change_reason="Doi chieu ban goc",
                expected_canonical_hash=rev.canonical_hash,
            )

    async def test_edited_revision_does_not_inherit_the_previous_standard_file(self) -> None:
        ready = self._ready("ks_rev_old")
        rev = self._revision(snapshot_metadata={"qnu_markdown": ready}, parse_provenance={"structured_artifact": {}})
        edited = await self._edit(rev)

        marker = edited.snapshot_metadata["qnu_markdown"]
        self.assertEqual(marker["status"], "unavailable")
        self.assertEqual(marker["reason"], "superseded_revision_content")
        self.assertEqual(marker["revision_id"], edited.id)
        self.assertEqual(marker["superseded_revision_id"], "ks_rev_old")
        self.assertNotIn("path", marker)
        self.assertNotIn("structured_path", marker)
        self.assertEqual(edited.parse_provenance["qnu_markdown"], marker)
        self.assertNotEqual(marker, ready)

        # History stays intact and unmutated.
        self.assertEqual(rev.snapshot_metadata["qnu_markdown"], ready)
        self.assertEqual(ready["status"], "ready")

    async def test_provenance_only_stale_artifact_is_rejected_not_revived(self) -> None:
        rev = self._revision(
            snapshot_metadata={"title": "Quy che"},
            parse_provenance={"structured_artifact": {}, "qnu_markdown": self._ready("ks_rev_other")},
        )
        db = AsyncMock()
        db.execute.side_effect = [_result(rev)]
        with (
            patch.object(
                source_ingestion_service,
                "get_source",
                AsyncMock(return_value=KnowledgeBinding(id="bnd_stale", collection_id="col", status="active")),
            ),
            self.assertRaises(AppException) as caught,
        ):
            await source_ingestion_service.get_qnu_markdown_artifact(db, "col", "bnd_stale", rev.id)
        self.assertEqual(caught.exception.code, "QNU_MARKDOWN_REVISION_MISMATCH")

    async def test_matching_artifact_still_resolves(self) -> None:
        rev = self._revision(snapshot_metadata={"qnu_markdown": self._ready("ks_rev_old")})
        db = AsyncMock()
        db.execute.side_effect = [_result(rev)]
        with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=KnowledgeBinding(
                id="bnd_stale", collection_id="col", status="active"))):
            artifact = await source_ingestion_service.get_qnu_markdown_artifact(db, "col", "bnd_stale", rev.id)
        self.assertEqual(artifact["status"], "ready")

    async def test_invalidated_marker_is_reported_as_not_ready(self) -> None:
        ready = self._ready("ks_rev_old")
        rev = self._revision(snapshot_metadata={"qnu_markdown": ready}, parse_provenance={"structured_artifact": {}})
        edited = await self._edit(rev)
        db = AsyncMock()
        db.execute.side_effect = [_result(edited)]
        with patch.object(source_ingestion_service, "get_source", AsyncMock(return_value=KnowledgeBinding(
                id="bnd_stale", collection_id="col", status="active"))):
            artifact = await source_ingestion_service.get_qnu_markdown_artifact(db, "col", "bnd_stale", edited.id)
        self.assertEqual(artifact["status"], "unavailable")
        self.assertNotEqual(artifact["revision_id"], rev.id)

    async def test_reused_parse_artifact_is_rendered_under_its_own_identity(self) -> None:
        document = _model(await _parse_docx_async(_fixture_structure()))
        content = self._structured_content(document)
        shared = self._ready("ks_rev_old", content)
        stored: dict[str, bytes] = {
            shared["structured_path"]: content,
            shared["path"]: render_qnu_markdown(document, document_id="bnd_stale", revision_id="ks_rev_old").encode(),
        }

        rebuilt = await self._rebuild(shared, stored)

        self.assertEqual(rebuilt["status"], "ready")
        self.assertEqual(rebuilt["structured_sha256"], shared["structured_sha256"])
        self.assertEqual(rebuilt["revision_id"], "ks_rev_new")
        self.assertEqual(rebuilt["derived_from_revision_id"], "ks_rev_old")
        self.assertNotEqual(rebuilt["path"], shared["path"])
        text = stored[rebuilt["path"]].decode("utf-8")
        self.assertIn('revision_id: "ks_rev_new"', text)
        self.assertNotIn('revision_id: "ks_rev_old"', text)
        self.assertTrue(validate_qnu_markdown(text).ok)
        self.assertEqual(shared["status"], "ready")

    async def test_structured_bytes_that_fail_their_checksum_are_not_reused(self) -> None:
        document = _model(await _parse_docx_async(_fixture_structure()))
        content = self._structured_content(document)
        shared = self._ready("ks_rev_old", content)
        stored: dict[str, bytes] = {
            shared["structured_path"]: content.replace(b"fixture.docx", b"tampered.docx"),
            shared["path"]: b"stale markdown",
        }

        rebuilt = await self._rebuild(shared, stored)

        self.assertEqual(rebuilt["status"], "failed")
        self.assertEqual(rebuilt["reason"], "structured_checksum_mismatch")
        self.assertEqual(rebuilt["expected_sha256"], shared["structured_sha256"])
        self.assertNotEqual(rebuilt["actual_sha256"], rebuilt["expected_sha256"])
        self.assertNotIn("path", rebuilt)
        self.assertNotIn("structured_path", rebuilt)
        self.assertEqual(set(stored), {shared["structured_path"], shared["path"]})

    async def test_reuse_without_a_recorded_checksum_stops_before_storage(self) -> None:
        for missing in ("absent", "null", "blank"):
            with self.subTest(missing):
                shared = self._ready("ks_rev_old")
                if missing == "absent":
                    del shared["structured_sha256"]
                else:
                    shared["structured_sha256"] = None if missing == "null" else "   "
                rebuilt = await self._rebuild(shared, {})
                self.assertEqual(rebuilt["status"], "unavailable")
                self.assertEqual(rebuilt["reason"], "structured_checksum_missing")
                self.assertEqual(rebuilt["revision_id"], "ks_rev_new")
                self.assertNotIn("path", rebuilt)

    async def test_reuse_with_malformed_checksum_is_refused(self) -> None:
        for bad in ("not-a-hash", "d" * 63, "D" * 64, "d" * 64 + " "):
            with self.subTest(bad):
                shared = self._ready("ks_rev_old")
                shared["structured_sha256"] = bad
                rebuilt = await self._rebuild(shared, {})
                self.assertEqual(rebuilt["status"], "unavailable")
                self.assertEqual(rebuilt["reason"], "structured_checksum_invalid")
                self.assertNotIn("path", rebuilt)

    async def test_reuse_without_structured_evidence_is_unavailable(self) -> None:
        rebuilt = await rebuild_qnu_markdown_for_revision(
            None, document_id="bnd_stale", revision_id="ks_rev_new", snapshot_path=self.SNAPSHOT
        )
        self.assertEqual(rebuilt["status"], "unavailable")
        self.assertEqual(rebuilt["reason"], "shared_artifact_not_ready")
        self.assertEqual(rebuilt["revision_id"], "ks_rev_new")


if __name__ == "__main__":
    unittest.main()
