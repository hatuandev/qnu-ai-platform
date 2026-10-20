"""Lossless code candidates; only published identity fields can verify them."""

import re
import unicodedata

TOKEN = re.compile(r'(?<![\w/-])[\w]+(?:[-_./][\w]+)*(?![\w/-])', re.UNICODE)
YEAR = re.compile(r'(?:19|20)\d{2}')


def normalize_code(value: str) -> str:
    return unicodedata.normalize('NFC', value).strip().upper()


def code_in_question(code: str, question: str) -> bool:
    return bool(re.search(r'(?<![\w/.-])' + re.escape(normalize_code(code)) + r'(?![\w/.-])',
                          normalize_code(question)))


def code_candidates(question: str) -> list[str]:
    candidates = []
    text = unicodedata.normalize('NFC', question)
    labeled_spans = {m.span('code') for m in re.finditer(
        r'\bmã(?:\s+(?:chương trình|ngành|nhiệm vụ|văn bản|số|CT))?\s+["\'`]?'
        r'(?P<code>[\w]+(?:[-_./][\w]+)*)', text, re.IGNORECASE)}
    for match in TOKEN.finditer(text):
        value = match.group()
        labeled = match.span() in labeled_spans
        structured = any(c.isalpha() for c in value) and any(c.isdigit() for c in value)
        numeric = value.isdigit() and (len(value) == 7 and value.startswith('7') or labeled
                                      or len(value) > 1 and value.startswith('0'))
        if (structured or numeric or labeled) and not (YEAR.fullmatch(value) and not labeled):
            candidates.append(normalize_code(value))
    return list(dict.fromkeys(candidates))


def code_cell(value: str) -> bool:
    """Called only for a source-declared code column, never a metric cell."""
    return bool(value and TOKEN.fullmatch(value) and any(c.isalnum() for c in value))
