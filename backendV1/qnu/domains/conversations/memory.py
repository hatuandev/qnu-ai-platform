"""Safe conversational memory extractor for multi-turn dialogues.

Extracts grounded context (verified active documents, entities, criteria,
and prior conclusions) strictly from completed and verified turns.
Never stores or propagates unverified assumptions, hallucinations, or
insufficient_evidence statements.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

_DOC_PATTERNS = [
    re.compile(
        r"\b((?:Quyết định|QĐ|Kế hoạch|KH)\s+\d+[\w/.-]*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d+/(?:QĐ-BGDĐT|KH-ĐHQN|KH-AM|QĐ-ĐHQN))\b",
        re.IGNORECASE,
    ),
]

_ENTITY_CRITERIA_RE = re.compile(
    r"\b(?:tiêu\s+chí|mục|điều)\s*(\d+\.\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_ENTITY_TASK_RE = re.compile(
    r"\b(?:nhiệm\s+vụ|mã\s+việc)\s*(\d+(?:\.\d+)?|[A-Z]{2,4}-?\d{1,5})\b",
    re.IGNORECASE,
)
_ENTITY_CODE_RE = re.compile(
    r"\b([A-Z]{2,4}-?\d{2,6}|\d{7})\b"
)
_ENTITY_TABLE_RE = re.compile(
    r"\b(?:bảng|phụ\s+lục)\s*(\d+)\b",
    re.IGNORECASE,
)

_USER_NAME_PATTERNS = [
    re.compile(
        r"\b(?:tên\s+(?:tôi|mình|em)\s+là|tên\s+(?:tôi|mình|em)|(?:tôi|mình|em)\s+tên\s+là|(?:tôi|mình|em)\s+tên)\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,3})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:tôi\s+là|mình\s+là|em\s+là)\s+([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){0,3})\b",
        re.IGNORECASE,
    ),
]

_NON_NAME_TOKENS = {
    "thí sinh",
    "học sinh",
    "sinh viên",
    "phụ huynh",
    "người dùng",
    "thầy",
    "cô",
    "cán bộ",
    "ai",
    "bot",
    "trợ lý",
}

_USER_ROLE_PATTERNS = [
    re.compile(
        r"\b(học\s+sinh\s+lớp\s+12|thí\s+sinh\s+tự\s+do|học\s+sinh|thí\s+sinh|phụ\s+huynh|sinh\s+viên)\b",
        re.IGNORECASE,
    ),
]

_USER_SCORE_PATTERNS = [
    re.compile(
        r"\b(?:được|đạt|thi\s+được|tổng\s+điểm|mức\s+điểm|điểm\s+(?:của\s+)?(?:tôi|em|mình)\s+(?:là\s+)?)\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:điểm|đ)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:điểm|đ)\b",
        re.IGNORECASE,
    ),
]

_COMBINATION_RE = re.compile(
    r"\b(?:khối|tổ\s+hợp|khối\s+thi|tổ\s+hợp\s+môn)?\s*([A-D]\d{2})\b"
)

_TARGET_MAJOR_PATTERNS = [
    re.compile(
        r"\b(?:ngành|chuyên\s+ngành)\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s-]{2,40}?)(?:\s+(?:năm|khối|học\s+phí|điểm|chỉ\s+tiêu|xét\s+tuyển|như\s+thế\s+nào)|\?|,|\.|$|được\s+không)",
        re.IGNORECASE,
    ),
]

_YEAR_MENTION_RE = re.compile(r"\b(202[4-9])\b")


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def _extract_doc_references(text: str) -> list[str]:
    raw_docs: list[str] = []
    for pat in _DOC_PATTERNS:
        for match in pat.finditer(text):
            val = match.group(1).strip() if match.groups() else match.group(0).strip()
            if val and val not in raw_docs:
                raw_docs.append(val)
    docs: list[str] = []
    for d in raw_docs:
        if not any(d != other and d in other for other in raw_docs):
            docs.append(d)
    return docs


def _extract_turn_entities(text: str) -> list[str]:
    entities: list[str] = []
    for m in _ENTITY_CRITERIA_RE.finditer(text):
        entities.append(f"Tiêu chí {m.group(1)}")
    for m in _ENTITY_TASK_RE.finditer(text):
        entities.append(f"Nhiệm vụ {m.group(1)}")
    for m in _ENTITY_TABLE_RE.finditer(text):
        entities.append(f"Bảng {m.group(1)}")
    for m in _ENTITY_CODE_RE.finditer(text):
        code = m.group(1)
        if not any(code in ent for ent in entities):
            entities.append(code)
    return list(dict.fromkeys(entities))


def extract_user_session_facts(turns: list[Any]) -> dict[str, Any]:
    """Extract self-reported user attributes across all turns of the conversation.

    Strict invariants:
    - Only tracks facts self-reported by the user in questions/prompts (name, score, combination, major, role).
    - NEVER fabricates admission scores, university cutoffs, or official criteria.
    - Used strictly for natural addressing and condition-matching against verified evidence.
    """
    user_name: str | None = None
    user_role: str | None = None
    user_score: str | None = None
    user_combination: str | None = None
    target_major: str | None = None
    target_major_code: str | None = None
    target_year: str | None = None

    for turn in turns:
        q = _normalize(
            getattr(turn, "resolved_question", None)
            or getattr(turn, "question", "")
            or (turn.get("resolved_question") or turn.get("question") or "" if isinstance(turn, dict) else "")
        )
        if not q:
            continue

        # 1. User Name
        for pat in _USER_NAME_PATTERNS:
            m = pat.search(q)
            if m:
                cand = m.group(1).strip()
                if cand.lower() not in _NON_NAME_TOKENS and len(cand) >= 2:
                    user_name = cand
                    break

        # 2. User Role
        for pat in _USER_ROLE_PATTERNS:
            m = pat.search(q)
            if m:
                user_role = m.group(1).strip()
                break

        # 3. User Score
        for pat in _USER_SCORE_PATTERNS:
            m = pat.search(q)
            if m:
                score_str = m.group(1).replace(",", ".")
                try:
                    val = float(score_str)
                    if 0.0 <= val <= 30.0:
                        user_score = score_str
                        break
                except ValueError:
                    pass

        # 4. Combination / Subjects
        m_comb = _COMBINATION_RE.search(q)
        if m_comb:
            user_combination = m_comb.group(1).upper()

        # 5. Target Major & Code
        for pat in _TARGET_MAJOR_PATTERNS:
            m = pat.search(q)
            if m:
                cand = m.group(1).strip()
                if len(cand) >= 3 and cand.lower() not in ("này", "đó", "nào", "gì"):
                    target_major = cand
                    break

        m_code = _ENTITY_CODE_RE.search(q)
        if m_code:
            code = m_code.group(1).strip()
            if len(code) == 7 and code.startswith("7"):
                target_major_code = code

        # 6. Target Year
        m_year = _YEAR_MENTION_RE.search(q)
        if m_year:
            target_year = m_year.group(1)

    # Format human-readable summary
    summary_parts = []
    if user_name:
        summary_parts.append(f"Tên: {user_name}")
    if user_role:
        summary_parts.append(f"Đối tượng: {user_role}")
    if user_score:
        score_desc = f"Mức điểm: {user_score}"
        if user_combination:
            score_desc += f" (tổ hợp {user_combination})"
        summary_parts.append(score_desc)
    elif user_combination:
        summary_parts.append(f"Tổ hợp môn: {user_combination}")
    if target_major:
        major_desc = f"Ngành quan tâm: {target_major}"
        if target_major_code:
            major_desc += f" (mã {target_major_code})"
        summary_parts.append(major_desc)
    elif target_major_code:
        summary_parts.append(f"Mã ngành: {target_major_code}")
    if target_year:
        summary_parts.append(f"Năm tuyển sinh: {target_year}")

    summary_text = ". ".join(summary_parts) if summary_parts else None

    return {
        "user_name": user_name,
        "user_role": user_role,
        "user_score": user_score,
        "user_combination": user_combination,
        "target_major": target_major,
        "target_major_code": target_major_code,
        "target_year": target_year,
        "summary": summary_text,
    }


def extract_safe_conversation_memory(
    turns: list[Any],
    all_turns: list[Any] | None = None,
) -> dict[str, Any]:
    """Extract bounded, grounded conversational memory from completed turns.

    Strict invariants:
    1. Only inspect turns with status == 'completed' and result['status'] == 'answered'.
    2. Drops turns with 'insufficient_evidence', 'failed', 'uncertain', or 'cancelled'.
    3. Extracts verified document names, entities, and brief grounded statements.
    4. Tracks self-reported user attributes across session turns via session_facts.
    5. Never carries ungrounded opinions or hallucinated external knowledge.
    """
    active_docs: list[str] = []
    active_entities: list[str] = []
    grounded_conclusions: list[dict[str, str]] = []
    turn_entity_history: list[list[str]] = []

    # Extract session facts across all conversation turns if provided
    session_facts = extract_user_session_facts(all_turns if all_turns is not None else turns)

    for turn in turns:
        # Determine status and result safely regardless of dict vs ORM model
        turn_status = getattr(turn, "status", None) or (
            turn.get("status") if isinstance(turn, dict) else None
        )
        if turn_status != "completed":
            continue

        result = getattr(turn, "result", None) or (
            turn.get("result") if isinstance(turn, dict) else None
        )
        if not result or not isinstance(result, dict):
            continue

        if result.get("status") != "answered":
            # Strictly skip insufficient_evidence or non-answered turns
            continue

        q = _normalize(
            getattr(turn, "resolved_question", None)
            or getattr(turn, "question", "")
            or (turn.get("resolved_question") or turn.get("question") or "")
        )

        # Extract docs from question and source citations
        docs_in_q = _extract_doc_references(q)
        for doc in docs_in_q:
            if doc not in active_docs:
                active_docs.append(doc)

        sources = result.get("sources") or []
        for src in sources:
            if isinstance(src, dict):
                src_title = src.get("title") or src.get("source_title") or ""
                docs_in_src = _extract_doc_references(src_title)
                for doc in docs_in_src:
                    if doc not in active_docs:
                        active_docs.append(doc)

        # Extract entities
        ents = _extract_turn_entities(q)
        turn_entity_history.append(ents)
        for ent in ents:
            if ent not in active_entities:
                active_entities.append(ent)

        # Extract brief grounded conclusion (max 160 chars) from first verified statement
        stmts = result.get("statements") or []
        if stmts and isinstance(stmts, list):
            first_stmt = stmts[0]
            stmt_text = (
                first_stmt.get("text", "") if isinstance(first_stmt, dict) else str(first_stmt)
            )
            clean_stmt = _normalize(stmt_text)
            if clean_stmt:
                short_conclusion = clean_stmt[:160] + ("..." if len(clean_stmt) > 160 else "")
                grounded_conclusions.append({
                    "question": q[:100],
                    "conclusion": short_conclusion,
                })

    last_entity = None
    prior_entity = None
    if turn_entity_history:
        for ents in reversed(turn_entity_history):
            if ents and last_entity is None:
                last_entity = ents[0]
            elif ents and prior_entity is None and ents[0] != last_entity:
                prior_entity = ents[0]
                break

    active_document = None
    if active_docs:
        full_named = [
            d
            for d in active_docs
            if re.match(r"^(?:Quyết định|Kế hoạch)\b", d, re.IGNORECASE)
        ]
        active_document = full_named[-1] if full_named else active_docs[-1]

    # Construct bounded summary text
    summary_parts = []
    if active_document:
        summary_parts.append(f"Văn bản đang trao đổi: {active_document}")
    if last_entity:
        summary_parts.append(f"Mục vừa đối chiếu: {last_entity}")
    if prior_entity:
        summary_parts.append(f"Mục trước đó: {prior_entity}")
    if session_facts and session_facts.get("summary"):
        summary_parts.append(f"Ngữ cảnh người hỏi: {session_facts['summary']}")

    return {
        "active_document": active_document,
        "all_active_documents": active_docs,
        "active_entities": active_entities,
        "last_entity": last_entity,
        "prior_entity": prior_entity,
        "grounded_conclusions": grounded_conclusions[-2:],  # keep at most 2 recent
        "session_facts": session_facts,
        "summary_text": ". ".join(summary_parts) if summary_parts else None,
    }
