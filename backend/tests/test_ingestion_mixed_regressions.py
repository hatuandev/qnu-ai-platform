"""Mixed-image routing and table context must not lose content or invent facts."""

import pymupdf

from app.modules.knowledge.parsers.base import ParsedContent
from app.modules.knowledge.services.source_artifact import build_source_artifact
from app.modules.knowledge.services.source_extraction import build_native_pages


def test_long_native_caption_does_not_hide_image_text():
    with pymupdf.open() as document, pymupdf.open() as raster:
        page = document.new_page()
        image = raster.new_page()
        image.insert_text((50, 100), "Image-only data 123456")
        page.insert_image(page.rect, stream=image.get_pixmap().tobytes("png"))
        page.insert_text((40, 40), "Caption with enough native characters " * 4, fontsize=5)
        data = document.tobytes()
    _, selected, _ = build_native_pages(data, ParsedContent(raw_text="caption", page_count=1))
    assert selected == [1]


def test_embedded_year_subheader_has_group_label_and_no_missing_columns():
    md = """| TT | Ngành | Mã ngành | Chỉ tiêu 2024 | Tuyển sinh | | |
| --- | --- | --- | --- | --- | --- | --- |
| I. | Trình độ tiến sĩ | | | 2021 | 2022 | 2023 |
| 1 | Ngành A | 9460104 | 5 | 0 | 1 | 2 |
"""
    artifact = build_source_artifact(md, 1, {})
    assert artifact["issues"] == []
    facts = artifact["facts"]
    assert any(f["raw_data"]["temporal_context"]["year"] == 2023 for f in facts)
    assert not any(f["entity_name"] == "Trình độ tiến sĩ" for f in facts)


def test_repeated_identity_labels_in_subheader_are_not_data():
    md = "| TT | Ngành | 2023 | 2023 |\n| --- | --- | --- | --- |\n| TT | Ngành | Số lượng | Điểm |\n| 1 | Ngành A | 5 | 20 |"
    artifact = build_source_artifact(md, 1, {})
    assert artifact["tables"][0]["headers"][-1] == "2023 / Điểm"
    assert not any(f["entity_name"] == "TT" for f in artifact["facts"])


def test_equal_deadline_for_different_tasks_is_not_a_conflict():
    md = """| TT | Thời gian | Công việc | Đơn vị |
| --- | --- | --- | --- |
| 1 | 10/7/2026 | Task A | Unit A |
| 2 | 10/7/2026 | Task B | Unit B |
"""
    assert build_source_artifact(md, 1, {})["issues"] == []


def test_continuation_after_page_number_keeps_original_header():
    md = """<!-- Trang 1 -->
| TT | Mã ngành | Ngành | Điểm |
| --- | --- | --- | --- |
| 15 | 7140248 | Ngành A | 20 |
2
<!-- Trang 2 -->
| 16 | 7140249 | Ngành B | 21 |
| --- | --- | --- | --- |
| 17 | 7220201 | Ngành C | 22 |
"""
    artifact = build_source_artifact(md, 2, {})
    assert artifact["tables"][1]["headers"] == artifact["tables"][0]["headers"]
    assert any(f["entity_name"] == "Ngành B" and f["attribute_value"] == "21" for f in artifact["facts"])


def test_same_page_ocr_fragment_inherits_only_on_sequential_evidence():
    md = "| TT | Mã ngành | Ngành | Điểm |\n| --- | --- | --- | --- |\n| 15 | 7140248 | Ngành A | 20 |\n\n| 16 | 7140249 | Ngành B | 21 |\n| --- | --- | --- | --- |\n| 17 | 7220201 | Ngành C | 22 |"
    artifact = build_source_artifact(md, 1, {})
    assert artifact["issues"] == []
    assert artifact["tables"][1]["headers"] == artifact["tables"][0]["headers"]


def test_mixed_docx_page_preserves_image_text_after_alignment():
    from app.modules.knowledge.services.source_extraction import align_office_markdown

    pages = [{"page_number": 1, "extracted_text": "Office text\nEmbedded image data 123456", "alignment_text": "Office text", "engine_used": "paddleocr_vl"}]
    align_office_markdown("Office text", pages)
    assert "Embedded image data 123456" in pages[0]["extracted_text"]


def test_html_spans_preserve_year_header_paths():
    from app.modules.knowledge.services.html_tables import normalize_html_tables

    md = normalize_html_tables('<table><tr><th rowspan="2">Ngành</th><th colspan="2">2024</th></tr><tr><th>Chỉ tiêu</th><th>Điểm</th></tr><tr><td>Ngành A</td><td>10</td><td>20</td></tr></table>')
    artifact = build_source_artifact(md, 1, {})
    assert any(f["raw_data"]["temporal_context"]["year"] == 2024 and f["attribute_value"] == "20" for f in artifact["facts"])
    td = normalize_html_tables('<table><tr><td rowspan="2">Ngành</td><td colspan="2">2024</td></tr><tr><td>Chỉ tiêu</td><td>Điểm</td></tr><tr><td>Ngành A</td><td>10</td><td>20</td></tr></table>')
    assert build_source_artifact(td, 1, {})["tables"][0]["headers"][-1] == "2024 / Điểm"


def test_visual_content_requires_review_without_inventing_numbers():
    from app.modules.knowledge.services.source_artifact import add_layout_issues

    artifact = build_source_artifact("Chart caption", 1, {})
    add_layout_issues(artifact, [{"page_number": 1, "blocks": [{"id": "chart", "type": "chart", "coordinates": {"width": 50, "height": 30}}]}])
    assert artifact["issues"][0]["code"] == "VISUAL_CONTENT_REVIEW"
    assert not artifact["facts"]


def test_one_column_layout_box_is_not_a_missing_data_table():
    artifact = build_source_artifact("A letter in a layout box", 1, {}, [{"headers": ["Title"], "rows": []}])
    assert artifact["issues"] == []


def test_native_whitespace_prose_is_not_a_missing_table():
    from app.modules.knowledge.services.source_artifact import add_layout_issues
    artifact = build_source_artifact("Native prose", 1, {})
    add_layout_issues(artifact, [{"page_number": 1, "blocks": [{"type": "table", "text": "| A long paragraph | |\n| --- | --- |\n| Continued prose | |"}]}])
    assert artifact["issues"] == []
    add_layout_issues(artifact, [{"page_number": 1, "blocks": [{"type": "table", "text": "| Entity | Value |\n| --- | --- |\n| Some entity | 42 |"}]}])
    assert artifact["issues"][0]["code"] == "TABLES_NOT_MATERIALIZED"


def test_code_name_only_table_keeps_identifier_as_fact():
    md = "| Mã ngành | Tên ngành |\n| --- | --- |\n| 7480201 | Công nghệ thông tin |"
    facts = build_source_artifact(md, 1, {})["facts"]
    assert any(f["entity_name"] == "Công nghệ thông tin" and f["attribute_value"] == "7480201" and f["raw_data"]["attribute_code"] == "entity_code" for f in facts)


def test_native_canonical_continuation_recovers_consumed_first_row():
    from app.modules.knowledge.normalization.models import (
        CanonicalCell,
        CanonicalRow,
        CanonicalTable,
        SourceSpan,
    )
    from app.modules.knowledge.parsers.table_continuation import inherit_table_header

    previous = CanonicalTable(table_id="first", schema_key="schema", headers=["TT", "Mã ngành", "Ngành", "Điểm"],
        rows=[CanonicalRow(row_id="r1", source_pages=[1], cells=[CanonicalCell(raw_value=value, source_span=SourceSpan(page_number=1)) for value in ["5", "7140206", "Ngành A", "19"]])], source_pages=[1], bbox=(50, 100, 550, 800))
    first = ["6", "7140209", "Ngành B", "20"]
    headers, rows = inherit_table_header(first, [], [previous], 2, (50, 20, 550, 800))
    assert headers == previous.headers and rows == [first]
    unrelated, _ = inherit_table_header(["40", "7140209", "Other", "20"], [], [previous], 2, (50, 20, 550, 800))
    assert unrelated[0] == "40"


async def test_inspector_timeout_kills_only_owned_child():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.modules.knowledge.parsers.inspector_process import inspect_pdf_safely

    async def pending(content):
        await asyncio.sleep(10)

    process = SimpleNamespace(returncode=None, communicate=pending, wait=AsyncMock())
    def kill():
        process.returncode = -9
    process.kill = kill
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=process)):
        result = await inspect_pdf_safely(b"pdf", timeout=0.01)
    assert result.inspector_engine == "native-inspector-timeout"
    assert process.returncode == -9
