"""Multi-turn Contextual Query Rewriter for QNU RAG (Slice 5 & DN-03).

Rewrites follow-up user questions in multi-turn conversations into complete,
self-contained standalone search queries before intent routing and retrieval.

Strictly follows AGENTS.md and RULE_REASONING_PROMPTS_SPEC.md:
- Preserves entity continuity, conversion scales, and topics across history.
- Inherits certificates, subjects, methods, conditions, years, and major codes.
- Strictly safe: never invents facts or hallucinates assumptions outside chat history.
- Preserves zero-prefixed IDs (0012), major codes, and exact numerical thresholds.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Anaphoric references / elliptical indicators in Vietnamese
_ANAPHORA_PRONOUN_RE = re.compile(
    r"\b(?:(?:hồ sơ nghiệm thu|hồ sơ|nhiệm vụ|phần|mục|bảng|điều|trường hợp|ngành|mã)\s+(?:này|đó|trên)|nó|cái đó)\b",
    re.IGNORECASE,
)

_ANAPHORA_PATTERNS = [
    _ANAPHORA_PRONOUN_RE,
    re.compile(r"^(?:thế còn|còn|vậy còn|thế|vậy|nếu là|với)\s+", re.IGNORECASE),
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
_CODE_RE = re.compile(r"\b([A-Z]{2,4}-?\d{1,7}|\d{7}|\b0\d{1,5}\b)\b")
_SCORE_RE = re.compile(r"\b(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:điểm|đ)\b", re.IGNORECASE)

_CERT_PATTERNS = {
    "VSTEP": re.compile(r"\b(?:VSTEP|V-STEP)\b", re.IGNORECASE),
    "IELTS": re.compile(r"\bIELTS\b", re.IGNORECASE),
    "TOEFL": re.compile(r"\bTOEFL(?:\s+iBT)?\b", re.IGNORECASE),
    "TOEIC": re.compile(r"\bTOEIC\b", re.IGNORECASE),
    "SAT": re.compile(r"\bSAT\b", re.IGNORECASE),
    "ACT": re.compile(r"\bACT\b", re.IGNORECASE),
    "ĐGNL": re.compile(r"\b(?:ĐGNL|đánh giá năng lực)\b", re.IGNORECASE),
    "ĐGTD": re.compile(r"\b(?:ĐGTD|đánh giá tư duy)\b", re.IGNORECASE),
    "HSG": re.compile(r"\b(?:HSG|học sinh giỏi)\b", re.IGNORECASE),
}

_ACTION_CONVERSION_RE = re.compile(
    r"\b(?:quy đổi|tương đương|bảng quy đổi|thang quy đổi)\b", re.IGNORECASE
)
_SUBJECT_ENG_RE = re.compile(r"\b(?:tiếng anh|ngoại ngữ)\b", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def _extract_history_pairs(
    history: list[dict[str, Any] | tuple[str, str]],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in history:
        if isinstance(item, tuple) and len(item) == 2:
            pairs.append((_normalize_text(item[0]), _normalize_text(item[1])))
        elif isinstance(item, dict):
            q = item.get("question") or item.get("user") or item.get("q") or ""
            a = (
                item.get("answer")
                or item.get("assistant")
                or item.get("a")
                or item.get("message")
                or ""
            )
            pairs.append((_normalize_text(str(q)), _normalize_text(str(a))))
    return pairs


def _extract_entities_from_text(text: str) -> dict[str, list[str]]:
    return {
        "years": _YEAR_RE.findall(text),
        "codes": _CODE_RE.findall(text),
        "scores": _SCORE_RE.findall(text),
    }


def _extract_cumulative_history_context(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """Scan history from earliest to latest to preserve entities and ongoing topics."""
    last_certificate: str | None = None
    last_year: str | None = None
    last_major: str | None = None
    all_codes: list[str] = []
    user_codes: list[str] = []
    has_conversion: bool = False
    has_eng_subject: bool = False

    for user_q, bot_a in pairs:
        combined_turn = f"{user_q} {bot_a}"

        # Detect certificate (latest user mention takes precedence, then bot)
        for cert_name, pattern in _CERT_PATTERNS.items():
            if pattern.search(user_q) or pattern.search(bot_a) and last_certificate is None:
                last_certificate = cert_name

        # Detect years
        years = _YEAR_RE.findall(user_q) or _YEAR_RE.findall(bot_a)
        if years:
            last_year = years[-1]

        # Detect major names
        major_match = re.search(
            r"ngành\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s]+?)(?:\s+(?:năm|học phí|điểm|chỉ tiêu|xét tuyển|như thế nào)|\?|$)",
            user_q,
            re.IGNORECASE,
        )
        if major_match:
            last_major = f"ngành {major_match.group(1).strip()}"

        # Codes
        q_codes = _CODE_RE.findall(user_q)
        user_codes.extend(q_codes)
        all_codes.extend(q_codes + _CODE_RE.findall(bot_a))

        # Topics
        if _ACTION_CONVERSION_RE.search(combined_turn):
            has_conversion = True
        if _SUBJECT_ENG_RE.search(combined_turn):
            has_eng_subject = True

    return {
        "certificate": last_certificate,
        "year": last_year,
        "major": last_major,
        "codes": list(dict.fromkeys(user_codes + all_codes)),
        "user_codes": list(dict.fromkeys(user_codes)),
        "has_conversion": has_conversion,
        "has_eng_subject": has_eng_subject,
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

    if not history:
        return clean_current, {"rewritten": False, "reason": "insufficient_history"}

    pairs = _extract_history_pairs(history)
    if not pairs:
        return clean_current, {"rewritten": False, "reason": "insufficient_history"}

    # Last turn context
    prev_user_q, prev_bot_a = pairs[-1]
    prev_bot_norm = prev_bot_a.casefold()

    rewritten = False
    resolved = clean_current
    rewrite_mode = "none"

    # Cumulative context across all turns
    ctx = _extract_cumulative_history_context(pairs)

    # Detect anaphora/ellipsis in current question
    has_leading_connector = bool(
        re.match(r"^(?:thế còn|còn|vậy còn|thế|vậy|nếu là|với)\s+", clean_current, re.IGNORECASE)
    )
    pronoun_match = _ANAPHORA_PRONOUN_RE.search(clean_current)
    has_score_or_tier = bool(
        re.match(
            r"^(?:thế còn|còn|vậy còn|thế|vậy|nếu là|với\s+)?(\d+(?:[.,]\d+)?|bậc\s+\d+)\b",
            clean_current,
            re.IGNORECASE,
        )
    )
    is_anaphoric = has_leading_connector or bool(pronoun_match) or has_score_or_tier

    # If < 2 turns and no anaphoric indication, preserve insufficient_history contract
    if len(pairs) < 2 and not is_anaphoric:
        # Check if bot asked clarification
        bot_asked = prev_bot_a.endswith("?") or any(
            kw in prev_bot_norm for kw in _BOT_CLARIFICATION_KEYWORDS
        )
        if not bot_asked:
            return clean_current, {"rewritten": False, "reason": "insufficient_history"}

    # Case 1: Elliptical reply to bot's clarification request
    bot_asked_clarification = prev_bot_a.endswith("?") or any(
        kw in prev_bot_norm for kw in _BOT_CLARIFICATION_KEYWORDS
    )
    is_short_reply = len(clean_current.split()) <= 12 and not clean_current.endswith("?")

    if bot_asked_clarification and is_short_reply:
        clean_reply = re.sub(
            r"\b(?:ạ|dạ|vâng|nhé|nha|với ạ|giúp mình|ơi)\b",
            "",
            clean_current,
            flags=re.IGNORECASE,
        ).strip()
        base_intent = re.sub(
            r"\s*(?:như thế nào|thế nào|bao nhiêu|là gì|có không|\?)+\s*$",
            "",
            prev_user_q,
            flags=re.IGNORECASE,
        ).strip()
        resolved = f"{base_intent} {clean_reply}".strip()
        rewritten = True
        rewrite_mode = "clarification_synthesis"

    # Case 2: Conversion scale & Certificate continuity (e.g. Q9 -> Q10)
    # Turn 1: Quy đổi VSTEP 6.0 ...
    # Turn 2: "Còn 7.0 và có được dùng cho phương thức xét học bạ không?"
    if not rewritten and ctx.get("certificate"):
        cert = ctx["certificate"]
        cert_in_current = bool(_CERT_PATTERNS[cert].search(clean_current))

        if not cert_in_current and (has_leading_connector or has_score_or_tier):
            body = re.sub(
                r"^(?:thế còn|còn|vậy còn|thế|vậy|nếu là|với)\s+",
                "",
                clean_current,
                flags=re.IGNORECASE,
            ).strip()
            match_thresh = re.match(r"^(\d+(?:[.,]\d+)?|bậc\s+\d+)\s*(.*)", body, re.IGNORECASE)

            if match_thresh:
                thresh_val = match_thresh.group(1).strip()
                tail = match_thresh.group(2).strip()
                if tail.lower().startswith("và "):
                    tail = tail[3:].strip()

                parts = []
                if ctx.get("has_conversion"):
                    parts.append(f"Quy đổi điểm chứng chỉ {cert} {thresh_val}")
                else:
                    parts.append(f"Chứng chỉ {cert} {thresh_val}")

                if (
                    ctx.get("has_eng_subject")
                    and "tiếng anh" not in tail.lower()
                    and "ngoại ngữ" not in tail.lower()
                ):
                    parts.append("môn Tiếng Anh")

                if tail:
                    parts.append(f"và {tail}")

                resolved = " ".join(parts).strip()
                # Attach inherited year if absent from resolved and present in history
                if ctx.get("year") and ctx["year"] not in resolved:
                    if resolved.endswith("?"):
                        resolved = f"{resolved[:-1].strip()} năm {ctx['year']}?"
                    else:
                        resolved = f"{resolved} năm {ctx['year']}"

                rewritten = True
                rewrite_mode = "conversion_continuity"
            elif re.search(r"\b(?:xét học bạ|học bạ|phương thức|áp dụng)\b", body, re.IGNORECASE):
                # Follow-up asking about method applicability for the ongoing certificate
                parts = [f"Chứng chỉ {cert}", body]
                resolved = " ".join(parts).strip()
                if ctx.get("year") and ctx["year"] not in resolved:
                    if resolved.endswith("?"):
                        resolved = f"{resolved[:-1].strip()} năm {ctx['year']}?"
                    else:
                        resolved = f"{resolved} năm {ctx['year']}"
                rewritten = True
                rewrite_mode = "conversion_continuity"

    # Case 3: Anaphoric references with pronoun or contextual noun phrase
    if not rewritten and pronoun_match:
        subject_matches: list[str] = []
        if ctx.get("user_codes"):
            subject_matches.extend(ctx["user_codes"])
        elif ctx.get("codes"):
            subject_matches.extend(ctx["codes"])
        if ctx.get("major"):
            subject_matches.append(ctx["major"])

        if subject_matches:
            target_sub = subject_matches[0]
            matched_text = pronoun_match.group(0)
            noun_prefix = re.sub(
                r"\s+(?:này|đó|trên)$", "", matched_text, flags=re.IGNORECASE
            ).strip()
            if (
                noun_prefix.lower() in ("nó", "cái đó")
                or target_sub.lower().startswith(noun_prefix.lower())
            ):
                replacement = target_sub
            else:
                replacement = f"{noun_prefix} {target_sub}"

            resolved = (
                clean_current[: pronoun_match.start()]
                + replacement
                + clean_current[pronoun_match.end() :]
            )
            resolved = re.sub(
                r"^(?:thế còn|còn|vậy còn)\s+", "", resolved, flags=re.IGNORECASE
            ).strip()
            rewritten = True
            rewrite_mode = "anaphora_substitution"

    # Case 4: Elliptical follow-up starting with "Thế còn...", "Còn..."
    if not rewritten and has_leading_connector:
        clean_follow_up = re.sub(
            r"^(?:thế còn|còn|vậy còn)\s+", "", clean_current, flags=re.IGNORECASE
        ).strip()
        # If user asks about a new year (e.g., "Thế còn năm 2025?")
        new_year_match = _YEAR_RE.search(clean_follow_up)
        if new_year_match and not any(
            w in clean_follow_up.lower() for w in ("ngành", "điểm", "học phí", "chỉ tiêu")
        ):
            base = re.sub(r"\b202[0-9]\b", "", prev_user_q).strip()
            base = re.sub(
                r"\s*(?:như thế nào|thế nào|bao nhiêu|là gì|có không|\?)+\s*$",
                "",
                base,
                flags=re.IGNORECASE,
            ).strip()
            resolved = f"{base} {clean_follow_up}".strip()
            rewritten = True
            rewrite_mode = "anaphora_substitution"
        elif ctx.get("major") and "ngành" not in clean_follow_up.lower():
            resolved = f"{clean_follow_up} {ctx['major']}".strip()
            if ctx.get("year") and ctx["year"] not in resolved:
                resolved = f"{resolved} năm {ctx['year']}"
            rewritten = True
            rewrite_mode = "anaphora_substitution"
        else:
            base = re.sub(r"\b202[0-9]\b", "", prev_user_q).strip()
            base = re.sub(
                r"\s*(?:như thế nào|thế nào|bao nhiêu|là gì|có không|\?)+\s*$",
                "",
                base,
                flags=re.IGNORECASE,
            ).strip()
            resolved = f"{base} {clean_follow_up}".strip()
            rewritten = True
            rewrite_mode = "anaphora_substitution"

    # Safety check: ensure essential codes and zero-prefixed IDs from user inputs are preserved
    prev_user_codes = _CODE_RE.findall(prev_user_q)
    curr_codes = _CODE_RE.findall(clean_current)
    user_history_codes = ctx.get("user_codes", [])
    preserved_codes = list(dict.fromkeys(user_history_codes + prev_user_codes + curr_codes))

    # Ensure zero-prefixed codes like 0012 or user codes are present in resolved query
    for code in preserved_codes:
        if code not in resolved:
            resolved = f"{resolved} {code}"

    trace = {
        "rewritten": rewritten,
        "mode": rewrite_mode,
        "original_question": clean_current,
        "resolved_question": resolved,
        "history_turns_count": len(pairs),
        "preserved_codes": preserved_codes,
    }
    return resolved, trace
