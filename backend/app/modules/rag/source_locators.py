"""Structural source locators are retrieval hints, never inferred applicability."""

import re

from app.modules.knowledge.entity_codes import code_candidates, code_in_question
from app.modules.rag.evidence_dependencies import source_identity
from app.modules.rag.evidence_schemas import EvidenceBlock

TABLE_LABEL = re.compile(r"\b(?:bảng|table)\s+(\d+(?:\.\d+)*|[IVXLCDM]+)\b", re.IGNORECASE)
SECTION_LABEL = re.compile(r"\b(phụ lục|appendix|điều|article|mục|section)\s+(\d+(?:\.\d+)*|[IVXLCDM]+)\b", re.IGNORECASE)


def addressed_prose(blocks: list[EvidenceBlock], question: str) -> list[EvidenceBlock]:
    """An explicitly named note/document code is an anchor too, not just a row code."""
    codes = code_candidates(question)
    matches = [(max((len(code) for code in codes if code_in_question(code, b.text)), default=0), b)
               for b in blocks if not b.is_container and b.origin == 'canonical'
               and b.fact_context.get('source_kind') not in {'heading', 'table', 'image'}]
    return [b for score, b in sorted(matches, key=lambda pair: pair[0], reverse=True) if score][:1]


def table_captions(blocks: list[EvidenceBlock], table_id: str) -> list[EvidenceBlock]:
    headers = [b for b in blocks if b.unit_id == f'{table_id}:header']
    if len(headers) != 1:
        return []
    header = headers[0]
    preceding = [b for b in blocks if source_identity(b) == source_identity(header)
                 and not b.is_container and b.end <= header.start]
    caption = max(preceding, key=lambda b: b.end, default=None)
    if caption and TABLE_LABEL.match(caption.text.strip()):
        return [caption]
    return []


def table_matches(blocks: list[EvidenceBlock], table_id: str, question: str) -> bool:
    wanted = {m[1].casefold() for m in TABLE_LABEL.finditer(question)}
    if not wanted:
        return True
    captions = table_captions(blocks, table_id)
    found = {m[1].casefold() for b in captions for m in TABLE_LABEL.finditer(b.text)}
    return bool(wanted.intersection(found))


def referenced_sections(blocks: list[EvidenceBlock], question: str) -> list[EvidenceBlock]:
    """Read direct children of an explicitly addressed section, within one source."""
    wanted = {(m[1].casefold(), m[2].casefold()) for m in SECTION_LABEL.finditer(question)}
    bare = {m[2] for m in SECTION_LABEL.finditer(question) if m[1].casefold() in {'mục', 'section'}}
    headings = []
    for block in blocks:
        if block.fact_context.get('source_kind') != 'heading':
            continue
        text = block.text.lstrip('# ').strip()
        label = SECTION_LABEL.match(text)
        number = re.match(r'(\d+(?:\.\d+)*)[.\s]', text)
        if label and (label[1].casefold(), label[2].casefold()) in wanted or number and number[1] in bare:
            headings.append(block)
    result = {}
    for parent in headings:
        if not parent.unit_id:
            continue
        descendants = {parent.unit_id}
        same = [b for b in blocks if source_identity(b) == source_identity(parent)]
        while True:
            expanded = descendants | {b.unit_id for b in same if b.parent_id in descendants and b.unit_id}
            if expanded == descendants:
                break
            descendants = expanded
        for child in same:
            if (child.parent_id in descendants and not child.is_container
                    and child.fact_context.get('source_kind') not in {'heading', 'table', 'image'}):
                result[child.id] = child
    return list(result.values())
