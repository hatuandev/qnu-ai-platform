"""Query Rewrite Node Handler — Normalizes user queries, corrects contextual typos and expands abbreviations."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any

from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service
from app.modules.workflows.nodes.base import (
    BaseNodeHandler,
    NodeExecutionResult,
    WorkflowContext,
)
from app.modules.workflows.schemas import WorkflowNodeSpec

logger = logging.getLogger(__name__)

# Fast Rule-based term mappings (0ms latency)
_ACRONYM_MAP: dict[str, str] = {
    r"\bcntt\b": "Công nghệ thông tin",
    r"\bit\b": "Công nghệ thông tin",
    r"\bqtkd\b": "Quản trị kinh doanh",
    r"\bqtnl\b": "Quản trị nhân lực",
    r"\btckt\b": "Tài chính - Ngân hàng",
    r"\btcnh\b": "Tài chính - Ngân hàng",
    r"\bkhmt\b": "Khoa học máy tính",
    r"\bktpm\b": "Kỹ thuật phần mềm",
    r"\bnna\b": "Ngôn ngữ Anh",
    r"\bsp toán\b": "Sư phạm Toán học",
    r"\bsp tin\b": "Sư phạm Tin học",
    r"\bsp lý\b": "Sư phạm Vật lý",
    r"\bsp hóa\b": "Sư phạm Hóa học",
    r"\bsp văn\b": "Sư phạm Ngữ văn",
    r"\bsp anh\b": "Sư phạm Tiếng Anh",
    r"\bsp sử\b": "Sư phạm Lịch sử",
    r"\bsp địa\b": "Sư phạm Địa lý",
    r"\bsp sinh\b": "Sư phạm Sinh học",
    r"\bđgnl\b": "Đánh giá năng lực",
    r"\bdgnl\b": "Đánh giá năng lực",
    r"\bthptqg\b": "THPT Quốc gia",
    r"\bthpt\b": "THPT",
    r"\bktx\b": "Ký túc xá",
    r"\bnd\s*116\b": "Nghị định 116",
    r"\bnghị định 116\b": "Nghị định 116",
    r"\bgdmn\b": "Giáo dục Mầm non",
    r"\bgdth\b": "Giáo dục Tiểu học",
    # Academic regulations & university life acronyms
    r"\bđrl\b": "Điểm rèn luyện",
    r"\bdrl\b": "Điểm rèn luyện",
    r"\bgpa\b": "GPA",
    r"\bctđt\b": "Chương trình đào tạo",
    r"\bctsv\b": "Công tác sinh viên",
    r"\bpđt\b": "Phòng Đào tạo",
    r"\bpctsv\b": "Phòng Công tác sinh viên",
    r"\bnckh\b": "Nghiên cứu khoa học",
    r"\bkhcn\b": "Khoa học - Công nghệ",
}

# Contextual typo patterns (e.g. valid Vietnamese words mistyped in context)
_TYPO_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # "ngày" mistyped instead of "ngành" when referring to majors / admissions
    (
        re.compile(
            r"\bngày\s+(công nghệ thông tin|cntt|khoa học máy tính|kỹ thuật phần mềm|quản trị kinh doanh|qtkd|kế toán|tài chính|kinh tế|sư phạm|ngôn ngữ|luật|du lịch|đào tạo|học\b)",
            re.IGNORECASE,
        ),
        r"ngành \1",
    ),
    (
        re.compile(
            r"\b(học phí|điểm chuẩn|chỉ tiêu|thông tin|xét tuyển|tuyển sinh|mã|chương trình)\s+ngày\b",
            re.IGNORECASE,
        ),
        r"\1 ngành",
    ),
    (re.compile(r"\b(các|những|tất cả các|danh sách|tuyển)\s+ngày\b", re.IGNORECASE), r"\1 ngành"),
    (re.compile(r"\bngày\s+(nào|gì|hot|mới)\b", re.IGNORECASE), r"ngành \1"),
    # "học bà" -> "học bạ"
    (re.compile(r"\bhọc\s+bà\b", re.IGNORECASE), "học bạ"),
    # "tín chì" -> "tín chỉ"
    (re.compile(r"\btín\s+chì\b", re.IGNORECASE), "tín chỉ"),
    # "học phầm" -> "học phần"
    (re.compile(r"\bhọc\s+phầm\b", re.IGNORECASE), "học phần"),
    # "rèn luyên" -> "rèn luyện"
    (re.compile(r"\brèn\s+luyên\b", re.IGNORECASE), "rèn luyện"),
    # "khen thướng" -> "khen thưởng"
    (re.compile(r"\bkhen\s+thướng\b", re.IGNORECASE), "khen thưởng"),
    # "giáo trinh" -> "giáo trình"
    (re.compile(r"\bgiáo\s+trinh\b", re.IGNORECASE), "giáo trình"),
    # "tài liêu" -> "tài liệu"
    (re.compile(r"\btài\s+liêu\b", re.IGNORECASE), "tài liệu"),
    # "quy trinh" -> "quy trình"
    (re.compile(r"\bquy\s+trinh\b", re.IGNORECASE), "quy trình"),
    # "điểm chuẫn" / "điễm chuẩn" -> "điểm chuẩn"
    (re.compile(r"\bđi[ểẽ]m\s+chu[ẫẩẳãả]n\b", re.IGNORECASE), "điểm chuẩn"),
    # "kí túc sá" / "ký túc sá" -> "ký túc xá"
    (re.compile(r"\bk[íy]\s+túc\s+s[áa]\b", re.IGNORECASE), "ký túc xá"),
    # "học bỗng" -> "học bổng"
    (re.compile(r"\bhọc\s+b[ỗõ]ng?\b", re.IGNORECASE), "học bổng"),
    # "sư pham" (missing dot) / "sư phạn" (typo n) -> "sư phạm"
    (re.compile(r"\bsư\s+(?:pham|phạn)\b", re.IGNORECASE), "sư phạm"),
    # "chỉ tiệu" -> "chỉ tiêu"
    (re.compile(r"\bchỉ\s+tiệu\b", re.IGNORECASE), "chỉ tiêu"),
    # "tuyển xính" -> "tuyển sinh"
    (re.compile(r"\btuyển\s+xính\b", re.IGNORECASE), "tuyển sinh"),
]

# Paraphrase expansion: "môn học nào để xét tuyển" -> "tổ hợp môn xét tuyển".
# Prevents Hybrid RAG from favoring Phụ lục 1 (môn thi HSG / xét tuyển thẳng)
# when the user actually asks for Trang 6 subject combinations.
_SUBJECT_COMBO_PARAPHRASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bnhững\s+môn\s+học\s+nào\b", re.IGNORECASE), "những tổ hợp môn nào"),
    (
        re.compile(r"(?<!tổ hợp\s)\bmôn\s+học\s+nào\b", re.IGNORECASE),
        "tổ hợp môn nào",
    ),
    (
        re.compile(r"(?<!tổ hợp\s)\bmôn\s+nào\s+để\s+xét\s+tuyển\b", re.IGNORECASE),
        "tổ hợp môn nào để xét tuyển",
    ),
    (
        re.compile(r"(?<!tổ hợp\s)\bmôn\s+học\s+để\s+xét\s+tuyển\b", re.IGNORECASE),
        "tổ hợp môn để xét tuyển",
    ),
    (
        re.compile(r"\bcần\s+học\s+môn\s+gì(?:\s+để\s+xét\s+tuyển)?\b", re.IGNORECASE),
        "cần xét tuyển tổ hợp môn gì",
    ),
    (
        re.compile(r"(?<!cần\s)\bhọc\s+môn\s+gì(?:\s+để\s+xét\s+tuyển)?\b", re.IGNORECASE),
        "xét tuyển tổ hợp môn gì",
    ),
]

_DIRECT_ADMISSION_MARKERS: tuple[str, ...] = (
    "học sinh giỏi",
    "tuyển thẳng",
    "ưu tiên xét tuyển",
)


def expand_subject_combo_paraphrase(text: str) -> str:
    """Expand ambiguous 'môn học' phrasing into explicit 'tổ hợp môn' wording."""
    if not text:
        return text
    lowered = text.lower()
    if "tổ hợp" in lowered:
        return text
    if any(marker in lowered for marker in _DIRECT_ADMISSION_MARKERS):
        return text
    if "xét tuyển" not in lowered and "ngành" not in lowered:
        return text
    expanded = text
    for pattern, replacement in _SUBJECT_COMBO_PARAPHRASES:
        if "tổ hợp" in expanded.lower() and "tổ hợp" in replacement.lower():
            continue
        expanded = pattern.sub(replacement, expanded)
    return expanded


# Canonical major capitalizations for standardized retrieval (matched longest first)
_CANONICAL_MAJORS: dict[str, str] = {
    r"\bsư phạm toán học\b": "Sư phạm Toán học",
    r"\bsư phạm toán(?!\s*học)\b": "Sư phạm Toán học",
    r"\bsư phạm ngữ văn\b": "Sư phạm Ngữ văn",
    r"\bsư phạm tiếng anh\b": "Sư phạm Tiếng Anh",
    r"\bsư phạm tin học\b": "Sư phạm Tin học",
    r"\bsư phạm vật lý\b": "Sư phạm Vật lý",
    r"\bsư phạm hóa học\b": "Sư phạm Hóa học",
    r"\bsư phạm sinh học\b": "Sư phạm Sinh học",
    r"\bsư phạm lịch sử\b": "Sư phạm Lịch sử",
    r"\bsư phạm địa lý\b": "Sư phạm Địa lý",
    r"\bcông nghệ thông tin\b": "Công nghệ thông tin",
    r"\bquản trị kinh doanh\b": "Quản trị kinh doanh",
    r"\bquản trị nhân lực\b": "Quản trị nhân lực",
    r"\btài chính\s*-\s*ngân hàng\b": "Tài chính - Ngân hàng",
    r"\bkhoa học máy tính\b": "Khoa học máy tính",
    r"\bkỹ thuật phần mềm\b": "Kỹ thuật phần mềm",
    r"\bngôn ngữ anh\b": "Ngôn ngữ Anh",
}


def fast_rule_normalize(text: str, extra_acronyms: dict[str, str] | None = None) -> str:
    """Apply rule-based acronym expansion and contextual typo correction in 0ms.

    `extra_acronyms` allows each new assistant to inject domain abbreviations
    via node config `custom_acronyms` without code changes.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", text.strip())

    # 1. Apply typo pattern replacements
    for pattern, replacement in _TYPO_PATTERNS:
        normalized = pattern.sub(replacement, normalized)

    # 1b. Expand ambiguous subject-combo paraphrases before acronyms
    normalized = expand_subject_combo_paraphrase(normalized)

    # 2. Apply acronym replacements (universal + per-assistant custom)
    for pat_str, replacement in _ACRONYM_MAP.items():
        normalized = re.sub(pat_str, replacement, normalized, flags=re.IGNORECASE)
    if extra_acronyms:
        for pat_str, replacement in extra_acronyms.items():
            if pat_str and replacement:
                normalized = re.sub(pat_str, replacement, normalized, flags=re.IGNORECASE)

    # 3. Apply canonical major capitalizations
    for pat_str, replacement in _CANONICAL_MAJORS.items():
        normalized = re.sub(pat_str, replacement, normalized, flags=re.IGNORECASE)

    # 4. Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def get_node_instruction(context: WorkflowContext, config: dict[str, Any]) -> str:
    """Resolve query rewrite instruction for this node.
    
    Priority:
    1. Explicit instruction/prompt configured directly on this DAG node.
    2. Role description from the executing assistant profile (if attached).
    3. Generic universal prompt for QNU AI Platform.
    """
    # 1. Explicit instruction or prompt configured on this DAG node
    node_instruction = (
        config.get("instruction")
        or config.get("prompt")
        or config.get("custom_prompt")
    )
    if node_instruction and str(node_instruction).strip():
        return str(node_instruction).strip()

    # 2. If a simple domain string is provided (e.g. 'ký túc xá', 'khảo thí')
    domain = config.get("domain")
    if domain and str(domain).strip():
        return (
            f"Bạn là trợ lý chuẩn hóa câu hỏi trong quy trình {str(domain).strip()} cho Trường Đại học Quy Nhơn (QNU).\n"
            "Nhiệm vụ: Sửa các từ gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh tiếng Việt, "
            "chuẩn hóa các từ viết tắt chuyên môn và viết hoa chuẩn danh từ riêng, thuật ngữ."
        )

    # 3. Inherit role context from Assistant Profile if running under an assistant
    profile = context.assistant_profile
    if profile:
        persona_scope = getattr(profile, "persona_scope", None)
        role_desc = None
        if persona_scope:
            role_desc = getattr(persona_scope, "persona", None) or getattr(
                persona_scope, "role_description", None
            )
            if role_desc:
                role_desc = str(role_desc).strip()
            assistant_label = getattr(profile, "name", None) or getattr(
                profile, "assistant_code", "Trợ lý QNU"
            )
            return (
                f"Bạn là trợ lý chuẩn hóa câu hỏi cho quy trình '{assistant_label}' "
                f"của Trường Đại học Quy Nhơn (QNU) ({role_desc}).\n"
                "Nhiệm vụ: Sửa các từ gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh tiếng Việt, "
                "chuẩn hóa các từ viết tắt chuyên môn và viết hoa chuẩn danh từ riêng, thuật ngữ."
            )

    # 4. Universal fallback for any workflow on QNU AI Platform
    return (
        "Bạn là trợ lý chuẩn hóa câu hỏi cho Trường Đại học Quy Nhơn (QNU).\n"
        "Nhiệm vụ: Sửa các từ gõ nhầm trượt phím Telex hoặc nhầm lẫn ngữ cảnh tiếng Việt, "
        "chuẩn hóa các từ viết tắt chuyên môn và viết hoa chuẩn danh từ riêng, thuật ngữ."
    )


_AFFIRMATIVE_SHORT_CUES = re.compile(
    r"^(có|ừ|vâng|được|tôi muốn|có tôi muốn|muốn|muốn ạ|muốn biết|tiếp đi|chi tiết đi|"
    r"nói rõ hơn|tìm hiểu thêm|xem thêm|ok|chỉ tiêu|phương thức|có chứ|rất muốn|"
    r"cho tôi biết|cho mình biết|hãy chia sẻ thêm|bạn chia sẻ đi|bạn nói đi|chia sẻ đi)$",
    re.IGNORECASE,
)

# Demonstratives, relative pronouns, and ellipsis cues in Vietnamese
_CONTEXT_DEPENDENT_MARKERS = re.compile(
    r"\b(ngành này|ngành đó|ngành trên|chuyên ngành này|chuyên ngành đó|khoa này|môn này|"
    r"thế còn|vậy còn|còn nó|ở đâu|bao giờ|tại sao|nó|này|đó|kia|trên)\b",
    re.IGNORECASE,
)


def _unaccent(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.replace("đ", "d").replace("Đ", "d")


# Common functional/conversational words that do not carry specific domain content
_FUNCTIONAL_STOPWORDS: frozenset[str] = frozenset(
    {
        "bạn", "biết", "không", "cho", "nào", "tôi", "xin", "chào", "năm",
        "được", "các", "những", "với", "của", "thế", "như", "bao", "nhiêu",
        "gì", "là", "và", "trong", "trường", "đại", "học", "muốn", "hỏi",
        "xét", "tuyển", "gồm", "danh", "sách", "thì", "sao", "ra", "vào",
        "ở", "tại", "có", "hay", "hoặc", "nhé", "ạ", "ơi", "này", "đó",
        "kia", "tất", "cả", "ai", "mấy", "sẽ", "đã", "đang", "về", "lại",
        "đi", "nhất", "hơn", "theo", "ngay", "liệu", "thông", "tin", "cần",
        "để", "ý", "em", "anh", "chị", "mình", "người", "ta",
    }
)

_UNACCENTED_FUNCTIONAL_STOPWORDS: frozenset[str] = frozenset(
    _unaccent(w) for w in _FUNCTIONAL_STOPWORDS
) | {"hoi", "voi", "nhe", "nhi"}

_CORE_INTENT_TERMS: tuple[str, ...] = (
    "phương thức",
    "học phí",
    "chỉ tiêu",
    "điểm chuẩn",
    "học bổng",
    "ký túc xá",
    "thời gian",
    "hạn chót",
    "lệ phí",
    "điều kiện",
    "thủ tục",
    "hồ sơ",
    "quy định",
    "chuẩn đầu ra",
    "tín chỉ",
    "giáo trình",
    "tài liệu",
    "ma trận",
    "ngân hàng câu hỏi",
)

_COMBO_SUBJECT_TERMS: tuple[str, ...] = (
    "toán", "lý", "hóa", "sinh", "văn", "sử", "địa", "tin", "tiếng anh", "ngoại ngữ"
)


def is_context_dependent_query(text: str) -> bool:
    """Determine whether a query is context-dependent and requires history to understand.

    A standalone complete sentence (e.g. 'Phương thức xét tuyển của trường gồm những gì?',
    'Học phí ngành Sư phạm Toán học là bao nhiêu?') does NOT depend on past conversational
    turns. Passing unrelated history causes recency bias and context bleeding.
    """
    if not text:
        return False
    clean = text.strip()
    words = re.findall(r"\w+", clean)
    if not words:
        return False

    # 1. Short affirmative responses (e.g. 'có', 'tôi muốn', 'tiếp đi', 'chi tiết đi')
    if _AFFIRMATIVE_SHORT_CUES.search(clean):
        return True

    # 2. Contains demonstratives or anaphora pointing back to prior turn
    if _CONTEXT_DEPENDENT_MARKERS.search(clean):
        return True

    # 3. Sentence fragment (<= 4 words) without full subject or verb
    # e.g., 'học phí bao nhiêu?', 'điểm chuẩn thế nào?', 'thế còn ngành CNTT?'
    return len(words) <= 4


def extract_entity_from_text(text: str) -> str | None:
    """Extract major or entity name from previous conversational turn."""
    if not text:
        return None
    for pat, canonical in _CANONICAL_MAJORS.items():
        if re.search(pat, text, re.IGNORECASE):
            return f"ngành {canonical}"
    m = re.search(
        r"\bngành\s+([a-zA-ZÀ-ỹ\s]+?)(?:\s+tại|\s+của|\s+ở|\s+xét|\s+cần|\s+không|\?|$)",
        text,
        re.IGNORECASE,
    )
    if m:
        name = m.group(1).strip()
        if (
            len(name) > 2
            and len(name.split()) <= 5
            and not any(
                p in name.lower()
                for p in ("cụ thể", "nào", "gì", "bất kỳ", "khác", "này", "đó", "mới")
            )
        ):
            return f"ngành {name}"
    return None


def resolve_multiturn_query(
    raw_query: str, history: list[dict[str, Any]] | None
) -> str | None:
    """Resolve short affirmative or pronoun follow-up queries using conversation history in 0ms."""
    if not history or not raw_query:
        return None
    query_clean = raw_query.strip()

    last_assistant = ""
    last_user = ""
    for msg in reversed(history):
        role = msg.get("role")
        content = str(msg.get("content") or "")
        if role == "assistant" and not last_assistant:
            last_assistant = content
        elif role == "user" and not last_user:
            last_user = content
        if last_assistant and last_user:
            break

    detected_entity = extract_entity_from_text(last_user) or extract_entity_from_text(last_assistant)

    # 1. Pronoun substitution (e.g. 'học phí ngành này' -> 'học phí ngành Công nghệ thông tin')
    if detected_entity:
        pronoun_sub = re.sub(
            r"\b(ngành này|ngành đó|chuyên ngành này|chuyên ngành đó)\b",
            detected_entity,
            query_clean,
            flags=re.IGNORECASE,
        )
        if pronoun_sub.lower() != query_clean.lower():
            return pronoun_sub

    # 2. Affirmative short response (e.g. 'có tôi muốn', 'vâng', 'tiếp đi')
    is_affirmative = bool(_AFFIRMATIVE_SHORT_CUES.search(query_clean)) or (
        len(query_clean.split()) <= 4
        and any(w in query_clean.lower() for w in ("có", "muốn", "tiếp", "thêm", "vâng", "ừ", "được"))
    )
    if is_affirmative and last_assistant:
        m = re.search(
            r"(?:chia sẻ thêm|tìm hiểu thêm|thông tin về)\s+([^?.\n]+?)(?:\s+áp dụng cho|\s+cho ngành|\s+không|\?|$)",
            last_assistant,
            re.IGNORECASE,
        )
        if m:
            topic = m.group(1).strip()
            topic = re.sub(r"\bhoặc\b", "và", topic, flags=re.IGNORECASE)
            topic = re.sub(r"^(thông tin về|về)\s+", "", topic, flags=re.IGNORECASE)
            entity_suffix = f" {detected_entity}" if detected_entity else ""
            return f"{topic.capitalize()}{entity_suffix}".strip()

        if detected_entity:
            return f"Chỉ tiêu và phương thức tuyển sinh {detected_entity}"

    return None


def build_rewrite_prompt(
    query: str, instruction: str, history: list[dict[str, Any]] | None = None
) -> str:
    """Build rewrite prompt with few-shot formatting rules using the workflow instruction and optional history."""
    # If the user specified a full template with {query} placeholder, honor it directly
    if "{query}" in instruction:
        return instruction.replace("{query}", query)

    history_context = ""
    if history:
        turns: list[str] = []
        for msg in history[-4:]:
            role_label = "Người dùng" if msg.get("role") == "user" else "Trợ lý AI"
            content = str(msg.get("content") or "").strip()
            if content:
                turns.append(f"- {role_label}: {content[:250]}")
        if turns:
            history_context = "LỊCH SỬ TRAO ĐỔI GẦN NHẤT:\n" + "\n".join(turns) + "\n\n"

    return (
        f"{instruction.strip()}\n\n"
        f"{history_context}"
        "QUY TẮC BẮT BUỘC:\n"
        "- Bạn KHÔNG PHẢI chatbot nói chuyện với người dùng. Nhiệm vụ của bạn CHỈ LÀ chuẩn hóa câu hỏi đầu vào (sửa lỗi gõ nhầm Telex, chính tả, viết tắt).\n"
        "- NẾU CÂU HỎI ĐÃ ĐỦ RÕ RÀNG HOẶC LÀ CÂU HỎI ĐỘC LẬP: BẮT BUỘC GIỮ NGUYÊN NGUYÊN VĂN CÂU HỎI. TUYỆT ĐỐI KHÔNG TỰ Ý ĐỔI SANG CHỦ ĐỀ KHÁC.\n"
        "- Nếu câu hỏi là phản hồi ngắn (ví dụ: 'có', 'tôi muốn', 'tiếp đi') hoặc chứa đại từ ('ngành đó', 'ở đâu'), "
        "mới kết hợp Lịch sử trao đổi để khôi phục thành một câu hỏi tra cứu độc lập, hoàn chỉnh.\n"
        "- TUYỆT ĐỐI KHÔNG tự ý suy diễn hoặc gán ghép tên ngành/tổ hợp môn từ lịch sử vào câu hỏi hiện tại nếu câu hỏi gốc KHÔNG yêu cầu.\n"
        "- Nếu câu hỏi là câu hỏi chung (ví dụ: câu hỏi về thủ tục, chính sách chung, cơ sở vật chất), hãy giữ nguyên tính chất câu hỏi chung, không ép buộc một chuyên ngành hay đối tượng cụ thể.\n"
        "- Giữ nguyên 100% ý định câu hỏi gốc của người dùng.\n"
        "- Trả về DUY NHẤT một dòng chứa câu hỏi đã được chuẩn hóa.\n"
        "- TUYỆT ĐỐI KHÔNG giải thích, KHÔNG hỏi ngược lại người dùng (không dùng 'Bạn muốn...', 'Vui lòng...'), KHÔNG thêm tiền tố, KHÔNG trả lời câu hỏi.\n\n"
        "Ví dụ:\n"
        "Input: học phí ngày cntt là bao nhiêu\n"
        "Học phí ngành Công nghệ thông tin là bao nhiêu?\n\n"
        "Input: quy định xét học bỗng đrl tín chì\n"
        "Quy định xét học bổng điểm rèn luyện và tín chỉ như thế nào?\n\n"
        "Input: chỉ tiêu tuyển sinh nghành sp toán\n"
        "Chỉ tiêu tuyển sinh ngành Sư phạm Toán học là bao nhiêu?\n\n"
        "Input: Điều kiện đăng ký nội trú ký túc xá gồm những gì?\n"
        "Điều kiện đăng ký nội trú ký túc xá gồm những gì?\n\n"
        f"Input: {query}"
    )


class QueryRewriteNodeHandler(BaseNodeHandler):
    """Normalizes user query, corrects contextual typos, and expands terminology per workflow."""

    async def execute(
        self, node_spec: WorkflowNodeSpec, context: WorkflowContext
    ) -> NodeExecutionResult:
        raw_query = context.node_data.get("user_message") or context.inputs.get("message", "")
        if not raw_query:
            return NodeExecutionResult(
                node_id=node_spec.id,
                status="completed",
                output={"normalized_query": "", "original_query": "", "modified": False},
            )

        config = node_spec.config or {}
        use_fast_rules = config.get("use_fast_rules", True)
        use_llm = config.get("use_llm", True)
        custom_acronyms = config.get("custom_acronyms")
        if not isinstance(custom_acronyms, dict):
            custom_acronyms = None

        # Stage 0: Multi-turn Context Resolution (0ms, recovers context from history)
        history = (
            context.inputs.get("conversation_history")
            or context.node_data.get("conversation_history")
            or []
        )
        multiturn_query = resolve_multiturn_query(raw_query, history)
        query_to_normalize = multiturn_query if multiturn_query else raw_query

        # Stage 1: Fast Rule-based Normalization (0ms, reusable per-assistant)
        rule_normalized = (
            fast_rule_normalize(query_to_normalize, extra_acronyms=custom_acronyms)
            if use_fast_rules
            else query_to_normalize
        )
        final_query = rule_normalized

        # Determine whether history should be exposed to LLM rewrite
        # Standalone complete queries must NOT receive past history to prevent context bleeding
        is_dependent = is_context_dependent_query(raw_query)
        effective_history = history if is_dependent else None

        # Stage 2: Fast Contextual LLM Rewrite (optional, ~150ms)
        # Skip LLM if Stage 0 already produced a full multi-turn query
        if use_llm and context.db and not multiturn_query:
            try:
                llm_query = await self._rewrite_with_llm(
                    context, rule_normalized, config=config, history=effective_history
                )
                if llm_query and len(llm_query) >= 3:
                    final_query = llm_query
            except Exception as exc:
                logger.warning(
                    "LLM query rewrite skipped due to %s: %s. Using rule-normalized query.",
                    type(exc).__name__,
                    exc,
                )

        # Store in workflow context for downstream nodes (e.g. knowledge_answer)
        context.node_data["raw_query"] = raw_query
        context.node_data["normalized_query"] = final_query
        context.node_data["user_message"] = final_query

        was_modified = final_query.strip().lower() != raw_query.strip().lower()
        if was_modified:
            logger.info("Query rewritten: '%s' -> '%s'", raw_query, final_query)

        return NodeExecutionResult(
            node_id=node_spec.id,
            status="completed",
            output={
                "normalized_query": final_query,
                "original_query": raw_query,
                "modified": was_modified,
            },
        )

    async def _rewrite_with_llm(
        self,
        context: WorkflowContext,
        query: str,
        config: dict[str, Any] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> str | None:
        """Call fast LLM with thinkingBudget=0 to correct contextual typos without altering intent."""
        if not context.db:
            return None

        node_cfg = config or {}
        instruction = get_node_instruction(context, node_cfg)
        prompt = build_rewrite_prompt(query, instruction, history=history)

        profile = context.assistant_profile
        primary_model = (
            profile.model_policy.primary_model
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else None
        )
        fallback_model = (
            profile.model_policy.fallback_model
            if (profile and hasattr(profile, "model_policy") and profile.model_policy)
            else None
        )

        req = LLMGenerateRequest(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.0,
            max_tokens=200,
            thinking_budget=0,
            preferred_model_name=primary_model,
            fallback_model_name=fallback_model,
        )

        # Enforce 3.0s timeout to never stall chat pipeline
        try:
            res = await asyncio.wait_for(
                modelops_service.generate(context.db, req),
                timeout=3.0,
            )
            raw_text = res.content.strip()
            if not raw_text or "[Local " in raw_text or "máy chủ AI nội bộ" in raw_text or "Đã ghi nhận yêu cầu" in raw_text:
                logger.debug("LLM query rewrite returned fallback mock, keeping rule query.")
                return query

            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if not lines:
                return query

            filtered_lines: list[str] = []
            for line in lines:
                cleaned = re.sub(
                    r"^(output|input|kết quả|câu hỏi|sửa lại|note):\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip().strip('"').strip("'")
                if cleaned and not cleaned.endswith(":") and len(cleaned) > 3:
                    filtered_lines.append(cleaned)

            candidate = filtered_lines[-1] if filtered_lines else lines[-1]
            candidate = re.sub(
                r"^(output|input|kết quả|câu hỏi|sửa lại|note):\s*",
                "",
                candidate,
                flags=re.IGNORECASE,
            ).strip().strip('"').strip("'")

            # Defensive guard 1: Reject meta-instruction / chatbot prompt leakage
            leakage_patterns = re.compile(
                r"(bạn muốn chuẩn hóa|vui lòng cung cấp|hãy nhập|tôi là trợ lý|chào bạn|"
                r"câu hỏi đầu vào|yêu cầu xử lý|hệ thống|bạn có thể hỏi|chuẩn hóa câu hỏi nào|"
                r"xin vui lòng|vui lòng cho biết)",
                re.IGNORECASE,
            )
            if leakage_patterns.search(candidate):
                logger.warning(
                    "LLM query rewrite leaked chatbot conversational meta '%s', fallback to original.",
                    candidate,
                )
                return query

            query_unaccented = _unaccent(query.lower())
            cand_unaccented = _unaccent(candidate.lower())

            # Defensive guard 2: Significant keywords recall check (prevent hallucinations & context hijacking)
            # Use unaccented tokens to accommodate unaccented or typo-laden user queries
            query_words = {
                _unaccent(w)
                for w in re.findall(r"\w+", query.lower())
                if len(_unaccent(w)) >= 2 and _unaccent(w) not in _UNACCENTED_FUNCTIONAL_STOPWORDS
            }
            cand_words = {
                _unaccent(w)
                for w in re.findall(r"\w+", candidate.lower())
                if len(_unaccent(w)) >= 2
            }
            if query_words:
                overlap = len(query_words & cand_words)
                preserved_ratio = overlap / len(query_words)
                if preserved_ratio < 0.5:
                    logger.warning(
                        "LLM query rewrite dropped key content words (preserved ratio %.2f: '%s' vs '%s'), fallback to original.",
                        preserved_ratio,
                        candidate,
                        query,
                    )
                    return query

            # Defensive guard 3: Preserve core domain inquiry intent terms
            for core_term in _CORE_INTENT_TERMS:
                core_unaccent = _unaccent(core_term.lower())
                if core_unaccent in query_unaccented and core_unaccent not in cand_unaccented:
                    logger.warning(
                        "LLM query rewrite dropped core intent phrase '%s' ('%s' vs '%s'), fallback to original.",
                        core_term,
                        candidate,
                        query,
                    )
                    return query

            # Defensive guard 4: Guard against unsolicited combo subject injection from history
            query_has_combo = any(_unaccent(s) in query_unaccented for s in _COMBO_SUBJECT_TERMS)
            cand_combo_count = sum(
                1 for s in _COMBO_SUBJECT_TERMS
                if re.search(r"\b" + re.escape(_unaccent(s)) + r"\b", cand_unaccented)
            )
            if not query_has_combo and cand_combo_count >= 2:
                logger.warning(
                    "LLM query rewrite hallucinated combo subjects into a query that had none ('%s'), fallback to original.",
                    candidate,
                )
                return query

            # Defensive guard 5: Candidate must not be excessively long or empty
            if len(candidate) > len(query) * 2.5 or len(candidate) < 3:
                return query
            return candidate
        except TimeoutError:
            logger.debug("LLM query rewrite timed out (>3.0s), using rule result")
            return None
