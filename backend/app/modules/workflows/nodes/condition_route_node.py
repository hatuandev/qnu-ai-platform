"""Condition Route Node Handler — Evaluates intents and routes DAG execution."""

from __future__ import annotations

import re

from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

_INQUIRY_KEYWORDS: tuple[str, ...] = (
    "cho tôi hỏi",
    "cho em hỏi",
    "cho mình hỏi",
    "cho hỏi",
    "hỏi",
    "thắc mắc",
    "bao nhiêu",
    "thế nào",
    "như thế nào",
    "ở đâu",
    "khi nào",
    "mấy",
    "sao",
    # Tuyển sinh
    "phương thức",
    "điểm chuẩn",
    "học phí",
    "chỉ tiêu",
    "ngành",
    "xét tuyển",
    "hồ sơ",
    "tuyển sinh",
    "đăng ký",
    "học bổng",
    # Quy chế học vụ
    "tín chỉ",
    "quy chế",
    "học phần",
    "cảnh báo học vụ",
    "buộc thôi học",
    "tốt nghiệp",
    "chuẩn đầu ra",
    "vstep",
    "điểm rèn luyện",
    "đrl",
    "gpa",
    # Thư viện
    "giáo trình",
    "tài liệu",
    "sách",
    "luận văn",
    "học liệu",
    "thư viện",
    "mượn trả",
    "turnitin",
    "đạo văn",
    "sciencedirect",
    # Soạn thảo văn bản
    "soạn thảo",
    "tờ trình",
    "công văn",
    "nghị định 30",
    "giấy mời",
    "kế hoạch",
    "thông báo",
    "quyết định",
    "xuất file",
    # Ngân hàng câu hỏi & Khảo thí
    "ma trận",
    "đề thi",
    "ngân hàng câu hỏi",
    "bloom",
    "trắc nghiệm",
    "tự luận",
    "clo",
    "plo",
    "biểu điểm",
    # Thời gian & Khóa
    "năm 202",
    "năm 203",
    "năm nay",
    "học kỳ",
)


_TITLE_PATTERNS = re.compile(
    r"\b("
    r"trợ lý tuyển sinh|trợ lý quy chế đào tạo|trợ lý quy chế|trợ lý học vụ|"
    r"trợ lý thư viện & học liệu số|trợ lý thư viện|trợ lý thư viện số|"
    r"trợ lý soạn thảo văn bản|trợ lý soạn thảo|trợ lý văn bản|"
    r"trợ lý ngân hàng câu hỏi & đề thi|trợ lý ngân hàng câu hỏi|trợ lý khảo thí|trợ lý đề thi|"
    r"trợ lý|ban tuyển sinh|phòng đào tạo|phòng hành chính - tổng hợp|phòng hành chính|phòng khảo thí|"
    r"trung tâm thông tin - thư viện|trung tâm thư viện|thư viện qnu|"
    r"qnu\.ai|qnu|bot|ai|bạn|em|thầy cô|thầy|cô|ad|admin|ạ|nhé|nha|ơi|với|nhỉ|cho tôi|cho em|mình"
    r")\b",
    re.IGNORECASE,
)

_GREETING_WORDS: tuple[str, ...] = (
    "xin chào",
    "chào bạn",
    "chào em",
    "chào thầy",
    "chào cô",
    "kính chào",
    "chào",
    "hello",
    "hi",
    "hey",
    "cảm ơn",
    "cm ơn",
    "thanks",
    "thank you",
    "tạm biệt",
    "bye",
)


def _is_pure_greeting(message: str, tokens: list[str]) -> bool:
    """Check if the message is purely a greeting rather than a substantive inquiry/question."""
    clean_msg = message.strip().lower()
    if not clean_msg:
        return False

    # 1. Any question mark indicates a real inquiry, never a pure greeting
    if "?" in clean_msg:
        return False

    # 2. Strip known greeting words and rule tokens
    remainder = clean_msg
    all_greetings = list(_GREETING_WORDS)
    for t in tokens:
        clean_t = re.sub(r"[^\w\s]", "", t).strip()
        if clean_t and clean_t not in all_greetings:
            all_greetings.append(clean_t)

    for g in sorted(all_greetings, key=len, reverse=True):
        remainder = re.sub(r"(?:^|\W)" + re.escape(g) + r"(?:\W|$)", " ", remainder, flags=re.IGNORECASE)

    # 3. Strip addressee titles and polite particles
    remainder = _TITLE_PATTERNS.sub(" ", remainder)
    clean_remainder = re.sub(r"[!.,~:;/\-_\s]+", "", remainder)

    # 4. If nothing meaningful is left, it's a pure greeting (e.g. "Xin chào Trợ lý Tuyển sinh!", "Hi QNU!")
    if len(clean_remainder) <= 2:
        return True

    # 5. If substantive content remains, check if it contains inquiry keywords
    if any(kw in clean_msg for kw in _INQUIRY_KEYWORDS):
        return False

    return len(clean_remainder) <= 2


class ConditionRouteNodeHandler(BaseNodeHandler):
    """Branches DAG execution based on intent matching rules."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        message = context.node_data.get("user_message", "").lower()
        config = node_spec.config or {}
        rules = config.get("rules", [])
        default_node = config.get("default_node")

        next_target = default_node
        matched_rule_id = None

        for rule in rules:
            match_spec = rule.get("match", {})
            pattern = match_spec.get("intent")
            if pattern:
                tokens = [t.strip() for t in pattern.split("|") if t.strip()]
                is_greeting_rule = (
                    "chào" in pattern.lower()
                    or "hello" in pattern.lower()
                    or "greeting" in rule.get("id", "").lower()
                )
                if is_greeting_rule:
                    if _is_pure_greeting(message, tokens):
                        next_target = rule.get("to")
                        matched_rule_id = rule.get("id")
                        break
                else:
                    safe_regex = r"(?:^|\W)(?:" + "|".join(re.escape(t) for t in tokens) + r")(?:\W|$)"
                    if re.search(safe_regex, message, re.IGNORECASE):
                        next_target = rule.get("to")
                        matched_rule_id = rule.get("id")
                        break

        context.node_data["routed_to"] = next_target
        context.node_data["matched_rule_id"] = matched_rule_id

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "next_node": next_target,
                "matched_rule_id": matched_rule_id,
            },
            next_node_override=next_target,
        )
