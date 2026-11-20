"""Record a deterministic intent hint; routing stays authoritative and unchanged."""

import re
import unicodedata

VERSION = "qnu.conversation.prefilter/v1"

SOCIAL_ROUTES = frozenset({"greeting", "courtesy"})

_SOCIAL_PREFIXES = (
    "xin chào",
    "xin chao",
    "chào",
    "chao",
    "hello",
    "hi",
    "hey",
    "cảm ơn",
    "cám ơn",
    "cam on",
    "cảm on",
    "thanks",
    "thank you",
    "tạm biệt",
    "tam biet",
    "bye",
    "goodbye",
    "chúc",
    "chuc",
    "dạ",
    "da",
    "vâng",
    "vang",
    "ok",
    "oke",
    "ừ",
    "u",
)
_ACKNOWLEDGMENT_PHRASES = (
    "tôi biết rồi",
    "tôi biet roi",
    "tôi hiểu rồi",
    "toi hieu roi",
    "mình biết rồi",
    "minh biet roi",
    "mình hiểu rồi",
    "minh hieu roi",
    "em hiểu rồi",
    "em hieu roi",
    "em biết rồi",
    "em biet roi",
    "dạ hiểu",
    "da hieu",
    "dạ em hiểu",
    "da em hieu",
    "dạ rõ rồi",
    "da ro roi",
    "rõ rồi",
    "ro roi",
    "ok rồi",
    "ok roi",
    "được rồi",
    "duoc roi",
    "cảm ơn",
    "cam on",
    "cảm ơn bạn",
    "cam on ban",
    "cảm ơn trợ lý",
    "cam on tro ly",
    "cảm ơn nhiều",
    "cam on nhieu",
    "thanks",
    "thank you",
    "ok",
    "oke",
)
_WH = frozenset(
    {
        "gì",
        "gi",
        "nào",
        "nao",
        "sao",
        "bao",
        "nhiêu",
        "nhieu",
        "đâu",
        "dau",
        "ai",
        "khi",
        "how",
        "what",
        "when",
        "where",
        "which",
        "why",
        "who",
    }
)
_REQUEST_CUES = (
    "cho tôi biết",
    "cho toi biet",
    "cho mình hỏi",
    "cho minh hoi",
    "cho em hỏi",
    "cho em hoi",
    "tra cứu",
    "tra cuu",
    "tìm hiểu",
    "tim hieu",
    "thông tin",
    "thong tin",
    "quy định",
    "quy dinh",
    "hướng dẫn",
    "huong dan",
    "điều kiện",
    "dieu kien",
    "thủ tục",
    "thu tuc",
    "liệt kê",
    "liet ke",
    "so sánh",
    "so sanh",
    "tóm tắt",
    "tom tat",
    "giải thích",
    "giai thich",
)
_TOKEN = re.compile(r"[^\W\d_]+")


def _normalized(question: str) -> str:
    return unicodedata.normalize("NFC", question).casefold().strip()


def _starts_with(text: str, phrase: str) -> bool:
    if not text.startswith(phrase):
        return False
    rest = text[len(phrase) : len(phrase) + 1]
    return not rest or not rest.isalpha()


def _hint(question: str, *, has_history: bool) -> dict:
    text = _normalized(question)
    tokens = _TOKEN.findall(text)
    signals = []
    if has_history:
        signals.append("history_present")
    social_prefix = next((p for p in _SOCIAL_PREFIXES if _starts_with(text, p)), None)
    if social_prefix:
        signals.append("social_prefix")
    has_wh = any(token in _WH for token in tokens)
    if has_wh:
        signals.append("wh")
    has_digit = any(char.isdigit() for char in text)
    if has_digit:
        signals.append("digit")
    request_cue = next((cue for cue in _REQUEST_CUES if cue in text), None)
    if request_cue:
        signals.append("request_cue")
    ack_match = next(
        (ack for ack in _ACKNOWLEDGMENT_PHRASES if _starts_with(text, ack) or text == ack),
        None,
    )
    if ack_match:
        signals.append("acknowledgment")
    # Acknowledgment phrases in ongoing conversations are directly recognized as courtesy/social
    if ack_match and not has_wh and not has_digit and request_cue is None and len(tokens) <= 8:
        return {"verdict": "social", "confidence": "high", "signals": signals}
    social = (
        not has_history
        and social_prefix is not None
        and not has_wh
        and not has_digit
        and request_cue is None
        and len(tokens) <= 12
    )
    if social:
        return {"verdict": "social", "confidence": "high", "signals": signals}
    if not has_history:
        knowledge = (
            (request_cue is not None and len(tokens) >= 4)
            or (has_digit and len(tokens) >= 2)
            or (has_wh and len(tokens) >= 5)
        )
        if knowledge:
            return {"verdict": "knowledge", "confidence": "high", "signals": signals}
    return {"verdict": "ambiguous", "confidence": "none", "signals": signals}


def classify_turn(question: str, *, has_history: bool) -> dict:
    """Return a shadow verdict only; callers must not route on it."""
    return {"version": VERSION, "has_history": has_history, **_hint(question, has_history=has_history)}


def compare_route(verdict: str, route: str) -> bool | None:
    if verdict == "knowledge":
        return route == "knowledge"
    if verdict == "social":
        return route in SOCIAL_ROUTES
    return None
