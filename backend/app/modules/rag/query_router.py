"""Query Router & Intent Classification for QNU AI Platform RAG Engine."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


class QueryIntent(StrEnum):
    """Classification of user query intent for tailored RAG retrieval strategy."""

    EXACT_FACT = "exact_fact"  # Tra cứu số liệu, mã ngành, chỉ tiêu, điểm chuẩn, hạn hoàn thành
    NARRATIVE = "narrative"    # Câu hỏi quy chế, hướng dẫn, giải thích chính sách
    MIXED = "mixed"            # Kết hợp cả số liệu cụ thể lẫn diễn giải ngữ cảnh


@dataclass
class QueryAnalysis:
    """Structured analysis of user query for routing."""

    intent: QueryIntent
    keywords: list[str] = field(default_factory=list)
    entity_codes: list[str] = field(default_factory=list)
    fact_attributes: list[str] = field(default_factory=list)
    is_fact_first: bool = False
    subject_names: list[str] = field(default_factory=list)
    target_entities: list[str] = field(default_factory=list)


class QueryClassifier:
    """Classifies user queries to route between Structured Facts and Hybrid Vector/FTS search."""

    # 1. Regex patterns for domain entities
    RE_PROGRAM_CODE = re.compile(r"\b(7\d{6})\b")
    RE_TASK_CODE = re.compile(r"\b(?:nhiệm vụ\s+)?(\d+\.\d+)\b", re.IGNORECASE)
    RE_IELTS_VSTEP = re.compile(r"\b(ielts|vstep|toefl)\b", re.IGNORECASE)

    # 2. Keywords indicating exact numerical/fact lookup
    FACT_KEYWORDS_ADMISSIONS = [
        "mã ngành",
        "mã tuyển sinh",
        "chỉ tiêu",
        "điểm chuẩn",
        "điểm trúng tuyển",
        "quy đổi",
        "thang điểm",
        "tổ hợp xét tuyển",
        "tổ hợp môn",
        "tổ hợp",
        "môn học",
        "học phí",
    ]

    FACT_KEYWORDS_PLAN = [
        "chủ trì",
        "ai chủ trì",
        "đơn vị chủ trì",
        "đơn vị phối hợp",
        "thời gian bắt đầu",
        "thời gian hoàn thành",
        "hạn hoàn thành",
        "sản phẩm kết quả",
        "sản phẩm đầu ra",
    ]

    FACT_KEYWORDS_LIBRARY = [
        "giáo trình",
        "sách chuyên khảo",
        "tài liệu tham khảo",
        "luận văn",
        "luận án",
        "mã tài liệu",
        "ký hiệu xếp giá",
        "nhà xuất bản",
        "năm xuất bản",
        "số lượng bản",
        "vị trí kệ",
    ]

    FACT_KEYWORDS_DRAFTING = [
        "số hiệu văn bản",
        "ngày ban hành",
        "cơ quan ban hành",
        "người ký",
        "trích yếu",
        "nghị định",
        "thông tư",
        "quyết định",
        "công văn",
        "tờ trình",
        "kế hoạch",
        "ngày hiệu lực",
    ]

    FACT_KEYWORDS_QUESTION_BANK = [
        "ma trận đề",
        "ma trận đề thi",
        "chuẩn đầu ra",
        "clo",
        "plo",
        "mức độ bloom",
        "thang bloom",
        "độ khó",
        "độ phân biệt",
        "số câu hỏi",
        "thời gian làm bài",
        "hình thức thi",
    ]

    FACT_KEYWORDS_REGULATIONS = [
        "điều",
        "khoản",
        "tín chỉ",
        "học phần",
        "điểm rèn luyện",
        "học bổng",
        "kỷ luật",
        "khiển trách",
        "cảnh cáo",
        "buộc thôi học",
    ]

    GENERIC_FACT_KEYWORDS = [
        "bao nhiêu",
        "mấy",
        "danh sách",
        "liệt kê",
        "thống kê",
        "mã số",
        "số lượng",
        "ngày",
        "hạn",
        "mức",
        "tỷ lệ",
    ]

    # Registry mapping module_code -> keyword pack for reusable routing.
    # New assistants reuse "general" fallback without code changes.
    FACT_KEYWORD_PACKS: dict[str, list[str]] = {
        "admissions": FACT_KEYWORDS_ADMISSIONS,
        "regulations": FACT_KEYWORDS_REGULATIONS,
        "library": FACT_KEYWORDS_LIBRARY,
        "drafting": FACT_KEYWORDS_DRAFTING,
        "question_bank": FACT_KEYWORDS_QUESTION_BANK,
        "plan": FACT_KEYWORDS_PLAN,
    }

    # 3. Canonical admissions major names mapped to official program codes (team session 179).
    # Kept alongside generic packs: entity augmentation boosts recall for natural
    # queries without memorized codes, while packs keep routing reusable per-module.
    MAJOR_NAME_TO_CODE: dict[str, str] = {
        "công nghệ thông tin": "7480201",
        "cntt": "7480201",
        "kỹ thuật phần mềm": "7480103",
        "ktpm": "7480103",
        "trí tuệ nhân tạo": "7480107",
        "khoa học dữ liệu": "7460108",
        "toán ứng dụng": "7460112",
        "quản trị kinh doanh": "7340101",
        "qtkd": "7340101",
        "tài chính - ngân hàng": "7340201",
        "tài chính ngân hàng": "7340201",
        "tcnh": "7340201",
        "kế toán": "7340301",
        "kiểm toán": "7340302",
        "luật": "7380101",
        "sư phạm toán học": "7140209",
        "sư phạm toán": "7140209",
        "sư phạm tin học": "7140210",
        "sư phạm tin": "7140210",
        "sư phạm vật lý": "7140211",
        "sư phạm lý": "7140211",
        "sư phạm hóa học": "7140212",
        "sư phạm hóa": "7140212",
        "sư phạm sinh học": "7140213",
        "sư phạm sinh": "7140213",
        "sư phạm ngữ văn": "7140217",
        "sư phạm văn": "7140217",
        "sư phạm lịch sử": "7140218",
        "sư phạm sử": "7140218",
        "sư phạm địa lý": "7140219",
        "sư phạm địa": "7140219",
        "sư phạm tiếng anh": "7140231",
        "sư phạm anh": "7140231",
        "giáo dục mầm non": "7140201",
        "giáo dục tiểu học": "7140202",
        "giáo dục thể chất": "7140206",
        "ngôn ngữ anh": "7220201",
        "ngôn ngữ trung quốc": "7220204",
        "logistics": "7510605",
        "kỹ thuật điện": "7520201",
        "công nghệ kỹ thuật ô tô": "7510205",
    }

    # Canonical subject names for reverse combo lookup ("which programs have Toan-Anh-Hoa?").
    # Patterns are ordered longest-first so "tiếng anh" wins over bare "anh" (a pronoun).
    # Extraction is gated on subject context ("tổ hợp" or "môn" + "xét tuyển") to avoid
    # pronoun false positives such as "anh cho em hỏi".
    SUBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"\btiếng\s+anh\b", re.IGNORECASE), "tiếng anh"),
        (re.compile(r"\bvật\s*l[ýy]\b", re.IGNORECASE), "lý"),
        (re.compile(r"\bhóa\s*học\b", re.IGNORECASE), "hóa"),
        (re.compile(r"\bsinh\s*học\b", re.IGNORECASE), "sinh"),
        (re.compile(r"\bngữ\s*văn\b", re.IGNORECASE), "văn"),
        (re.compile(r"\blịch\s*sử\b", re.IGNORECASE), "sử"),
        (re.compile(r"\bđịa\s*l[ýy]\b", re.IGNORECASE), "địa"),
        (re.compile(r"\btin\s*học\b", re.IGNORECASE), "tin"),
        (re.compile(r"\bgiáo\s*dục\s*(?:kt|kinh\s*tế).*?pháp\b", re.IGNORECASE), "giáo dục"),
        (re.compile(r"\bcông\s*nghệ\b", re.IGNORECASE), "công nghệ"),
        (re.compile(r"\btoán\b", re.IGNORECASE), "toán"),
        (re.compile(r"\blý\b", re.IGNORECASE), "lý"),
        (re.compile(r"\bhóa\b", re.IGNORECASE), "hóa"),
        (re.compile(r"\bsinh\b", re.IGNORECASE), "sinh"),
        (re.compile(r"\bvăn\b", re.IGNORECASE), "văn"),
        (re.compile(r"\bsử\b", re.IGNORECASE), "sử"),
        (re.compile(r"\bđịa\b", re.IGNORECASE), "địa"),
        (re.compile(r"\btin\b", re.IGNORECASE), "tin"),
        (re.compile(r"\banh\b", re.IGNORECASE), "anh"),
    ]

    # Conversational Vietnamese stopwords that should not dilute search keywords
    VI_CONVERSATIONAL_STOPWORDS: set[str] = {
        "tôi", "mình", "bạn", "em", "anh", "chị", "muốn", "hỏi", "cho", "biết",
        "xem", "với", "ạ", "nhé", "không", "nhỉ", "nào", "gì", "sao", "thế",
        "được", "có", "là", "của", "và", "các", "những", "cần", "để", "ý",
        "bao", "nhiêu", "như",
    }

    RE_DECISION_CODE = re.compile(
        r"\b(?:QĐ|NĐ|TT|CV|KH|TB|BC)[\s\-]*\d+[\/\-]\w+",
        re.IGNORECASE,
    )
    RE_MONEY = re.compile(r"\b\d[\d\.\,]*\s*(?:triệu|tỷ|nghìn|đồng|vnđ|vnd)\b", re.IGNORECASE)
    RE_YEAR = re.compile(r"\b(?:năm\s+)?(19|20)\d{2}\b")

    def analyze(self, query: str, module_code: str = "general") -> QueryAnalysis:
        """Analyze query intent, extract entity keys, and determine routing strategy."""
        clean_query = query.strip()
        query_lower = clean_query.lower()

        entity_codes: list[str] = []
        fact_attributes: list[str] = []
        keywords: list[str] = []
        target_entities: list[str] = []

        # 1. Detect program codes (e.g., 7480107, 7480201)
        for match in self.RE_PROGRAM_CODE.finditer(clean_query):
            code = match.group(1)
            entity_codes.append(code)
            keywords.append(code)

        # 1b. Detect canonical major names in admissions
        for major_name, code in self.MAJOR_NAME_TO_CODE.items():
            if re.search(r"\b" + re.escape(major_name) + r"\b", query_lower):
                if code not in entity_codes:
                    entity_codes.append(code)
                if code not in keywords:
                    keywords.append(code)
                if major_name not in keywords:
                    keywords.append(major_name)
                display_major = major_name.title()
                if display_major not in target_entities:
                    target_entities.append(display_major)

        # 1c. Detect generic major mention (e.g., 'ngành Công nghệ thông tin', 'ngành Kỹ thuật cơ khí')
        major_pattern = re.search(
            r"\b(?:ngành|chuyên ngành)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{3,40})\b", clean_query, re.IGNORECASE
        )
        if major_pattern:
            cand = major_pattern.group(1).strip()
            cand = re.sub(
                r"\b(?:cần|có|ở|tại|xét tuyển|năm|không|gì|bao nhiêu|như thế nào|thế nào).*$",
                "",
                cand,
                flags=re.IGNORECASE,
            ).strip()
            # Do NOT treat indefinite/placeholder words as majors (e.g. 'cụ thể nào', 'nào đó')
            if (
                cand
                and len(cand) >= 3
                and not any(
                    p in cand.lower()
                    for p in ("cụ thể", "nào", "gì", "bất kỳ", "khác", "này", "đó", "mới")
                )
                and cand.title() not in target_entities
            ):
                target_entities.append(cand.title())

        # 2. Detect task codes (e.g., 6.8, 1.1, 11.5)
        for match in self.RE_TASK_CODE.finditer(clean_query):
            task = match.group(1)
            entity_codes.append(task)
            keywords.append(f"nhiệm vụ {task}")

        # 3. Detect IELTS/VSTEP certificate conversions
        if self.RE_IELTS_VSTEP.search(query_lower):
            entity_codes.append("certificate_conversion")
            keywords.extend(["ielts", "vstep", "quy đổi"])
            fact_attributes.append("converted_score")

        # 4. Check admissions fact signals (kept for backward compatibility)
        has_admissions_fact = False
        for kw in self.FACT_KEYWORDS_ADMISSIONS:
            if kw in query_lower:
                has_admissions_fact = True
                keywords.append(kw)
                if "chỉ tiêu" in kw:
                    fact_attributes.append("expected_quota")
                elif "điểm" in kw:
                    fact_attributes.append("cutoff_score")
                elif "tổ hợp" in kw:
                    fact_attributes.append("subject_combinations")

        # 4b. Ambiguous "môn học ... xét tuyển" paraphrase means subject combinations.
        # Must exclude direct-admission tables (HSG / tuyển thẳng / ưu tiên xét tuyển)
        # so Phụ lục 1 does not outrank Trang 6 for CNTT-style queries.
        is_direct_admission_query = any(
            marker in query_lower
            for marker in ("học sinh giỏi", "tuyển thẳng", "ưu tiên xét tuyển")
        )
        if (
            not is_direct_admission_query
            and "môn" in query_lower
            and ("xét tuyển" in query_lower or "ngành" in query_lower)
        ):
            has_admissions_fact = True
            if "tổ hợp môn" not in keywords:
                keywords.append("tổ hợp môn")
            if "subject_combinations" not in fact_attributes:
                fact_attributes.append("subject_combinations")

        # 4c. Reverse combo lookup: extract subject names for "which programs have X-Y-Z?".
        # Gated on subject context so bare pronouns ("anh cho em hỏi") never match.
        subject_names: list[str] = []
        if not is_direct_admission_query and (
            "tổ hợp" in query_lower
            or ("môn" in query_lower and "xét tuyển" in query_lower)
        ):
            for pattern, canonical in self.SUBJECT_PATTERNS:
                if pattern.search(query_lower) and canonical not in subject_names:
                    subject_names.append(canonical)
            if "tiếng anh" in subject_names and "anh" in subject_names:
                subject_names.remove("anh")
            for subject in subject_names:
                if subject not in keywords:
                    keywords.append(subject)
            if subject_names:
                has_admissions_fact = True
                if "subject_combinations" not in fact_attributes:
                    fact_attributes.append("subject_combinations")

        # 5. Check implementation plan fact signals
        has_plan_fact = False
        for kw in self.FACT_KEYWORDS_PLAN:
            if kw in query_lower:
                has_plan_fact = True
                keywords.append(kw)
                if "chủ trì" in kw:
                    fact_attributes.append("lead_unit")
                elif "thời gian" in kw or "hạn" in kw:
                    fact_attributes.append("end_date")
                elif "sản phẩm" in kw:
                    fact_attributes.append("deliverables")

        # 5b. Generic reusable routing for any new assistant.
        # Uses module-specific pack + generic decision/money/year signals.
        has_module_fact = has_admissions_fact or has_plan_fact
        normalized_module = (module_code or "general").strip().lower()
        active_pack = self.FACT_KEYWORD_PACKS.get(normalized_module, [])
        for kw in active_pack:
            if kw in query_lower and kw not in keywords:
                has_module_fact = True
                keywords.append(kw)

        has_generic_signal = False
        for kw in self.GENERIC_FACT_KEYWORDS:
            if kw in query_lower:
                has_generic_signal = True
                if kw not in keywords:
                    keywords.append(kw)

        decision_match = self.RE_DECISION_CODE.search(clean_query)
        if decision_match:
            has_generic_signal = True
            entity_codes.append(decision_match.group(0))
            keywords.append("số hiệu văn bản")
        if self.RE_MONEY.search(query_lower):
            has_generic_signal = True
            keywords.append("mức phí")
        year_match = self.RE_YEAR.search(query_lower)
        if year_match:
            keywords.append(year_match.group(0))

        # 6. Intent classification decision
        has_specific_entity = len(entity_codes) > 0
        has_fact_keywords = has_module_fact or has_generic_signal

        # Questions asking for exact numbers or entities
        is_exact = (has_specific_entity and has_fact_keywords) or (
            has_specific_entity and any(w in query_lower for w in ["mấy", "bao nhiêu", "là gì", "nào"])
        )

        if is_exact:
            intent = QueryIntent.EXACT_FACT
            is_fact_first = True
        elif has_fact_keywords or has_specific_entity:
            intent = QueryIntent.MIXED
            is_fact_first = True
        else:
            intent = QueryIntent.NARRATIVE
            is_fact_first = False

        # Add general tokens if keywords list is short, excluding conversational stopwords
        if len(keywords) < 3:
            tokens = [
                w for w in re.findall(r"\w+", query_lower)
                if len(w) >= 3 and w not in self.VI_CONVERSATIONAL_STOPWORDS
            ]
            keywords.extend(tokens[:3])

        # Deduplicate keywords preserving order
        dedup_keywords = list(dict.fromkeys(keywords))

        logger.debug(
            "Query analysis: query='%s', intent=%s, entity_codes=%s, is_fact_first=%s",
            clean_query[:50],
            intent,
            entity_codes,
            is_fact_first,
        )

        return QueryAnalysis(
            intent=intent,
            keywords=dedup_keywords,
            entity_codes=entity_codes,
            fact_attributes=list(set(fact_attributes)),
            is_fact_first=is_fact_first,
            subject_names=subject_names,
            target_entities=target_entities,
        )


# Generic topic words too broad to signal continuity across turns.
_TOPIC_GENERIC_WORDS: frozenset[str] = frozenset(
    {
        "ngành", "xét", "tuyển", "tổ hợp", "môn", "nganh", "xet", "tuyen",
        "trường", "đại", "học", "truong", "dai", "hoc", "cho", "biết",
        "bao nhiêu", "bao nhieu", "năm", "nam",
    }
)


def scope_history_by_topic(
    history: list[dict] | None,
    analysis: QueryAnalysis,
    max_messages: int = 4,
) -> list[dict]:
    """Keep only history turns sharing topic signals with the current query.

    The most recent turn is always preserved for pronoun continuity ("ngành này").
    Older turns survive only when they mention the same entity codes, subject
    names or distinctive keywords. Prevents a stale answer (e.g. phương thức)
    from steering an independent new question (e.g. reverse combo lookup).
    """
    if not history:
        return []
    recent = [m for m in history if isinstance(m, dict)][:]

    signals: set[str] = set()
    for code in analysis.entity_codes:
        signals.add(code.strip().lower())
    for subject in analysis.subject_names:
        signals.add(subject.strip().lower())
    for kw in analysis.keywords:
        clean_kw = kw.strip().lower()
        if len(clean_kw) >= 8 and clean_kw not in _TOPIC_GENERIC_WORDS:
            signals.add(clean_kw)
    signals.discard("")

    if not signals:
        return recent[-max_messages:]

    # Always preserve the latest turn (up to 2 messages) for continuity.
    tail = recent[-2:]
    subject_set = {s.strip().lower() for s in analysis.subject_names}
    scoped: list[dict] = []
    for msg in recent[: len(recent) - len(tail)]:
        content = str(msg.get("content", "")).lower()
        matched = False
        for sig in signals:
            if sig not in content:
                continue
            # Bare subject words only count inside combo discussions, so "Kế toán"
            # never matches the "toán" subject of an unrelated older turn.
            if sig in subject_set and not any(
                marker in content for marker in ("tổ hợp", "môn", "xét tuyển")
            ):
                continue
            matched = True
            break
        if matched:
            scoped.append(msg)
    scoped.extend(tail)
    return scoped[-max_messages:]


query_classifier = QueryClassifier()
