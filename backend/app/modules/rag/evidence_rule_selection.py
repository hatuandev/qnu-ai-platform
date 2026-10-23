"""Offer native list siblings as draft evidence, never as approved dependencies."""

from itertools import groupby

from app.modules.rag.evidence_lists import list_groups
from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference
from app.modules.rag.evidence_validation import bind_quote


def offer_native_list_groups(claims: list[dict], blocks: list[EvidenceBlock]) -> list[dict]:
    """Let the existing independent verifier see a complete bounded native rule.

    Adjacency is only a selection hint. Every offered member still needs relevance,
    scope, entailment and whole-answer checks; it acquires no dependency authority.
    """
    by_id = {block.id: block for block in blocks}
    result = list(claims)
    for run in list_groups(blocks):
        for owner, members in groupby(run, key=_owner):
            group = list(members)
            if owner is None or len(group) < 2:
                continue
            if len({b.fact_context['qnu_block_id'] for b in group}) != len(group):
                continue
            ids = {b.id for b in group}
            selected = [c for c in result if c['references'][0]['block_id'] in ids]
            if not selected:
                continue
            others = [c for c in result if c['references'][0]['block_id'] not in ids]
            # Offer all or none. Never truncate a source clause or exceed the
            # existing proposal contract just to claim that a rule is complete.
            if len(others) + len(group) > 12 or any(not 3 <= len(b.text) <= 4000 for b in group):
                continue
            used = {c['id'] for c in others}
            offered = []
            for block in group:
                prior = next((c for c in selected if c['references'][0]['block_id'] == block.id), None)
                key = prior['id'] if prior else '__native_list_' + block.id
                while key in used:
                    key = '_' + key
                used.add(key)
                ref = bind_quote(QuoteReference(block_id=block.id, quote=block.text), by_id)
                extras = [r for r in prior['references'][1:] if r['block_id'] != block.id] if prior else []
                offered.append({'id': key, 'text': block.text, 'references': [ref, *extras]})
            result = [*others, *offered]
    return result


def _owner(block: EvidenceBlock) -> tuple | None:
    if (not block.parent_id or block.is_container or not block.fact_context.get('qnu_block_id')
            or block.fact_context.get('source_kind') != 'list' or not block.canonical_hash):
        return None
    return (block.binding_id, block.index_revision_id, block.source_revision_id,
            block.canonical_hash, block.parent_id)
