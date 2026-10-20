"""Literal table coordinates for model context; section position is not row scope."""

import re

from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.rag.evidence_schemas import EvidenceBlock


def model_position(section: str, table_row: dict) -> dict:
    """Retain location verbatim without projecting a table's position as its subject."""
    return ({'document_position': {'section': section, 'role': 'location_only'}} if table_row
            else {'section': section})


def table_row_context(block: EvidenceBlock) -> dict:
    """Expose original headers/cells together without assigning semantic roles."""
    if block.fact_context.get('source_kind') != 'table' or block.is_container:
        return {}
    lines = [line.strip() for line in block.header_context.splitlines() if line.lstrip().startswith('|')]
    if len(lines) != 2 or not re.fullmatch(r'[| :\-]+', lines[1]):
        return {}
    if not block.text.lstrip().startswith('|') or len(block.text.strip().splitlines()) != 1:
        return {}
    headers, cells = _split_gfm_row(lines[0]), _split_gfm_row(block.text)
    if not headers or len(headers) != len(cells):
        return {}
    return {'headers': headers, 'cells': cells, 'section_role': 'document_position',
            'scope_authority': 'explicit_row_and_applicable_source_rules'}
