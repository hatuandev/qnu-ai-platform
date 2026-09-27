"""Finalize a grounded document AST for the QNU DOCX template contract."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.exceptions import AppException
from app.modules.document_types.catalog import normalize_document_type_code
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.nodes.drafting_contracts import (
    DocumentAst,
    render_document_blocks,
    semantic_quality_issues,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

_UNSUPPORTED_CITATION_RE = re.compile(
    r"\b(?:căn cứ|theo)\s+(?:nghị định|nghị quyết|quyết định|thông tư|luật)\s+(?:số\s*)?[\w./-]+",
    re.IGNORECASE,
)
_CITATION_PREFIX_RE = re.compile(r"^\s*(?:căn\s+cứ|theo)\s+", re.IGNORECASE)
_TITLE_PREFIX_RE = re.compile(r"^(?:về\s+việc\s*)+", re.IGNORECASE)
_REQUEST_SUBJECT_RE = re.compile(r"\bvề\s+việc\s+([^\n.]+)", re.IGNORECASE)
_DOCUMENT_NUMBER_SUFFIX = {
    "to_trinh": "TTr-ĐHQN",
    "thong_bao": "TB-ĐHQN",
    "quyet_dinh": "QĐ-ĐHQN",
    "ke_hoach": "KH-ĐHQN",
}


def _format_date(parts: Any) -> tuple[str, str, str]:
    if isinstance(parts, list) and len(parts) == 3:
        return tuple(str(part) for part in parts)  # type: ignore[return-value]
    return "[BỔ SUNG NGÀY]", "[BỔ SUNG THÁNG]", "[BỔ SUNG NĂM]"


class DraftingValidationNodeHandler(BaseNodeHandler):
    """Enforce semantic obligations and grounded legal references before rendering."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        raw_draft = context.node_inputs.get(node_spec.id, {}).get("draft")
        if not isinstance(raw_draft, dict):
            raw_draft = context.node_data.get("drafting_draft")
        if not isinstance(raw_draft, dict) or not isinstance(raw_draft.get("ast"), dict):
            raise AppException(
                "Không nhận được document_ast.v1 từ node soạn thảo.",
                code="drafting_draft_missing",
                status_code=422,
            )

        ast = DocumentAst.model_validate(raw_draft["ast"])
        plan = raw_draft.get("plan")
        if not isinstance(plan, dict):
            raise AppException(
                "Bản nháp thiếu tiêu đề hoặc kế hoạch dữ kiện.",
                code="drafting_draft_invalid",
                status_code=422,
            )
        source = str(plan.get("source_text", ""))
        document_type = str(raw_draft.get("document_type") or "to_trinh")
        title = _TITLE_PREFIX_RE.sub("", ast.title).strip(" :-")
        if normalize_document_type_code(title) in _DOCUMENT_NUMBER_SUFFIX:
            subject_match = _REQUEST_SUBJECT_RE.search(source)
            title = subject_match.group(1).strip(" :-") if subject_match else title
        if not title:
            raise AppException(
                "Bản nháp thiếu trích yếu văn bản.",
                code="drafting_draft_invalid",
                status_code=422,
            )

        obligations = [str(item) for item in plan.get("semantic_obligations", [])]
        quality_issues = semantic_quality_issues(ast, obligations)
        if quality_issues:
            raise AppException(
                "Bản nháp chưa đáp ứng các nghĩa bắt buộc của loại văn bản.",
                code="drafting_semantic_quality_failed",
                status_code=502,
                details={"quality_issues": quality_issues},
            )

        explicit_fields = plan.get("explicit_fields", {})
        if not isinstance(explicit_fields, dict):
            explicit_fields = {}
        legal_basis = explicit_fields.get("legal_basis", [])
        if not isinstance(legal_basis, list):
            legal_basis = []
        reference_profile = plan.get("reference_profile", {})
        reference_text = (
            str(reference_profile.get("reference_text", ""))
            if isinstance(reference_profile, dict)
            else ""
        )
        confirmed_references = " ".join(str(value) for value in legal_basis)
        confirmed_references = f"{confirmed_references} {source} {reference_text}"
        normalized_confirmed_references = re.sub(
            r"\s+", " ", confirmed_references
        ).casefold()
        body = render_document_blocks(ast.blocks)
        unsupported_references = [
            reference
            for reference in _UNSUPPORTED_CITATION_RE.findall(body)
            if not any(
                candidate.casefold() in normalized_confirmed_references
                for candidate in (
                    reference,
                    _CITATION_PREFIX_RE.sub("", reference),
                )
            )
        ]
        if unsupported_references:
            raise AppException(
                "Bản nháp chứa căn cứ pháp lý chưa có trong nguồn được cung cấp.",
                code="drafting_unverified_legal_reference",
                status_code=422,
                details={"unverified_references": unsupported_references},
            )

        suffix = str(
            explicit_fields.get("symbol_suffix")
            or _DOCUMENT_NUMBER_SUFFIX.get(document_type)
            or ""
        ).strip(" /-")
        if not suffix:
            raise AppException(
                f"Không có quy tắc số hiệu cho loại văn bản '{document_type}'.",
                code="drafting_document_type_invalid",
                status_code=422,
            )

        missing_fields = list(
            dict.fromkeys(
                [
                    *(plan.get("missing_fields") or []),
                    *(ast.missing_fields or []),
                ]
            )
        )
        date_day, date_month, date_year = _format_date(explicit_fields.get("date_parts"))
        recipient = explicit_fields.get("recipient") or "[BỔ SUNG ĐƠN VỊ KÍNH GỬI]"
        recipients = explicit_fields.get("recipients") or ["[BỔ SUNG NƠI NHẬN]"]
        if isinstance(recipients, str):
            recipients = [recipients]
        recipient_lines = "\n".join(f"- {value}" for value in recipients)

        basis_parts = [str(basis).strip() for basis in legal_basis if str(basis).strip()]
        basis_text = "\n".join(basis_parts)
        body_parts: list[str] = []
        # Decision templates have a dedicated legal-basis block. Tờ trình and
        # Thông báo templates do not, so their confirmed basis stays in the
        # narrative body instead of being lost during rendering.
        if document_type != "quyet_dinh":
            for confirmed_basis in basis_parts:
                if confirmed_basis.casefold() not in body.casefold():
                    body_parts.append(confirmed_basis)
        body_parts.append(body)
        attachments = explicit_fields.get("attachments") or []
        if isinstance(attachments, list):
            missing_attachments = [
                str(item).strip()
                for item in attachments
                if str(item).strip() and str(item).strip().casefold() not in body.casefold()
            ]
            if missing_attachments:
                body_parts.append(
                    "Tài liệu kèm theo:\n"
                    + "\n".join(f"- {item}" for item in missing_attachments)
                )

        document_number = explicit_fields.get("document_number") or f"[CHƯA CẤP SỐ]/{suffix}"
        context_data = {
            "is_draft": True,
            "so_hieu": document_number,
            "dia_danh": explicit_fields.get("issue_place") or "Quy Nhơn",
            "ngay": date_day,
            "thang": date_month,
            "nam": date_year,
            "ngay_thang": f"ngày {date_day} tháng {date_month} năm {date_year}",
            "co_quan_chu_quan": explicit_fields.get("parent_organization") or "",
            "don_vi_ban_hanh": explicit_fields.get("issuer") or "",
            "kinh_gui": recipient,
            "trich_yeu": title,
            "noi_dung": "\n\n".join(part for part in body_parts if part),
            "document_ast": ast.model_dump(mode="json"),
            "can_cu_phap_ly": basis_text
            or "[BỔ SUNG CĂN CỨ PHÁP LÝ ĐÃ ĐƯỢC XÁC NHẬN (NẾU CẦN)]",
            "noi_nhan": recipient_lines,
            "chuc_vu_nguoi_ky": explicit_fields.get("signer_position")
            or "[BỔ SUNG CHỨC VỤ NGƯỜI KÝ]",
            "ho_ten_nguoi_ky": explicit_fields.get("signer_name")
            or "[BỔ SUNG HỌ TÊN NGƯỜI KÝ]",
        }
        validated_draft = {
            **raw_draft,
            "title": title,
            "ast": ast.model_dump(mode="json"),
            "missing_fields": missing_fields,
            "context": context_data,
            "quality_report": {
                "passed": True,
                "required_roles": obligations,
                "covered_roles": sorted({block.role for block in ast.blocks}),
                "issues": [],
            },
        }
        context.node_data["draft"] = validated_draft
        context.node_data["drafting_draft"] = validated_draft
        context.node_data["missing_fields"] = missing_fields
        context.node_data["assistant_status"] = "draft_ready"
        missing_summary = (
            "\n\nThông tin cần rà soát/bổ sung: " + "; ".join(missing_fields)
            if missing_fields
            else ""
        )
        context.node_data["llm_content"] = (
            f"Đã tạo bản nháp {raw_draft.get('document_type_label') or document_type}: "
            f"**{title}**. Bản nháp đã qua kiểm định nội dung và đang được kết xuất DOCX/PDF."
            f"{missing_summary}"
        )
        logger.info(
            "Draft validation [%s]: type=%s block_count=%d missing_field_count=%d",
            node_spec.id,
            document_type,
            len(ast.blocks),
            len(missing_fields),
        )
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"draft": validated_draft, "missing_fields": missing_fields},
        )
