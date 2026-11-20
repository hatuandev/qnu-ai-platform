"""Output hygiene for model prose; cleaning never adds facts or citations."""

import re

from qnu.domains.rag.answer.schemas import ModelAnswer

VERSION = "qnu.answer.hygiene/v2"

VIETNAMESE_CHAR = re.compile(
    r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)
VIETNAMESE_WORD = re.compile(
    r"\b(?:bạn|mình|giấy|học|trường|ngành|điểm|tuyển|sinh|năm|thông tin|liên hệ|cần|"
    r"không|của|là|và|với|để|khi|nếu|hồ sơ|nhập học|thí sinh|phương thức|đăng ký|"
    r"học phí|xét tuyển|thông báo|hướng dẫn|cung cấp|kiểm tra|nhà trường|sinh viên|"
    r"người|em|cô|chú|anh|chị)\b",
    re.IGNORECASE,
)
ENGLISH_WORD = re.compile(
    r"\b(?:the|and|is|are|was|were|this|that|these|those|with|for|from|need|needs|"
    r"should|must|would|could|you|your|we|our|it|its|not|but|actually|wait|role|"
    r"system|developer|prompt|instruction|format|message|conversation)\b",
    re.IGNORECASE,
)
CJK_IDEOGRAPH_PATTERN = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u2e80-\u2eff\u2f00-\u2fdf\u31c0-\u31ef\u3200-\u32ff\u3300-\u33ff]"
)
CJK_PUNCT_MAP = {
    "、": ", ",
    "，": ", ",
    "。": ". ",
    "！": "! ",
    "？": "? ",
    "：": ": ",
    "；": "; ",
    "（": " (",
    "）": ") ",
    "【": " [",
    "】": "] ",
    "“": '"',
    "”": '"',
    "　": " ",
}
CJK_REPLACEMENTS = (
    ("không cần客气", "không cần khách sáo"),
    ("đừng客气", "đừng khách sáo"),
    ("chớ客气", "chớ khách sáo"),
    ("太客气了", "quá khách sáo"),
    ("不用客气", "không có chi"),
    ("不客气", "đừng khách sáo"),
    ("别客气", "đừng khách sáo"),
    ("客气", "khách sáo"),
    ("不用谢", "không có chi"),
    ("谢谢", "cảm ơn bạn"),
    ("好的", "dạ vâng"),
    ("没事", "không sao"),
    ("没关系", "không sao cả"),
    ("你好", "xin chào"),
    ("您好", "kính chào"),
    ("欢迎", "chào mừng"),
    ("再见", "tạm biệt"),
    ("拜拜", "tạm biệt"),
)
REASONING_SIGNALS = (
    re.compile(r"\b(?:system|developer)\s+(?:role|message|prompt|instructions?|constraints?)\b", re.IGNORECASE),
    re.compile(r"\brole\s*:\s*(?:system|developer|assistant|user)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:chain[- ]of[- ]thought|reasoning_content|message format|prompt format)\b", re.IGNORECASE
    ),
    re.compile(
        r"^\s*(?:phân tích|suy luận|quá trình (?:suy nghĩ|tư duy)|ghi chú nội bộ|nháp)\s*[:：]",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"\b(?:chỉ dẫn|hướng dẫn|prompt) hệ thống\b", re.IGNORECASE),
    re.compile(
        r"^\s*(?:let me|i need to|i will|i'll|the user (?:asks|wants)|we (?:need|must)|"
        r"system prompt|developer prompt)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
)
REASONING_FLOW = re.compile(
    r"(?:^|\n)\s*(?:wait|hmm|no|but|so)\b|\b(?:actually|let me|let's|we need to|"
    r"we must|the user asks|the question is|i need to|so we|but we|no, it'?s)\b",
    re.IGNORECASE,
)


def has_vietnamese(text: str) -> bool:
    return bool(VIETNAMESE_CHAR.search(text) or VIETNAMESE_WORD.search(text))


def has_cjk(text: str) -> bool:
    """Return True if text contains any CJK ideograph character."""
    return bool(CJK_IDEOGRAPH_PATTERN.search(text))


def sanitize_cjk(text: str) -> tuple[str, bool]:
    """Replace common CJK conversational phrases and strip any remaining CJK characters."""
    if not text:
        return text, False
    had_cjk = has_cjk(text) or any(k in text for k in CJK_PUNCT_MAP)
    if not had_cjk:
        return text, False
    result = text
    for phrase, replacement in CJK_REPLACEMENTS:
        result = result.replace(phrase, replacement)
    for punct, replacement in CJK_PUNCT_MAP.items():
        result = result.replace(punct, replacement)
    result = CJK_IDEOGRAPH_PATTERN.sub("", result)
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r" +([,.:;!?])", r"\1", result)
    return result.strip(), True


def looks_foreign(text: str) -> bool:
    head = text.strip()[:1600]
    if has_cjk(head):
        return True
    if len(ENGLISH_WORD.findall(head)) < 6:
        return False
    return len(VIETNAMESE_CHAR.findall(head)) < 6 and len(VIETNAMESE_WORD.findall(head)) < 2


def reasoning_leak(text: str) -> bool:
    if not text.strip():
        return False
    if any(pattern.search(text) for pattern in REASONING_SIGNALS):
        return True
    head = text[:1000]
    return bool(REASONING_FLOW.search(head)) and looks_foreign(head)


def without_reasoning(text: str) -> str:
    if not reasoning_leak(text):
        return text
    lines = text.split("\n")
    cut = next((index for index, line in enumerate(lines) if reasoning_leak(line)), -1)
    if cut <= 0:
        return ""
    head = "\n".join(lines[:cut]).strip()
    return head if head and not reasoning_leak(head) and has_vietnamese(head) else ""


def without_repeated_tail(text: str) -> str:
    if "|" in text:
        return text
    units: list[tuple[int, str]] = []
    start = 0
    for match in re.finditer(r"[.!?](?=\s|$)|\n[ \t]*\n", text):
        value = " ".join(text[start : match.end()].split())
        if value:
            units.append((start, value))
        start = match.end()
    tail = " ".join(text[start:].split())
    if tail:
        units.append((start, tail))
    for period in range(1, 5):
        first = len(units) - period * 3
        if first < 0:
            break
        cycle = [unit[1] for unit in units[first : first + period]]
        if len(" ".join(cycle)) < 120:
            continue
        rest = units[first + period :]
        if all(unit[1] == cycle[index % period] for index, unit in enumerate(rest)):
            return text[: units[first + period][0]].rstrip()
    return text


def clean_text(text: str) -> tuple[str, dict]:
    original = text.strip()
    no_reasoning = without_reasoning(original).strip()
    cjk_cleaned, cjk_removed = sanitize_cjk(no_reasoning)
    trimmed = without_repeated_tail(cjk_cleaned)
    return trimmed, {
        "reasoning_removed": no_reasoning != original,
        "repeated_tail_trimmed": trimmed != cjk_cleaned,
        "cjk_removed": cjk_removed,
    }


def clean_model_answer(answer: ModelAnswer, question: str) -> tuple[ModelAnswer, dict]:
    report = {
        "version": VERSION,
        "reasoning_removed": 0,
        "repeated_tail_trimmed": 0,
        "cjk_removed": 0,
        "dropped_statements": 0,
        "language_mismatch": False,
    }
    statements = []
    for statement in answer.statements:
        text, flags = clean_text(statement.text)
        report["reasoning_removed"] += flags["reasoning_removed"]
        report["repeated_tail_trimmed"] += flags["repeated_tail_trimmed"]
        report["cjk_removed"] += int(flags.get("cjk_removed", False))
        if not text:
            report["dropped_statements"] += 1
            continue
        statements.append(statement.model_copy(update={"text": text}))
    message = answer.message
    if message:
        text, flags = clean_text(message)
        report["reasoning_removed"] += flags["reasoning_removed"]
        report["repeated_tail_trimmed"] += flags["repeated_tail_trimmed"]
        report["cjk_removed"] += int(flags.get("cjk_removed", False))
        message = text or None
    status = answer.status
    if status == "answered" and not statements and not answer.lookups:
        status = "insufficient_evidence"
        message = None
        report["emptied"] = True
    visible = "\n".join(item.text for item in statements) or (message or "")
    report["language_mismatch"] = has_vietnamese(question) and looks_foreign(visible)
    return (
        answer.model_copy(update={"status": status, "statements": statements, "message": message}),
        report,
    )
