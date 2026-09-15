"""Markdown Document Cleaner & Vietnamese Text Normalization."""

from __future__ import annotations

import re

# Regex patterns for cleaning document text
_RE_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_RE_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_RE_PAGE_NUMBERS = re.compile(r"^\s*[-—~]?\s*\d+\s*[-—~]?\s*$", re.MULTILINE)
_RE_HEADING_NORMALIZE = re.compile(
    r"^(điều|khoản|chương|mục|phần)\s+(\d+|[IVXLCDM]+)[\.:]?\s*", re.IGNORECASE | re.MULTILINE
)


def clean_markdown_text(raw_text: str) -> str:
    """Clean and normalize raw extracted markdown/text from documents."""
    if not raw_text:
        return ""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Remove standalone page number lines
    text = _RE_PAGE_NUMBERS.sub("", text)

    # 2. Normalize multiple spaces
    text = _RE_MULTIPLE_SPACES.sub(" ", text)

    # 3. Clean broken markdown tables
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Keep table row structure while trimming internal whitespace
        if stripped.startswith("|") and stripped.endswith("|"):
            parts = [p.strip() for p in stripped.split("|")]
            cleaned_lines.append("| " + " | ".join(parts[1:-1]) + " |")
        else:
            cleaned_lines.append(stripped)

    text = "\n".join(cleaned_lines)

    # 4. Limit consecutive blank lines to at most 2
    text = _RE_MULTIPLE_NEWLINES.sub("\n\n", text)

    return text.strip()


def extract_sections_metadata(text: str) -> list[dict[str, str]]:
    """Identify key legal document sections (Điều, Khoản, Chương) for metadata indexing."""
    sections = []
    for match in _RE_HEADING_NORMALIZE.finditer(text):
        sections.append(
            {
                "type": match.group(1).capitalize(),
                "number": match.group(2),
                "match": match.group(0).strip(),
            }
        )
    return sections
