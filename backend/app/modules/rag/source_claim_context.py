"""Bounded, immutable attribution proofs; adding context never establishes applicability."""

import re
from collections import defaultdict

from app.modules.knowledge.entity_codes import code_candidates, code_in_question, normalize_code
from app.modules.rag.evidence_dependencies import source_identity
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.source_row_context import table_row_context


def _owner_headings(body: EvidenceBlock, blocks: list[EvidenceBlock]) -> list[EvidenceBlock]:
    units = defaultdict(list)
    for block in blocks:
        if block.unit_id and source_identity(block) == source_identity(body):
            units[block.unit_id].append(block)
    result, seen, parent = [], {body.unit_id}, body.parent_id
    while parent:
        if parent in seen or len(units[parent]) != 1:
            return []  # Never infer ancestry from equal labels, missing units or a cycle.
        seen.add(parent)
        owner = units[parent][0]
        if owner.fact_context.get('source_kind') == 'heading' and len(owner.text) <= 4000:
            result.append(owner)
        parent = owner.parent_id
    return result


def _addressed_identity_rows(body: EvidenceBlock, blocks: list[EvidenceBlock], question: str) -> list[EvidenceBlock]:
    candidates, explicit = defaultdict(list), set(code_candidates(question))
    for block in blocks:
        if block.origin != 'canonical' or source_identity(block) != source_identity(body) or len(block.text) > 4000:
            continue
        context = table_row_context(block)
        for value in dict.fromkeys(cell.strip() for cell in context.get('cells', [])):
            # Source-defined alphabetic rule codes are valid too; never match
            # arbitrary words or numeric quantities merely appearing in a question.
            structured = re.fullmatch(r'(?=.*[^\W\d_])\w+(?:[-_/.]\w+)+', value)
            if (normalize_code(value) in explicit or structured) and code_in_question(value, question):
                candidates[normalize_code(value)].append(block)
    return [rows[0] for rows in candidates.values() if len(rows) == 1]


def supporting_scope_blocks(body: EvidenceBlock, blocks: list[EvidenceBlock], question: str) -> list[EvidenceBlock]:
    """Use only already supplied source evidence; no retrieval, role inference or source mutation."""
    if (body.origin != 'canonical' or body.is_container or body.fact_context.get('source_kind') == 'table'
            or not all(source_identity(body))):
        return []
    return list({b.id: b for b in [*_addressed_identity_rows(body, blocks, question),
                                  *_owner_headings(body, blocks)]}.values())
