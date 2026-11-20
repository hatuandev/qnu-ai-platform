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
    "so sánh",
    "khác gì",
    "khác nhau",
    "điểm khác biệt",
    "đối chiếu",
    "tương quan",
    "phân biệt",
    "giống và khác",
    "thống kê",
    "tổng hợp",
    "tổng số",
    "danh sách các",
    "liệt kê các",
    "tư vấn",
    "định hướng",
    "cần chuẩn bị",
    "cần làm gì",
    "để đạt được",
    "để đạt mức",
    "hướng dẫn triển khai",
    "nhiệm vụ",
    "đầu việc",
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

_MULTI_CRITERIA_RE = re.compile(
    r"\b(tiêu chí|mục|điều|khoản|bảng|chương trình|mã|nhiệm vụ|phụ lục)(?:\s+số)?\s+([A-Za-z0-9_.-]+(?:\s*\([^)]+\))?)"
    r"\s+(?:và|cùng với|cũng như|so với)\s+"
    r"(?:(?:tiêu chí|mục|điều|khoản|bảng|chương trình|mã|nhiệm vụ|phụ lục)(?:\s+số)?\s+)?([A-Za-z0-9_.-]+(?:\s*\([^)]+\))?)"
    r"(?=[?,;:\s]|$)",
    re.IGNORECASE,
)

_MULTI_NAMED_ENTITY_RE = re.compile(
    r"\b(ngành|mã ngành|chuyên ngành|tiêu chí|mục|điều|khoản|bảng|chương trình|mã|nhiệm vụ|phụ lục)"
    r"(?:\s+số)?\s+([^,;?]+?)\s+(?:và|cùng với|cũng như|so với)\s+"
    r"(?:(?:ngành|mã ngành|chuyên ngành|tiêu chí|mục|điều|khoản|bảng|chương trình|mã|nhiệm vụ|phụ lục)(?:\s+số)?\s+)?([^,;?]+?)"
    r"(?=\s+(?:có|về|được|theo|thuộc|là|trong|năm|\?|;|,)|$)",
    re.IGNORECASE,
)

_COMPOUND_TASK_RE = re.compile(
    r"^(?:Việc|Công tác|Hoạt động|Nhiệm vụ)?\s*(.+?)\s+và\s+(.+?)\s+"
    r"((?:do\s+(?:đơn vị|ai|bộ phận|phòng|ban)|thuộc trách nhiệm|giao cho).+?|\b(?:thực hiện|triển khai|diễn ra)\s+(?:như thế nào|khi nào|ở đâu|vào thời gian nào).+?)$",
    re.IGNORECASE,
)

_LEAD_CONDITION_RE = re.compile(
    r"^(Để\s+.+?),\s*(.+?\b(?:bao nhiêu|như thế nào|thế nào|ra sao|gì|nào)\b.+?)\s+và\s+(.+?\b(?:bao nhiêu|như thế nào|thế nào|ra sao|gì|nào|khi nào|ở đâu)\b.+?)[?.]?$",
    re.IGNORECASE,
)

_AGGREGATION_MULTI_RE = re.compile(
    r"^(?:Tổng hợp|Thống kê|Liệt kê)\s+(.+?\b(?:tiêu chí|mục|điều|bảng|nhiệm vụ)\s+[A-Za-z0-9_.-]+(?:\s*\([^)]+\))?)\s+và\s+(.+?\b(?:tiêu chí|mục|điều|bảng|nhiệm vụ)\s+[A-Za-z0-9_.-]+(?:\s*\([^)]+\))?)(.*)$",
    re.IGNORECASE,
)

_COMPARISON_RE = re.compile(
    r"^So sánh(?:\s+(?:giữa\s+)?(.+?)\s+giữa|\s+giữa)?\s+(.+?)\s+(?:và|với)\s+(.+?)(?:\s+về\s+(.+?))?(?:\s+\btheo\s+(.+?))?[?.]?$",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b(202[0-9])\b")
_CODE_RE = re.compile(r"\b(7\d{6}[A-Za-z0-9]*|[A-Z]{2,4}-?\d{2,7}|\d{7}|\b0\d{1,4}\b)\b")
_MAJOR_RE = re.compile(
    r"\b(ngành\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+?)(?:\s+(?:năm|học phí|điểm|chỉ tiêu|xét tuyển|như thế nào)|\?|,|;|$)",
    re.IGNORECASE,
)
_SUBJECT_RE = re.compile(
    r"\b(cơ sở giáo dục đại học|đoàn đánh giá ngoài|ban thư ký|bộ chỉ số(?: chuyển đổi số)?|quyết định\s+\d+[\w/-]*|kế hoạch\s+\d+[\w/-]*)\b",
    re.IGNORECASE,
)


def _extract_query_context(query: str) -> dict[str, Any]:
    years = _YEAR_RE.findall(query)
    codes = _CODE_RE.findall(query)
    major_match = _MAJOR_RE.search(query)
    major = major_match.group(1).strip() if major_match else None
    subj_match = _SUBJECT_RE.search(query)
    subject = subj_match.group(1).strip() if subj_match else None
    return {
        "years": years,
        "codes": codes,
        "major": major,
        "subject": subject,
    }


def _enrich_clause(clause: str, context: dict[str, Any]) -> str:
    missing_parts: list[str] = []
    subject = context.get("subject")
    if subject and subject.casefold() not in clause.casefold():
        missing_parts.append(subject)
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


_INTERROGATIVE_WORDS = (
    "bao nhiêu",
    "như thế nào",
    "thế nào",
    "ra sao",
    "ở đâu",
    "khi nào",
    "mấy",
    "là gì",
    "những gì",
    "ai chủ trì",
)


def _match_multi_named_entity(query: str) -> re.Match | None:
    for m in _MULTI_NAMED_ENTITY_RE.finditer(query):
        e1 = m.group(2).strip()
        e2 = m.group(3).strip()
        if (
            len(e1.split()) <= 10
            and len(e2.split()) <= 10
            and not any(iw in e1.lower() for iw in _INTERROGATIVE_WORDS)
            and not any(iw in e2.lower() for iw in _INTERROGATIVE_WORDS)
        ):
            return m
    return None


def needs_decomposition(query: str) -> bool:
    """Return True if query has conditional/comparison/exception keywords, multi-criteria, or >= 2 clauses."""
    norm = _normalize_text(query)
    if query.count("?") >= 2:
        return True
    if any(kw in norm for kw in _CONDITION_KEYWORDS):
        return True
    if bool(_MULTI_CRITERIA_RE.search(query)) or (_match_multi_named_entity(query) is not None):
        return True
    if bool(_COMPOUND_TASK_RE.search(query)):
        return True
    if bool(_LEAD_CONDITION_RE.search(query)):
        return True
    if bool(_AGGREGATION_MULTI_RE.search(query)):
        return True
    if bool(_COMPARISON_RE.search(query)):
        return True
    codes = list(dict.fromkeys(_CODE_RE.findall(query)))
    return len(codes) >= 2


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

    # Pattern A: Compound Tasks with shared interrogative predicate (e.g. "Việc A và B do ai chủ trì...")
    m_task = _COMPOUND_TASK_RE.search(clean_query)
    if m_task:
        lead = (
            "Việc "
            if clean_query.lower().startswith("việc")
            else (
                "Công tác "
                if clean_query.lower().startswith("công tác")
                else ("Nhiệm vụ " if clean_query.lower().startswith("nhiệm vụ") else "")
            )
        )
        t1 = m_task.group(1).strip()
        t2 = m_task.group(2).strip()
        pred = m_task.group(3).strip()
        return [f"{lead}{t1} {pred}".strip(), f"{lead}{t2} {pred}".strip()]

    # Pattern B: Lead condition with conjoined questions (e.g. "Để đạt mức X, cơ sở cần bao nhiêu điểm và cần lưu ý mốc báo cáo nào?")
    m_lead = _LEAD_CONDITION_RE.search(clean_query)
    if m_lead:
        lead = m_lead.group(1).strip()
        q1 = f"{lead}, {m_lead.group(2).strip()}"
        q2 = f"{lead}, {m_lead.group(3).strip()}"
        return [q1.strip(), q2.strip()]

    # Pattern C: Aggregation over multiple criteria (e.g. "Tổng hợp các phân hệ của tiêu chí 2.4 và các dịch vụ trực tuyến của tiêu chí 2.5 theo QĐ 4740")
    m_agg = _AGGREGATION_MULTI_RE.search(clean_query)
    if m_agg:
        tail = m_agg.group(3).strip()
        q1 = f"Quy định {m_agg.group(1).strip()} {tail}".strip()
        q2 = f"Quy định {m_agg.group(2).strip()} {tail}".strip()
        return [q1, q2]

    # Pattern D1: Comparison questions starting with "So sánh"
    m_comp = _COMPARISON_RE.search(clean_query)
    if m_comp:
        pre_aspect = m_comp.group(1).strip() if m_comp.group(1) else ""
        e1 = m_comp.group(2).strip()
        e2 = m_comp.group(3).strip()
        post_aspect = m_comp.group(4).strip() if m_comp.group(4) else ""
        doc = m_comp.group(5).strip() if m_comp.group(5) else ""
        aspect = f"{pre_aspect} {post_aspect}".strip()
        aspect = re.sub(r"\bgiữa\s*$", "", aspect, flags=re.IGNORECASE).strip()
        doc_part = f"theo {doc}" if doc else ""
        q1_parts = [aspect, e1, doc_part]
        q2_parts = [aspect, e2, doc_part]
        q1 = " ".join(p for p in q1_parts if p).strip()
        q2 = " ".join(p for p in q2_parts if p).strip()
        if q1 and q2:
            return [q1, q2]

    # Pattern D2: Multiple criteria / codes / programs / majors
    match = _match_multi_named_entity(clean_query) or _MULTI_CRITERIA_RE.search(clean_query)
    if match:
        kind = match.group(1).strip()
        code1 = match.group(2).rstrip(".,;:? ").strip()
        code2 = match.group(3).rstrip(".,;:? ").strip()
        q1 = clean_query[: match.start()] + f"{kind} {code1}" + clean_query[match.end() :]
        q2 = clean_query[: match.start()] + f"{kind} {code2}" + clean_query[match.end() :]
        # Clean up dangling "giữa" or "So sánh" if present
        q1 = re.sub(r"\bgiữa\s+", "", q1, flags=re.IGNORECASE).strip()
        q2 = re.sub(r"\bgiữa\s+", "", q2, flags=re.IGNORECASE).strip()
        q1 = re.sub(r"^So sánh\s+", "", q1, flags=re.IGNORECASE).strip()
        q2 = re.sub(r"^So sánh\s+", "", q2, flags=re.IGNORECASE).strip()
        return [q1.strip(), q2.strip()]

    # Pattern F: Explicit multiple codes / majors without structured conjunction
    codes = list(dict.fromkeys(_CODE_RE.findall(clean_query)))
    if len(codes) >= 2:
        sub_queries = []
        for code in codes[:3]:
            other_codes = [c for c in codes if c != code]
            focused = clean_query
            for oc in other_codes:
                focused = re.sub(rf"\b{re.escape(oc)}\b\s*(?:và|với|,)?\s*", "", focused, flags=re.IGNORECASE)
            focused = re.sub(r"^So sánh\s+", "", focused, flags=re.IGNORECASE)
            focused = re.sub(r"\s*(?:và|với|,)?\s*$", "", focused).strip()
            if code not in focused:
                focused = f"Mã {code} {focused}".strip()
            sub_queries.append(focused)
        if sub_queries:
            return sub_queries[:3]

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
