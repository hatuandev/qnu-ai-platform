"""IRAC 4-step reasoning extraction and separation for QNU RAG (Slice 4).

Extracts internal reasoning from <phan_tich>...</phan_tich> blocks into structured
trace logs for audit and evaluation, leaving clean, direct answers for end users.
"""

from __future__ import annotations

import re

CLOSED_TAG_RE = re.compile(r"<phan_tich>(.*?)</phan_tich>", re.DOTALL | re.IGNORECASE)
OPEN_TAG_RE = re.compile(r"<phan_tich>", re.IGNORECASE)
STRIP_TAGS_RE = re.compile(r"</?phan_tich>", re.IGNORECASE)
JSON_START_RE = re.compile(
    r"(\{\s*\"status\"\s*:\s*\"(?:answered|insufficient_evidence)\"[\s\S]*\})",
    re.IGNORECASE,
)
CONCLUSION_LINE_RE = re.compile(
    r"(?:^|\n)\s*(?:4[.)]|(?:4\s*\.\s*)?(?:kết\s+luận|conclusion)\b)[^\n]*\n",
    re.IGNORECASE,
)


def split_reasoning_and_answer(raw_output: str) -> tuple[str, str]:
    """Split raw model output into internal IRAC reasoning and clean user answer.

    Guards against unclosed <phan_tich> tags so the user answer is never swallowed.

    Returns:
        (internal_reasoning, clean_user_answer)
        - internal_reasoning: The 4-step analysis between <phan_tich> tags (saved to trace).
        - clean_user_answer: The user-facing answer with analysis tags cleanly stripped.
    """
    if not raw_output:
        return "", ""

    # Case 1: Perfectly closed <phan_tich>...</phan_tich>
    closed_match = CLOSED_TAG_RE.search(raw_output)
    if closed_match:
        internal_reasoning = closed_match.group(1).strip()
        clean_user_answer = CLOSED_TAG_RE.sub("", raw_output).strip()
        clean_user_answer = STRIP_TAGS_RE.sub("", clean_user_answer).strip()
        return internal_reasoning, clean_user_answer

    # Case 2: Unclosed <phan_tich> tag (model forgot or truncated </phan_tich>)
    open_match = OPEN_TAG_RE.search(raw_output)
    if open_match:
        after_open = raw_output[open_match.end() :]
        # Check if there is a JSON contract payload
        json_match = JSON_START_RE.search(after_open)
        if json_match:
            internal_reasoning = after_open[: json_match.start()].strip()
            clean_user_answer = json_match.group(1).strip()
            return internal_reasoning, clean_user_answer

        # Check if there is an IRAC step 4 (Conclusion) line
        concl_match = CONCLUSION_LINE_RE.search(after_open)
        if concl_match:
            split_pos = concl_match.end()
            internal_reasoning = after_open[:split_pos].strip()
            clean_user_answer = after_open[split_pos:].strip()
            if clean_user_answer:
                return internal_reasoning, clean_user_answer

        # If after_open has double newlines, take the last paragraph/block as user answer
        blocks = [b.strip() for b in after_open.split("\n\n") if b.strip()]
        if len(blocks) >= 2:
            internal_reasoning = "\n\n".join(blocks[:-1])
            clean_user_answer = blocks[-1]
            return internal_reasoning, clean_user_answer

        # Fallback to avoid empty user answer: do NOT swallow everything
        clean_user_answer = STRIP_TAGS_RE.sub("", raw_output).strip()
        return "", clean_user_answer

    # Case 3: No <phan_tich> tags at all
    clean_user_answer = STRIP_TAGS_RE.sub("", raw_output).strip()
    return "", clean_user_answer
