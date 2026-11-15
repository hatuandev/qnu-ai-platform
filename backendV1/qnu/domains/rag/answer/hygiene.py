"""Output hygiene for model prose; cleaning never adds facts or citations."""

import re

from qnu.domains.rag.answer.schemas import ModelAnswer

VERSION = "qnu.answer.hygiene/v1"

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


def looks_foreign(text: str) -> bool:
    head = text.strip()[:1600]
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
    cleaned = without_reasoning(original).strip()
    trimmed = without_repeated_tail(cleaned)
    return trimmed, {
        "reasoning_removed": cleaned != original,
        "repeated_tail_trimmed": trimmed != cleaned,
    }


def clean_model_answer(answer: ModelAnswer, question: str) -> tuple[ModelAnswer, dict]:
    report = {
        "version": VERSION,
        "reasoning_removed": 0,
        "repeated_tail_trimmed": 0,
        "dropped_statements": 0,
        "language_mismatch": False,
    }
    statements = []
    for statement in answer.statements:
        text, flags = clean_text(statement.text)
        report["reasoning_removed"] += flags["reasoning_removed"]
        report["repeated_tail_trimmed"] += flags["repeated_tail_trimmed"]
        if not text:
            report["dropped_statements"] += 1
            continue
        statements.append(statement.model_copy(update={"text": text}))
    message = answer.message
    if message:
        text, flags = clean_text(message)
        report["reasoning_removed"] += flags["reasoning_removed"]
        report["repeated_tail_trimmed"] += flags["repeated_tail_trimmed"]
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
