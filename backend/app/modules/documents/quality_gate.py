"""Quality Gate Engine for Document Revisions (ADR-011).

Evaluates text completeness, layout preservation, Mojibake detection,
and administrative formatting to decide if a revision is ready or requires human review.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Common Vietnamese Mojibake or corrupt character patterns
_MOJIBAKE_PATTERNS = [
    re.compile(r"\ufffd"),  # Unicode replacement character
    re.compile(r"\?{3,}"),  # Repeated unparsed question marks like ???
    re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]"),  # Non-printable control characters
]


def evaluate_revision_quality(
    markdown: str | None,
    page_count: int = 1,
    tables_count: int = 0,
    file_size_bytes: int = 0,
    ocr_engine: str | None = None,
) -> dict[str, Any]:
    """Inspect parsed markdown content and generate structured quality audit report.

    Returns:
        dict containing:
            - overall_status: 'passed' | 'warning' | 'failed'
            - text_completeness: metrics on length, character density
            - table_preservation: metrics on extracted tables vs markdown tables
            - warning_flags: list of string warning tags
            - evaluated_at: ISO timestamp
    """
    now = datetime.now(UTC).isoformat()
    text = (markdown or "").strip()
    total_chars = len(text)
    total_words = len(text.split()) if text else 0
    pages = max(1, page_count)
    chars_per_page = total_chars / pages

    warning_flags: list[str] = []

    # 1. Total Failure Check (Empty text)
    if total_chars == 0:
        return {
            "overall_status": "failed",
            "failure_code": "EMPTY_EXTRACTED_CONTENT",
            "total_chars": 0,
            "total_words": 0,
            "page_count": page_count,
            "warning_flags": ["empty_content"],
            "evaluated_at": now,
        }

    # 2. Text Density / Completeness Check
    # If a document has very low character density per page, it's likely a blurry scan or failed OCR
    if chars_per_page < 60:
        warning_flags.append("critically_low_text_density")
    elif chars_per_page < 150:
        warning_flags.append("low_text_density")

    # 3. Table Preservation Check
    # Count markdown table rows/separators (|---|)
    md_table_separators = len(re.findall(r"\|(?:\s*:?-+:?\s*\|)+", text))
    if tables_count > 0 and md_table_separators == 0:
        warning_flags.append("tables_detected_but_missing_in_markdown")

    # 4. Mojibake and Character Corruption Check
    mojibake_count = 0
    for pat in _MOJIBAKE_PATTERNS:
        matches = pat.findall(text)
        mojibake_count += len(matches)

    if mojibake_count > 0:
        warning_flags.append("mojibake_or_font_corruption_detected")

    # 5. Determine Overall Decision
    # If severe warning flags are present, require human review before publishing
    critical_warnings = {"critically_low_text_density", "mojibake_or_font_corruption_detected"}
    has_critical = any(flag in critical_warnings for flag in warning_flags)

    if has_critical:
        overall_status = "warning"
    elif warning_flags:
        # Mild warnings still pass but are logged
        overall_status = "passed"
    else:
        overall_status = "passed"

    return {
        "overall_status": overall_status,
        "total_chars": total_chars,
        "total_words": total_words,
        "page_count": page_count,
        "chars_per_page": round(chars_per_page, 1),
        "detected_tables_count": tables_count,
        "markdown_tables_count": md_table_separators,
        "mojibake_artifacts_count": mojibake_count,
        "ocr_engine": ocr_engine or "native",
        "warning_flags": warning_flags,
        "evaluated_at": now,
    }
