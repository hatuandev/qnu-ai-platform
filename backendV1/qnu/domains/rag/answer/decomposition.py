"""Query decomposition for multi-clause regulation questions (Slice 4).

Decomposes conditional, comparative, or exception questions into <= 3 focused
sub-queries while preserving codes, zero-prefixed IDs (0012), subject groups, and years.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_CONDITION_KEYWORDS = (
    "nhưng",
    "nếu",
    "còn",
    "thay cho",
    "thay thế",
    "dùng điểm",
    "ngoại lệ",
    "trừ trường hợp",
    "loại trừ",
    "so với",
    "khác gì",
    "có được dùng",
    "có thể dùng",
    "đồng thời",
    "kết hợp",
    "điều kiện",
    "ngưỡng đầu vào",
)

_SPLIT_PATTERN = re.compile(
    r"\s*(?:;|,?\s*còn\b|nhưng\b|nếu\b|hoặc\b|đồng thời\b|mặt khác\b|\?)\s*",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b(202[0-9])\b")
_CODE_RE = re.compile(r"\b([A-Z]{2,4}-?\d{4,7}|\d{7}|\b0\d{1,4}\b)\b")
_MAJOR_RE = re.compile(
    r"\b(ngành\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+?)(?:\s+(?:năm|học phí|điểm|chỉ tiêu|xét tuyển|như thế nào)|\?|,|;|$)",
    re.IGNORECASE,
)


def _extract_query_context(query: str) -> dict[str, Any]:
    years = _YEAR_RE.findall(query)
    codes = _CODE_RE.findall(query)
    major_match = _MAJOR_RE.search(query)
    major = major_match.group(1).strip() if major_match else None
    return {
        "years": years,
        "codes": codes,
        "major": major,
    }


def _enrich_clause(clause: str, context: dict[str, Any]) -> str:
    missing_parts: list[str] = []
    major = context.get("major")
    if major and major.casefold() not in clause.casefold():
        missing_parts.append(major)
    for code in context.get("codes", []):
        if code not in clause and (not major or code not in major):
            missing_parts.append(code)
    # Only append year from context if clause has NO year of its own
    clause_years = _YEAR_RE.findall(clause)
    if not clause_years and context.get("years"):
        missing_parts.append(f"năm {context['years'][-1]}")

    if missing_parts:
        context_prefix = " ".join(missing_parts)
        return f"{context_prefix}: {clause}"
    return clause


def _normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split()).casefold()


def needs_decomposition(query: str) -> bool:
    """Return True if query has conditional/comparison/exception keywords or >= 2 clauses."""
    norm = _normalize_text(query)
    if query.count("?") >= 2:
        return True
    return any(kw in norm for kw in _CONDITION_KEYWORDS)


def decompose_query(query: str) -> list[str]:
    """Decompose a complex question into at most 3 independent sub-queries.

    Preserves subject codes (e.g. 0012, AM-0070), subject combinations (Toán, Văn, Anh),
    years, and thresholds without inventing information.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    if not needs_decomposition(clean_query):
        return [clean_query]

    # Rule-based syntactic/clause extraction
    clauses = [c.strip() for c in _SPLIT_PATTERN.split(clean_query) if c.strip()]
    if not clauses:
        return [clean_query]

    sub_queries: list[str] = []
    # If the user asks about replacement / alternative combinations (e.g. "Dùng 15 điểm tổ hợp A thay cho tổ hợp B xét học bạ"):
    norm = _normalize_text(clean_query)
    if any(k in norm for k in ("thay cho", "thay thế", "dùng điểm", "có được dùng", "có thể dùng")):
        sub_queries.append(f"Quy định xét tuyển {clean_query}")
        sub_queries.append(f"Điều kiện ngưỡng đầu vào quy đổi điểm xét tuyển {clean_query}")
        sub_queries.append(f"Trường hợp ngoại lệ điều kiện loại trừ {clean_query}")
    else:
        context = _extract_query_context(clean_query)
        for clause in clauses:
            enriched = _enrich_clause(clause, context)
            if enriched not in sub_queries:
                sub_queries.append(enriched)
            if len(sub_queries) >= 3:
                break

    # Bound to maximum 3 sub-queries per spec
    return sub_queries[:3] if sub_queries else [clean_query]
