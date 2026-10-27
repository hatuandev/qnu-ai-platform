"""DOCX body XML is projected to HTML without losing structure or literal values.

The projection is deterministic on purpose: the same DOCX must always produce the same
HTML, because that HTML becomes a page image and therefore part of the evidence.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from qnu.domains.ocr.artifacts.docx_html import convert_docx_to_html
from qnu.platform.errors import AppException

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(body: str, *, footnotes: str = "", media: dict[str, bytes] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{W}"><w:body>'
            f"{body}</w:body></w:document>",
        )
        if footnotes:
            archive.writestr(
                "word/footnotes.xml",
                f'<?xml version="1.0" encoding="UTF-8"?><w:footnotes xmlns:w="{W}">'
                f"{footnotes}</w:footnotes>",
            )
        for name, payload in (media or {}).items():
            archive.writestr(f"word/media/{name}", payload)
    return buffer.getvalue()


def _paragraph(text: str, style: str | None = None, extra: str = "") -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{properties}<w:r><w:t xml:space=\"preserve\">{text}</w:t></w:r>{extra}</w:p>"


def test_headings_and_paragraphs_keep_their_text() -> None:
    conversion = convert_docx_to_html(
        _docx(
            _paragraph("PHỤ LỤC 01", "Heading1")
            + _paragraph("Chỉ tiêu tuyển sinh năm 2023")
        )
    )
    assert "<h1" in conversion.html and "PHỤ LỤC 01" in conversion.html
    assert "<p" in conversion.html and "Chỉ tiêu tuyển sinh năm 2023" in conversion.html
    assert conversion.paragraphs == 2


def test_bold_and_italic_runs_are_marked() -> None:
    body = (
        "<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Đậm</w:t></w:r>"
        "<w:r><w:rPr><w:i/></w:rPr><w:t>Nghiêng</w:t></w:r></w:p>"
    )
    html = convert_docx_to_html(_docx(body)).html
    assert "<b>Đậm</b>" in html
    assert "<i>Nghiêng</i>" in html


def test_table_spans_header_cells_and_literal_values() -> None:
    body = (
        "<w:tbl><w:tr><w:trPr><w:tblHeader/></w:trPr>"
        '<w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>Nhóm</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr><w:p><w:r><w:t>Năm</w:t></w:r></w:p></w:tc>'
        "</w:tr>"
        "<w:tr>"
        '<w:tc><w:tcPr><w:vMerge w:val="restart"/></w:tcPr><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc>'
        "<w:tc><w:p><w:r><w:t>2023</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>0</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>-</w:t></w:r></w:p></w:tc>"
        "</w:tr>"
        "<w:tr>"
        '<w:tc><w:tcPr><w:vMerge/></w:tcPr><w:p/></w:tc>'
        "<w:tc><w:p><w:r><w:t>2024</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p/></w:tc>"
        "<w:tc><w:p><w:r><w:t>150</w:t></w:r></w:p></w:tc>"
        "</w:tr></w:tbl>"
    )
    conversion = convert_docx_to_html(_docx(body))
    html = conversion.html
    assert 'colspan="2"' in html
    assert 'rowspan="2"' in html
    assert "<th" in html
    assert ">0<" in html and ">-<" in html
    assert conversion.tables == 1
    assert conversion.table_rows == 3


def test_footnote_reference_becomes_a_marker_and_a_note() -> None:
    body = _paragraph(
        "Chỉ tiêu",
        extra='<w:r><w:footnoteReference w:id="1"/></w:r>',
    )
    notes = (
        '<w:footnote w:id="1"><w:p><w:r><w:t>Ghi chú: số liệu năm 2023.</w:t></w:r></w:p></w:footnote>'
    )
    conversion = convert_docx_to_html(_docx(body, footnotes=notes))
    assert 'class="fn"' in conversion.html
    assert "Ghi chú: số liệu năm 2023." in conversion.html
    assert conversion.footnotes == 1


def test_drawing_is_embedded_as_a_data_uri() -> None:
    body = (
        "<w:p><w:r><w:drawing><wp:inline xmlns:wp=\"http://schemas.openxmlformats.org/"
        "drawingml/2006/wordprocessingDrawing\"><a:graphic xmlns:a=\"http://schemas."
        "openxmlformats.org/drawingml/2006/main\"><a:graphicData><pic:pic xmlns:pic=\"http://"
        "schemas.openxmlformats.org/drawingml/2006/picture\"><pic:blipFill><a:blip r:embed="
        "\"rId5\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/"
        "relationships\"/></pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline>"
        "</w:drawing></w:r></w:p>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
        'openxmlformats.org/package/2006/relationships"><Relationship Id="rId5" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        'Target="media/image1.png"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>',
        )
        archive.writestr("word/_rels/document.xml.rels", relationships)
        archive.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    conversion = convert_docx_to_html(buffer.getvalue())
    assert "data:image/png;base64," in conversion.html
    assert conversion.images == 1


def test_a_non_docx_package_is_rejected() -> None:
    with pytest.raises(AppException) as caught:
        convert_docx_to_html(b"not a zip at all")
    assert caught.value.code == "docx_invalid"


def test_a_package_without_document_xml_is_rejected() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/styles.xml", "<styles/>")
    with pytest.raises(AppException) as caught:
        convert_docx_to_html(buffer.getvalue())
    assert caught.value.code == "docx_invalid"


def test_projection_is_deterministic() -> None:
    payload = _docx(_paragraph("PHỤ LỤC 01", "Heading1"))
    assert convert_docx_to_html(payload).html == convert_docx_to_html(payload).html
