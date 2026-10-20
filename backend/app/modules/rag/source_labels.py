"""Literal row and caption anchors; these select evidence, never establish facts."""

import re

from app.modules.knowledge.entity_codes import code_candidates
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.table_context import clean_cell, row_identities
from app.modules.rag.evidence_dependencies import source_identity
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.query_constraints import source_name_in_question


def row_identity(cells: list[str], table: dict, question: str) -> tuple[int, int, str, str | None] | None:
    identities = row_identities(cells, table)
    if len(identities) != 1:
        return None
    if code_candidates(question):
        return identities[0]
    # A first-column multiword label literally requested by the user can name a
    # measure itself; a later condition cell must not replace it as the entity.
    label = clean_cell(cells[0])
    if (len(label.split()) >= 2 and any(c.isalpha() for c in label)
            and source_name_in_question(label, question)):
        return 0, len(cells), label, identities[0][3]
    return identities[0]


def supplemental_context(blocks: list[EvidenceBlock], question: str, *, allow_tables: bool) -> list[EvidenceBlock]:
    """Exact row labels and immediate caption bodies within one immutable section."""
    selected = {}
    ordered = sorted(blocks, key=lambda b: (source_identity(b), b.start, b.end))
    for index, block in enumerate(ordered):
        if block.is_container or block.origin != 'canonical':
            continue
        kind = block.fact_context.get('source_kind')
        if (allow_tables and kind == 'table' and block.text != block.header_context
                and not block.fact_context.get('unresolved_cell_columns')
                and block.unit_id != f'{block.parent_id}:header'):
            cells = _split_gfm_row(block.text)
            if cells and len(cells[0].strip()) >= 3 and source_name_in_question(clean_cell(cells[0]), question):
                selected[block.id] = block
        formula = re.match(r'^\s*([^\W\d_]\w*)\s*=\s*[^\n]+[+×*/^][^\n]+$', block.text)
        if formula and source_name_in_question(formula[1], question):
            selected[block.id] = block
            for sibling in ordered[index + 1:index + 2]:
                if (source_identity(sibling) == source_identity(block) and sibling.parent_id == block.parent_id
                        and sibling.fact_context.get('source_kind') == 'paragraph' and not sibling.is_container):
                    selected[sibling.id] = sibling
        caption = re.match(r'^\s*((?:Hình|Figure|Sơ đồ|Biểu đồ)\s+\d+(?:\.\d+)*)[.:]', block.text, re.IGNORECASE)
        if not caption or not source_name_in_question(caption[1], question):
            continue
        for sibling in ordered[index + 1:index + 2]:
            if (source_identity(sibling) == source_identity(block) and sibling.parent_id == block.parent_id
                    and sibling.fact_context.get('source_kind') in {'paragraph', 'list', 'code'}
                    and not sibling.is_container):
                selected[sibling.id] = sibling
    return list(selected.values())
