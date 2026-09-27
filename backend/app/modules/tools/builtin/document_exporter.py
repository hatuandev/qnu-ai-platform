"""Document Exporter Tool — Generates Word .docx files complying with Decree 30/2020/ND-CP."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.modules.document_types.catalog import get_document_type_label, normalize_document_type_code
from app.modules.tools.builtin.base import BaseTool

settings = get_settings()


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
            "theo mẫu DOCX QNU đã cấu hình cho Nghị định 30/2020/NĐ-CP."
        )

    @property
    def category(self) -> str:
        return "drafting"

    @property
    def requires_approval(self) -> bool:
        """Kích hoạt phê duyệt Human-in-the-loop trước khi xuất tệp văn bản chính thức."""
        return True

    def get_openapi_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "enum": ["to_trinh", "thong_bao", "quyet_dinh"],
                        "description": "Mã loại văn bản trong taxonomy qnu-ai-core",
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
                    },
                    "signer_name": {
                        "type": "string",
                        "description": "Họ và tên người ký",
                    },
                    "recipients": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Nơi nhận văn bản",
                    },
                },
                "required": ["document_type", "title", "body_paragraphs"],
            },
        }

    async def execute(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        requested_doc_type = str(parameters.get("document_type") or "thong_bao")
        doc_type_code = normalize_document_type_code(requested_doc_type)
        if not doc_type_code:
            raise AppException(
                f"Loại văn bản không được hỗ trợ: {requested_doc_type}",
                code="document_type_invalid",
                details={"document_type": requested_doc_type},
            )
        if doc_type_code not in {"to_trinh", "thong_bao", "quyet_dinh"}:
            raise AppException(
                "Chưa có mẫu DOCX QNU được cấu hình cho loại văn bản này. Hiện hỗ trợ Tờ trình, Thông báo và Quyết định.",
                code="document_template_not_supported",
                details={"document_type": doc_type_code},
            )
        doc_type = get_document_type_label(doc_type_code) or requested_doc_type
        title = parameters.get("title", "[BỔ SUNG TRÍCH YẾU]")
        paragraphs = parameters.get("body_paragraphs", [])
        signer_title = parameters.get("signer_title", "[BỔ SUNG CHỨC VỤ NGƯỜI KÝ]")
        signer_name = parameters.get("signer_name", "[BỔ SUNG HỌ TÊN NGƯỜI KÝ]")
        recipients = parameters.get("recipients", ["[BỔ SUNG NƠI NHẬN]"])

        from app.modules.tools.document_generator import export_document_package

        content_body = (
            "\n\n".join(paragraphs)
            if isinstance(paragraphs, list)
            else str(paragraphs or "[BỔ SUNG NỘI DUNG DỰ THẢO]")
        )
        recipients_str = (
            "\n".join(f"- {r}" for r in recipients)
            if isinstance(recipients, list)
            else str(recipients or "- [BỔ SUNG NƠI NHẬN]")
        )

        context_data = {
            "trich_yeu": title,
            "noi_dung": content_body,
            "chuc_vu_nguoi_ky": signer_title,
            "ho_ten_nguoi_ky": signer_name,
            "noi_nhan": recipients_str,
            "don_vi_ban_hanh": parameters.get("issuing_unit", "TRƯỜNG ĐẠI HỌC QUY NHƠN"),
            "so_hieu": parameters.get("document_number", "[CHƯA CẤP SỐ VĂN BẢN]"),
            "is_draft": True,
        }

        formats = parameters.get("formats", ["docx", "pdf"])
        clean_title = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title[:30].strip())
        base_name = f"{doc_type_code}_{clean_title}"

        artifacts = await export_document_package(
            template_code=doc_type_code,
            context=context_data,
            formats=formats if isinstance(formats, list) else ["docx", "pdf"],
            base_name=base_name,
        )

        docx_art = next((a for a in artifacts if a["type"] == "docx"), None)
        pdf_art = next((a for a in artifacts if a["type"] == "pdf"), None)

        return {
            "status": "generated",
            "document_type": doc_type,
            "document_type_code": doc_type_code,
            "title": title,
            "standard": "Decree 30/2020/ND-CP",
            "artifacts": artifacts,
            "docx_url": docx_art["url"] if docx_art else None,
            "pdf_url": pdf_art["url"] if pdf_art else None,
            "size_bytes": docx_art["size"] if docx_art else 0,
            "file_name": docx_art["name"] if docx_art else f"{base_name}.docx",
        }
