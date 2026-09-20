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

        # Add general tokens if keywords list is short
        if len(keywords) < 2:
            tokens = [
                w for w in clean_query.split()
                if len(w) >= 3 and w.lower() not in {"bao", "nhiêu", "như", "thế", "nào"}
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
