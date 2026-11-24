"""Flexible document drafting extraction and real DOCX / XLSX / PDF export."""

from __future__ import annotations

import asyncio
import html
import io
import re
import unicodedata
from datetime import datetime
from typing import Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
import pymupdf
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.conversations.access import owned
from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.identity.actor import AuthActor
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, EntityNotFound, Forbidden
from qnu.platform.logging import get_logger

logger = get_logger(__name__)

ExportFormat = Literal["docx", "pdf", "xlsx"]
DocumentLayout = Literal["standard", "administrative", "spreadsheet"]

EXPORT_MEDIA_TYPES: dict[ExportFormat, str] = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

_DOC_BLOCK_RE = re.compile(
    r"<<<\s*DOCUMENT(?P<attrs>[^>]*)>>>\s*(?P<body>[\s\S]*?)\s*<<<\s*END_DOCUMENT\s*>>>",
    re.IGNORECASE,
)
_UNCLOSED_DOC_BLOCK_RE = re.compile(
    r"<<<\s*DOCUMENT(?P<attrs>[^>]*)>>>\s*(?P<body>[\s\S]+)$",
    re.IGNORECASE,
)
_STRAY_DOC_MARKER_RE = re.compile(
    r"<<<\s*/?\s*(?:END_)?DOCUMENT[^>]*>{1,3}",
    re.IGNORECASE,
)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_REQUESTED_FORMAT_RE: tuple[tuple[ExportFormat, re.Pattern[str]], ...] = (
    ("docx", re.compile(r"\b(?:docx|word|\.docx)\b", re.IGNORECASE)),
    ("pdf", re.compile(r"\b(?:pdf|\.pdf)\b", re.IGNORECASE)),
    ("xlsx", re.compile(r"\b(?:xlsx|excel|\.xlsx)\b", re.IGNORECASE)),
)
_EXPORT_REQUEST_ACTION_RE = re.compile(
    r"\b(?:xuất|tạo|làm|lập|soạn|chuyển\s+sang|đổi\s+sang|tải|download|export|generate|save\s+as|"
    r"gửi\s+(?:file|tệp|bản)|cho\s+(?:mình|tôi|em|anh|chị)\s+(?:file|tệp|bản))\b",
    re.IGNORECASE,
)
_TABLE_SEP_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$")
_DRAFT_INTENT_RE = re.compile(
    r"\b(soạn|viết\s+(?:giúp|mẫu|bản|đơn|giấy|báo\s+cáo|kế\s+hoạch|tờ\s+trình|công\s+văn|thông\s+báo|quy\s+định|quy\s+chế|biên\s+bản)|"
    r"tạo\s+(?:mẫu|văn\s+bản|bản\s+thảo|file|tệp|bảng|kế\s+hoạch|báo\s+cáo|đơn|giấy|quy\s+định|quy\s+chế|biên\s+bản)|"
    r"làm\s+(?:giúp|mẫu|bản|đơn|giấy|báo\s+cáo|kế\s+hoạch|tờ\s+trình|biên\s+bản)|"
    r"lập\s+(?:kế\s+hoạch|bảng|danh\s+sách|báo\s+cáo|tờ\s+trình|biên\s+bản)|"
    r"xuất\s+(?:file|tệp|docx|word|pdf|excel|xlsx))\b",
    re.IGNORECASE,
)
_REFUSAL_REPLY_RE = re.compile(
    r"(?:chưa\s+được\s+gắn\s+kho(?:\s+dữ\s+liệu)?\s+tri\s+thức|"
    r"(?:chưa|không)\s+có\s+(?:dữ\s+liệu|kho)\s+tri\s+thức|"
    r"không\s+thể\s+(?:cung\s+cấp\s+thông\s+tin|trả\s+lời|tra\s+cứu)|"
    r"chưa\s+có\s+thông\s+tin\s+.*?(?:nội\s+bộ|tri\s+thức|quy\s+định\s+này))",
    re.IGNORECASE,
)
_HTML_BR_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_ADMIN_CUES_RE = re.compile(
    r"(?:cộng\s+hòa\s+xã\s+hội\s+chủ\s+nghĩa\s+việt\s+nam|"
    r"\b(?:tờ\s+trình|kế\s+hoạch|quyết\s+định|thông\s+báo|công\s+văn|"
    r"báo\s+cáo|quy\s+chế|biên\s+bản|đơn\s+xin|giấy\s+nghỉ\s+phép)\b)",
    re.IGNORECASE,
)
_PREAMBLE_LINE_RE = re.compile(
    r"^(?:dưới\s+đây\s+là|sau\s+đây\s+là|mình\s+(?:đã|xin|gửi)|tôi\s+(?:đã|xin|gửi)|"
    r"chào\s+bạn|xin\s+chào|vâng|dạ|được\s+rồi|ok)\b",
    re.IGNORECASE,
)
_EPILOGUE_LINE_RE = re.compile(
    r"^(?:hy\s+vọng|nếu\s+bạn\s+(?:cần|muốn)|bạn\s+(?:có\s+thể|hãy|cần)|"
    r"chúc\s+bạn|mọi\s+chỉnh\s+sửa|vui\s+lòng\s+cho\s+(?:mình|tôi)\s+biết)\b",
    re.IGNORECASE,
)
_PRELIMINARY_INQUIRY_RE = re.compile(
    r"(?:\bcó\s+được\s+(?:không|ko|k)\b|\bđược\s+(?:không|ko|k)\b|"
    r"\bcó\s+(?:hỗ\s+trợ|soạn|viết|làm|tạo)\s+.*?\b(?:không|ko|k)\b|"
    r"\bbạn\s+có\s+thể\s+.*?\b(?:không|ko|k)\b)",
    re.IGNORECASE,
)
_EXPLICIT_EXPORT_NOW_RE = re.compile(
    r"\b(xuất\s+(?:file|tệp|word|docx|pdf|excel|xlsx)|tạo\s+file|tạo\s+tệp|soạn\s+ngay|tạo\s+mẫu\s+ngay)\b",
    re.IGNORECASE,
)


class DocumentDraft(BaseModel):
    title: str
    layout: DocumentLayout = "standard"
    markdown: str
    has_tables: bool = False
    preferred_format: ExportFormat | None = None


def enabled_export_formats(config: dict | None) -> list[ExportFormat]:
    """Read enabled export formats from an assistant config or snapshot dict."""
    if not isinstance(config, dict):
        return []
    policy = config.get("rag_policy") if isinstance(config.get("rag_policy"), dict) else config
    formats: list[ExportFormat] = []
    if policy.get("allow_export_docx"):
        formats.append("docx")
    if policy.get("allow_export_pdf"):
        formats.append("pdf")
    if policy.get("allow_export_xlsx"):
        formats.append("xlsx")
    return formats


NO_KNOWLEDGE_GROUNDING_POLICY = (
    "\n\n[NGUYÊN TẮC DỮ LIỆU TRI THỨC — CHẾ ĐỘ KHÔNG GẮN KHO TRI THỨC]\n"
    "Trợ lý hiện CHƯA được gắn Kho tri thức nội bộ.\n"
    "- ĐƯỢC PHÉP: Chào hỏi, giao tiếp tự nhiên và soạn thảo, dựng mẫu, biên tập nội dung "
    "dựa trên CHÍNH dữ liệu/ngữ cảnh mà người dùng cung cấp trực tiếp trong hội thoại.\n"
    "- BẮT BUỘC TỪ CHỐI THẲNG THẮN: Với mọi câu hỏi yêu cầu thông tin thực tế, số liệu, quy định, "
    "danh sách (khoa/viện, ngành đào tạo, mã ngành, điểm chuẩn, học phí, nhân sự, văn bản cụ thể...) "
    "hoặc kiến thức ngoài cuộc hội thoại mà người dùng chưa cung cấp: KHÔNG tự lấy kiến thức chung "
    "của mô hình để trả lời, KHÔNG phỏng đoán URL/số liệu và KHÔNG giải thích dài dòng. "
    "Chỉ trả lời ngắn gọn, lịch sự (1–2 câu) rằng hiện trợ lý chưa có dữ liệu tri thức về nội dung này "
    "nên không thể trả lời, và gợi ý người dùng cung cấp dữ liệu trực tiếp nếu muốn hỗ trợ soạn thảo."
)

_ALL_EXPORT_FORMATS: tuple[ExportFormat, ...] = ("docx", "pdf", "xlsx")


_EXPORT_FORMAT_LABELS: dict[ExportFormat, str] = {
    "docx": "Word (DOCX)",
    "pdf": "PDF",
    "xlsx": "Excel (XLSX)",
}


_VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_VIETNAM_WEEKDAYS: tuple[str, ...] = (
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy",
    "Chủ Nhật",
)
_VALID_SHORT_REPLIES = frozenset(
    {
        "ok",
        "oke",
        "okay",
        "được",
        "vâng",
        "dạ",
        "dạ vâng",
        "có",
        "không",
        "cảm ơn",
        "cảm ơn bạn",
        "chào bạn",
        "xin chào",
    }
)

DECREE_30_DRAFTING_PERSONA = (
    "Bạn là Trợ lý soạn thảo văn bản hành chính của Trường Đại học Quy Nhơn, "
    "tuân thủ thể thức và kỹ thuật trình bày theo Nghị định 30/2020/NĐ-CP.\n\n"
    "1. THỂ THỨC HÀNH CHÍNH CỐT LÕI (NĐ 30/2020/NĐ-CP):\n"
    "- Đủ bố cục chuẩn từng loại văn bản (Đơn, Tờ trình, Công văn, Kế hoạch, Thông báo, Báo cáo, Biên bản, Quyết định): "
    "Quốc hiệu & Tiêu ngữ; Tên cơ quan/đơn vị ban hành; Số, ký hiệu; Địa danh và ngày tháng năm; "
    "Tên loại & trích yếu nội dung; Căn cứ (nếu có); Nội dung chính mạch lạc; Nơi nhận; Khối chữ ký.\n"
    "- Văn phong hành chính chuẩn mực, súc tích, khách quan, 100% tiếng Việt trong sáng.\n\n"
    "2. QUY TẮC HỘI THOẠI & KHÔNG HỎI VẶN NHIỀU LƯỢT:\n"
    "- Chỉ hỏi làm rõ tối đa 1 lượt ngắn gọn nếu người dùng mới ngỏ ý quá chung chung (chưa nêu rõ loại văn bản hoặc mục đích cơ bản).\n"
    "- Ngay khi người dùng đã nêu loại văn bản kèm thông tin cơ bản, bổ sung dữ liệu, hoặc yêu cầu chốt "
    '("soạn giúp mình", "làm luôn đi", "phần thiếu tự điền", "nơi nhận tôi tự ghi"), '
    "PHẢI SOẠN NGAY bản thảo hoàn chỉnh — không hỏi vặn thêm lượt nào nữa.\n"
    "- Tự quy đổi chính xác mốc thời gian tương đối (hôm nay, ngày mai, ngày kia, tuần sau...) theo ngày giờ Việt Nam hiện tại.\n\n"
    "3. CHỐNG BỊA DỮ KIỆN & PLACEHOLDER:\n"
    "- TUYỆT ĐỐI không bịa số văn bản, căn cứ pháp lý, số liệu, họ tên, chức vụ hay quy định nội bộ chưa được cung cấp.\n"
    "- Mọi trường còn thiếu tự điền chỗ giữ chỗ rõ ràng dạng [Tên thông tin], ví dụ: "
    "[Nơi nhận], [Ngày bắt đầu], [Ngày kết thúc], [Chức vụ/Đơn vị], [Lý do], [Người ký]."
)


def vietnam_time_context(now: datetime | None = None) -> str:
    """Build current Vietnam date/time context so the model resolves relative dates accurately."""
    current = now.astimezone(_VIETNAM_TZ) if now is not None else datetime.now(_VIETNAM_TZ)
    weekday = _VIETNAM_WEEKDAYS[current.weekday()]
    formatted = f"{weekday}, {current.strftime('%d/%m/%Y %H:%M')}"
    return (
        "\n\n[NGỮ CẢNH THỜI GIAN HIỆN TẠI]\n"
        f"Hiện tại là {formatted} (múi giờ Việt Nam — Asia/Ho_Chi_Minh).\n"
        'Khi người dùng dùng mốc thời gian tương đối ("hôm nay", "ngày mai", "ngày kia", '
        '"tuần sau", "nghỉ 2 ngày"...), hãy tự quy đổi chính xác sang ngày DD/MM/YYYY dựa trên '
        "mốc thời gian này; TUYỆT ĐỐI KHÔNG hỏi ngược lại người dùng hôm nay là ngày nào."
    )


def dialogue_turn_policy(prior_turns: int) -> str:
    """Return turn-aware conversation hygiene rules (no repeated greetings or endless follow-up questions)."""
    if prior_turns > 0:
        return (
            "\n\n[QUY TẮC MẠCH HỘI THOẠI — LƯỢT NỐI TIẾP]\n"
            f"Đây là lượt tiếp nối trong cùng phiên (đã có {prior_turns} lượt trước đó).\n"
            '- TUYỆT ĐỐI KHÔNG mở đầu bằng "Chào bạn", "Xin chào", "Chào anh/chị" hay lời chào/tự giới thiệu lặp lại; '
            "đi thẳng ngay vào nội dung hoặc bản thảo.\n"
            "- KHÔNG hỏi vặn đi hỏi vặn lại: nếu người dùng đã bổ sung thông tin, hoặc đã nói rõ ý muốn soạn ngay "
            '("soạn giúp mình", "làm luôn đi", "phần thiếu tự điền", "nơi nhận tôi tự ghi"...), '
            "hãy SOẠN NGAY bản thảo hoàn chỉnh và dùng chỗ giữ chỗ rõ ràng dạng [Nơi nhận], [Ngày bắt đầu], "
            "[Ngày kết thúc], [Chức vụ/Đơn vị] cho các trường còn thiếu."
        )
    return (
        "\n\n[QUY TẮC MẠCH HỘI THOẠI — LƯỢT ĐẦU]\n"
        "Nếu cần chào mở đầu, chỉ chào ngắn gọn tối đa 1 câu rồi đi thẳng vào yêu cầu của người dùng."
    )


def is_abnormally_truncated_reply(text: str, question: str = "") -> bool:
    """Detect sudden early-EOS cutoffs (e.g., 1-word 'Cảm' on quantized Q4 models)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return True
    if cleaned[-1] in ",;:-" and len(cleaned) < 20:
        return True
    normalized = cleaned.lower().strip(" .!?")
    if normalized in _VALID_SHORT_REPLIES:
        return False
    if len(cleaned) < 10:
        return True
    words = cleaned.split()
    return (
        len(words) <= 2
        and len(cleaned) < 16
        and cleaned[-1] not in ".!?…"
        and len((question or "").strip()) >= 15
    )


def export_policy_prompt_addon(formats: list[ExportFormat]) -> str:
    """Prompt rules enforcing exact enabled/disabled export toggles (DOCX/PDF/Excel)."""
    if not formats:
        return (
            "\n\n[QUY TẮC TẠO & XUẤT TỆP]\n"
            "Trợ lý hiện KHÔNG có chức năng tạo hoặc xuất tệp (DOCX, PDF, Excel). "
            "TUYỆT ĐỐI KHÔNG dùng thẻ <<<DOCUMENT ...>>>. "
            "Nếu người dùng yêu cầu tạo hoặc xuất tệp Word/DOCX, PDF hoặc Excel, "
            "hãy trả lời ngắn gọn, rõ ràng rằng trợ lý hiện không có chức năng tạo tệp định dạng đó."
        )
    enabled_labels = ", ".join(fmt.upper() for fmt in formats)
    disabled = [fmt.upper() for fmt in _ALL_EXPORT_FORMATS if fmt not in formats]
    disabled_rule = (
        f"- CÁC ĐỊNH DẠNG ĐANG TẮT: {', '.join(disabled)}. "
        f"Nếu người dùng yêu cầu tạo/xuất sang định dạng đang tắt ({', '.join(disabled)}), "
        "hãy trả lời ngắn gọn, rõ ràng rằng trợ lý hiện KHÔNG có chức năng tạo tệp định dạng đó; "
        "TUYỆT ĐỐI KHÔNG xuất thẻ <<<DOCUMENT ...>>> và KHÔNG tự ý tạo sang định dạng khác khi người dùng chưa yêu cầu.\n"
        if disabled
        else ""
    )
    return (
        "\n\n[QUY TẮC SOẠN THẢO VĂN BẢN & TẠO TỆP]\n"
        f"- CÁC ĐỊNH DẠNG ĐANG BẬT (ĐƯỢC PHÉP TẠO TỆP): {enabled_labels}.\n"
        f"- TẬP TRUNG ĐÚNG 1 ĐỊNH DẠNG NGƯỜI DÙNG YÊU CẦU: Chỉ làm việc và nhắc đúng định dạng người dùng yêu cầu "
        f"(nếu định dạng đó đang bật). KHÔNG tự ý liệt kê, gợi ý hay tạo tràn lan cả 3 loại tệp (DOCX, PDF, Excel) "
        f"khi người dùng không hỏi.\n"
        f"- HỆ THỐNG TỰ ĐỘNG TẠO TỆP THẬT: Nền tảng QNU sẽ tự động chuyển nội dung đặt trong cặp thẻ "
        f"<<<DOCUMENT ...>>> ... <<<END_DOCUMENT>>> thành tệp tải về thật cho đúng định dạng đang bật ({enabled_labels}). "
        f"TUYỆT ĐỐI KHÔNG trả lời rằng bạn không thể tạo hoặc xuất tệp đối với các định dạng đang bật ({enabled_labels}).\n"
        f"{disabled_rule}"
        "- KHÔNG TẠO BẢN THẢO SỚM (CHỈ HỎI TỐI ĐA 1 LƯỢT): Chỉ hỏi làm rõ tối đa 1 lượt ngắn gọn khi người dùng mới "
        'ngỏ ý quá chung chung (ví dụ: "tôi muốn làm 1 đơn xin nghỉ phép có được không?", "tôi muốn soạn đơn") '
        "mà chưa cung cấp thông tin cơ bản hay yêu cầu soạn ngay — KHÔNG xuất thẻ <<<DOCUMENT ...>>> ở lượt hỏi thăm này.\n"
        "- XUẤT BẢN THẢO NGAY, KHÔNG HỎI VẶN THÊM: Ngay khi người dùng đã cung cấp thông tin cơ bản để soạn, "
        'bổ sung dữ kiện ở lượt tiếp theo, hoặc ra tín hiệu chốt ("soạn giúp mình", "làm luôn đi", '
        '"phần thiếu tự điền", "nơi nhận tôi tự ghi", yêu cầu tạo/xuất tệp ngay): '
        "BẮT BUỘC tạo ngay bản thảo hoàn chỉnh (không hỏi vặn thêm lượt nào nữa):\n"
        "  1. Trao đổi ngắn gọn, tự nhiên với người dùng ở ngoài thẻ tài liệu (nhắc đúng định dạng tệp đang tạo, "
        "không liệt kê các định dạng khác).\n"
        "  2. Đặt TOÀN BỘ thân văn bản sạch (không dính lời chào, lời dẫn hay ghi chú nháp) vào trong cặp thẻ:\n"
        '     <<<DOCUMENT title="Tiêu đề văn bản ngắn gọn" layout="standard|administrative|spreadsheet" format="docx|pdf|xlsx">>>\n'
        "     ...nội dung văn bản bằng Markdown sạch (tiêu đề #, ##, đoạn văn, danh sách, bảng |...|)...\n"
        "     <<<END_DOCUMENT>>>\n"
        '  3. Chọn layout="administrative" cho văn bản hành chính/đơn từ/kế hoạch/tờ trình/báo cáo; '
        'layout="spreadsheet" khi nội dung chủ yếu là bảng số liệu/lịch trình; còn lại dùng layout="standard". '
        'Đặt format="docx", "pdf" hoặc "xlsx" khớp đúng định dạng người dùng yêu cầu.\n'
        "  4. Chỉ dùng kiến thức nền để tổ chức bố cục, văn phong và khung mẫu văn bản. "
        "TUYỆT ĐỐI KHÔNG tự suy đoán hoặc bịa thông tin thực tế của đơn vị/nhà trường "
        "(cơ cấu tổ chức, khoa/viện, ngành đào tạo, số liệu, quy định, mốc thời gian) nếu không có "
        "trong ngữ cảnh hoặc người dùng chưa cung cấp; tự động điền chỗ giữ chỗ rõ ràng dạng [...] hoặc [Tên thông tin] "
        "(ví dụ: [Nơi nhận], [Ngày bắt đầu], [Ngày kết thúc], [Chức vụ/Đơn vị]) cho phần còn thiếu."
    )


def strip_document_markers(text: str, *, remove_blocks: bool = False) -> str:
    """Remove any raw <<<DOCUMENT ...>>> or <<<END_DOCUMENT>>> tags from visible chat text."""
    if not text or "<<<" not in text:
        return text
    cleaned = text
    if remove_blocks:
        cleaned = _DOC_BLOCK_RE.sub("", cleaned)
        cleaned = _UNCLOSED_DOC_BLOCK_RE.sub("", cleaned)
    cleaned = _STRAY_DOC_MARKER_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def disabled_requested_format(
    question: str,
    enabled_formats: list[ExportFormat],
) -> ExportFormat | None:
    """Return the requested format if the user explicitly asks to create/export a disabled format."""
    text = (question or "").strip()
    if not text or not _EXPORT_REQUEST_ACTION_RE.search(text):
        return None
    req_fmt = requested_export_format(text)
    if req_fmt is not None and req_fmt not in enabled_formats:
        return req_fmt
    return None


def disabled_format_refusal_message(fmt: ExportFormat) -> str:
    """Fallback refusal message when the user asks to generate a disabled file format."""
    label = _EXPORT_FORMAT_LABELS.get(fmt, fmt.upper())
    return f"Hiện tại trợ lý không có chức năng tạo tệp định dạng {label}."


def requested_export_format(question: str) -> ExportFormat | None:
    """Return the explicitly requested export format (docx/pdf/xlsx) if present in question."""
    text = (question or "").strip()
    if not text:
        return None
    for fmt, pattern in _REQUESTED_FORMAT_RE:
        if pattern.search(text):
            return fmt
    return None


MAX_DIRECT_HISTORY_TURNS = 6
MAX_HISTORY_QUESTION_CHARS = 800
MAX_HISTORY_ANSWER_CHARS = 1200
MAX_DIRECT_HISTORY_CHARS = 4800


class DirectHistoryEntry(BaseModel):
    turn_id: str | None = None
    question: str
    answer: str = ""


def _truncate_history_text(text: str, limit: int) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(limit - 1, 1)].rstrip() + "…"


def trim_direct_history(
    entries: list[DirectHistoryEntry],
    *,
    max_turns: int = 3,
    max_chars: int = MAX_DIRECT_HISTORY_CHARS,
) -> list[DirectHistoryEntry]:
    """Bound direct-chat history by turn count, per-message length, and total char budget.

    Keeps the most recent turns (always preserving at least the latest turn when
    ``max_turns > 0`` and ``entries`` is non-empty) so long 5-10+ turn sessions
    stay well within quantized Q4 model sweet spots without losing recent context.
    """
    cap = min(max(int(max_turns or 0), 0), MAX_DIRECT_HISTORY_TURNS)
    if cap == 0 or not entries:
        return []
    candidates = [
        DirectHistoryEntry(
            turn_id=item.turn_id,
            question=_truncate_history_text(item.question, MAX_HISTORY_QUESTION_CHARS),
            answer=_truncate_history_text(item.answer, MAX_HISTORY_ANSWER_CHARS),
        )
        for item in entries[-cap:]
    ]
    kept: list[DirectHistoryEntry] = []
    used = 0
    for item in reversed(candidates):
        size = len(item.question) + len(item.answer)
        if kept and used + size > max_chars:
            break
        kept.append(item)
        used += size
    kept.reverse()
    return kept


def active_draft_prompt_context(draft: DocumentDraft | None) -> str:
    """Inject the latest active draft in the session so follow-up export/edit turns stay anchored."""
    if draft is None or not draft.markdown.strip():
        return ""
    body = draft.markdown.strip()
    if len(body) > 4500:
        body = body[:4500].rstrip() + "\n..."
    return (
        "\n\n[BẢN THẢO HIỆN HÀNH TRONG PHIÊN]\n"
        f"Tiêu đề: {draft.title}\n"
        f"Bố cục: {draft.layout}\n"
        "Nội dung hiện tại:\n"
        f"{body}\n"
        "Nếu người dùng yêu cầu xuất định dạng ĐANG BẬT hoặc chỉnh sửa tiếp, hãy bám sát bản thảo hiện hành "
        "này (chỉ thay đổi đúng phần người dùng yêu cầu) và đặt bản thảo hoàn chỉnh vào cặp thẻ "
        "<<<DOCUMENT ...>>> ... <<<END_DOCUMENT>>>."
    )


def drafting_prompt_addon(formats: list[ExportFormat]) -> str:
    """Backward-compatible wrapper returning drafting instructions when export is enabled."""
    if not formats:
        return ""
    return export_policy_prompt_addon(formats)


def _has_markdown_table(text: str) -> bool:
    lines = text.splitlines()
    for idx in range(len(lines) - 1):
        if "|" in lines[idx] and _TABLE_SEP_RE.match(lines[idx + 1]):
            return True
    return False


def _infer_layout(title: str, body: str) -> DocumentLayout:
    if _has_markdown_table(body):
        table_lines = sum(1 for ln in body.splitlines() if ln.strip().startswith("|"))
        non_empty = max(1, sum(1 for ln in body.splitlines() if ln.strip()))
        if table_lines / non_empty >= 0.45:
            return "spreadsheet"
    if _ADMIN_CUES_RE.search(f"{title}\n{body[:400]}"):
        return "administrative"
    return "standard"


def _clean_title(raw: str, fallback: str = "Bản thảo văn bản") -> str:
    cleaned = re.sub(r"^[#*\-\s]+", "", raw or "").strip()
    cleaned = re.sub(r"[*_`]+", "", cleaned).strip(" :.-")
    if not cleaned:
        return fallback
    return cleaned[:120]


def _extract_title_from_markdown(markdown: str, question: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = _clean_title(stripped)
            if title:
                return title
    for line in markdown.splitlines():
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("|")
            and not stripped.startswith("-")
            and len(stripped) <= 100
            and (stripped.isupper() or stripped.startswith("**"))
        ):
            title = _clean_title(stripped)
            if title:
                return title
    q = _clean_title(question, fallback="Bản thảo văn bản")
    return q[:80] if len(q) > 80 else q


def _strip_conversational_edges(text: str) -> str:
    lines = text.strip().splitlines()
    while lines and (not lines[0].strip() or _PREAMBLE_LINE_RE.match(lines[0].strip())):
        lines.pop(0)
    while lines and (not lines[-1].strip() or _EPILOGUE_LINE_RE.match(lines[-1].strip())):
        lines.pop()
    cleaned = "\n".join(lines).strip()
    return cleaned or text.strip()


def _is_preliminary_inquiry(question: str) -> bool:
    text = (question or "").strip()
    if not text or _EXPLICIT_EXPORT_NOW_RE.search(text):
        return False
    return bool(_PRELIMINARY_INQUIRY_RE.search(text)) and len(text) <= 140


def _is_refusal_reply(text: str) -> bool:
    """Detect plain missing-knowledge refusal replies that must never become document drafts."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    return bool(_REFUSAL_REPLY_RE.search(cleaned))


def _clean_html_entities(text: str) -> str:
    """Decode HTML entities (&nbsp;, &#160;, &amp;, ...) and replace NBSP with regular spaces."""
    if not text:
        return text
    cleaned = html.unescape(text) if "&" in text else text
    return cleaned.replace("\u00a0", " ")


def _clean_html_br_to_newlines(text: str) -> str:
    """Convert HTML <br>/<br/> tags to real newlines and decode HTML entities."""
    if not text:
        return text
    cleaned = _clean_html_entities(text)
    if "<" not in cleaned:
        return cleaned.strip()
    replaced = _HTML_BR_RE.sub("\n", cleaned)
    return "\n".join(part.strip() for part in replaced.splitlines()).strip()


def _normalize_draft_markdown(markdown: str) -> str:
    """Decode HTML entities and replace <br>/<br/> outside Markdown table rows with real line breaks.

    Table rows stay single-line so Markdown table syntax stays intact; table cells
    are cleaned separately in ``_split_table_row``.
    """
    lines = _clean_html_entities(markdown or "").splitlines()
    out: list[str] = []
    in_table = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        is_table_header = (
            idx + 1 < len(lines) and "|" in line and bool(_TABLE_SEP_RE.match(lines[idx + 1]))
        )
        if is_table_header:
            in_table = True
            out.append(line)
            continue
        if in_table:
            if "|" in line and stripped:
                out.append(line)
                continue
            in_table = False
        if _HTML_BR_RE.search(line):
            for sub in _HTML_BR_RE.sub("\n", line).splitlines():
                out.append(sub.rstrip())
        else:
            out.append(line)
    return "\n".join(out).strip()


def _normalize_format_attr(raw: str | None) -> ExportFormat | None:
    token = (raw or "").strip().lower()
    if token in ("docx", "word"):
        return "docx"
    if token == "pdf":
        return "pdf"
    if token in ("xlsx", "excel"):
        return "xlsx"
    return None


def resolve_preferred_format(
    draft: DocumentDraft,
    question: str,
    enabled_formats: list[ExportFormat],
) -> DocumentDraft:
    """Resolve a single concrete enabled format for a DocumentDraft."""
    if not enabled_formats:
        return draft.model_copy(update={"preferred_format": None})
    req_fmt = requested_export_format(question)
    preferred: ExportFormat | None = None
    if req_fmt is not None and req_fmt in enabled_formats:
        preferred = req_fmt
    elif draft.preferred_format is not None and draft.preferred_format in enabled_formats:
        preferred = draft.preferred_format
    elif draft.layout == "spreadsheet" and "xlsx" in enabled_formats:
        preferred = "xlsx"
    else:
        preferred = enabled_formats[0]
    if draft.preferred_format == preferred:
        return draft
    return draft.model_copy(update={"preferred_format": preferred})


def extract_document_draft(
    answer_text: str,
    question: str = "",
    *,
    force_heuristic: bool = False,
) -> tuple[str, DocumentDraft | None]:
    """Extract a clean DocumentDraft from an assistant answer.

    Returns ``(display_chat_text, draft)``. When explicit ``<<<DOCUMENT>>>`` markers
    are present, the markers are stripped from ``display_chat_text`` so the chat
    bubble stays conversational while the preview/export receives the clean document.
    """
    raw = (answer_text or "").strip()
    if not raw:
        return raw, None

    match = _DOC_BLOCK_RE.search(raw) or _UNCLOSED_DOC_BLOCK_RE.search(raw)
    if match:
        attrs = dict(_ATTR_RE.findall(match.group("attrs") or ""))
        body = _normalize_draft_markdown(strip_document_markers(match.group("body").strip()))
        if not body:
            cleaned_empty = strip_document_markers(_DOC_BLOCK_RE.sub("", raw))
            return cleaned_empty or raw, None
        title = _clean_title(attrs.get("title") or _extract_title_from_markdown(body, question))
        raw_layout = (attrs.get("layout") or "").strip().lower()
        layout: DocumentLayout = (
            raw_layout
            if raw_layout in ("standard", "administrative", "spreadsheet")
            else _infer_layout(title, body)
        )
        attr_format = _normalize_format_attr(attrs.get("format"))
        outside = strip_document_markers(
            (raw[: match.start()].strip() + "\n\n" + raw[match.end() :].strip()).strip()
        )
        if not outside:
            outside = (
                f"Mình đã soạn xong bản thảo **{title}**. "
                "Bạn có thể xem trước ở khung tài liệu, yêu cầu chỉnh sửa thêm hoặc tải tệp về."
            )
        draft = DocumentDraft(
            title=title,
            layout=layout,
            markdown=body,
            has_tables=_has_markdown_table(body),
            preferred_format=attr_format,
        )
        return outside, draft

    cleaned_raw = strip_document_markers(raw)
    if not force_heuristic and _is_preliminary_inquiry(question):
        return cleaned_raw, None

    has_tables = _has_markdown_table(cleaned_raw)
    heading_count = sum(1 for ln in cleaned_raw.splitlines() if ln.strip().startswith("#"))
    if not force_heuristic and not has_tables and heading_count == 0 and _is_refusal_reply(cleaned_raw):
        return cleaned_raw, None
    has_draft_intent = bool(_DRAFT_INTENT_RE.search(question or ""))
    is_clarifying_reply = "?" in cleaned_raw and not has_tables and heading_count == 0
    looks_like_doc = (
        force_heuristic
        or has_tables
        or heading_count >= 2
        or (heading_count >= 1 and len(cleaned_raw) >= 220)
        or (has_draft_intent and not is_clarifying_reply and len(cleaned_raw) >= 120)
    )
    if not looks_like_doc:
        return cleaned_raw, None

    cleaned_body = _normalize_draft_markdown(_strip_conversational_edges(cleaned_raw))
    title = _extract_title_from_markdown(cleaned_body, question)
    draft = DocumentDraft(
        title=title,
        layout=_infer_layout(title, cleaned_body),
        markdown=cleaned_body,
        has_tables=has_tables,
    )
    return cleaned_raw, draft


def _parse_markdown_tables(markdown: str) -> list[tuple[str, list[str], list[list[str]]]]:
    """Parse all Markdown tables along with their nearest preceding heading."""
    lines = markdown.splitlines()
    tables: list[tuple[str, list[str], list[list[str]]]] = []
    current_heading = ""
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            current_heading = _clean_title(stripped, fallback="")
            i += 1
            continue
        if i + 1 < len(lines) and "|" in lines[i] and _TABLE_SEP_RE.match(lines[i + 1]):
            headers = _split_table_row(lines[i])
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = _split_table_row(lines[i])
                if len(row) < len(headers):
                    row.extend([""] * (len(headers) - len(row)))
                rows.append(row[: len(headers)])
                i += 1
            if headers:
                tables.append((current_heading or f"Bảng {len(tables) + 1}", headers, rows))
            continue
        i += 1
    return tables


def _split_table_row(line: str) -> list[str]:
    text = line.strip().removeprefix("|").removesuffix("|")
    cells: list[str] = []
    for cell in text.split("|"):
        cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cell)
        cleaned = _clean_html_br_to_newlines(cleaned).strip()
        cells.append(cleaned)
    return cells


def _add_inline_runs(paragraph, text: str, *, font_name: str = "Times New Roman", size_pt: int = 13):
    """Render simple Markdown inline bold/italic runs into a python-docx paragraph."""
    cleaned = _HTML_BR_RE.sub("\n", _clean_html_entities(text))
    token_re = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
    pos = 0
    for match in token_re.finditer(cleaned):
        if match.start() > pos:
            run = paragraph.add_run(cleaned[pos : match.start()])
            run.font.name = font_name
            run.font.size = Pt(size_pt)
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
        elif token.startswith("*") and token.endswith("*"):
            run = paragraph.add_run(token[1:-1])
            run.italic = True
        else:
            run = paragraph.add_run(token[1:-1])
        run.font.name = font_name
        run.font.size = Pt(size_pt)
        pos = match.end()
    if pos < len(cleaned):
        run = paragraph.add_run(cleaned[pos:])
        run.font.name = font_name
        run.font.size = Pt(size_pt)


def _set_cell_shading(cell, fill_hex: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


def _set_table_borders(table, color: str = "CBD5E1") -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tbl_pr.append(borders)


def _remove_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "none")
        borders.append(el)
    tbl_pr.append(borders)


def render_docx(draft: DocumentDraft) -> bytes:
    """Render a DocumentDraft into a clean, print-ready A4 .docx file."""
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.0)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(13)
    normal.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    normalized_md = _normalize_draft_markdown(draft.markdown)
    body_upper = normalized_md.upper()
    if draft.layout == "administrative" and "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" not in body_upper:
        hdr_tbl = doc.add_table(rows=1, cols=2)
        hdr_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _remove_table_borders(hdr_tbl)
        left_p = hdr_tbl.cell(0, 0).paragraphs[0]
        left_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = left_p.add_run("TRƯỜNG ĐẠI HỌC QUY NHƠN\n")
        r1.bold = True
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(12)
        r2 = left_p.add_run("[Đơn vị soạn thảo]")
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(12)

        right_p = hdr_tbl.cell(0, 1).paragraphs[0]
        right_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = right_p.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
        r3.bold = True
        r3.font.name = "Times New Roman"
        r3.font.size = Pt(12)
        r4 = right_p.add_run("Độc lập - Tự do - Hạnh phúc")
        r4.bold = True
        r4.underline = True
        r4.font.name = "Times New Roman"
        r4.font.size = Pt(13)

        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(6)

    lines = normalized_md.splitlines()
    first_non_empty = next((ln.strip() for ln in lines if ln.strip()), "")
    if not first_non_empty.startswith("#"):
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_p.paragraph_format.space_before = Pt(4)
        title_p.paragraph_format.space_after = Pt(10)
        tr = title_p.add_run(draft.title.upper() if draft.layout == "administrative" else draft.title)
        tr.bold = True
        tr.font.name = "Times New Roman"
        tr.font.size = Pt(15)

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()
        if not stripped:
            i += 1
            continue
        if stripped in ("---", "***", "___"):
            i += 1
            continue
        # Markdown table
        if i + 1 < len(lines) and "|" in raw_line and _TABLE_SEP_RE.match(lines[i + 1]):
            headers = _split_table_row(raw_line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = _split_table_row(lines[i])
                if len(row) < len(headers):
                    row.extend([""] * (len(headers) - len(row)))
                rows.append(row[: len(headers)])
                i += 1
            if headers:
                table = doc.add_table(rows=1 + len(rows), cols=len(headers))
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                _set_table_borders(table)
                for col_idx, header_text in enumerate(headers):
                    cell = table.cell(0, col_idx)
                    _set_cell_shading(cell, "E6F4F1")
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(3)
                    p.paragraph_format.space_after = Pt(3)
                    run = p.add_run(header_text)
                    run.bold = True
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(12)
                for row_idx, row_vals in enumerate(rows, start=1):
                    for col_idx, val in enumerate(row_vals):
                        cell = table.cell(row_idx, col_idx)
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_before = Pt(2)
                        p.paragraph_format.space_after = Pt(2)
                        _add_inline_runs(p, val, size_pt=12)
                after_tbl = doc.add_paragraph()
                after_tbl.paragraph_format.space_after = Pt(4)
            continue

        # Headings
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading_text = stripped.lstrip("#").strip()
            p = doc.add_paragraph()
            if level == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(8)
                run = p.add_run(heading_text)
                run.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(15)
            elif level == 2:
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(heading_text)
                run.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(14)
            else:
                p.paragraph_format.space_before = Pt(6)
                p.paragraph_format.space_after = Pt(3)
                run = p.add_run(heading_text)
                run.bold = True
                run.font.name = "Times New Roman"
                run.font.size = Pt(13)
            i += 1
            continue

        # Bullet list
        bullet_match = re.match(r"^[-*•]\s+(.*)$", stripped)
        if bullet_match:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            _add_inline_runs(p, bullet_match.group(1))
            i += 1
            continue

        # Numbered list
        num_match = re.match(r"^(\d+[.)])\s+(.*)$", stripped)
        if num_match:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            _add_inline_runs(p, f"**{num_match.group(1)}** {num_match.group(2)}")
            i += 1
            continue

        # Regular paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        _add_inline_runs(p, stripped)
        i += 1

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _safe_sheet_name(raw: str, used: set[str]) -> str:
    cleaned = re.sub(r"[\[\]:*?/\\]", " ", raw or "").strip() or "DuLieu"
    base = cleaned[:28].strip()
    candidate = base
    idx = 2
    while candidate in used:
        candidate = f"{base[:25]}_{idx}"
        idx += 1
    used.add(candidate)
    return candidate


def render_xlsx(draft: DocumentDraft) -> bytes:
    """Render Markdown tables (or structured outline fallback) into a styled .xlsx workbook."""
    wb = Workbook()
    normalized_md = _normalize_draft_markdown(draft.markdown)
    tables = _parse_markdown_tables(normalized_md)
    used_names: set[str] = set()

    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
    header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    body_font = Font(name="Calibri", size=11, color="1E293B")

    def populate_sheet(ws, sheet_title: str, headers: list[str], rows: list[list[str]]) -> None:
        def text_cell(row: int, column: int, value: str):
            cell = ws.cell(row=row, column=column, value=value)
            cell.data_type = "s"  # Draft cells are source text, including formula-like strings.
            return cell

        text_cell(1, 1, sheet_title).font = title_font
        if len(headers) > 1:
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        ws.row_dimensions[1].height = 24

        header_row = 3
        ws.row_dimensions[header_row].height = 22
        for col_idx, h_text in enumerate(headers, start=1):
            cell = text_cell(header_row, col_idx, h_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        for r_offset, row_vals in enumerate(rows, start=1):
            excel_row = header_row + r_offset
            for col_idx, val in enumerate(row_vals, start=1):
                cell = text_cell(excel_row, col_idx, val)
                cell.font = body_font
                cell.border = border
                if r_offset % 2 == 0:
                    cell.fill = zebra_fill
                cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        for col_idx in range(1, len(headers) + 1):
            col_letter = get_column_letter(col_idx)
            max_len = len(str(headers[col_idx - 1]))
            for row_vals in rows:
                if col_idx - 1 < len(row_vals):
                    max_len = max(max_len, *(len(part) for part in str(row_vals[col_idx - 1]).splitlines() or [""]))
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 52)
        ws.freeze_panes = f"A{header_row + 1}"

    if tables:
        for idx, (tbl_title, headers, rows) in enumerate(tables):
            ws = wb.active if idx == 0 else wb.create_sheet()
            ws.title = _safe_sheet_name(tbl_title, used_names)
            populate_sheet(ws, f"{draft.title} — {tbl_title}" if idx > 0 else draft.title, headers, rows)
    else:
        ws = wb.active
        ws.title = _safe_sheet_name(draft.title, used_names)
        outline_rows: list[list[str]] = []
        current_section = "Nội dung chính"
        for line in normalized_md.splitlines():
            stripped = line.strip()
            if not stripped or stripped in ("---", "***", "___"):
                continue
            if stripped.startswith("#"):
                current_section = _clean_title(stripped, fallback=current_section)
            else:
                clean_item = re.sub(r"^[-*•]\s+", "", stripped)
                clean_item = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean_item)
                clean_item = _clean_html_br_to_newlines(clean_item)
                if clean_item:
                    outline_rows.append([current_section, clean_item])
        populate_sheet(ws, draft.title, ["Mục", "Nội dung"], outline_rows or [["Nội dung", normalized_md]])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _markdown_to_simple_html(draft: DocumentDraft) -> str:
    """Convert DocumentDraft markdown to clean HTML for PyMuPDF Story PDF fallback."""
    parts: list[str] = []
    normalized_md = _normalize_draft_markdown(draft.markdown)
    if draft.layout == "administrative" and "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" not in normalized_md.upper():
        parts.append(
            "<table style='width:100%; border:none; margin-bottom:12px;'>"
            "<tr>"
            "<td style='width:45%; text-align:center; border:none;'><b>TRƯỜNG ĐẠI HỌC QUY NHƠN</b><br/>[Đơn vị soạn thảo]</td>"
            "<td style='width:55%; text-align:center; border:none;'><b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b><br/><u><b>Độc lập - Tự do - Hạnh phúc</b></u></td>"
            "</tr></table>"
        )
    lines = normalized_md.splitlines()
    first_non_empty = next((ln.strip() for ln in lines if ln.strip()), "")
    if not first_non_empty.startswith("#"):
        parts.append(f"<h1 style='text-align:center;'>{html.escape(draft.title)}</h1>")

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()
        if not stripped or stripped in ("---", "***", "___"):
            i += 1
            continue
        if i + 1 < len(lines) and "|" in raw_line and _TABLE_SEP_RE.match(lines[i + 1]):
            headers = _split_table_row(raw_line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                row = _split_table_row(lines[i])
                if len(row) < len(headers):
                    row.extend([""] * (len(headers) - len(row)))
                rows.append(row[: len(headers)])
                i += 1
            th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
            tr_html = "".join(
                "<tr>" + "".join(f"<td>{html.escape(v)}</td>" for v in r) + "</tr>"
                for r in rows
            )
            parts.append(f"<table><thead><tr>{th}</tr></thead><tbody>{tr_html}</tbody></table>")
            continue
        if stripped.startswith("#"):
            level = min(3, len(stripped) - len(stripped.lstrip("#")))
            text = html.escape(stripped.lstrip("#").strip())
            parts.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue
        escaped = html.escape(stripped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", escaped)
        parts.append(f"<p>{escaped}</p>")
        i += 1

    css = (
        "body { font-family: sans-serif; font-size: 11pt; line-height: 1.45; color: #1e293b; }"
        "h1 { font-size: 15pt; margin: 8px 0 10px; }"
        "h2 { font-size: 13pt; margin: 10px 0 6px; }"
        "h3 { font-size: 11.5pt; margin: 8px 0 4px; }"
        "p { margin: 4px 0; }"
        "table { width: 100%; border-collapse: collapse; margin: 8px 0; }"
        "th, td { border: 1px solid #cbd5e1; padding: 5px 7px; font-size: 10pt; }"
        "th { background-color: #e6f4f1; font-weight: bold; text-align: left; }"
    )
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(parts)}</body></html>"


def _render_pdf_pymupdf(draft: DocumentDraft) -> bytes:
    """Fallback PDF renderer using PyMuPDF Story on A4 pages."""
    story = pymupdf.Story(html=_markdown_to_simple_html(draft))
    mediabox = pymupdf.paper_rect("a4")
    content_rect = mediabox + (56, 56, -56, -56)
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    more = 1
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(content_rect)
        story.draw(device)
        writer.end_page()
    writer.close()
    return buf.getvalue()


async def render_pdf(draft: DocumentDraft) -> bytes:
    """Render DocumentDraft to PDF via Gotenberg LibreOffice (with PyMuPDF fallback)."""
    docx_bytes = await asyncio.to_thread(render_docx, draft)
    gotenberg_url = (get_settings().GOTENBERG_URL or "").strip().rstrip("/")
    if gotenberg_url:
        target = f"{gotenberg_url}/forms/libreoffice/convert"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    target,
                    files={
                        "files": (
                            "document.docx",
                            docx_bytes,
                            EXPORT_MEDIA_TYPES["docx"],
                        )
                    },
                )
            if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                return resp.content
            logger.warning(
                "document_export_gotenberg_non_pdf",
                status=resp.status_code,
            )
        except Exception as exc:
            logger.warning("document_export_gotenberg_fallback", error=str(exc))
    return await asyncio.to_thread(_render_pdf_pymupdf, draft)


def safe_download_filename(title: str, fmt: ExportFormat) -> str:
    """Build a clean, filesystem-safe filename preserving Vietnamese readability."""
    cleaned = unicodedata.normalize("NFC", title or "ban-thao").strip()
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "ban-thao"
    return f"{cleaned[:80]}.{fmt}"


def content_disposition_header(filename: str) -> str:
    ascii_fallback = (
        unicodedata.normalize("NFKD", filename)
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
    )
    ascii_fallback = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_fallback).strip("_") or "document"
    encoded = quote(filename, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'


def _turn_answer_text(turn: ConversationTurn) -> str:
    result = turn.result or {}
    if not isinstance(result, dict):
        return ""
    if result.get("status") == "direct_reply":
        return str(result.get("answer") or "")
    statements = result.get("statements") or []
    if statements:
        return "\n".join(str(s.get("text") or "") for s in statements if isinstance(s, dict))
    return str(result.get("answer") or "")


async def export_turn_document(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    fmt: ExportFormat,
) -> tuple[bytes, str, str]:
    """Authorize, enforce assistant export toggles, and render the requested file."""
    conversation = await owned(db, actor, workspace_id, conversation_id)
    turn = await db.scalar(
        select(ConversationTurn).where(
            ConversationTurn.id == turn_id,
            ConversationTurn.conversation_id == conversation.id,
        )
    )
    if turn is None:
        raise EntityNotFound("Không tìm thấy lượt hội thoại.", code="conversation_turn_not_found")

    # Enforce live assistant toggle first; fall back to snapshot if assistant was deleted.
    assistant = await db.scalar(
        select(Assistant).where(
            Assistant.id == conversation.assistant_id,
            Assistant.workspace_id == workspace_id,
        )
    )
    live_config = {"rag_policy": assistant.rag_policy} if assistant is not None else conversation.assistant_snapshot
    allowed_formats = enabled_export_formats(live_config)
    if fmt not in allowed_formats:
        raise Forbidden(
            f"Trợ lý hiện không bật xuất định dạng {fmt.upper()}.",
            code="assistant_export_format_disabled",
        )

    trace = turn.rewrite_trace if isinstance(turn.rewrite_trace, dict) else {}
    stored_draft = trace.get("document_draft")
    draft: DocumentDraft | None = None
    if isinstance(stored_draft, dict) and stored_draft.get("markdown"):
        draft = DocumentDraft.model_validate(stored_draft)
    else:
        raw_text = _turn_answer_text(turn)
        _, draft = extract_document_draft(raw_text, turn.question, force_heuristic=True)

    if draft is None or not draft.markdown.strip():
        raise AppException(
            "Lượt hội thoại này chưa có nội dung văn bản hoặc bảng biểu để xuất tệp.",
            code="conversation_turn_no_document",
            status_code=422,
        )

    if fmt == "docx":
        payload = await asyncio.to_thread(render_docx, draft)
    elif fmt == "xlsx":
        payload = await asyncio.to_thread(render_xlsx, draft)
    else:
        payload = await render_pdf(draft)

    filename = safe_download_filename(draft.title, fmt)
    return payload, EXPORT_MEDIA_TYPES[fmt], filename
