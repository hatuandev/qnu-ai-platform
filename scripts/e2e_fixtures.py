"""Synthetic test documents generator for QNU V1 E2E tests.

Generates:
1. de_an_tuyen_sinh_2026.pdf (2-page native text PDF)
2. thong_bao_scan_2024.pdf (scanned image PDF without text layer)
3. phu_luc_bang_bieu.docx (DOCX with Vietnamese text, table, footnote)
4. tep_hong.pdf (corrupt bytes)
5. hop_dong_khong_ho_tro.exe (unsupported file format)
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pymupdf

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def install_font(page):
    candidates = [
        os.environ.get("E2E_FONT_PATH", ""),
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font = next((x for x in candidates if x and Path(x).is_file()), None)
    if font is None:
        raise RuntimeError("Set E2E_FONT_PATH to a Unicode font supporting Vietnamese.")
    page.insert_font(fontname="e2e", fontfile=font)


def generate_native_pdf(output_path: Path) -> Path:
    """Valid 2-page native PDF with text layer."""
    doc = pymupdf.open()
    try:
        # Page 1: General info
        p1 = doc.new_page(width=595, height=842)
        text1 = (
            "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n\n"
            "THÔNG BÁO TUYỂN SINH ĐẠI HỌC NĂM 2026\n\n"
            "Năm 2026, Trường Đại học Quy Nhơn thông báo tuyển sinh đại học chính quy "
            "với tổng chỉ tiêu là 5500 sinh viên cho 50 ngành đào tạo.\n\n"
            "Phương thức tuyển sinh:\n"
            "1. Xét tuyển dựa vào kết quả học tập THPT (học bạ).\n"
            "2. Xét tuyển dựa vào kết quả thi tốt nghiệp THPT năm 2026."
        )
        install_font(p1)
        p1.insert_textbox(
            pymupdf.Rect(50, 60, 545, 790), text1, fontsize=12, fontname="e2e"
        )

        # Page 2: Specific major quotas
        p2 = doc.new_page(width=595, height=842)
        text2 = (
            "CHỈ TIÊU CHI TIẾT CÁC NGÀNH NĂM 2026\n\n"
            "1. Ngành Công nghệ thông tin: 350 chỉ tiêu\n"
            "2. Ngành Trí tuệ nhân tạo: 100 chỉ tiêu\n"
            "3. Ngành Sư phạm Toán học: 120 chỉ tiêu\n"
            "4. Ngành Quản trị kinh doanh: 250 chỉ tiêu\n\n"
            "Học phí dự kiến: 18.000.000 đồng/năm học."
        )
        install_font(p2)
        p2.insert_textbox(
            pymupdf.Rect(50, 60, 545, 790), text2, fontsize=12, fontname="e2e"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
        return output_path
    finally:
        doc.close()


def generate_scanned_pdf(output_path: Path) -> Path:
    """Image-only scanned PDF without hidden text layer."""
    # First create temporary page with text to render to pixmap image
    temp_doc = pymupdf.open()
    try:
        p = temp_doc.new_page(width=595, height=842)
        install_font(p)
        p.insert_textbox(
            pymupdf.Rect(50, 60, 545, 790),
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "THÔNG BÁO ĐIỂM CHUẨN NĂM 2024\n\n"
            "Điểm chuẩn trúng tuyển ngành Công nghệ thông tin năm 2024 là 24.5 điểm.\n"
            "Chỉ tiêu tuyển sinh năm 2024 đã hoàn thành 100%.",
            fontsize=14,
            fontname="e2e",
        )
        pix = p.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
    finally:
        temp_doc.close()

    # Now create new PDF and insert as image only (no text layer)
    scan_doc = pymupdf.open()
    try:
        scan_page = scan_doc.new_page(width=595, height=842)
        scan_page.insert_image(pymupdf.Rect(0, 0, 595, 842), stream=img_bytes)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        scan_doc.save(str(output_path))
        return output_path
    finally:
        scan_doc.close()


def _cell(text: str, *, span: int = 1, merge: str | None = None) -> str:
    properties = "<w:tcPr>"
    if span > 1:
        properties += f'<w:gridSpan w:val="{span}"/>'
    if merge:
        properties += f'<w:vMerge w:val="{merge}"/>'
    properties += "</w:tcPr>"
    runs = f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'
    return f"<w:tc>{properties}<w:p>{runs}</w:p></w:tc>"


def generate_docx(output_path: Path) -> Path:
    """DOCX document with Vietnamese text, table, and footnote."""
    body = (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        "<w:r><w:t>PHỤ LỤC CHỈ TIÊU VÀ HỌC PHÍ NĂM 2026</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Đơn vị: Trường Đại học Quy Nhơn</w:t></w:r></w:p>"
        '<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="700"/><w:gridCol w:w="3800"/>'
        '<w:gridCol w:w="1900"/><w:gridCol w:w="2600"/></w:tblGrid>'
        "<w:tr><w:trPr><w:tblHeader/></w:trPr>"
        + _cell("STT")
        + _cell("Ngành đào tạo")
        + _cell("Chỉ tiêu 2026")
        + _cell("Học phí (đồng/năm)")
        + "</w:tr>"
        + "<w:tr>"
        + _cell("1")
        + _cell("Công nghệ thông tin")
        + _cell("350")
        + _cell("18.000.000")
        + "</w:tr>"
        + "<w:tr>"
        + _cell("2")
        + _cell("Trí tuệ nhân tạo")
        + _cell("100")
        + _cell("18.000.000")
        + "</w:tr>"
        + "<w:tr>"
        + _cell("3")
        + _cell("Sư phạm Toán")
        + _cell("120")
        + _cell("Miễn học phí")
        + "</w:tr>"
        + "</w:tbl>"
        + "<w:p><w:r><w:t>Ghi chú học phí</w:t></w:r>"
        + '<w:r><w:footnoteReference w:id="1"/></w:r></w:p>'
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        + '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        + "</w:sectPr>"
    )
    # LibreOffice needs the OPC root relationship and registered document content type.
    relationships = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_relationships = (
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    )
    content_types = "application/vnd.openxmlformats-officedocument.wordprocessingml"
    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/word/document.xml" ContentType="{content_types}.document.main+xml"/>'
            f'<Override PartName="/word/styles.xml" ContentType="{content_types}.styles+xml"/>'
            f'<Override PartName="/word/footnotes.xml" ContentType="{content_types}.footnotes+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{relationships}">'
            f'<Relationship Id="rId1" Type="{office_relationships}/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"
        ),
        "word/document.xml": f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>',
        "word/_rels/document.xml.rels": (
            f'<Relationships xmlns="{relationships}">'
            f'<Relationship Id="rId1" Type="{office_relationships}/styles" Target="styles.xml"/>'
            f'<Relationship Id="rId2" Type="{office_relationships}/footnotes" Target="footnotes.xml"/>'
            "</Relationships>"
        ),
        "word/styles.xml": (
            f'<w:styles xmlns:w="{W}">'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Liberation Sans" w:hAnsi="Liberation Sans"/>'
            '<w:sz w:val="22"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
            '<w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
            "</w:styles>"
        ),
        "word/footnotes.xml": (
            f'<w:footnotes xmlns:w="{W}">'
            '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
            '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
            '<w:footnote w:id="1"><w:p><w:r><w:footnoteRef/></w:r><w:r>'
            "<w:t> Dữ liệu giả lập cho kiểm tra; học phí không phải thông báo chính thức.</w:t>"
            "</w:r></w:p></w:footnote></w:footnotes>"
        ),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, xml in parts.items():
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(
                entry, ('<?xml version="1.0" encoding="UTF-8"?>' + xml).encode("utf-8")
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buffer.getvalue())
    validate_docx_fixture(output_path)
    return output_path


def validate_docx_fixture(file: Path) -> None:
    """Check the OPC contract before uploading the synthetic Word fixture."""
    with zipfile.ZipFile(file) as archive:
        try:
            types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
            relations = ElementTree.fromstring(archive.read("_rels/.rels"))
            document = ElementTree.fromstring(archive.read("word/document.xml"))
            for name in (
                "word/styles.xml",
                "word/footnotes.xml",
                "word/_rels/document.xml.rels",
            ):
                ElementTree.fromstring(archive.read(name))
        except (KeyError, ElementTree.ParseError) as exc:
            raise RuntimeError(
                "DOCX fixture thiếu thành phần OPC hợp lệ; tạo phiên E2E mới."
            ) from exc
        has_type = any(
            node.attrib.get("PartName") == "/word/document.xml"
            and node.attrib.get("ContentType")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
            for node in types
        )
        has_root = any(
            node.attrib.get("Target") == "word/document.xml"
            and node.attrib.get("Type", "").endswith("/officeDocument")
            for node in relations
        )
        if not has_type or not has_root or document.tag != f"{{{W}}}document":
            raise RuntimeError(
                "DOCX fixture thiếu content type hoặc officeDocument relationship."
            )


def generate_corrupt_pdf(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"%PDF-1.7\nCorrupted content invalid xref stream footer")
    return output_path


def generate_unsupported_file(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00Binary Executable Data")
    return output_path


def generate_all_fixtures(target_dir: Path) -> dict[str, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    return {
        "native_pdf_2026": generate_native_pdf(
            target_dir / "de_an_tuyen_sinh_2026.pdf"
        ),
        "scanned_pdf_2024": generate_scanned_pdf(
            target_dir / "thong_bao_scan_2024.pdf"
        ),
        "docx_table": generate_docx(target_dir / "phu_luc_bang_bieu.docx"),
        "corrupt_pdf": generate_corrupt_pdf(target_dir / "tep_hong.pdf"),
        "unsupported_file": generate_unsupported_file(
            target_dir / "hop_dong_khong_ho_tro.exe"
        ),
    }


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "tmp" / "e2e_fixtures"
    files = generate_all_fixtures(out)
    for name, p in files.items():
        print(f"Generated {name}: {p} ({p.stat().st_size} bytes)")
