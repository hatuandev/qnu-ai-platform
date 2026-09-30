"""Universal Report & Artifact Exporter Service — QNU AI Platform.

Generates high-fidelity downloadable reports across three core formats:
1. Excel (.xlsx) via openpyxl with QNU Academic Teal branding, auto-fit columns, and multi-sheet support.
2. Word (.docx) via python-docx with official QNU academic heading, metadata tables, and styled sections.
3. PDF (.pdf) via Gotenberg LibreOffice conversion with resilient fallback.
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import openpyxl
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Mm, Pt, RGBColor
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.storage import storage_service
from app.modules.tools.document_generator import convert_docx_to_pdf_gotenberg

logger = logging.getLogger(__name__)
settings = get_settings()

# QNU Brand Palette
QNU_TEAL_HEX = "0D7E8A"
QNU_DARK_TEAL_HEX = "06525B"
QNU_LIGHT_TEAL_HEX = "E6F4F5"
QNU_GRAY_HEX = "F3F4F6"
QNU_BORDER_HEX = "CBD5E1"


class ReportTable(BaseModel):
    """Structured table definition for report export."""

    sheet_name: str = Field(default="Bảng dữ liệu", description="Tên Sheet trong Excel")
    table_title: str = Field(default="", description="Tiêu đề bảng biểu")
    headers: list[str] = Field(default_factory=list, description="Tiêu đề các cột")
    rows: list[list[Any]] = Field(default_factory=list, description="Dữ liệu các dòng")
    notes: str | None = Field(default=None, description="Ghi chú dưới chân bảng")


class UniversalReportPayload(BaseModel):
    """Universal payload for generating multi-format reports across AI assistants."""

    title: str = Field(..., description="Tiêu đề báo cáo / phiếu tư vấn")
    subtitle: str | None = Field(default=None, description="Phụ đề hoặc đơn vị phụ trách")
    issuing_unit: str = Field(default="TRƯỜNG ĐẠI HỌC QUY NHƠN", description="Đơn vị ban hành / Tư vấn")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Thông tin hồ sơ (Thí sinh, Khối, Điểm, Ngày...)")
    summary_paragraphs: list[str] = Field(default_factory=list, description="Các đoạn văn nhận xét, phân tích, tóm tắt")
    tables: list[ReportTable] = Field(default_factory=list, description="Danh sách các bảng biểu số liệu")
    formats: list[str] = Field(default_factory=lambda: ["xlsx", "docx", "pdf"], description="Danh sách định dạng cần xuất")
    base_name: str | None = Field(default=None, description="Tên file cơ sở (không đuôi)")


def _safe_slug(text: str) -> str:
    """Generate safe ASCII/alphanumeric slug for filenames."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"[^\w\-]+", "_", normalized).strip("_")
    return clean[:40].lower() or "qnu_report"


def _set_cell_background(cell: Any, fill_hex: str) -> None:
    """Apply background color to python-docx table cell."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def _set_cell_margins(cell: Any, top: int = 120, bottom: int = 120, left: int = 160, right: int = 160) -> None:
    """Set internal cell margins (padding) in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table: Any, color: str = "CBD5E1") -> None:
    """Set clean thin borders for python-docx table."""
    tblPr = table._tbl.tblPr
    borders_elm = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders_elm)


# ==============================================================================
# 1. EXCEL (.XLSX) GENERATOR
# ==============================================================================

def generate_excel_report(payload: UniversalReportPayload) -> bytes:
    """Generate high-quality Excel spreadsheet with QNU branding and auto-fitted columns."""
    wb = openpyxl.Workbook()
    # Remove default sheet if we have custom tables
    default_sheet = wb.active

    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_meta_key = Font(name="Calibri", size=10, bold=True, color="334155")
    font_meta_val = Font(name="Calibri", size=10, color="0F172A")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_body = Font(name="Calibri", size=10, color="0F172A")
    font_body_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_note = Font(name="Calibri", size=9, italic=True, color="64748B")

    fill_teal_header = PatternFill(start_color=QNU_TEAL_HEX, end_color=QNU_TEAL_HEX, fill_type="solid")
    fill_dark_header = PatternFill(start_color=QNU_DARK_TEAL_HEX, end_color=QNU_DARK_TEAL_HEX, fill_type="solid")
    fill_light_meta = PatternFill(start_color=QNU_LIGHT_TEAL_HEX, end_color=QNU_LIGHT_TEAL_HEX, fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border_side = Side(border_style="thin", color=QNU_BORDER_HEX)
    cell_border = Border(top=thin_border_side, bottom=thin_border_side, left=thin_border_side, right=thin_border_side)

    # Highlight styles for admissions chance zones
    fill_safe = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")      # Green
    fill_target = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")    # Yellow
    fill_reach = PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid")     # Orange

    tables = payload.tables or [
        ReportTable(sheet_name="Báo cáo", table_title=payload.title, headers=["Nội dung"], rows=[[p] for p in payload.summary_paragraphs])
    ]

    for t_idx, table in enumerate(tables):
        sheet_title = re.sub(r"[\\/*?:\[\]]", "_", table.sheet_name)[:30] or f"Sheet_{t_idx + 1}"
        if t_idx == 0:
            ws = default_sheet
            ws.title = sheet_title
        else:
            ws = wb.create_sheet(title=sheet_title)

        ws.views.sheetView[0].showGridLines = True

        # Row 1-2: Banner Title
        max_cols = max(len(table.headers), 6)
        ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=max_cols)
        title_cell = ws.cell(row=1, column=1, value=f"{payload.issuing_unit}\n{payload.title.upper()}")
        title_cell.font = font_title
        title_cell.fill = fill_dark_header
        title_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        current_row = 4

        # Metadata Section (only on first sheet or if table metadata is present)
        if t_idx == 0 and payload.metadata:
            ws.cell(row=current_row, column=1, value="THÔNG TIN HỒ SƠ TƯ VẤN:").font = font_body_bold
            current_row += 1
            meta_items = list(payload.metadata.items())
            for i in range(0, len(meta_items), 2):
                k1, v1 = meta_items[i]
                ws.cell(row=current_row, column=1, value=f"{k1}:").font = font_meta_key
                ws.cell(row=current_row, column=1).fill = fill_light_meta
                c1 = ws.cell(row=current_row, column=2, value=str(v1))
                c1.font = font_meta_val

                if i + 1 < len(meta_items):
                    k2, v2 = meta_items[i + 1]
                    ws.cell(row=current_row, column=3, value=f"{k2}:").font = font_meta_key
                    ws.cell(row=current_row, column=3).fill = fill_light_meta
                    c2 = ws.cell(row=current_row, column=4, value=str(v2))
                    c2.font = font_meta_val
                current_row += 1
            current_row += 1

        # Summary Paragraphs
        if t_idx == 0 and payload.summary_paragraphs:
            for p in payload.summary_paragraphs:
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=max_cols)
                p_cell = ws.cell(row=current_row, column=1, value=f"• {p}")
                p_cell.font = font_body
                p_cell.alignment = Alignment(wrap_text=True)
                current_row += 1
            current_row += 1

        # Table Header
        if table.table_title:
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=len(table.headers))
            tb_title_cell = ws.cell(row=current_row, column=1, value=table.table_title.upper())
            tb_title_cell.font = Font(name="Calibri", size=11, bold=True, color=QNU_TEAL_HEX)
            tb_title_cell.alignment = Alignment(horizontal="left", vertical="center")
            current_row += 1

        header_row = current_row
        for col_idx, h_text in enumerate(table.headers, start=1):
            cell = ws.cell(row=header_row, column=col_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_teal_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cell_border
        ws.row_dimensions[header_row].height = 28
        current_row += 1

        # Table Data Rows
        for r_idx, row_values in enumerate(table.rows):
            is_even = r_idx % 2 == 1
            ws.row_dimensions[current_row].height = 20
            for col_idx, val in enumerate(row_values, start=1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.font = font_body
                cell.border = cell_border

                # Formats and alignments
                if isinstance(val, (int, float)):
                    cell.value = val
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    str_val = str(val or "")
                    cell.value = str_val
                    # Align numbers / codes in center, text on left
                    if len(str_val) <= 10 or str_val.isdigit():
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

                    # Highlight admission zones
                    val_lower = str_val.lower()
                    if "an toàn" in val_lower or "safe" in val_lower:
                        cell.fill = fill_safe
                        cell.font = font_body_bold
                    elif "mục tiêu" in val_lower or "target" in val_lower or "vừa sức" in val_lower:
                        cell.fill = fill_target
                        cell.font = font_body_bold
                    elif "thử thách" in val_lower or "mạo hiểm" in val_lower or "reach" in val_lower:
                        cell.fill = fill_reach
                        cell.font = font_body_bold
                    elif is_even:
                        cell.fill = fill_zebra

            current_row += 1

        # Table Footer Notes
        if table.notes:
            current_row += 1
            ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=len(table.headers))
            n_cell = ws.cell(row=current_row, column=1, value=f"* Ghi chú: {table.notes}")
            n_cell.font = font_note
            n_cell.alignment = Alignment(wrap_text=True)

        # Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row < header_row:
                    continue  # Ignore merged header rows for width calculation
                val_str = str(cell.value or "")
                if val_str:
                    lines = val_str.split("\n")
                    max_len = max(max_len, max(len(l) for l in lines))
            ws.column_dimensions[col_letter].width = max(min(max_len + 4, 45), 10)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ==============================================================================
# 2. WORD (.DOCX) GENERATOR
# ==============================================================================

def generate_docx_report(payload: UniversalReportPayload) -> bytes:
    """Generate professional Word document with official QNU header and styled tables."""
    doc = Document()

    # Standard A4 Page Setup: 20mm margins
    for section in doc.sections:
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(25)
        section.right_margin = Mm(20)
        section.header_distance = Mm(12.7)
        section.footer_distance = Mm(12.7)

    # 1. Official Header Block (Two columns: Unit & Motto)
    head_table = doc.add_table(rows=1, cols=2)
    head_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    head_table.autofit = False

    cell_left, cell_right = head_table.rows[0].cells
    cell_left.width = Mm(85)
    cell_right.width = Mm(80)

    # Left: Issuing Unit
    p_left = cell_left.paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_left.paragraph_format.line_spacing = 1.15
    p_left.paragraph_format.space_after = Pt(2)
    r1 = p_left.add_run("BỘ GIÁO DỤC VÀ ĐÀO TẠO\n")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(10)
    r2 = p_left.add_run(payload.issuing_unit.upper() + "\n")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(11)
    r2.font.bold = True
    r2.font.color.rgb = RGBColor(13, 126, 138)  # QNU Teal
    r3 = p_left.add_run("TRỢ LÝ ẢO TƯ VẤN THÔNG MINH\n")
    r3.font.name = "Times New Roman"
    r3.font.size = Pt(9.5)
    r3.font.italic = True

    # Right: National Motto
    p_right = cell_right.paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_right.paragraph_format.line_spacing = 1.15
    p_right.paragraph_format.space_after = Pt(2)
    r_m1 = p_right.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
    r_m1.font.name = "Times New Roman"
    r_m1.font.size = Pt(10)
    r_m1.font.bold = True
    r_m2 = p_right.add_run("Độc lập - Tự do - Hạnh phúc\n")
    r_m2.font.name = "Times New Roman"
    r_m2.font.size = Pt(11)
    r_m2.font.bold = True
    r_m3 = p_right.add_run(f"Quy Nhơn, ngày {datetime.now(UTC).strftime('%d')} tháng {datetime.now(UTC).strftime('%m')} năm {datetime.now(UTC).strftime('%Y')}")
    r_m3.font.name = "Times New Roman"
    r_m3.font.size = Pt(9.5)
    r_m3.font.italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 2. Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run(payload.title.upper())
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(15)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(13, 126, 138)

    if payload.subtitle:
        p_sub = doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sub.paragraph_format.space_after = Pt(12)
        run_sub = p_sub.add_run(payload.subtitle)
        run_sub.font.name = "Times New Roman"
        run_sub.font.size = Pt(11)
        run_sub.font.italic = True

    # 3. Metadata Card (Table with soft teal background)
    if payload.metadata:
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        meta_table = doc.add_table(rows=0, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(meta_table, color="0D7E8A")

        for key, val in payload.metadata.items():
            row = meta_table.add_row()
            c_k, c_v = row.cells
            c_k.width = Mm(50)
            c_v.width = Mm(115)
            _set_cell_background(c_k, QNU_LIGHT_TEAL_HEX)
            _set_cell_margins(c_k, top=60, bottom=60, left=100, right=100)
            _set_cell_margins(c_v, top=60, bottom=60, left=100, right=100)

            pk = c_k.paragraphs[0]
            pk.paragraph_format.space_after = Pt(0)
            rk = pk.add_run(f"• {key}:")
            rk.font.name = "Times New Roman"
            rk.font.size = Pt(10.5)
            rk.font.bold = True

            pv = c_v.paragraphs[0]
            pv.paragraph_format.space_after = Pt(0)
            rv = pv.add_run(str(val))
            rv.font.name = "Times New Roman"
            rv.font.size = Pt(10.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 4. Summary / Strategic Evaluation Paragraphs
    if payload.summary_paragraphs:
        p_h = doc.add_paragraph()
        p_h.paragraph_format.space_before = Pt(8)
        p_h.paragraph_format.space_after = Pt(4)
        run_h = p_h.add_run("I. ĐÁNH GIÁ & NHẬN XÉT CHIẾN LƯỢC")
        run_h.font.name = "Times New Roman"
        run_h.font.size = Pt(12)
        run_h.font.bold = True
        run_h.font.color.rgb = RGBColor(6, 82, 91)

        for p_text in payload.summary_paragraphs:
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.2
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.first_line_indent = Mm(8)
            run_body = p.add_run(p_text)
            run_body.font.name = "Times New Roman"
            run_body.font.size = Pt(11)

    # 5. Tables Section
    roman_numerals = ["II", "III", "IV", "V", "VI"]
    for t_idx, table in enumerate(payload.tables):
        sec_num = roman_numerals[min(t_idx, len(roman_numerals) - 1)]
        title_text = table.table_title or f"Bảng dữ liệu {t_idx + 1}"

        p_tb_h = doc.add_paragraph()
        p_tb_h.paragraph_format.space_before = Pt(12)
        p_tb_h.paragraph_format.space_after = Pt(4)
        run_tb_h = p_tb_h.add_run(f"{sec_num}. {title_text.upper()}")
        run_tb_h.font.name = "Times New Roman"
        run_tb_h.font.size = Pt(12)
        run_tb_h.font.bold = True
        run_tb_h.font.color.rgb = RGBColor(6, 82, 91)

        if not table.headers:
            continue

        doc_table = doc.add_table(rows=1, cols=len(table.headers))
        doc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(doc_table, color="CBD5E1")

        # Header Row
        hdr_row = doc_table.rows[0]
        for col_idx, h_text in enumerate(table.headers):
            cell = hdr_row.cells[col_idx]
            _set_cell_background(cell, QNU_TEAL_HEX)
            _set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(h_text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)

        # Data Rows
        for r_idx, row_data in enumerate(table.rows):
            row = doc_table.add_row()
            is_even = r_idx % 2 == 1
            for col_idx, val in enumerate(row_data):
                cell = row.cells[col_idx]
                _set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                str_val = str(val or "")
                run = p.add_run(str_val)
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)

                # Format alignment
                if len(str_val) <= 10 or str_val.isdigit():
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                # Highlight admission zones
                val_lower = str_val.lower()
                if "an toàn" in val_lower or "safe" in val_lower:
                    _set_cell_background(cell, "DCFCE7")
                    run.font.bold = True
                elif "mục tiêu" in val_lower or "target" in val_lower:
                    _set_cell_background(cell, "FEF9C3")
                    run.font.bold = True
                elif "thử thách" in val_lower or "reach" in val_lower:
                    _set_cell_background(cell, "FFEDD5")
                    run.font.bold = True
                elif is_even:
                    _set_cell_background(cell, "F8FAFC")

        # Table Notes
        if table.notes:
            p_n = doc.add_paragraph()
            p_n.paragraph_format.space_before = Pt(3)
            p_n.paragraph_format.space_after = Pt(6)
            run_n = p_n.add_run(f"* Ghi chú: {table.notes}")
            run_n.font.name = "Times New Roman"
            run_n.font.size = Pt(9.5)
            run_n.font.italic = True
            run_n.font.color.rgb = RGBColor(100, 116, 139)

    # 6. Footer Disclaimer & Contact
    doc.add_paragraph().paragraph_format.space_before = Pt(16)
    p_ft = doc.add_paragraph()
    p_ft.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ft1 = p_ft.add_run("Bản báo cáo này được tạo tự động bởi Hệ thống QNU AI Platform dựa trên Đề án tuyển sinh chính thức.\n")
    r_ft1.font.name = "Times New Roman"
    r_ft1.font.size = Pt(9.5)
    r_ft1.font.italic = True
    r_ft2 = p_ft.add_run("Mọi thắc mắc vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU — Hotline: 0256.3846.156 | Email: tuyensinh@qnu.edu.vn")
    r_ft2.font.name = "Times New Roman"
    r_ft2.font.size = Pt(9.5)
    r_ft2.font.bold = True
    r_ft2.font.color.rgb = RGBColor(13, 126, 138)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ==============================================================================
# 3. UNIVERSAL REPORT EXPORTER ENGINE (EXCEL + WORD + PDF)
# ==============================================================================

async def export_universal_report(payload: UniversalReportPayload) -> list[dict[str, Any]]:
    """Export report into all requested formats (.xlsx, .docx, .pdf), persist to Storage, and return artifacts."""
    target_formats = [f.lower().strip() for f in (payload.formats or ["xlsx", "docx", "pdf"])]
    if "all" in target_formats or "both" in target_formats:
        target_formats = ["xlsx", "docx", "pdf"]

    time_tag = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    clean_slug = _safe_slug(payload.base_name or payload.title)
    base_filename = f"{clean_slug}_{time_tag}"

    artifacts: list[dict[str, Any]] = []

    # 1. EXCEL (.XLSX)
    if "xlsx" in target_formats or "excel" in target_formats:
        try:
            xlsx_bytes = generate_excel_report(payload)
            xlsx_filename = f"{base_filename}.xlsx"
            xlsx_rel_path = f"artifacts/{xlsx_filename}"
            await storage_service.save(xlsx_rel_path, xlsx_bytes)
            artifacts.append(
                {
                    "id": f"art_xlsx_{uuid.uuid4().hex[:8]}",
                    "name": xlsx_filename,
                    "type": "xlsx",
                    "size": len(xlsx_bytes),
                    "url": f"/platform/v1alpha1/tools/artifacts/{quote(xlsx_filename, safe='')}",
                    "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
            )
            logger.info("Successfully exported Excel artifact '%s' (%d bytes)", xlsx_filename, len(xlsx_bytes))
        except Exception:
            logger.exception("Failed to generate Excel report")

    # 2. WORD (.DOCX) - Always generated if DOCX or PDF requested
    docx_bytes: bytes | None = None
    if "docx" in target_formats or "word" in target_formats or "pdf" in target_formats:
        try:
            docx_bytes = generate_docx_report(payload)
            if "docx" in target_formats or "word" in target_formats:
                docx_filename = f"{base_filename}.docx"
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
                    }
                )
                logger.info("Successfully exported Word artifact '%s' (%d bytes)", docx_filename, len(docx_bytes))
        except Exception:
            logger.exception("Failed to generate Word report")

    # 3. PDF (.PDF) - Converted from DOCX via Gotenberg
    if "pdf" in target_formats and docx_bytes:
        try:
            pdf_bytes = await convert_docx_to_pdf_gotenberg(docx_bytes, f"{base_filename}.docx")
            if pdf_bytes:
                pdf_filename = f"{base_filename}.pdf"
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
                    }
                )
                logger.info("Successfully exported PDF artifact '%s' via Gotenberg (%d bytes)", pdf_filename, len(pdf_bytes))
            else:
                logger.warning("Gotenberg returned no PDF bytes for '%s'; graceful fallback active", base_filename)
        except Exception as exc:
            logger.warning("Gotenberg PDF conversion exception for '%s': %s", base_filename, exc)

    return artifacts
