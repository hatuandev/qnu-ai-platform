"""Deterministic source selection and sentence envelopes, never semantic approval."""
import re

from app.modules.rag.evidence_schemas import QuoteReference


def canonical_selection_blocks(blocks):
    def identity(block, uid):
        return (block.binding_id, block.index_revision_id, block.source_revision_id,
                block.canonical_hash, uid)
    owners = {}
    for block in blocks:
        if block.origin == 'canonical' and block.unit_id and not block.is_container:
            owners.setdefault(identity(block, block.unit_id), []).append(block)
    # Raw canonical row already includes its headers/context. Exclude only a
    # duplicate derivative with one exact immutable owner; retain legacy facts.
    return [b for b in blocks if b.origin != 'reviewed_fact' or len(owners.get(
        identity(b, b.fact_context.get('source_unit_id')), [])) != 1]


def sentence_envelope(reference: QuoteReference, blocks: dict) -> QuoteReference:
    block = blocks.get(reference.block_id)
    if not block or block.text.count(reference.quote) != 1:
        raise ValueError('Condition must identify one exact source occurrence')
    if block.origin != 'canonical' or block.fact_context.get('source_kind') == 'table':
        return reference
    start = block.text.index(reference.quote)
    end = start + len(reference.quote)
    points = [0, *[m.end() for m in re.finditer(
        r'(?<!\d\.)(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])|\n+(?=\s*(?:\d+|[a-z])[.)]\s)', block.text)], len(block.text)]
    lo = max(p for p in points if p <= start)
    hi = min(p for p in points if p >= end)
    quote = block.text[lo:hi].strip()
    if len(quote) > 4000:
        raise ValueError('Complete condition exceeds bounded source recovery')
    return QuoteReference(block_id=block.id, quote=quote)


def retain_recovered_conditions(claims: list[dict], restored: list[dict]) -> list[dict]:
    """Preserve audited restrictions even when a new model draft omits them.

    Only the same owning block AND canonical coordinates can make a recovered
    restriction redundant. The merged draft still requires a fresh verifier/audit.
    """
    result = list(claims)
    used = {c['id'] for c in result}
    identity = ('binding_id', 'index_revision_id', 'source_revision_id', 'canonical_hash', 'block_id', 'origin')
    for item in restored:
        ref = item['references'][0]
        if any(item['text'] in claim['text'] and any(
                all(own.get(k) == ref.get(k) for k in identity)
                and type(own.get('start')) is int and type(own.get('end')) is int
                and type(ref.get('start')) is int and type(ref.get('end')) is int
                and own['start'] <= ref['start'] <= ref['end'] <= own['end']
                for own in claim['references']) for claim in result):
            continue
        key = item['id']
        while key in used:
            key = '_' + key
        result.append({**item, 'id': key})
        used.add(key)
    return result
