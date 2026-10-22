"""Request-local, source-bound restrictions cannot disappear during answer repair."""
import hashlib
import json

from app.core.exceptions import AppException
from app.modules.rag.evidence_audit import literal_condition_retained
from app.modules.rag.evidence_schemas import QuoteReference
from app.modules.rag.evidence_validation import bind_quote


def _scope(req, plan):
    value = [req.collection_id, req.original_question or req.question, plan.model_dump(mode='json')]
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _identity(reference):
    return tuple(reference.get(key) for key in
        ('binding_id', 'index_revision_id', 'source_revision_id', 'canonical_hash'))


def remember_conditions(req, plan, indexed, _audit, clauses, catalog, blocks):
    """Remember only restrictions already selected by an independent source audit."""
    by_id = {block.id: block for block in blocks}
    references = [QuoteReference(block_id=catalog[check.clause_id.split('.c')[0]].block_id,
        quote=clauses[check.clause_id]) for check in getattr(indexed, 'source_conditions', [])
        if check.required and check.clause_id in clauses]
    # A qualifier's proof may be a whole paragraph with unrelated clauses.
    # Only precise source-side required clauses become persistent restrictions.
    stored = req._source_obligations.setdefault(_scope(req, plan), {})
    for reference in references:
        bound = bind_quote(reference, by_id)
        if bound.get('origin') != 'canonical' or any(
                type(bound.get(key)) is not int or bound[key] < 0 for key in ('start', 'end')):
            raise AppException('Điều kiện cần trích đoạn nguồn gốc có tọa độ xác thực.',
                code='SOURCE_CONDITION_PROVENANCE_INVALID', status_code=503)
        key = (*_identity(bound), bound['block_id'], bound['start'], bound['end'], bound['quote'])
        stored[key] = bound
    if len(stored) > 48:
        raise AppException('Vượt ngân sách đối soát điều kiện nguồn.',
            code='SOURCE_CONDITION_OBLIGATION_BUDGET', status_code=422)


def missing_conditions(req, plan, claims, blocks):
    """A later model verdict may not erase an existing same-scope obligation."""
    stored = req._source_obligations.get(_scope(req, plan), {})
    active_sources = {_identity(ref) for claim in claims for ref in claim['references']}
    by_id = {block.id: block for block in blocks}
    missing, unavailable = [], []
    for reference in stored.values():
        if _identity(reference) not in active_sources:
            continue
        if literal_condition_retained(reference, claims, 'value_constraint', []):
            continue
        quote = QuoteReference(block_id=reference['block_id'], quote=reference['quote'])
        try:
            rebound = bind_quote(quote, by_id)
        except ValueError:
            unavailable.append(reference['block_id'])
            continue
        if any(rebound.get(key) != reference.get(key) for key in
               ('binding_id', 'index_revision_id', 'source_revision_id', 'canonical_hash', 'start', 'end')):
            unavailable.append(reference['block_id'])
        else:
            missing.append(quote)
    req._retrieval_diagnostics.setdefault('source_condition_obligations', []).append({
        'recorded': len(stored), 'missing_block_ids': list(dict.fromkeys(ref.block_id for ref in missing)),
        'unavailable_block_ids': list(dict.fromkeys(unavailable))})
    return missing, unavailable
