"""Build an adaptive, provenance-aware administrative drafting plan."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.exceptions import AppException
from app.modules.document_types.catalog import get_document_type_label, normalize_document_type_code
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.nodes.drafting_contracts import normalize_text
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

_SUPPORTED_TEMPLATES = frozenset({"to_trinh", "thong_bao", "quyet_dinh", "ke_hoach"})
_STRUCTURE_PROFILES = frozenset(
    {"adaptive", "reference_led", "compact_narrative", "detailed_plan"}
)
_DATE_RE = re.compile(r"\b(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})\b")
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_VIETNAMESE_DATE_RE = re.compile(
    r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
    re.IGNORECASE,
)
_LEGAL_BASIS_RE = re.compile(r"^\s*căn cứ\b[^\n.;]*[.;]?", re.IGNORECASE | re.MULTILINE)
_EXPLICIT_DOCUMENT_DATE_RE = re.compile(
    r"(?:ngày\s+ban\s+hành|ngày\s+ký|ký\s+ngày)\s*(?:là|:)?\s*([^,.;\n]+)",
    re.IGNORECASE,
)
_INLINE_BASIS_RE = re.compile(
    r"\bcăn\s+cứ(?:\s+pháp\s+lý)?\s*(?:(?:là|:|-)\s*)?([^.;\n]+(?:[.;]|$))",
    re.IGNORECASE,
)

# These are semantic field labels, not a vocabulary shortcut. They let the
# parser split a free-form request at the next labeled field while preserving
# punctuation inside names such as ``TS. Nguyễn Thành Đạt``.
_KNOWN_FIELD_LABELS = (
    r"số(?:\s*,\s*ký\s*hiệu|\s+hiệu(?:\s+văn\s+bản)?)?",
    r"ngày\s+(?:ban\s+hành|ký)",
    r"kính\s+(?:gửi|trình)",
    r"người\s+ký",
    r"chức\s+(?:vụ|danh)\s+người\s+ký",
    r"họ\s+tên\s+người\s+ký",
    r"đơn\s+vị\s+ban\s+hành",
    r"cơ\s+quan\s+ban\s+hành",
    r"địa\s+danh(?:\s+ban\s+hành)?",
    r"cơ\s+quan\s+chủ\s+quản",
    r"ký\s+hiệu\s+hậu\s+tố",
    r"hậu\s+tố\s+số\s+hiệu",
    r"căn\s+cứ(?:\s+pháp\s+lý)?",
    r"nơi\s+nhận",
    r"tài\s+liệu\s+kèm\s+theo",
)
_NEXT_FIELD_RE = re.compile(
    rf"\s+(?=(?:{'|'.join(_KNOWN_FIELD_LABELS)})\s*(?:là|:|-)\s*)",
    re.IGNORECASE,
)

_FIELD_LABELS = {
    "document_number": "Số, ký hiệu văn bản",
    "date_parts": "Ngày ban hành",
    "recipient": "Đơn vị kính gửi",
    "signer_position": "Chức vụ người ký",
    "signer_name": "Họ tên người ký",
    "recipients": "Danh sách nơi nhận",
    "legal_basis": "Căn cứ đã được xác nhận (nếu cần)",
    "issuer": "Đơn vị ban hành",
    "issue_place": "Địa danh ban hành",
}
_DEFAULT_OBLIGATIONS = {
    "to_trinh": ["rationale", "proposal", "closing"],
    "thong_bao": ["announcement", "implementation"],
    "quyet_dinh": ["decision", "implementation", "effectiveness"],
    "ke_hoach": ["objective", "requirements", "schedule", "responsibilities"],
}


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        lines = [
            normalize_text(line).lstrip("-• ")
            for line in re.split(r"\r?\n|;(?=\s*)", value)
        ]
        return [line for line in lines if line]
    if isinstance(value, list):
        return [text for item in value if (text := normalize_text(item))]
    return []


def _extract_date(source: str) -> list[str] | None:
    iso_match = _ISO_DATE_RE.search(source)
    if iso_match:
        year, month, day = (int(part) for part in iso_match.groups())
    else:
        match = _VIETNAMESE_DATE_RE.search(source) or _DATE_RE.search(source)
        if not match:
            return None
        day, month, year = (int(part) for part in match.groups())
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None
    return [f"{day:02d}", f"{month:02d}", str(year)]


def _pick_text(
    supplied: dict[str, Any],
    supplied_keys: tuple[str, ...],
    organization: dict[str, Any],
    organization_keys: tuple[str, ...] = (),
) -> tuple[str | None, str]:
    for key in supplied_keys:
        if text := normalize_text(supplied.get(key)):
            return text, "user"
    for key in organization_keys:
        if text := normalize_text(organization.get(key)):
            return text, "organization_profile"
    return None, "missing"


def _extract_labeled_value(source: str, labels: str) -> str | None:
    """Read one labeled value up to the next labeled field.

    Splitting at the next semantic label keeps abbreviated names and model
    identifiers intact while still preventing one field from consuming the
    remainder of a natural-language request.
    """
    match = re.search(rf"(?:{labels})\s*(?:là|:|-)\s*", source, re.IGNORECASE)
    if not match:
        return None
    remainder = source[match.end() :]
    next_match = _NEXT_FIELD_RE.search(remainder)
    line_break = re.search(r"\r?\n", remainder)
    boundaries = [len(remainder)]
    if next_match:
        boundaries.append(next_match.start())
    if line_break:
        boundaries.append(line_break.start())
    value = remainder[: min(boundaries)]
    value = value.strip(" \t\r\n,;.")
    return value or None


def _collect_explicit_fields(
    supplied: dict[str, Any],
    organization: dict[str, Any],
    source: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    provenance: dict[str, str] = {}

    document_number, provenance["document_number"] = _pick_text(
        supplied, ("document_number", "so_hieu"), organization
    )
    if not document_number:
        document_number = _extract_labeled_value(
            source, r"số(?:\s*,\s*ký\s*hiệu|\s+hiệu(?:\s+văn\s+bản)?)?"
        )
        if document_number:
            provenance["document_number"] = "user_message"

    date_parts = _extract_date(str(supplied.get("date") or ""))
    if date_parts:
        provenance["date_parts"] = "user"
    else:
        date_match = _EXPLICIT_DOCUMENT_DATE_RE.search(source)
        date_parts = _extract_date(date_match.group(1)) if date_match else None
        provenance["date_parts"] = "user_message" if date_parts else "missing"

    recipient, provenance["recipient"] = _pick_text(
        supplied, ("recipient", "kinh_gui"), organization, ("default_recipient",)
    )
    if not recipient:
        recipient = _extract_labeled_value(source, r"kính\s+(?:gửi|trình)")
        if recipient:
            provenance["recipient"] = "user_message"

    signer_position, provenance["signer_position"] = _pick_text(
        supplied,
        ("signer_position", "signer_title", "chuc_vu_nguoi_ky"),
        organization,
        ("signer_position", "leader_title"),
    )
    if not signer_position:
        signer_position = _extract_labeled_value(
            source, r"chức vụ người ký|chức danh người ký"
        )
        provenance["signer_position"] = "user_message" if signer_position else "missing"
    signer_name, provenance["signer_name"] = _pick_text(
        supplied,
        ("signer_name", "signer", "ho_ten_nguoi_ky"),
        organization,
        ("signer_name", "leader_name"),
    )
    if not signer_name:
        signer_name = _extract_labeled_value(
            source,
            r"họ tên người ký|ký bởi|(?<!vụ )(?<!danh )người ký",
        )
        provenance["signer_name"] = "user_message" if signer_name else "missing"
    issuer, provenance["issuer"] = _pick_text(
        supplied,
        ("issuer", "don_vi_ban_hanh"),
        organization,
        ("issuer", "unit_name"),
    )
    if not issuer:
        issuer = _extract_labeled_value(source, r"đơn vị ban hành|cơ quan ban hành")
        provenance["issuer"] = "user_message" if issuer else "missing"
    parent_organization, provenance["parent_organization"] = _pick_text(
        supplied,
        ("parent_organization", "co_quan_chu_quan"),
        organization,
        ("parent_organization",),
    )
    if not parent_organization:
        parent_organization = _extract_labeled_value(source, r"cơ quan chủ quản")
        provenance["parent_organization"] = (
            "user_message" if parent_organization else "missing"
        )
    issue_place, provenance["issue_place"] = _pick_text(
        supplied,
        ("issue_place", "dia_danh"),
        organization,
        ("issue_place", "location"),
    )
    if not issue_place:
        issue_place = _extract_labeled_value(source, r"địa danh ban hành|địa danh")
        provenance["issue_place"] = "user_message" if issue_place else "missing"
    symbol_suffix, provenance["symbol_suffix"] = _pick_text(
        supplied,
        ("symbol_suffix", "ky_hieu_hau_to"),
        organization,
        ("symbol_suffix",),
    )
    if not symbol_suffix:
        symbol_suffix = _extract_labeled_value(source, r"ký hiệu hậu tố|hậu tố số hiệu")
        provenance["symbol_suffix"] = "user_message" if symbol_suffix else "missing"

    legal_basis = _as_text_list(supplied.get("legal_basis") or supplied.get("can_cu_phap_ly"))
    if legal_basis:
        provenance["legal_basis"] = "user"
    else:
        legal_basis = [match.group(1).strip(" .;,") for match in _INLINE_BASIS_RE.finditer(source)]
        if not legal_basis:
            legal_basis = [match.group(0).strip() for match in _LEGAL_BASIS_RE.finditer(source)]
        provenance["legal_basis"] = "user_message" if legal_basis else "missing"

    recipients = _as_text_list(supplied.get("recipients") or supplied.get("noi_nhan"))
    if recipients:
        provenance["recipients"] = "user"
    else:
        recipient_list = _extract_labeled_value(source, r"nơi\s+nhận")
        recipients = _as_text_list(recipient_list)
        if recipients:
            provenance["recipients"] = "user_message"
        elif recipient:
            recipients = [recipient]
            provenance["recipients"] = provenance["recipient"]
        else:
            provenance["recipients"] = "missing"

    attachments = _as_text_list(supplied.get("attachments") or supplied.get("tai_lieu_kem_theo"))
    provenance["attachments"] = "user" if attachments else "missing"

    return (
        {
            "document_number": document_number,
            "date_parts": date_parts,
            "recipient": recipient,
            "signer_position": signer_position,
            "signer_name": signer_name,
            "legal_basis": legal_basis,
            "recipients": recipients,
            "issuer": issuer,
            "parent_organization": parent_organization,
            "issue_place": issue_place,
            "symbol_suffix": symbol_suffix,
            "attachments": attachments,
        },
        provenance,
    )


class DraftingPlanNodeHandler(BaseNodeHandler):
    """Resolve template, structure profile, obligations, and missing-field policy."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        port_inputs = context.node_inputs.get(node_spec.id, {})
        extracted = port_inputs.get("fields") or context.node_data.get("extracted_fields") or {}
        if not isinstance(extracted, dict):
            extracted = {}
        reference_profile = (
            port_inputs.get("reference_profile")
            or context.node_data.get("drafting_reference_profile")
            or {}
        )
        if not isinstance(reference_profile, dict):
            reference_profile = {}

        source = (
            normalize_text(extracted.get("raw_text"))
            or normalize_text(context.node_data.get("normalized_query"))
            or normalize_text(context.inputs.get("message"))
        )
        requested_type = normalize_text(context.inputs.get("document_type"))
        if requested_type.casefold() == "auto":
            requested_type = ""
        requested_type = (
            requested_type
            or normalize_text(extracted.get("doc_type"))
            or normalize_text((node_spec.config or {}).get("default_document_type"))
            or "to_trinh"
        )
        document_type = normalize_document_type_code(requested_type)
        if document_type not in _SUPPORTED_TEMPLATES:
            raise AppException(
                f"Chưa có mẫu DOCX đã cấu hình cho loại văn bản '{requested_type}'. Hiện hỗ trợ Tờ trình, Kế hoạch, Thông báo và Quyết định.",
                code="drafting_template_not_supported",
                status_code=422,
                details={"requested_document_type": requested_type},
            )

        supplied = context.inputs.get("document_fields") or context.inputs.get("draft_fields") or {}
        organization = (
            context.inputs.get("organization_profile")
            or (node_spec.config or {}).get("organization_profile")
            or {}
        )
        if not isinstance(supplied, dict):
            supplied = {}
        if not isinstance(organization, dict):
            organization = {}
        explicit, provenance = _collect_explicit_fields(supplied, organization, source)

        configured_blocking = (node_spec.config or {}).get("blocking_fields", [])
        requested_blocking = context.inputs.get("required_fields", configured_blocking)
        blocking_codes = (
            {
                normalize_text(item)
                for item in requested_blocking
                if normalize_text(item) in _FIELD_LABELS
            }
            if isinstance(requested_blocking, list)
            else set()
        )
        missing_codes = [key for key in _FIELD_LABELS if not explicit.get(key)]
        blocking_missing = [
            _FIELD_LABELS[key] for key in missing_codes if key in blocking_codes
        ]
        missing = [_FIELD_LABELS[key] for key in missing_codes]

        requested_profile = normalize_text(context.inputs.get("structure_mode"))
        reference_recommendation = normalize_text(reference_profile.get("recommended_profile"))
        structure_profile = (
            requested_profile
            if requested_profile in _STRUCTURE_PROFILES
            else reference_recommendation
            if reference_recommendation in _STRUCTURE_PROFILES
            else "adaptive"
        )

        obligations = list(_DEFAULT_OBLIGATIONS[document_type])
        if explicit["legal_basis"]:
            obligations.insert(0, "basis")
        if explicit["attachments"]:
            obligations.append("attachments")

        plan = {
            "document_ast_version": "document_ast.v1",
            "source_text": source,
            "document_type": document_type,
            "document_type_label": get_document_type_label(document_type) or requested_type,
            "structure_profile": structure_profile,
            "semantic_obligations": obligations,
            "explicit_fields": explicit,
            "field_provenance": provenance,
            "missing_fields": missing,
            "blocking_missing_fields": blocking_missing,
            "reference_profile": reference_profile,
            "tenant_id": context.tenant_id,
        }
        context.node_data["drafting_plan"] = plan
        context.node_data["missing_fields"] = missing
        selected_port = "needs_input" if blocking_missing else "ready"
        if blocking_missing:
            context.node_data["assistant_status"] = "needs_clarification"
            context.node_data["llm_content"] = (
                "Để lập bản nháp chính xác, vui lòng bổ sung: "
                + "; ".join(blocking_missing)
                + "."
            )
            context.outputs["missing_fields"] = blocking_missing

        logger.info(
            "Drafting plan [%s]: type=%s structure=%s obligations=%d blocking_missing=%d",
            node_spec.id,
            document_type,
            structure_profile,
            len(obligations),
            len(blocking_missing),
        )
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "plan": plan,
                "missing_fields": missing,
                "ready": plan,
                "needs_input": blocking_missing,
            },
            selected_port=selected_port,
        )
