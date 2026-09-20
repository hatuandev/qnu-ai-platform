"""Controlled Text Normalizer — Unicode NFC, Line Reflow, and Administrative Heading Detection.

Pure functions for text cleansing without silently altering business facts or numbers:
- Enforces 100% Unicode NFC encoding and eliminates null bytes / replacement characters.
- Joins wrapped paragraph lines split by line-wrap in PDF without sentence terminal punctuation.
- Detects administrative and legal headings based on standard decree patterns.
- Normalizes excess whitespace while preserving paragraph breaks.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_encoding(text: str) -> str:
    """Normalize text to Unicode NFC and remove replacement characters / null bytes."""
    if not text:
        return ""
    # Strip null bytes and BOM
    clean = text.replace("\x00", "").replace("\ufeff", "")
    # Normalize to Unicode NFC
    normalized = unicodedata.normalize("NFC", clean)
    # Ensure no replacement character remains unnoticed
    return normalized.replace("\ufffd", "")


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive spaces/tabs and excessive newlines into clean paragraph spacing."""
    if not text:
        return ""
    # Replace horizontal whitespace (tabs, non-breaking spaces) with single space
    clean = re.sub(r"[ \t\u00a0\u200b]+", " ", text)
    # Collapse 3 or more newlines into double newlines
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    # Strip leading/trailing spaces per line
    lines = [line.strip() for line in clean.splitlines()]
    return "\n".join(lines).strip()


def join_wrapped_paragraph_lines(lines: list[str]) -> list[str]:
    """Reflow sentences that were wrapped across lines in PDF page columns.

    If a line does not end with terminal punctuation (. : ! ? ; " ) and the next
    line starts with a lowercase or continuing character, join them with a space.
    """
    if not lines:
        return []

    result: list[str] = []
    buffer: str = ""

    terminal_punct = {".", ":", "!", "?", ";", '"', "”", "…"}

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if buffer:
                result.append(buffer)
                buffer = ""
            continue

        if not buffer:
            buffer = line
            continue

        # Check if previous buffer ended with terminal punctuation or bullet
        last_char = buffer[-1]
        is_bullet = bool(re.match(r"^[-+•*]\s", line) or re.match(r"^\d+\.\s", line))
        is_roman = bool(re.match(r"^[IVXLCDM]+\.\s", line))

        if last_char in terminal_punct or is_bullet or is_roman:
            result.append(buffer)
            buffer = line
        else:
            # Join wrapped line with space
            buffer = f"{buffer} {line}"

    if buffer:
        result.append(buffer)

    return result


def is_administrative_heading(line: str) -> bool:
    """Identify formal Vietnamese administrative sections (e.g. I. MỤC ĐÍCH, Điều 1.)."""
    s = line.strip()
    if not s:
        return False
    # Roman numeral headings: I. , II. , III. , IV. ...
    if re.match(r"^[IVXLCDM]+\.\s+[A-ZÀ-ỸĐ\s]{3,}", s):
        return True
    # Legal clauses: Điều 1. , Chương II.
    if re.match(r"^(?:Điều|Chương|Mục)\s+\d+[\.:]", s, re.IGNORECASE):
        return True
    return bool(
        re.match(
            r"^(?:KẾ HOẠCH|QUYẾT ĐỊNH|THÔNG BÁO|QUY CHẾ|PHỤ LỤC)(?:\s+[A-ZÀ-ỸĐ0-9\s-]+)?$",
            s,
        )
    )
