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

    # 3. Canonical admissions major names mapped to official program codes
    MAJOR_NAME_TO_CODE: dict[str, str] = {
        "công nghệ thông tin": "7480201",
        "cntt": "7480201",
        "kỹ thuật phần mềm": "7480103",
        "ktpm": "7480103",
        "trí tuệ nhân tạo": "7480107",
        "ai": "7480107",
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

    # Conversational Vietnamese stopwords that should not dilute search keywords
    VI_CONVERSATIONAL_STOPWORDS: set[str] = {
        "tôi", "mình", "bạn", "em", "anh", "chị", "muốn", "hỏi", "cho", "biết",
        "xem", "với", "ạ", "nhé", "không", "nhỉ", "nào", "gì", "sao", "thế",
        "được", "có", "là", "của", "và", "các", "những", "cần", "để", "ý",
        "bao", "nhiêu", "như"
    }

    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze query intent, extract entity keys, and determine routing strategy."""
        clean_query = query.strip()
        query_lower = clean_query.lower()

        entity_codes: list[str] = []
        fact_attributes: list[str] = []
        keywords: list[str] = []

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

        # 4. Check admissions fact signals
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

        # 6. Intent classification decision
        has_specific_entity = len(entity_codes) > 0
        has_fact_keywords = has_admissions_fact or has_plan_fact

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
        )


query_classifier = QueryClassifier()
