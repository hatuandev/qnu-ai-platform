"""Evidence-bearing document dates, separate from years attached to facts."""

import re
import unicodedata
from datetime import date
from typing import Any

YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_DATE_LINE = re.compile(r"^(?:[^,\n]{1,60},\s*)?ngày\s+(?P<day>\d{1,2}|[. …]+)?\s*tháng\s+(?P<month>\d{1,2}|[. …]+)?\s*năm\s+(?P<year>(?:19|20)\d{2})\s*$", re.IGNORECASE)


def extract_temporal_metadata(markdown: str, filename: str = "") -> dict[str, Any]:
    from app.modules.knowledge.services.source_pages import canonical_pages

    pages = canonical_pages(unicodedata.normalize("NFC", markdown))
    first = pages[0]["markdown_content"] if pages else ""
    candidates, subjects = [], []
    for offset, line in enumerate(first.splitlines()):
        clean = line.strip().strip("*_# ")
        match = _DATE_LINE.fullmatch(clean)
        if match:
            value = None
            try:
                if match["month"] and match["day"]:
                    value = date(int(match["year"]), int(match["month"]), int(match["day"])).isoformat()
            except ValueError:
                if match["day"].isdigit() and match["month"].isdigit():
                    candidates.append({"value": None, "year": None, "status": "invalid",
                                       "evidence": {"page_number": pages[0]["page_number"], "line_number": offset + 1, "raw_text": line}})
                    continue
            candidates.append({"value": value, "year": int(match["year"]),
                               "precision": "day" if value else "year", "status": "verified" if value else "proposed",
                               "evidence": {"page_number": pages[0]["page_number"], "line_number": offset + 1, "raw_text": line},
                               "method": "document_date_line"})
        if line.lstrip().startswith(("#", "**")) and len(clean) < 180:
            subjects.extend({"value": int(year), "evidence": {"page_number": pages[0]["page_number"],
                            "line_number": offset + 1, "raw_text": line}} for year in YEAR.findall(clean))
    complete = [item for item in candidates if item["value"]]
    chosen = complete[0] if len({c["value"] for c in complete}) == 1 else None
    status = "verified" if chosen else "conflict" if len(complete) > 1 else "unknown"
    partial = candidates[0] if len(candidates) == 1 and not chosen else None
    return {"version": "document-time-v1", "issued_date": {"value": chosen["value"] if chosen else None,
            "status": status, "precision": "day" if chosen else None, "evidence": chosen["evidence"] if chosen else None},
            "issued_year": {"value": chosen["year"] if chosen else partial["year"] if partial else None,
                            "status": "verified" if chosen else "proposed" if partial else status, "precision": "year"},
            "subject_years": {"values": sorted({s["value"] for s in subjects}), "status": "proposed", "evidence": subjects},
            "filename_years": {"values": sorted({int(y) for y in YEAR.findall(filename)}), "status": "proposed", "evidence": filename},
            "candidates": candidates}
