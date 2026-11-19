"""Intent router / orchestrator for fast question classification (Slice 4).

Diverts pure tabular listing/aggregation to deterministic facts query (< 30ms),
complex multi-clause regulation questions to rule reasoning with decomposition,
and simple questions to standard direct hybrid RAG.
"""

from __future__ import annotations

import unicodedata
from typing import Literal

from qnu.domains.rag.answer.decomposition import needs_decomposition

IntentType = Literal["tabular_aggregation", "rule_reasoning", "direct_lookup"]

_TABULAR_KEYWORDS = (
    "liệt kê tất cả",
    "liệt kê các",
    "liệt kê danh sách",
    "có bao nhiêu ngành",
    "có bao nhiêu",
    "danh sách các ngành",
    "những ngành nào",
    "tất cả ngành",
    "tất cả các ngành",
    "toàn bộ các ngành",
    "điểm chuẩn cao nhất",
    "điểm chuẩn thấp nhất",
    "chỉ tiêu cao nhất",
    "chỉ tiêu thấp nhất",
    "bao nhiêu chỉ tiêu",
    "tổng số chỉ tiêu",
    "tổng chỉ tiêu",
    "ngành nào xét tuyển",
    "ngành nào xét môn",
    "ngành nào xét tổ hợp",
)


def _normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split()).casefold()


def classify_intent(question: str) -> IntentType:
    """Classify user question into tabular aggregation, rule reasoning, or direct lookup."""
    norm = _normalize_text(question)
    if any(kw in norm for kw in _TABULAR_KEYWORDS):
        return "tabular_aggregation"
    if needs_decomposition(question):
        return "rule_reasoning"
    return "direct_lookup"
