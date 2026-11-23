"""Derive reading groups from the pinned document without changing draft content."""

import re
from dataclasses import dataclass
from itertools import groupby

_OUTLINE = re.compile(
    r"^(phần|phụ lục|appendix|chương|chapter|mục|tiểu mục|điều|article)\s+(?:[ivxlcdm]+|\d+)\b",
    re.IGNORECASE,
)
_LEVELS = {
    "phần": 1,
    "phụ lục": 1,
    "appendix": 1,
    "chương": 2,
    "chapter": 2,
    "mục": 3,
    "tiểu mục": 4,
    "điều": 5,
    "article": 5,
}
_ROMAN = re.compile(r"^[IVXLCDM]+[.)]\s+\S")
_NUMBERED = re.compile(r"^\d{1,2}[.)]\s+[^:;.!?]+:?$")
_HEADING_LABELS = {"title", "section-header", "section_header", "paragraph_title", "heading"}


@dataclass(frozen=True, slots=True)
class SourceHeading:
    level: int
    text: str
    citation: str


@dataclass(frozen=True, slots=True)
class SourceSection:
    source: int
    page: int
    heading: str = ""
    citation: str = ""
    path: tuple[SourceHeading, ...] = ()
    sheet: str | None = None
    slide: int | None = None

    def context(self) -> dict:
        result = {}
        if self.path:
            result["heading_path"] = [
                {"level": entry.level, "text": entry.text, "citation": entry.citation}
                for entry in self.path
            ]
        if self.sheet is not None:
            result["source_scope"] = {"kind": "sheet", "name": self.sheet}
        elif self.slide is not None:
            result["source_scope"] = {"kind": "slide", "number": self.slide}
        return result


def _heading(block: dict, path: list[SourceHeading]) -> tuple[str, int] | None:
    if block.get("table") or block.get("type") in {"table", "figure"}:
        return None
    title = block["text"].strip()
    if not title or len(title) > 160 or "\n" in title:
        return None
    locator = block.get("source_locator") or {}
    level = locator.get("level")
    if type(level) is int and 1 <= level <= 9:
        return title, level
    if locator.get("format") == "pptx":
        return None
    marked = (block.get("label") or "").casefold() in _HEADING_LABELS or block.get(
        "type"
    ) in _HEADING_LABELS
    numbered_heading = (
        not locator.get("format")
        and len(title) <= 60
        and _NUMBERED.fullmatch(title)
        and not any(_OUTLINE.match(entry.text) for entry in path)
    )
    outline = _OUTLINE.match(title)
    if outline and (marked or not title.endswith((".", ";", "?", "!"))):
        return title, _LEVELS[outline[1].lower()]
    if (
        marked
        or numbered_heading
        or (_ROMAN.match(title) and not title.endswith((".", ";", "?", "!")))
    ):
        return title, 1
    return None


def source_sections(documents: list[dict]) -> dict[str, SourceSection]:
    sections = {}
    for source, document in enumerate(documents, start=1):
        run = document["ocr_run_id"]
        active = None
        path: list[SourceHeading] = []
        for page in document["pages"]:
            first = next(iter(page["blocks"]), {})
            locator = first.get("source_locator") or {}
            sheet = locator.get("sheet") if locator.get("format") == "xlsx" else None
            slide = locator.get("slide") if locator.get("format") == "pptx" else None
            if locator.get("format") in {"xlsx", "pptx"}:
                active = None
                path.clear()
            fallback = SourceSection(source, page["page_number"], sheet=sheet, slide=slide)
            for block in page["blocks"]:
                ref = f"{run}:{block['evidence_id']}"
                heading = _heading(block, path)
                if heading:
                    title, level = heading
                    while path and path[-1].level >= level:
                        path.pop()
                    path.append(SourceHeading(level, title, ref))
                    active = SourceSection(
                        source, page["page_number"], title, ref, tuple(path), sheet, slide
                    )
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
