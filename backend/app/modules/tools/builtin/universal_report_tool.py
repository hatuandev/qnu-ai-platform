"""Universal Report & Multi-format Document Export Tool — QNU AI Platform.

Enables any AI Assistant across the platform to export structured consulting reports,
data sheets, and guidelines into Excel (.xlsx), Word (.docx), and PDF (.pdf) via Gotenberg.
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.tools.builtin.base import BaseTool
from app.modules.tools.universal_report import (
    ReportTable,
    UniversalReportPayload,
    export_universal_report,
)

logger = logging.getLogger(__name__)


class UniversalReportExportTool(BaseTool):
    """Platform-wide generic tool for exporting reports to Excel, Word, and PDF."""

    @property
    def name(self) -> str:
        return "export_universal_report"

    @property
    def display_name(self) -> str:
        return "Kỹ năng Kết Xuất Báo Cáo Đa Định Dạng (Excel, Word, PDF)"

    @property
    def description(self) -> str:
        return (
            "Tự động tạo và xuất tài liệu, báo cáo tư vấn, bảng tổng hợp dữ liệu "
            "thành các tệp tải về định dạng Excel (.xlsx), Word (.docx) và PDF (.pdf) "
            "với phong cách chuẩn nhận diện học thuật Trường Đại học Quy Nhơn."
        )

    @property
    def category(self) -> str:
        return "export"

    def get_openapi_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề chính của báo cáo hoặc tài liệu cần kết xuất",
                    },
                    "subtitle": {
                        "type": "string",
                        "description": "Tiêu đề phụ hoặc ngữ cảnh (ví dụ: Trường Đại học Quy Nhơn — Hệ Thống Trợ Lý AI)",
                        "default": "Trường Đại học Quy Nhơn — Nền Tảng Trí Tuệ Nhân Tạo QNU AI",
                    },
                    "issuing_unit": {
                        "type": "string",
                        "description": "Tên cơ quan hoặc đơn vị ban hành báo cáo",
                        "default": "TRƯỜNG ĐẠI HỌC QUY NHƠN",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Các thông tin tóm lược dạng cặp khóa - giá trị (ví dụ: Người lập, Ngày xuất, Hotline...)",
                        "default": {},
                    },
                    "summary_paragraphs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Các đoạn văn bản nội dung tóm tắt, đánh giá, phân tích chiến lược hoặc lời khuyên tư vấn",
                        "default": [],
                    },
                    "tables": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sheet_name": {"type": "string", "default": "Dữ liệu"},
                                "table_title": {"type": "string"},
                                "headers": {"type": "array", "items": {"type": "string"}},
                                "rows": {
                                    "type": "array",
                                    "items": {"type": "array", "items": {}},
                                },
                                "notes": {"type": "string", "default": ""},
                            },
                            "required": ["headers", "rows"],
                        },
                        "description": "Danh sách các bảng số liệu chi tiết cần đóng khung và kẻ dòng trong báo cáo",
                        "default": [],
                    },
                    "formats": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["xlsx", "docx", "pdf"]},
                        "description": "Danh sách các định dạng tệp cần xuất (xlsx, docx, pdf)",
                        "default": ["xlsx", "docx", "pdf"],
                    },
                    "base_name": {
                        "type": "string",
                        "description": "Tên gốc của file không bao gồm phần mở rộng (tiếng Việt không dấu hoặc tiếng Anh)",
                        "default": "bao_cao_tu_van_qnu",
                    },
                },
                "required": ["title"],
            },
        }

    async def execute(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        title = parameters.get("title") or "Báo Cáo Tổng Hợp Thông Tin QNU"
        subtitle = parameters.get("subtitle") or "Trường Đại học Quy Nhơn — Nền Tảng Trí Tuệ Nhân Tạo QNU AI"
        issuing_unit = parameters.get("issuing_unit") or "TRƯỜNG ĐẠI HỌC QUY NHƠN"
        metadata = parameters.get("metadata") or {}
        summary_paragraphs = parameters.get("summary_paragraphs") or []
        formats = parameters.get("formats") or ["xlsx", "docx", "pdf"]
        base_name = parameters.get("base_name") or "bao_cao_tu_van_qnu"

        # Construct Report Tables
        raw_tables = parameters.get("tables") or []
        report_tables: list[ReportTable] = []
        for t in raw_tables:
            report_tables.append(
                ReportTable(
                    sheet_name=t.get("sheet_name", "Dữ liệu"),
                    table_title=t.get("table_title", ""),
                    headers=t.get("headers", []),
                    rows=t.get("rows", []),
                    notes=t.get("notes", ""),
                )
            )

        payload = UniversalReportPayload(
            title=title,
            subtitle=subtitle,
            issuing_unit=issuing_unit,
            metadata=metadata,
            summary_paragraphs=summary_paragraphs,
            tables=report_tables,
            formats=formats,
            base_name=base_name,
        )

        artifacts = await export_universal_report(payload)

        docx_art = next((a for a in artifacts if a["type"] == "docx"), None)
        pdf_art = next((a for a in artifacts if a["type"] == "pdf"), None)
        xlsx_art = next((a for a in artifacts if a["type"] == "xlsx"), None)

        return {
            "status": "success",
            "artifacts": artifacts,
            "total_files": len(artifacts),
            "docx_url": docx_art["url"] if docx_art else None,
            "pdf_url": pdf_art["url"] if pdf_art else None,
            "xlsx_url": xlsx_art["url"] if xlsx_art else None,
            "message": f"Đã kết xuất thành công {len(artifacts)} tệp báo cáo ({', '.join(formats)}) để tải về.",
        }
