"""Valid Word package shared by offline and HTTP integration tests."""

import io
import zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _cell(text: str, *, span: int = 1, merge: str | None = None, footnote: bool = False) -> str:
    properties = "<w:tcPr>"
    if span > 1:
        properties += f'<w:gridSpan w:val="{span}"/>'
    if merge:
        properties += f'<w:vMerge w:val="{merge}"/>'
    properties += "</w:tcPr>"
    runs = f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'
    if footnote:
        runs += '<w:r><w:footnoteReference w:id="1"/></w:r>'
    return f"<w:tc>{properties}<w:p>{runs}</w:p></w:tc>"


def docx_with_table() -> bytes:
    """DOCX with a two-level header, a merged cell, an empty cell, 0, '-' and a footnote."""
    body = (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        "<w:r><w:t>PHỤ LỤC 01</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Đơn vị: Khoa Công nghệ thông tin</w:t></w:r></w:p>"
    )
    borders = "".join(
        f'<w:{edge} w:val="single" w:sz="4" w:color="000000"/>'
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    body += (
        '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/>'
        f"<w:tblBorders>{borders}</w:tblBorders></w:tblPr>"
        '<w:tblGrid><w:gridCol w:w="700"/><w:gridCol w:w="4300"/>'
        '<w:gridCol w:w="2000"/><w:gridCol w:w="2000"/></w:tblGrid>'
        "<w:tr><w:trPr><w:tblHeader/></w:trPr>"
    )
    body += _cell("STT") + _cell("Chỉ tiêu") + _cell("Năm", span=2)
    body += "</w:tr><w:tr><w:trPr><w:tblHeader/></w:trPr>"
    body += _cell("") + _cell("") + _cell("2023") + _cell("2024")
    body += "</w:tr><w:tr>"
    body += _cell("1") + _cell("Chỉ tiêu tuyển sinh") + _cell("0") + _cell("-")
    body += "</w:tr><w:tr>"
    body += _cell("2") + _cell("Chỉ tiêu trúng tuyển", footnote=True) + _cell("") + _cell("150")
    body += "</w:tr><w:tr>"
    body += _cell("3") + _cell("Ghi chú", merge="restart") + _cell("15", span=2)
    body += "</w:tr><w:tr>"
    body += _cell("4") + _cell("", merge="continue") + _cell("20", span=2)
    body += (
        "</w:tr></w:tbl>"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        "</w:sectPr>"
    )
    return _docx_package(body)


def _docx_package(body: str) -> bytes:
    """An actual OPC Word package, readable by LibreOffice and the native projector."""
    relations = "http://schemas.openxmlformats.org/package/2006/relationships"
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    types = "application/vnd.openxmlformats-officedocument.wordprocessingml"
    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/word/document.xml" ContentType="{types}.document.main+xml"/>'
            f'<Override PartName="/word/styles.xml" ContentType="{types}.styles+xml"/>'
            f'<Override PartName="/word/footnotes.xml" ContentType="{types}.footnotes+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{relations}">'
            f'<Relationship Id="doc" Type="{office}/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"
        ),
        "word/document.xml": f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>',
        "word/_rels/document.xml.rels": (
            f'<Relationships xmlns="{relations}">'
            f'<Relationship Id="styles" Type="{office}/styles" Target="styles.xml"/>'
            f'<Relationship Id="notes" Type="{office}/footnotes" Target="footnotes.xml"/>'
            "</Relationships>"
        ),
        "word/styles.xml": (
            f'<w:styles xmlns:w="{W}">'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Liberation Sans" '
            'w:hAnsi="Liberation Sans"/><w:sz w:val="22"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1">'
            '<w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style></w:styles>'
        ),
        "word/footnotes.xml": (
            f'<w:footnotes xmlns:w="{W}">'
            '<w:footnote w:type="separator" w:id="0">'
            "<w:p><w:r><w:separator/></w:r></w:p></w:footnote>"
            '<w:footnote w:id="1"><w:p><w:r><w:t>Ghi chú: số liệu năm 2023.</w:t>'
            "</w:r></w:p></w:footnote></w:footnotes>"
        ),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, xml in parts.items():
            archive.writestr(name, ('<?xml version="1.0" encoding="UTF-8"?>' + xml).encode())
    return buffer.getvalue()
