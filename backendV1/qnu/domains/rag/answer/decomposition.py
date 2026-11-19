"""Query decomposition for multi-clause regulation questions (Slice 4).

Decomposes conditional, comparative, or exception questions into <= 3 focused
sub-queries while preserving codes, zero-prefixed IDs (0012), subject groups, and years.
"""

from __future__ import annotations

import re
import unicodedata

_CONDITION_KEYWORDS = (
    "nhưng",
    "nếu",
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
    r"\s*(?:;|nhưng\b|nếu\b|hoặc\b|đồng thời\b|mặt khác\b|\?)\s*",
    re.IGNORECASE,
)


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
        for clause in clauses:
            if clause not in sub_queries:
                sub_queries.append(clause)
            if len(sub_queries) >= 3:
                break

    # Bound to maximum 3 sub-queries per spec
    return sub_queries[:3] if sub_queries else [clean_query]
