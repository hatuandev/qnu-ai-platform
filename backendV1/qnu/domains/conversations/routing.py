"""Route high-confidence conversational turns before rewriting or retrieval."""

import re
import unicodedata

from qnu.domains.conversations.schemas import DirectReply

_GREETING = (
    r"(?:(?:da|vang) )?(?:(?:em|minh|toi) )?"
    r"(?:(?:xin |kinh )?chao|hello|hi|hey|alo|a lo)"
    r"(?: (?:ban|anh|chi|thay|co|tro ly|ad|admin|bot|moi nguoi|there))?"
    r"(?: (?:a|nhe|nha))?"
)
_COURTESY = (
    r"(?:(?:da|vang|ok) )?(?:(?:em|minh|toi) )?"
    r"(?:cam on|thanks|thank you)(?: (?:ban|anh|chi|thay|co|tro ly))?"
    r"(?: (?:rat nhieu|nhieu lam|nhieu|a|nhe|nha))*"
)
_IDENTITY = r"(?:ban|tro ly|bot|chatbot) (?:la ai|ten (?:la )?gi|(?:co the )?(?:giup|ho tro) (?:minh )?gi)"
_PROTECTED_REQUEST = (
    r"(?:hay |vui long |ban co the )?"
    r"(?:cho (?:toi|minh|em) xem|tiet lo|in ra|hien thi|reveal|show(?: me)?) "
    r"(?:(?:toan bo|nguyen van|the|your) )?"
    r"(?:system prompt|prompt he thong|chi dan he thong|chi dan an|"
    r"api key|khoa api|mat khau|access token)"
)


def direct_reply(question: str, assistant_name: str, turn_id: str) -> DirectReply | None:
    decomposed = unicodedata.normalize("NFD", question.casefold().replace("đ", "d"))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    normalized = re.sub(r"[\s,]+", " ", plain).strip(" .!?:;…")
    if re.fullmatch(_GREETING, normalized):
        return DirectReply(
            id=turn_id,
            route="greeting",
            answer=f"Chào bạn! Mình là {assistant_name}. Bạn muốn tra cứu thông tin gì?",
        )
    if re.fullmatch(_COURTESY, normalized):
        return DirectReply(id=turn_id, route="courtesy", answer="Rất vui được hỗ trợ bạn!")
    if re.fullmatch(_IDENTITY, normalized):
        return DirectReply(
            id=turn_id,
            route="identity",
            answer=f"Mình là {assistant_name}. Bạn có thể hỏi mình về tài liệu trong kho tri thức được gắn với trợ lý này.",
        )
    if re.fullmatch(_PROTECTED_REQUEST, normalized):
        return DirectReply(
            id=turn_id,
            route="protected_request",
            answer="Mình không thể cung cấp chỉ dẫn nội bộ hoặc thông tin xác thực.",
        )
    return None
