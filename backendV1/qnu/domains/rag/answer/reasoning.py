"""IRAC 4-step reasoning extraction and separation for QNU RAG (Slice 4).

Extracts internal reasoning from <phan_tich>...</phan_tich> blocks into structured
trace logs for audit and evaluation, leaving clean, direct answers for end users.
"""

from __future__ import annotations

import re

ANALYSIS_TAG_RE = re.compile(r"<phan_tich>(.*?)(?:</phan_tich>|$)", re.DOTALL | re.IGNORECASE)
STRIP_TAGS_RE = re.compile(r"</?phan_tich>", re.IGNORECASE)


def split_reasoning_and_answer(raw_output: str) -> tuple[str, str]:
    """Split raw model output into internal IRAC reasoning and clean user answer.

    Returns:
        (internal_reasoning, clean_user_answer)
        - internal_reasoning: The 4-step analysis between <phan_tich> tags (saved to trace).
        - clean_user_answer: The user-facing answer with analysis tags cleanly stripped.
    """
    if not raw_output:
        return "", ""

    match = ANALYSIS_TAG_RE.search(raw_output)
    if match:
        internal_reasoning = match.group(1).strip()
        clean_user_answer = ANALYSIS_TAG_RE.sub("", raw_output).strip()
        clean_user_answer = STRIP_TAGS_RE.sub("", clean_user_answer).strip()
        return internal_reasoning, clean_user_answer

    # Graceful fallback when model emitted no tags
    clean_user_answer = STRIP_TAGS_RE.sub("", raw_output).strip()
    return "", clean_user_answer
