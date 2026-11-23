"""Native extraction uses source text, preserves tables/images, and never calls a model."""

import io
import zipfile

import pymupdf
import pytest

from qnu.domains.ocr.artifacts.render import render_document
from qnu.domains.ocr.config import processing_config
from qnu.domains.ocr.direct_docx import extract_docx
from qnu.domains.ocr.layout import parse_page
from qnu.domains.ocr.native import extract_native, merge_layout
from qnu.domains.ocr.pdf_inspector import extract_pdf
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException

pytestmark = pytest.mark.usefixtures("offline_document_conversion")


def pdf(text="Source text 2023: 0 -", image=False):
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    if text:
        page.insert_text((40, 50), text)
    if image:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
        pix.clear_with(120)
        page.insert_image(pymupdf.Rect(60, 200, 160, 300), stream=pix.tobytes("png"))
    data = doc.tobytes()
    doc.close()
    return data


def plan(data, extension=".pdf"):
    rendered = render_document(data, extension, processing_config(get_settings()))
    return extract_native(data, rendered)


def test_pdf_text_is_native_and_needs_no_provider():
    page = plan(pdf()).pages[0]
    assert page.layout.text == "Source text 2023: 0 -"
    assert not page.needs_ocr
    assert page.layout.blocks[0].origin == "native"


def test_docx_with_header_reads_source_without_fixed_layout():
    from docx import Document

    source = Document()
    source.sections[0].header.paragraphs[0].text = "Section header"
    source.sections[0].footer.paragraphs[0].text = "Section footer"
    source.add_paragraph("Body text")
    table = source.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Merged cell"
    table.cell(1, 0).text = "Left"
    table.cell(1, 1).text = "Right"
    payload = io.BytesIO()
    source.save(payload)
    rendered, result = extract_docx(payload.getvalue())
    assert rendered.fixed_layout_pdf is None and rendered.pages[0].png is None
    blocks = result.pages[0].layout.blocks
    assert {"Body text", "Section header", "Section footer"} <= {b.text for b in blocks}
    assert {b.kind for b in blocks} >= {"text", "header", "footer", "table"}
    assert all(b.bbox is None and b.source_locator for b in blocks)
    [parsed_table] = [b.table for b in blocks if b.table]
    assert parsed_table.rows[0][0].text == "Merged cell"
    assert parsed_table.rows[0][0].col_span == 2


def test_blank_pdf_is_not_sent_to_ocr():
    page = plan(pdf(text="")).pages[0]
    assert not page.needs_ocr
    assert not page.layout.blocks


def test_docx_preserves_native_outline_levels():
    from docx import Document

    source = Document()
    source.add_heading("Chương mở đầu", 1)
    source.add_heading("Điều kiện", 3)
    source.add_paragraph("Nội dung yêu cầu.")
    payload = io.BytesIO()
    source.save(payload)

    _, plan = extract_docx(payload.getvalue())
    blocks = plan.pages[0].layout.blocks
    assert [(block.text, block.source_locator.get("level")) for block in blocks] == [
        ("Chương mở đầu", 1),
        ("Điều kiện", 3),
        ("Nội dung yêu cầu.", None),
    ]


def test_image_is_preserved_and_marks_only_that_page_for_ocr():
    page = plan(pdf(image=True)).pages[0]
    assert page.needs_ocr
    assert "Source text" in page.layout.text
    assert len(page.images) == 1
    assert page.images[0].payload.startswith(b"\x89PNG")
    assert any(b.image for b in page.layout.blocks)


def test_hybrid_merge_keeps_source_text_and_ignores_ocr_duplicate():
    page = plan(pdf(image=True)).pages[0]
    ocr = parse_page(
        "<x_0.05><y_0.02>WRONG SOURCE<x_0.7><y_0.08><class_Text>"
        "<x_0.11><y_0.25>Image text<x_0.25><y_0.32><class_Text>"
    )
    merged = merge_layout(page, ocr)
    assert "Source text 2023: 0 -" in merged.text
    assert "Image text" in merged.text
    assert "WRONG SOURCE" not in merged.text
    assert len({b.order for b in merged.blocks}) == len(merged.blocks)


def test_scan_is_not_mistaken_for_native_text():
    page = plan(pdf(text="", image=True)).pages[0]
    assert page.needs_ocr
    assert not page.native_text


def test_docx_reads_unicode_and_literal_numbers_without_ocr():
    from tests.docx_fixture import _docx_package

    _, result = extract_docx(
        _docx_package("<w:p><w:r><w:t>Thông báo năm 2023: 0 -</w:t></w:r></w:p>")
    )
    assert "Thông báo năm 2023: 0 -" in result.pages[0].layout.text
    assert not result.pages[0].needs_ocr
    assert result.source_artifact == "source_revision"


def test_docx_keeps_cached_field_values_without_recalculation():
    from tests.docx_fixture import _docx_package

    payload = _docx_package(
        "<w:tbl><w:tblGrid><w:gridCol/><w:gridCol/></w:tblGrid><w:tr>"
        '<w:tc><w:p><w:fldSimple w:instr="=SUM(ABOVE)"><w:r><w:t>00451</w:t></w:r>'
        "</w:fldSimple></w:p></w:tc>"
        '<w:tc><w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        "<w:r><w:instrText> =SUM(ABOVE) </w:instrText></w:r>"
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>402</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:tc></w:tr></w:tbl>'
    )
    _, result = extract_docx(payload)
    [table] = [block.table for block in result.pages[0].layout.blocks if block.table]
    assert [cell.text for cell in table.rows[0]] == ["00451", "402"]


@pytest.mark.parametrize("extract", [extract_native, extract_pdf])
def test_pdf_table_keeps_cells_and_empty_zero_dash(extract):
    doc = pymupdf.open()
    page = doc.new_page()
    for x in (40, 140, 240, 340):
        page.draw_line((x, 80), (x, 180))
    for y in (80, 130, 180):
        page.draw_line((40, y), (340, y))
    for x, y, text in [
        (45, 100, "Year"),
        (145, 100, "2023"),
        (245, 100, "2024"),
        (45, 150, "0"),
        (145, 150, "-"),
    ]:
        page.insert_text((x, y), text)
    data = doc.tobytes()
    doc.close()
    rendered = render_document(data, ".pdf", processing_config(get_settings()))
    result = extract(data, rendered).pages[0]
    table = next(b.table for b in result.layout.blocks if b.table)
    assert [[c.text for c in row] for row in table.rows] == [
        ["Year", "2023", "2024"],
        ["0", "-", ""],
    ]
    assert not result.needs_ocr
    if extract is extract_pdf:
        assert result.inspector_markdown
        assert not any("regions_recovered" in warning for warning in result.layout.warnings)


def docx_image():
    source = pymupdf.open(stream=pdf(image=True), filetype="pdf")
    image = next(b["image"] for b in source[0].get_text("dict")["blocks"] if b["type"] == 1)
    source.close()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:r><w:t>Text before image</w:t></w:r></w:p><w:p><w:r><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r></w:p><w:p><w:r><w:t>Text after image</w:t></w:r></w:p></w:body></w:document>',
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="media/image1.png" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"/></Relationships>',
        )
        archive.writestr("word/media/image1.png", image)
    return output.getvalue()


def test_docx_embedded_image_is_not_lost_in_native_projection():
    result = plan(docx_image(), ".docx")
    assert len(result.pages[0].images) == 1
    blocks = result.pages[0].layout.blocks
    before = next(i for i, b in enumerate(blocks) if "Text before" in b.text)
    image = next(i for i, b in enumerate(blocks) if b.image)
    after = next(i for i, b in enumerate(blocks) if "Text after" in b.text)
    assert before < image < after
    assert result.pages[0].needs_ocr


def test_serialized_native_evidence_reconstructs_layout_and_images():
    from qnu.domains.ocr.native import page_from_payload, page_payload

    original = plan(pdf(image=True)).pages[0]
    restored = page_from_payload(page_payload(original, "source_revision"))
    assert restored.layout == original.layout
    assert restored.needs_ocr == original.needs_ocr


def test_unusable_unicode_is_not_accepted_as_native_text():
    from qnu.domains.ocr.native import _usable

    assert not _usable("text\ufffd")
    assert not _usable("text\x00")
    assert _usable("Thông báo: 0 -\n2023")


def test_pdf_columns_are_read_column_by_column():
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    for x, y, text in [
        (40, 50, "Left first"),
        (40, 80, "Left second"),
        (340, 50, "Right first"),
        (340, 80, "Right second"),
    ]:
        page.insert_text((x, y), text)
    data = doc.tobytes()
    doc.close()
    assert plan(data).pages[0].layout.text.split("\n\n") == [
        "Left first",
        "Left second",
        "Right first",
        "Right second",
    ]


def test_scan_hidden_text_layer_does_not_duplicate_ocr_content():
    document = pymupdf.open(stream=pdf(text="", image=True), filetype="pdf")
    document[0].insert_text((65, 240), "Hidden text", fontsize=8, render_mode=3)
    data = document.tobytes()
    document.close()
    page = plan(data).pages[0]
    assert page.needs_ocr and not page.native_text
    assert "native_image_text_overlap_requires_ocr" in page.layout.warnings
    result = merge_layout(page, parse_page("<x_0.11><y_0.25>OCR text<x_0.25><y_0.32><class_Text>"))
    assert "Hidden text" not in result.text and "OCR text" in result.text


def test_docx_skipped_image_cannot_be_claimed_as_complete_native_output():
    original = zipfile.ZipFile(io.BytesIO(docx_image()))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as changed:
        for name in original.namelist():
            data = original.read(name)
            if name.endswith(".rels"):
                data = data.replace(b"image1.png", b"image1.emf")
            changed.writestr(name.replace("image1.png", "image1.emf"), data)
    original.close()
    with pytest.raises(AppException) as caught:
        plan(output.getvalue(), ".docx")
    assert caught.value.code == "docx_image_unsupported"


def test_docx_vertical_merge_keeps_more_than_two_rows():
    from qnu.domains.ocr.artifacts.docx_html import convert_docx_to_html

    cells = []
    for i, merge in enumerate(("restart", "continue", "continue")):
        text = "Group" if i == 0 else ""
        cells.append(
            f'<w:tr><w:tc><w:tcPr><w:vMerge w:val="{merge}"/></w:tcPr><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>{i}</w:t></w:r></w:p></w:tc></w:tr>'
        )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>'
            + "".join(cells)
            + "</w:tbl></w:body></w:document>",
        )
    assert 'rowspan="3"' in convert_docx_to_html(output.getvalue()).html
