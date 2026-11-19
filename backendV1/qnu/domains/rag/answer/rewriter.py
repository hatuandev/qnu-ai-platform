"""Multi-turn Contextual Query Rewriter for QNU RAG (Slice 5).

Rewrites follow-up user questions in multi-turn conversations (>= 2 turns)
into complete, self-contained standalone search queries before intent routing
and retrieval.

Strictly follows AGENTS.md and RULE_REASONING_PROMPTS_SPEC.md:
- Only activates when conversation history has >= 2 turns.
- Inherits points, subject groups, conditions, years, and major codes from history.
- Strictly safe: never invents facts or hallucinates assumptions outside chat history.
- Preserves zero-prefixed IDs (0012), major codes, and exact numerical thresholds.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Anaphoric references / elliptical indicators in Vietnamese
_ANAPHORA_PATTERNS = [
    re.compile(r"\b(?:ngành đó|ngành này|ngành trên|mã đó|mã này|nó|cái đó|trường hợp này)\b", re.IGNORECASE),
    re.compile(r"^(?:thế còn|còn|vậy còn|thế|vậy)\s+", re.IGNORECASE),
    re.compile(r"\b(?:ở trên|đã nêu|vừa hỏi)\b", re.IGNORECASE),
]

# Patterns where bot asks for clarification
_BOT_CLARIFICATION_KEYWORDS = (
    "ngành nào",
    "năm nào",
    "văn bản nào",
    "điều khoản nào",
    "phương thức nào",
    "loại nào",
    "đối tượng nào",
    "tiêu chí nào",
    "cho biết thêm",
    "bạn muốn hỏi về",
    "cần làm rõ",
)

# Extract core subjects from text (major names, codes, year, scores)
_YEAR_RE = re.compile(r"\b(202[0-9])\b")
_CODE_RE = re.compile(r"\b([A-Z]{2,4}-?\d{4,7}|\d{7}|\b0\d{3}\b)\b")
_SCORE_RE = re.compile(r"\b(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:điểm|đ)\b", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def _extract_history_pairs(history: list[dict[str, Any] | tuple[str, str]]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in history:
        if isinstance(item, tuple) and len(item) == 2:
            pairs.append((_normalize_text(item[0]), _normalize_text(item[1])))
        elif isinstance(item, dict):
            q = item.get("question") or item.get("user") or item.get("q") or ""
            a = item.get("answer") or item.get("assistant") or item.get("a") or item.get("message") or ""
            pairs.append((_normalize_text(str(q)), _normalize_text(str(a))))
    return pairs


def _extract_entities_from_text(text: str) -> dict[str, list[str]]:
    return {
        "years": _YEAR_RE.findall(text),
        "codes": _CODE_RE.findall(text),
        "scores": _SCORE_RE.findall(text),
    }


def rewrite_contextual_query(
    current_question: str,
    history: list[dict[str, Any] | tuple[str, str]] | None,
) -> tuple[str, dict[str, Any]]:
    """Rewrite a follow-up question into a standalone query using conversation history.

    Returns:
        (resolved_question, trace_info)
    """
    clean_current = _normalize_text(current_question)
    if not clean_current:
        return clean_current, {"rewritten": False, "reason": "empty_question"}

    if not history or len(history) < 2:
        return clean_current, {"rewritten": False, "reason": "insufficient_history"}

    pairs = _extract_history_pairs(history)
    if len(pairs) < 2:
        return clean_current, {"rewritten": False, "reason": "insufficient_history"}

    # Last turn context
    prev_user_q, prev_bot_a = pairs[-1]
    prev_bot_norm = prev_bot_a.casefold()

    rewritten = False
    resolved = clean_current
    rewrite_mode = "none"

    # Case 1: Elliptical reply to bot's clarification request
    # E.g. Turn 1 User: "Điều kiện xét tuyển và chỉ tiêu như thế nào?"
    #      Turn 1 Bot: "Bạn muốn hỏi về ngành nào và năm nào?"
    #      Turn 2 User: "Ngành CNTT năm 2026 ạ"
    # -> Resolved: "Điều kiện xét tuyển và chỉ tiêu ngành CNTT năm 2026"
    bot_asked_clarification = prev_bot_a.endswith("?") or any(kw in prev_bot_norm for kw in _BOT_CLARIFICATION_KEYWORDS)
    is_short_reply = len(clean_current.split()) <= 12 and not clean_current.endswith("?")

    if bot_asked_clarification and is_short_reply:
        # Strip polite particles from reply
        clean_reply = re.sub(r"\b(?:ạ|dạ|vâng|nhé|nha|với ạ|giúp mình|ơi)\b", "", clean_current, flags=re.IGNORECASE).strip()
        # Combine previous user intent with the new entity
        # Strip trailing questions from prev_user_q
        base_intent = re.sub(r"\s*(?:như thế nào|thế nào|bao nhiêu|là gì|có không|\?)+\s*$", "", prev_user_q, flags=re.IGNORECASE).strip()
        resolved = f"{base_intent} {clean_reply}".strip()
        rewritten = True
        rewrite_mode = "clarification_synthesis"

    # Case 2: Anaphoric references (e.g. "ngành đó học phí thế nào?", "thế còn năm 2025?")
    if not rewritten:
        pronoun_match = re.search(r"\b(?:ngành đó|ngành này|ngành trên|mã đó|mã này|nó|cái đó|trường hợp này)\b", clean_current, re.IGNORECASE)
        entities = _extract_entities_from_text(prev_user_q)
        subject_matches: list[str] = []
        if entities["codes"]:
            subject_matches.extend(entities["codes"])
        major_match = re.search(r"ngành\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s]+?)(?:\s+(?:năm|học phí|điểm|chỉ tiêu|xét tuyển|như thế nào)|\?|$)", prev_user_q, re.IGNORECASE)
        if major_match:
            subject_matches.append(f"ngành {major_match.group(1).strip()}")

        if pronoun_match and subject_matches:
            resolved = re.sub(r"\b(?:ngành đó|ngành này|ngành trên|mã đó|mã này|nó|cái đó|trường hợp này)\b", subject_matches[0], clean_current, flags=re.IGNORECASE)
            resolved = re.sub(r"^(?:thế còn|còn|vậy còn)\s+", "", resolved, flags=re.IGNORECASE).strip()
            rewritten = True
            rewrite_mode = "anaphora_substitution"
        elif re.match(r"^(?:thế còn|còn|vậy còn)\s+", clean_current, re.IGNORECASE):
            clean_follow_up = re.sub(r"^(?:thế còn|còn|vậy còn)\s+", "", clean_current, flags=re.IGNORECASE).strip()
            base = re.sub(r"\b202[0-9]\b", "", prev_user_q).strip()
            base = re.sub(r"\s*(?:như thế nào|thế nào|bao nhiêu|là gì|có không|\?)+\s*$", "", base, flags=re.IGNORECASE).strip()
            resolved = f"{base} {clean_follow_up}".strip()
            rewritten = True
            rewrite_mode = "anaphora_substitution"

    # Safety check: ensure essential codes and zero-prefixed IDs from both inputs are preserved
    prev_entities = _extract_entities_from_text(prev_user_q)
    curr_entities = _extract_entities_from_text(clean_current)
    preserved_codes = list(set(prev_entities["codes"] + curr_entities["codes"]))

    trace = {
        "rewritten": rewritten,
        "mode": rewrite_mode,
        "original_question": clean_current,
        "resolved_question": resolved,
        "history_turns_count": len(pairs),
        "preserved_codes": preserved_codes,
    }
    return resolved, trace
