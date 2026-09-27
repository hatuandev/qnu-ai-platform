"""Validate composed draft content and map it onto the QNU DOCX template contract."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.exceptions import AppException
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

_UNSUPPORTED_CITATION_RE = re.compile(
    r"\b(?:căn cứ|theo)\s+(?:nghị định|nghị quyết|quyết định|thông tư|luật)\s+(?:số\s*)?[\w./-]+",
    re.IGNORECASE,
)
_TITLE_PREFIX_RE = re.compile(r"^(?:về\s+việc\s*)+", re.IGNORECASE)
_DOCUMENT_NUMBER_SUFFIX = {
    "to_trinh": "TTr-ĐHQN",
    "thong_bao": "TB-ĐHQN",
    "quyet_dinh": "QĐ-ĐHQN",
}


def _format_date(parts: Any) -> tuple[str, str, str]:
    if isinstance(parts, list) and len(parts) == 3:
        return tuple(str(part) for part in parts)  # type: ignore[return-value]
    return "[BỔ SUNG NGÀY]", "[BỔ SUNG THÁNG]", "[BỔ SUNG NĂM]"


def _section_text(sections: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for section in sections:
        heading = str(section.get("heading", "")).strip()
        if heading:
            blocks.append(heading)
        for paragraph in section.get("paragraphs", []):
            content = str(paragraph).strip()
            if content:
                blocks.append(content)
    return "\n\n".join(blocks)


class DraftingValidationNodeHandler(BaseNodeHandler):
    """Reject malformed or fabricated legal-reference output before file generation."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        raw_draft = context.node_inputs.get(node_spec.id, {}).get("draft")
        if not isinstance(raw_draft, dict):
            raw_draft = context.node_data.get("draft")
        if not isinstance(raw_draft, dict):
            raise AppException(
                "Không nhận được bản nháp có cấu trúc từ node soạn thảo.",
                code="drafting_draft_missing",
                status_code=422,
            )

        title = _TITLE_PREFIX_RE.sub("", str(raw_draft.get("title") or "").strip()).strip(
            " :-"
        )
        sections = raw_draft.get("sections")
        plan = raw_draft.get("plan")
        if not title or not isinstance(sections, list) or not sections or not isinstance(plan, dict):
            raise AppException(
                "Bản nháp thiếu tiêu đề, nội dung hoặc kế hoạch trường dữ liệu.",
                code="drafting_draft_invalid",
                status_code=422,
            )

        explicit_fields = plan.get("explicit_fields", {})
        if not isinstance(explicit_fields, dict):
            explicit_fields = {}
        legal_basis = explicit_fields.get("legal_basis", [])
        if not isinstance(legal_basis, list):
            legal_basis = []
        source = str(plan.get("source_text", ""))
        confirmed_references = " ".join(str(value) for value in legal_basis) + " " + source
        body = _section_text(sections)
        unsupported_references = [
            reference
            for reference in _UNSUPPORTED_CITATION_RE.findall(body)
            if reference.casefold() not in confirmed_references.casefold()
        ]
        if unsupported_references:
            raise AppException(
                "Bản nháp chứa căn cứ pháp lý chưa được cung cấp. Hãy bổ sung căn cứ đã xác nhận rồi thử lại.",
                code="drafting_unverified_legal_reference",
                status_code=422,
                details={"unverified_references": unsupported_references},
            )

        document_type = str(raw_draft.get("document_type") or "to_trinh")
        suffix = _DOCUMENT_NUMBER_SUFFIX.get(document_type)
        if not suffix:
            raise AppException(
                f"Không có quy tắc số hiệu cho loại văn bản '{document_type}'.",
                code="drafting_document_type_invalid",
                status_code=422,
            )

        missing_fields = list(dict.fromkeys(
            [
                *(plan.get("missing_fields") or []),
                *(raw_draft.get("model_missing_fields") or []),
            ]
        ))
        date_day, date_month, date_year = _format_date(explicit_fields.get("date_parts"))
        recipient = explicit_fields.get("recipient") or "[BỔ SUNG ĐƠN VỊ KÍNH GỬI]"
        recipients = explicit_fields.get("recipients") or ["[BỔ SUNG NƠI NHẬN]"]
        if isinstance(recipients, str):
            recipients = [recipients]
        recipient_lines = "\n".join(f"- {value}" for value in recipients)
        legal_basis_text = "\n".join(str(value) for value in legal_basis)
        body_parts = [legal_basis_text] if legal_basis_text else [
            "[BỔ SUNG CĂN CỨ PHÁP LÝ ĐÃ ĐƯỢC XÁC NHẬN (NẾU CẦN)]"
        ]
        body_parts.append(body)
        placeholder_fields = plan.get("placeholder_fields", {})
        if isinstance(placeholder_fields, dict):
            for label, placeholder in placeholder_fields.items():
                if str(placeholder) not in body:
                    body_parts.append(f"{label}: {placeholder}")
        document_number = explicit_fields.get("document_number") or f"[CHƯA CẤP SỐ]/{suffix}"

        context_data = {
            "is_draft": True,
            "so_hieu": document_number,
            "ngay": date_day,
            "thang": date_month,
            "nam": date_year,
            "ngay_thang": f"ngày {date_day} tháng {date_month} năm {date_year}",
            "don_vi_ban_hanh": explicit_fields.get("issuer") or "TRƯỜNG ĐẠI HỌC QUY NHƠN",
            "kinh_gui": recipient,
            "trich_yeu": title,
            "noi_dung": "\n\n".join(part for part in body_parts if part),
            "noi_nhan": recipient_lines,
            "chuc_vu_nguoi_ky": explicit_fields.get("signer_position") or "[BỔ SUNG CHỨC VỤ NGƯỜI KÝ]",
            "ho_ten_nguoi_ky": explicit_fields.get("signer_name") or "[BỔ SUNG HỌ TÊN NGƯỜI KÝ]",
            "can_cu_phap_ly": legal_basis_text or "[BỔ SUNG CĂN CỨ PHÁP LÝ ĐÃ ĐƯỢC XÁC NHẬN (NẾU CẦN)]",
        }
        validated_draft = {
            **raw_draft,
            "title": title,
            "missing_fields": missing_fields,
            "context": context_data,
        }
        context.node_data["draft"] = validated_draft
        context.node_data["missing_fields"] = missing_fields
        context.node_data["assistant_status"] = "draft_created"
        missing_summary = (
            "\n\nThông tin cần rà soát/bổ sung: " + "; ".join(missing_fields)
            if missing_fields
            else ""
        )
        context.node_data["llm_content"] = (
            f"Đã tạo bản nháp {raw_draft.get('document_type_label') or document_type}: **{title}**. "
            "Tệp được đánh dấu là dự thảo, chưa được phê duyệt hoặc ban hành."
            f"{missing_summary}"
        )
        logger.info(
            "Draft validation [%s]: type=%s section_count=%d missing_field_count=%d",
            node_spec.id,
            document_type,
            len(sections),
            len(missing_fields),
        )
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"draft": validated_draft, "missing_fields": missing_fields},
        )
