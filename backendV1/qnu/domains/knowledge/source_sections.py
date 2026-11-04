"""Derive reading groups from the pinned document without changing draft content."""

import re
from dataclasses import dataclass
from itertools import groupby

_OUTLINE = re.compile(
    r"^(?:[IVXLCDM]+[.)]\s+\S|(?i:chương|phần|phụ lục|điều|chapter|appendix)\s+[IVXLCDMivxlcdm\d]+\b)"
)
_NUMBERED = re.compile(r"^\d{1,2}[.)]\s+[^:;.!?]+:?$")
_HEADING_LABELS = {"title", "section-header", "section_header", "paragraph_title", "heading"}


@dataclass(frozen=True, slots=True)
class SourceSection:
    source: int
    page: int
    heading: str = ""
    citation: str = ""


def _heading(block: dict) -> str:
    if block.get("table") or block.get("type") in {"table", "figure"}:
        return ""
    title = block["text"].strip()
    if not title or len(title) > 160 or "\n" in title:
        return ""
    if (
        (block.get("label") or "").casefold() in _HEADING_LABELS
        or block.get("type") in _HEADING_LABELS
        or (_OUTLINE.match(title) and not title.endswith((".", ";", "?", "!")))
        or (len(title) <= 60 and _NUMBERED.fullmatch(title))
    ):
        return title
    return ""


def source_sections(documents: list[dict]) -> dict[str, SourceSection]:
    sections = {}
    for source, document in enumerate(documents, start=1):
        run = document["ocr_run_id"]
        active = None
        for page in document["pages"]:
            fallback = SourceSection(source, page["page_number"])
            for block in page["blocks"]:
                ref = f"{run}:{block['evidence_id']}"
                heading = _heading(block)
                if heading:
                    active = SourceSection(source, page["page_number"], heading, ref)
                section = active or fallback
                sections[ref] = section
                for row in (block.get("table") or {}).get("rows", []):
                    for cell in row:
                        sections[f"{run}:{cell['evidence_id']}"] = section
    return sections


def shared_section(refs: list[str], sections: dict[str, SourceSection]) -> SourceSection | None:
    matches = {sections.get(ref) for ref in refs}
    return matches.pop() if len(matches) == 1 else None


def reading_groups(content: dict, documents: list[dict]) -> list[dict]:
    sections = source_sections(documents)
    entries = []
    for section_no, section in enumerate(content["sections"]):
        for paragraph_no, paragraph in enumerate(section["paragraphs"]):
            source = shared_section(paragraph["citations"], sections)
            if source is None or section["heading"] == "Giới hạn dữ liệu trích xuất":
                key = section_no
                heading = section["heading"]
            else:
                key = source
                heading = source.heading or f"Trang {source.page}"
                if len(documents) > 1:
                    heading = f"Nguồn {source.source} · {heading}"
            entries.append(((key, heading), (section_no, paragraph_no)))
    return [
        {"heading": heading, "paragraphs": [position for _, position in group]}
        for (_, heading), group in groupby(entries, key=lambda entry: entry[0])
    ]
