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
    r"\b(?:(?:hồ sơ nghiệm thu|hồ sơ|nhiệm vụ|tiêu chí|ý|mục|phần|bảng|điều|mốc|thời gian|trường hợp|ngành|mã)\s+(?:này|đó|trên)|nó|cái đó)\b",
    re.IGNORECASE,
)

_COMPARE_PREVIOUS_RE = re.compile(
    r"\b(?:tóm lại\s+)?so với\s+(?:mục|tiêu chí|nhiệm vụ|phần|nội dung)?\s*(?:trước|vừa rồi|đó|trên)\b",
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
_CODE_RE = re.compile(r"(?<!/)\b([A-Z]{2,4}-?\d{1,7}|\d{7}|0\d{2,5})\b(?!/)")
_SECTION_RE = re.compile(r"\b(?:\d+\.\d+(?:\.\d+)?)\b")
_SCORE_RE = re.compile(r"\b(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:điểm|đ)\b", re.IGNORECASE)

_ENTITY_TYPE_RE = re.compile(
    r"\b(tiêu\s+chí|nhiệm\s+vụ|chương\s+trình\s+mã|chương\s+trình|ngành|mã\s+xét\s+tuyển|mã\s+việc|mã\s+ngành|mã|mục|điều|bảng)\b",
    re.IGNORECASE,
)

_COMMON_PREDICATES = (
    "tính điểm và mức độ",
    "tính điểm",
    "cách tính điểm",
    "mức độ",
    "điều kiện",
    "tiêu chuẩn",
    "yêu cầu",
    "hồ sơ",
    "thủ tục",
    "chỉ tiêu",
    "kinh phí",
    "thời gian thực hiện",
    "thời gian",
    "tiến độ",
    "đơn vị chủ trì",
    "ai chủ trì",
    "đơn vị phối hợp",
    "sản phẩm",
    "kết quả",
    "nội dung thực hiện",
    "nội dung",
    "quy định gì",
    "điều kiện gì",
)


def _extract_identifiers(text: str) -> list[str]:
    codes = _CODE_RE.findall(text)
    sections = _SECTION_RE.findall(text)
    return list(dict.fromkeys(codes + sections))

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


_DOC_REF_RE = re.compile(
    r"\b(?:theo\s+)?(Quyết định\s+\d+[\w/.-]*|QĐ\s+\d+[\w/.-]*|Kế hoạch\s+\d+[\w/.-]*|KH\s+\d+[\w/.-]*|\d+/(?:QĐ-BGDĐT|KH-ĐHQN|KH-AM))\b",
    re.IGNORECASE,
)
_CRITERIA_MATCH_RE = re.compile(r"\b(tiêu\s+chí\s+\d+\.\d+(?:\.\d+)?)\b", re.IGNORECASE)
_TASK_MATCH_RE = re.compile(r"\b(nhiệm\s+vụ\s+(?:\d+(?:\.\d+)?|[A-Z]{2,4}-?\d{1,5}))\b", re.IGNORECASE)
_MUC_RE = re.compile(r"\b(mục\s+\d+(?:\.\d+)*)\b", re.IGNORECASE)

_PROPERTY_FOLLOWUP_KEYWORDS = (
    "đơn vị chủ trì",
    "chủ trì",
    "đơn vị phối hợp",
    "phối hợp",
    "thời gian thực hiện",
    "thời gian",
    "tiến độ",
    "mốc thời gian",
    "sản phẩm",
    "kết quả",
    "kinh phí",
    "chi phí",
    "ngân sách",
    "trách nhiệm",
    "ai thực hiện",
    "ai",
    "khi nào",
    "ở đâu",
    "hồ sơ",
    "thủ tục",
)


def _extract_cumulative_history_context(
    pairs: list[tuple[str, str]],
    conversation_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Scan history from earliest to latest to preserve entities, documents, and ongoing topics."""
    last_certificate: str | None = None
    last_year: str | None = None
    last_major: str | None = None
    last_document: str | None = None
    all_codes: list[str] = []
    user_codes: list[str] = []
    entities_history: list[str] = []
    has_conversion: bool = False
    has_eng_subject: bool = False

    for user_q, bot_a in pairs:
        combined_turn = f"{user_q} {bot_a}"

        # Detect document reference
        doc_m = _DOC_REF_RE.search(user_q) or _DOC_REF_RE.search(bot_a)
        if doc_m:
            last_document = doc_m.group(0).strip()
            if last_document.lower().startswith("theo "):
                last_document = last_document[5:].strip()

        # Detect specific entities (criteria, tasks, sections)
        crit_m = _CRITERIA_MATCH_RE.search(user_q)
        if crit_m:
            entities_history.append(crit_m.group(1).capitalize())
        else:
            task_m = _TASK_MATCH_RE.search(user_q)
            if task_m:
                entities_history.append(task_m.group(1).capitalize())
            else:
                secs = _SECTION_RE.findall(user_q)
                if secs:
                    prefix = (
                        "Tiêu chí"
                        if "tiêu chí" in user_q.lower() or "tiêu chí" in bot_a.lower()
                        else "Mục"
                    )
                    for s in secs:
                        entities_history.append(f"{prefix} {s}")
                else:
                    muc_m = _MUC_RE.search(user_q)
                    if muc_m:
                        entities_history.append(muc_m.group(1).capitalize())

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

    unique_entities = []
    for ent in entities_history:
        if not unique_entities or unique_entities[-1] != ent:
            unique_entities.append(ent)

    last_entity = unique_entities[-1] if unique_entities else None
    prior_entity = (
        unique_entities[-2]
        if len(unique_entities) >= 2 and unique_entities[-2] != last_entity
        else None
    )

    if conversation_memory:
        if last_document is None and conversation_memory.get("active_document"):
            last_document = str(conversation_memory["active_document"])
        if last_entity is None and conversation_memory.get("last_entity"):
            last_entity = str(conversation_memory["last_entity"])
        if last_year is None and conversation_memory.get("year"):
            last_year = str(conversation_memory["year"])
        if conversation_memory.get("codes"):
            mem_codes = [str(c) for c in conversation_memory["codes"]]
            user_codes.extend(mem_codes)
            all_codes.extend(mem_codes)

    return {
        "certificate": last_certificate,
        "year": last_year,
        "major": last_major,
        "document": last_document,
        "last_entity": last_entity,
        "prior_entity": prior_entity,
        "codes": list(dict.fromkeys(user_codes + all_codes)),
        "user_codes": list(dict.fromkeys(user_codes)),
        "has_conversion": has_conversion,
        "has_eng_subject": has_eng_subject,
    }


def rewrite_contextual_query(
    current_question: str,
    history: list[dict[str, Any] | tuple[str, str]] | None,
    conversation_memory: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Rewrite a follow-up question into a standalone query using conversation history.

    Returns:
        (resolved_question, trace_info)
    """
    clean_current = _normalize_text(current_question)
    if not clean_current:
        return clean_current, {"rewritten": False, "reason": "empty_question"}

    pairs = _extract_history_pairs(history) if history else []
    if not pairs and not conversation_memory:
        return clean_current, {"rewritten": False, "reason": "insufficient_history"}

    # Last turn context
    prev_user_q = pairs[-1][0] if pairs else ""
    prev_bot_a = pairs[-1][1] if pairs else ""
    prev_bot_norm = prev_bot_a.casefold()

    rewritten = False
    resolved = clean_current
    rewrite_mode = "none"

    # Cumulative context across all turns
    ctx = _extract_cumulative_history_context(pairs, conversation_memory=conversation_memory)

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
    is_compare_previous = bool(_COMPARE_PREVIOUS_RE.search(clean_current))

    # Detect elliptical property questions (e.g. "Đơn vị nào chủ trì và phối hợp?", "Thời gian thực hiện khi nào?")
    curr_codes = _CODE_RE.findall(clean_current)
    has_own_entity = bool(
        curr_codes
        or _DOC_REF_RE.search(clean_current)
        or _CRITERIA_MATCH_RE.search(clean_current)
        or _TASK_MATCH_RE.search(clean_current)
    )
    is_property_followup = (
        not has_own_entity
        and any(
            re.search(r"\b" + re.escape(w) + r"\b", clean_current, re.IGNORECASE)
            for w in _PROPERTY_FOLLOWUP_KEYWORDS
        )
        and bool(ctx.get("last_entity") or ctx.get("document"))
    )

    is_anaphoric = (
        has_leading_connector
        or bool(pronoun_match)
        or has_score_or_tier
        or is_compare_previous
        or is_property_followup
    )

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

        matched_text = pronoun_match.group(0)
        noun_prefix = re.sub(
            r"\s+(?:này|đó|trên)$", "", matched_text, flags=re.IGNORECASE
        ).strip()

        if noun_prefix.lower() in ("mốc", "thời gian", "mốc thời gian"):
            resolved = clean_current
            rewritten = True
            rewrite_mode = "anaphora_substitution"
        elif subject_matches:
            target_sub = subject_matches[0]
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

        if (
            rewritten
            and ctx.get("document")
            and ctx["document"].lower() not in resolved.lower()
        ):
            if resolved.endswith("?"):
                resolved = f"{resolved[:-1].strip()} theo {ctx['document']}?"
            else:
                resolved = f"{resolved} theo {ctx['document']}"

    # Case 3.5: Cross-turn comparison (e.g. "Tóm lại so với mục trước thì thế nào?", "So với tiêu chí trước thì sao?")
    if not rewritten and _COMPARE_PREVIOUS_RE.search(clean_current):
        last_ent = ctx.get("last_entity")
        prior_ent = ctx.get("prior_entity")
        doc_str = ctx.get("document")
        doc_clause = (
            f" theo {doc_str}"
            if doc_str and doc_str.lower() not in clean_current.lower()
            else ""
        )
        if last_ent and prior_ent:
            cleaned_comp = _COMPARE_PREVIOUS_RE.sub("", clean_current).strip()
            cleaned_comp = re.sub(
                r"^(?:thì\s+sao|thế\s+nào|như\s+thế\s+nào|\?)+",
                "",
                cleaned_comp,
                flags=re.IGNORECASE,
            ).strip()
            predicate = f" {cleaned_comp}" if cleaned_comp else " như thế nào"
            resolved = f"So sánh {last_ent} với {prior_ent}{doc_clause}{predicate}?"
            rewritten = True
            rewrite_mode = "cross_turn_comparison"

    # Case 3.6: Elliptical property follow-up (e.g. "Đơn vị nào chủ trì và phối hợp?", "Thời gian thực hiện khi nào?")
    if not rewritten and is_property_followup:
        last_ent = ctx.get("last_entity")
        doc_str = ctx.get("document")
        doc_clause = (
            f" theo {doc_str}"
            if doc_str and doc_str.lower() not in clean_current.lower()
            else ""
        )
        entity_clause = (
            f" của {last_ent}"
            if last_ent and last_ent.lower() not in clean_current.lower()
            else ""
        )
        clean_core = re.sub(
            r"\s*(?:thì\s+sao|thế\s+nào|như\s+thế\s+nào|\?)+\s*$",
            "",
            clean_current,
            flags=re.IGNORECASE,
        ).strip()
        if any(
            w in clean_current.lower()
            for w in ("ai", "nào", "gì", "đâu", "bao nhiêu", "khi nào")
        ):
            resolved = f"{clean_core}{entity_clause}{doc_clause}?"
        else:
            resolved = f"{clean_core}{entity_clause}{doc_clause} như thế nào?"
        rewritten = True
        rewrite_mode = "property_followup"

    # Case 4: Elliptical follow-up starting with "Thế còn...", "Còn..."
    if not rewritten and has_leading_connector:
        clean_follow_up = re.sub(
            r"^(?:thế còn|còn|vậy còn)\s+", "", clean_current, flags=re.IGNORECASE
        ).strip()

        curr_ids = _extract_identifiers(clean_follow_up)
        prev_ids = _extract_identifiers(prev_user_q)
        has_new_identifier = bool(curr_ids and any(cid not in prev_ids for cid in curr_ids))

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
        elif has_new_identifier:
            # Ca biên 2: When follow-up introduces a new code/criterion/section distinct from previous turn,
            # do not blindly prepend the previous turn's base which contains the old entity.
            clean_core = re.sub(
                r"\s*(?:thì\s+sao|thế\s+nào|như\s+thế\s+nào|bao\s+nhiêu|là\s+gì|có\s+không|\?)+\s*$",
                "",
                clean_follow_up,
                flags=re.IGNORECASE,
            ).strip()

            entity_prefix = ""
            ent_match = _ENTITY_TYPE_RE.search(prev_user_q)
            if ent_match:
                kw = ent_match.group(0)
                if not re.search(r"\b" + re.escape(kw) + r"\b", clean_core, re.IGNORECASE):
                    entity_prefix = kw.capitalize() + " "

            subject_part = f"{entity_prefix}{clean_core}".strip()

            has_own_predicate = any(
                w in clean_core.lower()
                for w in (
                    "ai",
                    "ở đâu",
                    "khi nào",
                    "bao nhiêu",
                    "yêu cầu",
                    "điều kiện",
                    "chủ trì",
                    "thời gian",
                    "sản phẩm",
                    "tính điểm",
                )
            )

            predicate_part = ""
            if not has_own_predicate:
                for pred in _COMMON_PREDICATES:
                    if re.search(r"\b" + re.escape(pred) + r"\b", prev_user_q, re.IGNORECASE):
                        predicate_part = f" {pred}"
                        break
                if not predicate_part:
                    prev_base = prev_user_q
                    if prev_ids:
                        pattern = (
                            r"(?:(?:tiêu chí|nhiệm vụ|chương trình|mã|mục|điều)\s+)?(?:[\w\s]{0,30})?"
                            + re.escape(prev_ids[0])
                            + r"\)?"
                        )
                        prev_base = re.sub(pattern, "", prev_base, flags=re.IGNORECASE)
                    prev_base = re.sub(
                        r"\s*(?:như thế nào|thế nào|bao nhiêu|là gì|có không|\?)+\s*$",
                        "",
                        prev_base,
                        flags=re.IGNORECASE,
                    ).strip()
                    if prev_base:
                        predicate_part = f" {prev_base}"

            doc_match = re.search(
                r"\b(?:theo\s+)?(Quyết định\s+\d+[\w/.-]*|QĐ\s+\d+[\w/.-]*|Kế hoạch\s+\d+[\w/.-]*|KH\s+\d+[\w/.-]*)\b",
                prev_user_q,
                re.IGNORECASE,
            )
            doc_part = ""
            if doc_match:
                doc_str = doc_match.group(0)
                if not doc_str.lower().startswith("theo"):
                    doc_str = f"theo {doc_str}"
                if (
                    doc_str.lower() not in subject_part.lower()
                    and doc_str.lower() not in predicate_part.lower()
                ):
                    doc_part = f" {doc_str}"

            resolved = f"{subject_part}{predicate_part}{doc_part}".strip()
            if not resolved.endswith("?"):
                if any(
                    w in resolved.lower()
                    for w in (
                        "ai",
                        "nào",
                        "gì",
                        "đâu",
                        "bao nhiêu",
                        "sao",
                        "thế nào",
                        "như thế nào",
                    )
                ):
                    resolved += "?"
                else:
                    resolved += " như thế nào?"
            rewritten = True
            rewrite_mode = "anaphora_substitution"
        elif ctx.get("major") and "ngành" not in clean_follow_up.lower():
            resolved = f"{clean_follow_up} {ctx['major']}".strip()
            if ctx.get("year") and ctx["year"] not in resolved:
                resolved = f"{resolved} năm {ctx['year']}"
            rewritten = True
            rewrite_mode = "anaphora_substitution"
        elif any(
            w in clean_follow_up.lower()
            for w in (
                "chủ trì",
                "phối hợp",
                "sản phẩm",
                "kết quả",
                "thời gian",
                "tiến độ",
                "kinh phí",
                "chi phí",
                "trách nhiệm",
                "ai",
                "ở đâu",
                "khi nào",
                "bao nhiêu",
                "điều kiện",
                "yêu cầu",
            )
        ) and ctx.get("last_entity"):
            last_ent = ctx["last_entity"]
            doc_str = ctx.get("document")
            doc_clause = (
                f" theo {doc_str}"
                if doc_str and doc_str.lower() not in clean_follow_up.lower()
                else ""
            )
            clean_core_prop = re.sub(
                r"\s*(?:thì\s+sao|thế\s+nào|như\s+thế\s+nào|\?)+\s*$",
                "",
                clean_follow_up,
                flags=re.IGNORECASE,
            ).strip()
            if any(
                w in clean_follow_up.lower()
                for w in ("ai", "nào", "gì", "đâu", "bao nhiêu", "khi nào")
            ):
                resolved = f"{clean_core_prop} của {last_ent}{doc_clause}?"
            else:
                resolved = f"{clean_core_prop} của {last_ent}{doc_clause} như thế nào?"
            rewritten = True
            rewrite_mode = "property_followup"
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

    # If the current user question provided its own codes distinct from history,
    # preserve ONLY current codes to prevent cross-turn entity conflict
    if curr_codes:
        preserved_codes = list(dict.fromkeys(curr_codes))
    else:
        preserved_codes = list(dict.fromkeys(user_history_codes + prev_user_codes))

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
