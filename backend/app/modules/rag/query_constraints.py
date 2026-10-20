"""Explicit user constraints, separate from interpreting source column headers."""

import re
import unicodedata

from app.modules.knowledge.metric_roles import header_unit


def metric_attributes(question: str) -> list[str]:
    """Collect coordinated requests instead of forcing them into a single role.

    These are language constructions, never a catalog of document labels/entities.
    Bare quantity remains unknown; a rate does not also request its numerator.
    """
    text = question.casefold()
    roles = []
    if re.search(r'\b(?:chỉ tiêu|quota|số lượng tuyển(?: sinh)?)\b', text):
        roles.append('expected_quota')
    rate = bool(re.search(r'\b(?:tỷ lệ|tỉ lệ|percentage|rate)\b', text))
    quantity = bool(re.search(r'\b(?:số|bao nhiêu|mấy|count|quantity)\b', text))
    coordinated = bool(re.search(r'\b(?:và|cùng|riêng|đồng thời|and)\b', text))
    if re.search(r'\b(?:ghi nhận|recorded|reported)\b', text) and quantity and (not rate or coordinated):
        roles.append('reported_count')
    if quantity and re.search(r'\bđã\s+(?:nghiệm thu|xác nhận)\b', text):
        roles.append('reported_count')
    if re.search(r'\b(?:ước tính|dự báo|estimated|forecast)\b', text) and (not rate or coordinated):
        roles.append('estimated_count')
    if rate:
        roles.append('rate')
    return list(dict.fromkeys(roles))


def requested_unit(question: str) -> str | None:
    """Read an explicit unit without converting it or guessing a default."""
    parenthetic = header_unit(question)
    if parenthetic:
        return parenthetic
    match = re.search(r'\b(?:tính|đo)\s+(?:theo|bằng)\s+([^\W\d_]+(?:/[^\W\d_]+)?)', question, re.IGNORECASE)
    return match[1] if match else None


def source_name_in_question(name: str, question: str) -> bool:
    """Match complete source labels; retain accents, leading zeroes and punctuation."""
    normalized = lambda value: ' '.join(unicodedata.normalize('NFC', value).casefold().split())
    return bool(re.search(r'(?<!\w)' + re.escape(normalized(name)) + r'(?!\w)', normalized(question)))
