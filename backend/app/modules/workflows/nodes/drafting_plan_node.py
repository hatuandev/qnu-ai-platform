"""Plan administrative document drafts without requiring a knowledge collection."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from app.core.exceptions import AppException
from app.modules.document_types.catalog import get_document_type_label, normalize_document_type_code
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

_SUPPORTED_TEMPLATES = frozenset({"to_trinh", "thong_bao", "quyet_dinh"})
_NUMBER_RE = re.compile(r"\b\d{1,5}\s*[/\-]\s*[A-ZĐ]{2,8}(?:\s*[-/]\s*[A-ZĐ0-9]{2,10})?\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4})\b")
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_VIETNAMESE_DATE_RE = re.compile(
    r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
    re.IGNORECASE,
)
_RECIPIENT_RE = re.compile(
    r"(?:kính\s+gửi|kính\s+trình)\s+([^,.;\n]+)",
    re.IGNORECASE,
)
_LEGAL_BASIS_RE = re.compile(r"^\s*căn cứ\b[^\n.;]*[.;]?", re.IGNORECASE | re.MULTILINE)
_EXPLICIT_DOCUMENT_DATE_RE = re.compile(
    r"(?:ngày\s+ban\s+hành|ngày\s+ký|ký\s+ngày)\s*(?:là|:)?\s*([^,.;\n]+)",
    re.IGNORECASE,
)

_EVENT_PLACEHOLDERS = {
    "Thời gian tổ chức": "[BỔ SUNG THỜI GIAN TỔ CHỨC]",
    "Địa điểm cụ thể": "[BỔ SUNG ĐỊA ĐIỂM CỤ THỂ]",
    "Đơn vị chủ trì": "[BỔ SUNG ĐƠN VỊ CHỦ TRÌ]",
    "Dự toán kinh phí": "[BỔ SUNG DỰ TOÁN KINH PHÍ]",
    "Thành phần tham dự": "[BỔ SUNG THÀNH PHẦN THAM DỰ]",
}


def _as_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return unicodedata.normalize("NFC", value.strip())
    return None


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [
            unicodedata.normalize("NFC", line.strip().lstrip("-• "))
            for line in value.splitlines()
            if line.strip()
        ] or ([unicodedata.normalize("NFC", value.strip())] if value.strip() else [])
    if isinstance(value, list):
        return [text for item in value if (text := _as_text(item))]
    return []


def _extract_date(source: str) -> tuple[str, str, str] | None:
    iso_match = _ISO_DATE_RE.search(source)
    if iso_match:
        year, month, day = (int(part) for part in iso_match.groups())
        if 1 <= day <= 31 and 1 <= month <= 12:
            return f"{day:02d}", f"{month:02d}", str(year)
    match = _VIETNAMESE_DATE_RE.search(source) or _DATE_RE.search(source)
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return None
    return f"{day:02d}", f"{month:02d}", str(year)


def _extract_labeled_value(source: str, labels: str) -> str | None:
    match = re.search(
        rf"(?:{labels})\s*(?:là|:|-)\s*([^,.;\n]+)",
        source,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _collect_explicit_fields(
    supplied: dict[str, Any], source: str
) -> dict[str, Any]:
    document_number = _as_text(supplied.get("document_number") or supplied.get("so_hieu"))
    if not document_number:
        number_match = _NUMBER_RE.search(source)
        document_number = number_match.group(0).strip() if number_match else None

    date_parts = _extract_date(str(supplied["date"])) if supplied.get("date") else None
    if not date_parts:
        document_date_match = _EXPLICIT_DOCUMENT_DATE_RE.search(source)
        if document_date_match:
            date_parts = _extract_date(document_date_match.group(1))

    recipient = _as_text(supplied.get("recipient") or supplied.get("kinh_gui"))
    if not recipient:
        recipient_match = _RECIPIENT_RE.search(source)
        recipient = recipient_match.group(1).strip() if recipient_match else None

    legal_basis = _as_text_list(supplied.get("legal_basis") or supplied.get("can_cu_phap_ly"))
    if not legal_basis:
        legal_basis = [match.group(0).strip() for match in _LEGAL_BASIS_RE.finditer(source)]

    recipients = _as_text_list(supplied.get("recipients") or supplied.get("noi_nhan"))
    if not recipients:
        recipients = _as_text_list(supplied.get("recipient"))

    return {
        "document_number": document_number,
        "date_parts": list(date_parts) if date_parts else None,
        "recipient": recipient,
        "signer_position": _as_text(
            supplied.get("signer_position") or supplied.get("signer_title") or supplied.get("chuc_vu_nguoi_ky")
        ) or _extract_labeled_value(source, r"chức vụ người ký|chức danh người ký"),
        "signer_name": _as_text(
            supplied.get("signer_name") or supplied.get("signer") or supplied.get("ho_ten_nguoi_ky")
        ) or _extract_labeled_value(source, r"người ký|ký bởi|họ tên người ký"),
        "legal_basis": legal_basis,
        "recipients": recipients,
        "issuer": _as_text(supplied.get("issuer") or supplied.get("don_vi_ban_hanh")),
        "event_time": _as_text(supplied.get("event_time") or supplied.get("timeframe"))
        or _extract_labeled_value(source, r"thời gian tổ chức|thời gian dự kiến|ngày tổ chức"),
        "venue": _as_text(supplied.get("venue") or supplied.get("meeting_place"))
        or _extract_labeled_value(source, r"địa điểm tổ chức|địa điểm"),
        "owner": _as_text(supplied.get("owner") or supplied.get("organizer"))
        or _extract_labeled_value(source, r"đơn vị chủ trì|đơn vị tổ chức|chủ trì"),
        "budget": _as_text(supplied.get("budget") or supplied.get("kinh_phi"))
        or _extract_labeled_value(source, r"dự toán kinh phí|kinh phí|ngân sách"),
        "attendees": _as_text(supplied.get("attendees") or supplied.get("participants"))
        or _extract_labeled_value(source, r"thành phần tham dự|đối tượng tham dự|khách mời"),
    }


class DraftingPlanNodeHandler(BaseNodeHandler):
    """Resolve the supported template and mark every unprovided administrative field."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        port_inputs = context.node_inputs.get(node_spec.id, {})
        extracted = port_inputs.get("fields") or context.node_data.get("extracted_fields") or {}
        if not isinstance(extracted, dict):
            extracted = {}

        source = _as_text(extracted.get("raw_text")) or _as_text(
            context.node_data.get("normalized_query")
        ) or _as_text(context.inputs.get("message")) or ""
        requested_type = _as_text(context.inputs.get("document_type"))
        if requested_type and requested_type.casefold() == "auto":
            requested_type = None
        requested_type = (
            requested_type
            or _as_text(extracted.get("doc_type"))
            or _as_text((node_spec.config or {}).get("default_document_type"))
            or "to_trinh"
        )
        document_type = normalize_document_type_code(requested_type)
        if document_type not in _SUPPORTED_TEMPLATES:
            raise AppException(
                f"Chưa có mẫu DOCX đã cấu hình cho loại văn bản '{requested_type}'. Hiện hỗ trợ Tờ trình, Thông báo và Quyết định.",
                code="drafting_template_not_supported",
                status_code=422,
                details={"requested_document_type": requested_type},
            )

        supplied = context.inputs.get("document_fields") or context.inputs.get("draft_fields") or {}
        if not isinstance(supplied, dict):
            supplied = {}
        explicit = _collect_explicit_fields(supplied, source)
        missing: list[str] = []
        required_fields = (
            ("document_number", "Số, ký hiệu văn bản"),
            ("date_parts", "Ngày ban hành"),
            ("recipient", "Nơi nhận hoặc đơn vị kính gửi"),
            ("signer_position", "Chức vụ người ký"),
            ("signer_name", "Họ tên người ký"),
        )
        for key, label in required_fields:
            if not explicit[key]:
                missing.append(label)
        if not explicit["recipients"]:
            missing.append("Danh sách nơi nhận")
        if not explicit["legal_basis"]:
            missing.append("Căn cứ pháp lý đã được đơn vị xác nhận (nếu cần)")

        placeholder_fields: dict[str, str] = {}
        event_request = any(
            marker in source.casefold()
            for marker in ("sự kiện", "chương trình", "tổ chức")
        )
        if event_request:
            event_checks = (
                ("event_time", "Thời gian tổ chức"),
                ("venue", "Địa điểm cụ thể"),
                ("owner", "Đơn vị chủ trì"),
                ("budget", "Dự toán kinh phí"),
                ("attendees", "Thành phần tham dự"),
            )
            for key, label in event_checks:
                if not explicit[key]:
                    missing.append(label)
                    placeholder_fields[label] = _EVENT_PLACEHOLDERS[label]

        plan = {
            "source_text": source,
            "document_type": document_type,
            "document_type_label": get_document_type_label(document_type) or requested_type,
            "explicit_fields": explicit,
            "missing_fields": missing,
            "placeholder_fields": placeholder_fields,
            "tenant_id": context.tenant_id,
        }
        context.node_data["drafting_plan"] = plan
        logger.info(
            "Drafting plan [%s]: type=%s missing_field_count=%d knowledge_required=false",
            node_spec.id,
            document_type,
            len(missing),
        )
        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={"plan": plan},
        )
