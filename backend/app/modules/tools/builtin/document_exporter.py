"""Document Exporter Tool — Generates Word .docx files complying with Decree 30/2020/ND-CP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

from app.core.config import settings
from app.modules.tools.builtin.base import BaseTool


class DocumentExporterTool(BaseTool):
    """Tool that formats administrative text into a formal .docx file based on Decree 30/2020/ND-CP."""

    @property
    def name(self) -> str:
        return "export_administrative_document"

    @property
    def display_name(self) -> str:
        return "Xuất Văn bản Hành chính Word (.docx) Chuẩn NĐ 30"

    @property
    def description(self) -> str:
        return (
            "Tạo và định dạng tệp Word (.docx) văn bản hành chính (Thông báo, Tờ trình, Quyết định) "
            "tuân thủ nghiêm ngặt thể thức và kỹ thuật trình bày theo Nghị định 30/2020/NĐ-CP của Chính phủ."
        )

    @property
    def category(self) -> str:
        return "drafting"

    def get_openapi_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "enum": ["THÔNG BÁO", "TỜ TRÌNH", "KẾ HOẠCH", "QUYẾT ĐỊNH"],
                        "description": "Tên loại văn bản",
                    },
                    "title": {
                        "type": "string",
                        "description": "Trích yếu nội dung văn bản (Về việc...)",
                    },
                    "body_paragraphs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Danh sách các đoạn văn nội dung",
                    },
                    "signer_title": {
                        "type": "string",
                        "description": "Chức vụ người ký (ví dụ: HIỆU TRƯỞNG, TRƯỞNG KHOA)",
                        "default": "HIỆU TRƯỞNG",
                    },
                    "signer_name": {
                        "type": "string",
                        "description": "Họ và tên người ký",
                        "default": "PGS.TS. Đỗ Ngọc Mỹ",
                    },
                    "recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Nơi nhận văn bản",
                        "default": ["Như Điều 3", "Lưu: VT, ĐT."],
                    },
                },
                "required": ["document_type", "title", "body_paragraphs"],
            },
        }

    async def execute(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        doc_type = parameters.get("document_type", "THÔNG BÁO").upper()
        title = parameters.get("title", "Về việc triển khai công tác đào tạo")
        paragraphs = parameters.get("body_paragraphs", [])
        signer_title = parameters.get("signer_title", "HIỆU TRƯỞNG")
        signer_name = parameters.get("signer_name", "PGS.TS. Đỗ Ngọc Mỹ")
        recipients = parameters.get("recipients", ["Như Điều 3", "Lưu: VT, ĐT."])

        # Create DOCX Document
        doc = docx.Document()

        # Set Standard Margins (Top: 2cm, Bottom: 2cm, Left: 3cm, Right: 1.5cm according to ND 30)
        sections = doc.sections
        for s in sections:
            s.top_margin = Inches(0.79)
            s.bottom_margin = Inches(0.79)
            s.left_margin = Inches(1.18)
            s.right_margin = Inches(0.59)

        # 1. Header Table (Left: Issuing Agency; Right: National Motto)
        header_table = doc.add_table(rows=2, cols=2)
        header_table.autofit = True

        # Left Header
        cell_agency = header_table.cell(0, 0)
        p_agency = cell_agency.paragraphs[0]
        p_agency.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_parent = p_agency.add_run("BỘ GIÁO DỤC VÀ ĐÀO TẠO\n")
        run_parent.font.size = Pt(12)
        run_parent.font.name = "Times New Roman"
        run_qnu = p_agency.add_run("TRƯỜNG ĐẠI HỌC QUY NHƠN")
        run_qnu.bold = True
        run_qnu.font.size = Pt(12)
        run_qnu.font.name = "Times New Roman"

        cell_number = header_table.cell(1, 0)
        p_num = cell_number.paragraphs[0]
        p_num.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_num = p_num.add_run("Số: ... /TB-ĐHQN")
        run_num.italic = True
        run_num.font.size = Pt(12)

        # Right Header (Motto)
        cell_motto = header_table.cell(0, 1)
        p_motto = cell_motto.paragraphs[0]
        p_motto.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_country = p_motto.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
        run_country.bold = True
        run_country.font.size = Pt(12)
        run_motto = p_motto.add_run("Độc lập - Tự do - Hạnh phúc")
        run_motto.bold = True
        run_motto.font.size = Pt(13)

        cell_date = header_table.cell(1, 1)
        p_date = cell_date.paragraphs[0]
        p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_date = p_date.add_run("Quy Nhơn, ngày ... tháng ... năm 2026")
        run_date.italic = True
        run_date.font.size = Pt(12)

        doc.add_paragraph()

        # 2. Document Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_dt = p_title.add_run(f"{doc_type}\n")
        run_dt.bold = True
        run_dt.font.size = Pt(15)

        run_sub = p_title.add_run(f"{title}")
        run_sub.bold = True
        run_sub.font.size = Pt(13)

        doc.add_paragraph()

        # 3. Document Body
        for idx, p_text in enumerate(paragraphs, start=1):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Inches(0.4)
            p.paragraph_format.line_spacing = 1.2
            run = p.add_run(p_text)
            run.font.name = "Times New Roman"
            run.font.size = Pt(13)

        doc.add_paragraph()

        # 4. Footer Table (Left: Recipients; Right: Signer)
        footer_table = doc.add_table(rows=1, cols=2)
        cell_rec = footer_table.cell(0, 0)
        p_rec = cell_rec.paragraphs[0]
        run_rh = p_rec.add_run("Nơi nhận:\n")
        run_rh.bold = True
        run_rh.italic = True
        run_rh.font.size = Pt(11)
        for r in recipients:
            run_item = p_rec.add_run(f"- {r}\n")
            run_item.font.size = Pt(10)

        cell_sig = footer_table.cell(0, 1)
        p_sig = cell_sig.paragraphs[0]
        p_sig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_st = p_sig.add_run(f"{signer_title}\n\n\n\n")
        run_st.bold = True
        run_st.font.size = Pt(13)
        run_sn = p_sig.add_run(signer_name)
        run_sn.bold = True
        run_sn.font.size = Pt(13)

        # Save to Artifacts directory
        artifacts_dir = Path(settings.LOCAL_STORAGE_PATH) / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{doc_type.lower()}_{title[:30].strip().replace(' ', '_')}.docx"
        file_path = artifacts_dir / filename
        doc.save(str(file_path))

        return {
            "status": "generated",
            "file_name": filename,
            "file_path": str(file_path),
            "document_type": doc_type,
            "title": title,
            "standard": "Decree 30/2020/ND-CP",
            "size_bytes": file_path.stat().st_size,
        }
