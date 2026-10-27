"""Pure proposal boundary; does not persist, verify semantics, index or publish."""
from app.core.exceptions import AppException
from app.modules.knowledge.compilation_schemas import proposal_contract
from app.modules.knowledge.services.wiki_compiler import digest, source_identity, source_units
from app.modules.rag.evidence_validation import YEAR


def invalid(reason):
    return AppException('Đề xuất biên soạn chưa khớp bằng chứng nguồn.',
        code='KNOWLEDGE_COMPILATION_INVALID', status_code=422, details={'reason': reason})


def evidence_catalog(sources: list, collection_id: str) -> dict:
    """Caller supplies server-authorized source revisions, never model URLs/IDs.

    Draft sources are allowed in a draft compilation; none become serving sources.
    Publication authorization remains owned by the existing publication service.
    """
    catalog = {}
    identities = set()
    for source in sources:
        if getattr(source, 'collection_id', None) != collection_id:
            raise invalid('source_collection')
        identity = source_identity(source, collection_id)
        key = source.binding_id, source.id
        if key in identities:
            raise invalid('duplicate_source_revision')
        identities.add(key)
        for unit in source_units(source):
            if unit.is_container:
                continue
            ref = {**identity, 'unit_id': unit.id, 'start': unit.start, 'end': unit.end,
                'quote': unit.text, 'source_locations': unit.source_locations}
            catalog['proof_' + digest(ref)[:24]] = ref
    return catalog


def bind_draft(payload: dict, sources: list, collection_id: str, actor) -> dict:
    if not actor or not actor.authenticated or not actor.has_permission('ai.knowledge.upload'):
        raise AppException('Bạn không có quyền biên soạn tài liệu.', code='forbidden', status_code=403)
    return _bind_draft(payload, sources, collection_id)


def _bind_draft(payload: dict, sources: list, collection_id: str) -> dict:
    """Internal integrity validation only; callers separately authorize reads/writes."""
    draft = proposal_contract(payload).model_validate(payload)
    catalog = evidence_catalog(sources, collection_id)
    snapshot_hash = digest(catalog)
    if draft.snapshot_hash != snapshot_hash:
        raise invalid('stale_snapshot')
    entities = {item.id: item for item in draft.entities}
    assertions = {item.id: item for item in draft.assertions}
    ids = [item.id for item in [*draft.entities, *draft.assertions, *draft.relations]]
    if len(ids) != len(set(ids)):
        raise invalid('duplicate_object_id')
    def require_proof(refs):
        if len(refs) != len(set(refs)) or any(ref not in catalog for ref in refs):
            raise invalid('missing_or_duplicate_evidence')
    for entity in draft.entities:
        require_proof(entity.evidence_ids)
    for item in [*draft.assertions, *draft.relations]:
        require_proof(item.evidence_ids)
        require_proof(item.condition_ids)
        require_proof(item.exception_ids)
        for scope in item.scope:
            require_proof(scope.evidence_ids)
            if not set(scope.evidence_ids).issubset(item.evidence_ids):
                raise invalid('scope_evidence_outside_item')
        for temporal in item.temporal:
            require_proof(temporal.evidence_ids)
            if not set(temporal.evidence_ids).issubset(item.evidence_ids):
                raise invalid('temporal_evidence_outside_item')
            literal = {int(y) for ref in temporal.evidence_ids for y in YEAR.findall(catalog[ref]['quote'])}
            if not set(temporal.years).issubset(literal):
                raise invalid('year_without_literal_proof')
    for item in draft.assertions:
        if item.entity_id not in entities:
            raise invalid('unknown_entity')
        own = {(catalog[ref]['binding_id'], catalog[ref]['source_revision_id']) for ref in item.evidence_ids}
        if len(own) != 1 or any((catalog[ref]['binding_id'], catalog[ref]['source_revision_id']) not in own
                               for ref in [*item.condition_ids, *item.exception_ids]):
            raise invalid('assertion_crosses_sources')
    for relation in draft.relations:
        if relation.source_id not in {*entities, *assertions} or relation.target_id not in {*entities, *assertions}:
            raise invalid('unknown_relation_endpoint')
    for section in draft.sections:
        if any(key not in assertions for key in section.assertion_ids):
            raise invalid('unknown_section_assertion')
    from app.modules.knowledge.services.compilation_manifest import validate_groups

    validate_groups(draft.model_dump(mode='json'), catalog)
    # This receipt certifies binding only. Independent entailment, role, condition
    # completeness and any necessary human decision still precede effective use.
    result = {'version': draft.version, 'state': 'evidence_bound', 'usage': 'review_only',
        'collection_id': collection_id, 'snapshot_hash': snapshot_hash,
        'proposal_hash': digest(draft.model_dump(mode='json')), 'proposal': draft.model_dump(mode='json'),
        'evidence': catalog, 'semantic_verification': 'not_run', 'publication': 'unpublished'}
    return {**result, 'sha256': digest(result)}
