"""Document Generator Service — Renders ND 30 Word (.docx) via docxtpl and converts to PDF via Gotenberg."""

from __future__ import annotations

import io
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from docx.text.paragraph import Paragraph
from docxtpl import DocxTemplate

from app.core.config import get_settings
from app.core.storage import storage_service

logger = logging.getLogger(__name__)
settings = get_settings()

_RICH_BODY_MARKER = "[[QNU_DOCUMENT_AST_BODY]]"
_DECISION_TEMPLATE_CODES = {"quyet_dinh", "mau_quyet_dinh", "qnu_quyet_dinh"}

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "documents"

TEMPLATE_MAP = {
    "to_trinh": "mau_to_trinh_nd30.docx",
    "mau_to_trinh": "mau_to_trinh_nd30.docx",
    "qnu_to_trinh": "mau_to_trinh_nd30.docx",
    "thong_bao": "mau_thong_bao_nd30.docx",
    "mau_thong_bao": "mau_thong_bao_nd30.docx",
    "qnu_thong_bao": "mau_thong_bao_nd30.docx",
    "quyet_dinh": "mau_quyet_dinh_nd30.docx",
    "mau_quyet_dinh": "mau_quyet_dinh_nd30.docx",
    "qnu_quyet_dinh": "mau_quyet_dinh_nd30.docx",
    "ke_hoach": "mau_ke_hoach_nd30.docx",
    "mau_ke_hoach": "mau_ke_hoach_nd30.docx",
    "qnu_ke_hoach": "mau_ke_hoach_nd30.docx",
}

def _normalize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Fill unset fields with visible placeholders instead of invented facts."""
    normalized = dict(context)

    normalized.setdefault("ngay", "[BỔ SUNG NGÀY]")
    normalized.setdefault("thang", "[BỔ SUNG THÁNG]")
    normalized.setdefault("nam", "[BỔ SUNG NĂM]")
    normalized.setdefault("ngay_thang", "[BỔ SUNG NGÀY BAN HÀNH]")
    normalized.setdefault("dia_danh", "Quy Nhơn")
    normalized.setdefault("so_hieu", "[CHƯA CẤP SỐ VĂN BẢN]")
    parent_organization = str(normalized.get("co_quan_chu_quan") or "").strip()
    issuing_unit = str(normalized.get("don_vi_ban_hanh") or "").strip()
    if parent_organization.casefold() == issuing_unit.casefold():
        parent_organization = ""
    normalized["co_quan_chu_quan"] = parent_organization.upper()
    normalized["don_vi_ban_hanh"] = issuing_unit.upper()
    normalized.setdefault("kinh_gui", "[BỔ SUNG ĐƠN VỊ KÍNH GỬI]")
    normalized.setdefault("trich_yeu", "[BỔ SUNG TRÍCH YẾU]")
    normalized.setdefault("noi_dung", "[BỔ SUNG NỘI DUNG DỰ THẢO]")
    normalized.setdefault("noi_nhan", "- [BỔ SUNG NƠI NHẬN]")
    normalized.setdefault("chuc_vu_nguoi_ky", "[BỔ SUNG CHỨC VỤ NGƯỜI KÝ]")
    normalized["chuc_vu_nguoi_ky"] = str(normalized["chuc_vu_nguoi_ky"]).upper()
    normalized.setdefault("ho_ten_nguoi_ky", "[BỔ SUNG HỌ TÊN NGƯỜI KÝ]")
    normalized.setdefault(
        "can_cu_phap_ly", "[BỔ SUNG CĂN CỨ PHÁP LÝ ĐÃ ĐƯỢC XÁC NHẬN (NẾU CẦN)]"
    )
    return normalized


def _iter_document_paragraphs(document: Any) -> list[Paragraph]:
    paragraphs = list(document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    return paragraphs


def _replace_issue_place(document: Any, issue_place: str) -> None:
    """Replace the template's default place while preserving the date-line styling."""
    for paragraph in _iter_document_paragraphs(document):
        if "Quy Nhơn, ngày" not in paragraph.text:
            continue
        for run in paragraph.runs:
            if "Quy Nhơn" in run.text:
                run.text = run.text.replace("Quy Nhơn", issue_place, 1)
                return


def _assert_rendered_docx_quality(docx_bytes: bytes) -> dict[str, Any]:
    """Reject unresolved template tokens and verify the administrative A4 canvas."""
    document = Document(io.BytesIO(docx_bytes))
    paragraphs = _iter_document_paragraphs(document)
    rendered_text = "\n".join(paragraph.text for paragraph in paragraphs)
    unresolved_tokens = [
        match.group(0)
        for paragraph in paragraphs
        for match in re.finditer(r"{{\s*[^{}]+\s*}}", paragraph.text)
    ]
    if unresolved_tokens:
        raise ValueError(
            "Unresolved DOCX template tokens: " + ", ".join(sorted(set(unresolved_tokens)))
        )
    a4_sections = sum(
        1
        for section in document.sections
        if abs(section.page_width.mm - 210) < 1 and abs(section.page_height.mm - 297) < 1
    )
    if a4_sections != len(document.sections):
        raise ValueError("Rendered DOCX contains a non-A4 section")
    expected_margins = (20, 20, 30, 15)
    compliant_margins = sum(
        1
        for section in document.sections
        if all(
            abs(actual.mm - expected) < 1
            for actual, expected in zip(
                (
                    section.top_margin,
                    section.bottom_margin,
                    section.left_margin,
                    section.right_margin,
                ),
                expected_margins,
                strict=True,
            )
        )
    )
    if compliant_margins != len(document.sections):
        raise ValueError("Rendered DOCX contains margins outside the Decree 30 range")
    if "DỰ THẢO — CHƯA BAN HÀNH" in rendered_text:
        raise ValueError("Rendered DOCX contains an internal draft-state banner")
    page_number_fields = sum(
        section.header._element.xml.count(" PAGE ") for section in document.sections
    )
    if page_number_fields != len(document.sections):
        raise ValueError("Rendered DOCX is missing an administrative page-number field")
    return {
        "unresolved_template_tokens": 0,
        "a4_sections": a4_sections,
        "compliant_margin_sections": compliant_margins,
        "page_number_fields": page_number_fields,
        "paragraph_count": len(paragraphs),
    }


def _apply_administrative_page_setup(document: Any) -> None:
    """Apply the A4 canvas and page margins from Appendix I of Decree 30."""
    for section in document.sections:
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(30)
        section.right_margin = Mm(15)
        section.header_distance = Mm(10)
        section.footer_distance = Mm(10)


def _set_paragraph_bottom_border(
    paragraph: Paragraph,
    *,
    left_indent_mm: float = 0,
    right_indent_mm: float = 0,
) -> None:
    """Draw a restrained rule below a paragraph without underlining its spaces."""
    paragraph.paragraph_format.left_indent = Mm(left_indent_mm)
    paragraph.paragraph_format.right_indent = Mm(right_indent_mm)
    paragraph_properties = paragraph._p.get_or_add_pPr()
    borders = paragraph_properties.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        paragraph_properties.append(borders)
    bottom = borders.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        borders.append(bottom)
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")


def _add_page_number_field(paragraph: Paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run()
    _set_run_font(run, size=13)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "2"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instruction, separate, text, end):
        run._r.append(element)


def _apply_page_numbering(document: Any) -> None:
    """Place page numbers at the top centre and hide them on the first page."""
    for section in document.sections:
        section.different_first_page_header_footer = True
        header_paragraph = section.header.paragraphs[0]
        _clear_paragraph(header_paragraph)
        _add_page_number_field(header_paragraph)
        first_page_header = section.first_page_header.paragraphs[0]
        _clear_paragraph(first_page_header)


def _clear_paragraph(paragraph: Paragraph) -> None:
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)


def _apply_organization_header(
    document: Any,
    parent_organization: str,
    issuing_unit: str,
) -> None:
    """Build both halves of the administrative header and their required rules."""
    if not document.tables or not document.tables[0].rows:
        raise ValueError("Administrative template does not contain a header table")

    header_row = document.tables[0].rows[0]
    left_cell = header_row.cells[0]
    for paragraph in list(left_cell.paragraphs)[1:]:
        left_cell._tc.remove(paragraph._p)
    paragraph = left_cell.paragraphs[0]
    _clear_paragraph(paragraph)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(0)
    values = [value for value in (parent_organization, issuing_unit) if value]
    for index, value in enumerate(values):
        run = paragraph.add_run(value)
        _set_run_font(run, size=12, bold=index == len(values) - 1)
        if index < len(values) - 1:
            run.add_break()
    left_rule = left_cell.add_paragraph()
    left_rule.paragraph_format.space_before = Pt(0)
    left_rule.paragraph_format.space_after = Pt(0)
    left_rule.paragraph_format.line_spacing = 0.5
    _set_paragraph_bottom_border(left_rule, left_indent_mm=20, right_indent_mm=20)

    right_cell = header_row.cells[1]
    for extra_paragraph in list(right_cell.paragraphs)[1:]:
        right_cell._tc.remove(extra_paragraph._p)
    right_paragraph = right_cell.paragraphs[0]
    _clear_paragraph(right_paragraph)
    right_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    right_paragraph.paragraph_format.space_after = Pt(0)
    country_run = right_paragraph.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    _set_run_font(country_run, size=12, bold=True)
    _set_run_width_scale(country_run, 90)
    country_run.add_break()
    motto_run = right_paragraph.add_run("Độc lập - Tự do - Hạnh phúc")
    _set_run_font(motto_run, size=13, bold=True)
    right_rule = right_cell.add_paragraph()
    right_rule.paragraph_format.space_before = Pt(0)
    right_rule.paragraph_format.space_after = Pt(0)
    right_rule.paragraph_format.line_spacing = 0.5
    _set_paragraph_bottom_border(right_rule, left_indent_mm=22, right_indent_mm=22)


def _apply_subject_rule(document: Any, subject: str) -> None:
    """Add the short rule required below the document subject/title block."""
    normalized_subject = subject.strip()
    if not normalized_subject:
        return
    title = next(
        (
            paragraph
            for paragraph in document.paragraphs
            if normalized_subject in paragraph.text
            and paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
        ),
        None,
    )
    if title is None:
        return
    rule = document.add_paragraph()
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rule.paragraph_format.space_before = Pt(0)
    rule.paragraph_format.space_after = Pt(6)
    rule.paragraph_format.line_spacing = 0.5
    _set_paragraph_bottom_border(rule, left_indent_mm=62, right_indent_mm=62)
    title._p.addnext(rule._p)


def _set_table_widths(table: Any, widths_mm: list[float]) -> None:
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table_properties = table._tbl.tblPr
    table_width = table_properties.first_child_found_in("w:tblW")
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        table_properties.append(table_width)
    table_width.set(qn("w:type"), "dxa")
    table_width.set(qn("w:w"), str(round(sum(widths_mm) * 1440 / 25.4)))
    table_indent = table_properties.first_child_found_in("w:tblInd")
    if table_indent is None:
        table_indent = OxmlElement("w:tblInd")
        table_properties.append(table_indent)
    table_indent.set(qn("w:type"), "dxa")
    table_indent.set(qn("w:w"), "0")
    grid_columns = table._tbl.tblGrid.gridCol_lst
    for index, width in enumerate(widths_mm):
        width_twips = str(round(width * 1440 / 25.4))
        if index < len(grid_columns):
            grid_columns[index].set(qn("w:w"), width_twips)
        table.columns[index].width = Mm(width)
        for row in table.rows:
            row.cells[index].width = Mm(width)


def _format_structural_tables(document: Any) -> None:
    """Fit header/signature tables to the A4 text area and keep signatures intact."""
    if len(document.tables) < 2:
        raise ValueError("Administrative template requires header and signature tables")
    printable_width = 165.0
    widths = [printable_width * 0.45, printable_width * 0.55]
    _set_table_widths(document.tables[0], widths)

    signature_table = document.tables[-1]
    _set_table_widths(signature_table, widths)
    row_properties = signature_table.rows[0]._tr.get_or_add_trPr()
    cannot_split = OxmlElement("w:cantSplit")
    row_properties.append(cannot_split)
    signature_cell = signature_table.cell(0, 1)
    values = [
        line.strip()
        for paragraph in signature_cell.paragraphs
        for line in paragraph.text.splitlines()
        if line.strip()
    ]
    title = next((value for value in values if value), "")
    signer = next((value for value in reversed(values) if value and value != title), "")
    for paragraph in list(signature_cell.paragraphs)[1:]:
        signature_cell._tc.remove(paragraph._p)
    paragraph = signature_cell.paragraphs[0]
    _clear_paragraph(paragraph)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(title)
    _set_run_font(run, size=12, bold=True)
    for _ in range(2):
        spacer = signature_cell.add_paragraph()
        spacer.paragraph_format.space_after = Pt(0)
        spacer.paragraph_format.keep_with_next = True
    name_paragraph = signature_cell.add_paragraph()
    name_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = name_paragraph.add_run(signer)
    _set_run_font(name_run, size=12, bold=True)


def _set_run_font(run: Any, *, size: float, bold: bool = False, italic: bool = False) -> None:
    run.bold = bold
    run.italic = italic
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run_properties = run._element.get_or_add_rPr()
    run_properties.rFonts.set(qn("w:ascii"), "Times New Roman")
    run_properties.rFonts.set(qn("w:hAnsi"), "Times New Roman")


def _set_run_width_scale(run: Any, percent: int) -> None:
    """Keep the prescribed point size while fitting fixed administrative headings."""
    run_properties = run._element.get_or_add_rPr()
    width = run_properties.find(qn("w:w"))
    if width is None:
        width = OxmlElement("w:w")
        run_properties.append(width)
    width.set(qn("w:val"), str(percent))


def _format_body_paragraph(
    paragraph: Paragraph,
    *,
    role: str,
    document_type: str,
    heading: bool = False,
) -> None:
    is_decision_basis = (
        role == "basis" and document_type.casefold() in _DECISION_TEMPLATE_CODES
    )
    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.LEFT if heading else WD_ALIGN_PARAGRAPH.JUSTIFY
    )
    paragraph.paragraph_format.space_before = Pt(6 if heading else 0)
    paragraph.paragraph_format.space_after = Pt(4 if heading else 6)
    paragraph.paragraph_format.line_spacing = 1.15
    if not heading and role != "closing" and not is_decision_basis:
        paragraph.paragraph_format.first_line_indent = Mm(12.7)
    for run in paragraph.runs:
        _set_run_font(
            run,
            size=14,
            bold=heading,
            italic=is_decision_basis,
        )


def _append_content_paragraphs(
    document: Any,
    marker: Paragraph,
    content: str,
    role: str,
    document_type: str,
) -> None:
    """Render logical lines separately so justified text never stretches short headings."""
    for line in (value.strip() for value in content.splitlines()):
        if not line:
            continue
        is_numbered_heading = bool(re.fullmatch(r"\d+(?:\.\d+)*\.\s+[^.;:]{1,80}", line))
        paragraph = document.add_paragraph()
        paragraph.add_run(line)
        _format_body_paragraph(
            paragraph,
            role=role,
            document_type=document_type,
            heading=is_numbered_heading,
        )
        marker._p.addprevious(paragraph._p)


def _repeat_table_header(row: Any) -> None:
    table_properties = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    table_properties.append(repeat)


def _set_table_cell_margins(cell: Any, margin_twips: int = 70) -> None:
    cell_properties = cell._tc.get_or_add_tcPr()
    margins = cell_properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        cell_properties.append(margins)
    for edge in ("top", "left", "bottom", "right"):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(margin_twips))
        node.set(qn("w:type"), "dxa")


def _table_column_widths(columns: list[str], rows: list[list[str]]) -> list[float]:
    """Allocate the printable width from observed cell lengths, with bounded columns."""
    column_count = len(columns)
    weights: list[float] = []
    for index, heading in enumerate(columns):
        longest = max(
            [len(heading), *(len(row[index]) for row in rows if index < len(row))],
            default=len(heading),
        )
        weights.append(float(min(max(longest, 5), 36)))
    total = sum(weights) or float(column_count)
    printable_width_mm = 165.0
    widths = [printable_width_mm * weight / total for weight in weights]
    minimum_width = 8.0
    widths = [max(minimum_width, width) for width in widths]
    scale = printable_width_mm / sum(widths)
    return [width * scale for width in widths]


def _append_rich_table(document: Any, block: dict[str, Any], marker: Paragraph) -> None:
    columns = [str(value) for value in block.get("columns", [])]
    rows = [[str(cell) for cell in row] for row in block.get("rows", [])]
    if not columns or not rows:
        return
    table = document.add_table(rows=1, cols=len(columns))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = _table_column_widths(columns, rows)
    header = table.rows[0]
    _repeat_table_header(header)
    for index, heading in enumerate(columns):
        cell = header.cells[index]
        cell.width = Mm(widths[index])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _set_table_cell_margins(cell)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(heading)
        _set_run_font(run, size=9, bold=True)
    for values in rows:
        row = table.add_row()
        for index, value in enumerate(values):
            cell = row.cells[index]
            cell.width = Mm(widths[index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_table_cell_margins(cell)
            paragraph = cell.paragraphs[0]
            paragraph.alignment = (
                WD_ALIGN_PARAGRAPH.CENTER if index == 0 else WD_ALIGN_PARAGRAPH.LEFT
            )
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(value)
            _set_run_font(run, size=9)
    marker._p.addprevious(table._tbl)


def _render_document_ast(
    template: DocxTemplate,
    ast_payload: dict[str, Any],
    *,
    document_type: str,
) -> None:
    """Replace the body marker with native Word paragraphs, lists, and tables."""
    document = template.docx
    marker = next(
        (
            paragraph
            for paragraph in document.paragraphs
            if _RICH_BODY_MARKER in paragraph.text
        ),
        None,
    )
    if marker is None:
        raise ValueError("Administrative template does not contain the AST body marker")
    for raw_block in ast_payload.get("blocks", []):
        if not isinstance(raw_block, dict):
            continue
        block_type = str(raw_block.get("type") or "paragraph")
        role = str(raw_block.get("role") or "other")
        heading = str(raw_block.get("heading") or "").strip()
        content = str(raw_block.get("content") or "").strip()
        items = [str(item).strip() for item in raw_block.get("items", []) if str(item).strip()]

        if heading:
            paragraph = document.add_paragraph()
            paragraph.add_run(heading)
            _format_body_paragraph(
                paragraph,
                role=role,
                document_type=document_type,
                heading=True,
            )
            marker._p.addprevious(paragraph._p)
        if content:
            _append_content_paragraphs(
                document,
                marker,
                content,
                role,
                document_type,
            )
        if block_type in {"bullet_list", "numbered_list"}:
            for index, item in enumerate(items, start=1):
                paragraph = document.add_paragraph()
                prefix = f"{index}. " if block_type == "numbered_list" else "- "
                paragraph.add_run(prefix + item)
                _format_body_paragraph(
                    paragraph,
                    role=role,
                    document_type=document_type,
                )
                paragraph.paragraph_format.left_indent = Mm(12.7)
                paragraph.paragraph_format.first_line_indent = Mm(-6.3)
                marker._p.addprevious(paragraph._p)
        if block_type == "table":
            _append_rich_table(document, raw_block, marker)
            spacer = document.add_paragraph()
            spacer.paragraph_format.space_after = Pt(3)
            marker._p.addprevious(spacer._p)
    marker._element.getparent().remove(marker._element)


def render_docx_template(template_code: str, context: dict[str, Any]) -> bytes:
    """Render a DOCX document using docxtpl from a registered template code."""
    filename = TEMPLATE_MAP.get(template_code.lower())
    if not filename:
        raise ValueError(f"No administrative DOCX template is registered for '{template_code}'")
    template_path = TEMPLATES_DIR / filename

    if not template_path.is_file():
        raise FileNotFoundError(f"Template '{filename}' not found in {TEMPLATES_DIR}")

    prepared_context = _normalize_context(context)
    ast_payload = prepared_context.get("document_ast")
    if isinstance(ast_payload, dict):
        prepared_context["noi_dung"] = _RICH_BODY_MARKER
    doc = DocxTemplate(str(template_path))
    doc.render(prepared_context)
    document = doc.docx
    _apply_administrative_page_setup(document)
    _apply_page_numbering(document)
    _format_structural_tables(document)
    _apply_organization_header(
        document,
        str(prepared_context["co_quan_chu_quan"]),
        str(prepared_context["don_vi_ban_hanh"]),
    )
    _replace_issue_place(document, str(prepared_context["dia_danh"]))
    _apply_subject_rule(document, str(prepared_context["trich_yeu"]))
    if isinstance(ast_payload, dict):
        _render_document_ast(doc, ast_payload, document_type=template_code)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    docx_bytes = buffer.getvalue()
    _assert_rendered_docx_quality(docx_bytes)
    return docx_bytes


async def convert_docx_to_pdf_gotenberg(docx_bytes: bytes, filename: str) -> bytes | None:
    """Convert DOCX bytes to PDF bytes via Gotenberg 8 LibreOffice endpoint.

    Gracefully returns None if Gotenberg is unreachable or fails, allowing fallback.
    """
    gotenberg_url = settings.clean_gotenberg_url
    target_url = f"{gotenberg_url}/forms/libreoffice/convert"
    docx_name = filename if filename.endswith(".docx") else f"{filename}.docx"

    try:
        async with httpx.AsyncClient(timeout=60.0, auth=settings.gotenberg_auth) as client:
            response = await client.post(
                target_url,
                files={"files": (docx_name, docx_bytes)},
            )
            if response.status_code == 200 and response.content.startswith(b"%PDF-"):
                logger.info("Successfully converted '%s' to PDF via Gotenberg", docx_name)
                return response.content
            logger.warning(
                "Gotenberg conversion failed for '%s' (status=%d): %s",
                docx_name,
                response.status_code,
                response.text[:200],
            )
            return None
    except Exception as exc:
        logger.warning(
            "Gotenberg unreachable at %s for '%s': %s (Graceful fallback to DOCX)",
            target_url,
            docx_name,
            exc,
        )
        return None


async def export_document_package(
    template_code: str,
    context: dict[str, Any],
    formats: list[str] | None = None,
    base_name: str | None = None,
) -> list[dict[str, Any]]:
    """Generate both DOCX and PDF (if requested & available), persist to storage, and return artifacts."""
    target_formats = [f.lower().strip() for f in (formats or ["docx", "pdf"])]
    if "both" in target_formats:
        target_formats = ["docx", "pdf"]
    unsupported = sorted(set(target_formats) - {"docx", "pdf"})
    if unsupported:
        raise ValueError(f"Unsupported document format(s): {', '.join(unsupported)}")

    base = base_name or f"qnu_van_ban_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    clean_base = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base)
    artifacts: list[dict[str, Any]] = []

    # DOCX is the conversion source even when only PDF was requested.
    docx_bytes = render_docx_template(template_code, context)
    docx_quality = _assert_rendered_docx_quality(docx_bytes)
    docx_filename = f"{clean_base}.docx"
    if "docx" in target_formats:
        docx_rel_path = f"artifacts/{docx_filename}"
        await storage_service.save(docx_rel_path, docx_bytes)
        artifacts.append(
            {
                "id": f"art_docx_{uuid.uuid4().hex[:8]}",
                "name": docx_filename,
                "type": "docx",
                "size": len(docx_bytes),
                "url": f"/platform/v1alpha1/tools/artifacts/{quote(docx_filename, safe='')}",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "quality": docx_quality,
            }
        )

    # 2. Convert to PDF if requested
    if "pdf" in target_formats:
        pdf_bytes = await convert_docx_to_pdf_gotenberg(docx_bytes, docx_filename)
        if pdf_bytes:
            pdf_filename = f"{clean_base}.pdf"
            pdf_rel_path = f"artifacts/{pdf_filename}"
            await storage_service.save(pdf_rel_path, pdf_bytes)
            artifacts.append(
                {
                    "id": f"art_pdf_{uuid.uuid4().hex[:8]}",
                    "name": pdf_filename,
                    "type": "pdf",
                    "size": len(pdf_bytes),
                    "url": f"/platform/v1alpha1/tools/artifacts/{quote(pdf_filename, safe='')}",
                    "mime_type": "application/pdf",
                    "quality": {
                        "pdf_signature_valid": pdf_bytes.startswith(b"%PDF-"),
                        "source_docx": docx_quality,
                    },
                }
            )

    return artifacts
