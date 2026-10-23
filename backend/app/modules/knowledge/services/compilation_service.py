"""Authenticated draft compilation lifecycle. Human review never publishes or mutates source facts."""
import asyncio
import logging
import uuid
from copy import deepcopy
from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import COMPILER, POLICY, CompilerPolicy
from app.modules.knowledge.services.compilation_catalog import invalid, load_sources, require
from app.modules.knowledge.services.compilation_engine import compile_topic
from app.modules.knowledge.services.compilation_modelops import (
    configuration_hash,
    generator,
    resolve_route,
)
from app.modules.knowledge.services.compilation_store import (
    append_event,
    assign,
    audit_events,
    available_packets,
    check_lineage,
    now,
    read_object,
    registry,
    save_object,
)
from app.modules.knowledge.services.compilation_validation import validate_result
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.knowledge.services.wiki_compiler import digest

logger = logging.getLogger(__name__)


def clean_transaction(db) -> None:
    if db.new or db.dirty or db.deleted:
        raise invalid('caller_transaction_has_writes')


async def preview(db, collection_id: str, ids: list[str], actor) -> dict:
    require(actor, 'ai.knowledge.upload')
    _, sources, catalog, fingerprint = await load_sources(db, collection_id, ids, actor)
    return {'source_set_hash': fingerprint, 'sources': [source.id for source in sources],
        'evidence_units': len(catalog), 'compiler': COMPILER, 'policy_version': POLICY,
        'usage': 'review_only', 'publication': 'unpublished'}


async def reserve(db, collection_id: str, request, actor, config: str) -> tuple:
    collection, sources, _, fingerprint = await load_sources(db, collection_id, request.source_revision_ids, actor, lock=True)
    if fingerprint != request.expected_source_set_hash:
        raise invalid('stale_source_set')
    state = registry(collection)
    token = digest([actor.actor_id, actor.username, request.idempotency_key])
    signature = digest({**request.model_dump(exclude={'idempotency_key'}), 'config': config})
    if token in state['requests']:
        old = state['jobs'][state['requests'][token]]
        if old['request_hash'] != signature:
            raise invalid('idempotency_conflict')
        await db.rollback()
        return deepcopy(old), None, None
    if len(state['requests']) >= 4000:
        raise invalid('request_ledger_capacity', 422)
    if len(state['jobs']) >= 1000:
        raise invalid('registry_capacity', 422)
    # Only one request may own inference for the same exact build, even with a new key.
    for old in state['jobs'].values():
        if old['request_hash'] == signature and old['status'] == 'running':
            state['requests'][token] = old['id']
            assign(collection, state)
            await db.commit()
            return deepcopy(old), None, None
    record = {'id': 'kc_' + uuid.uuid4().hex, 'request_hash': signature, 'status': 'running',
        'version': 1, 'created_at': now(), 'topic': request.topic,
        'source_revision_ids': sorted(request.source_revision_ids), 'source_set_hash': fingerprint,
        'configuration_hash': config, 'events': [], 'action_receipts': {}}
    await append_event(collection_id, record, {'type': 'compilation_requested', 'actor_id': actor.actor_id,
        'request_hash': signature, 'source_set_hash': fingerprint})
    state['jobs'][record['id']] = record
    state['requests'][token] = record['id']
    assign(collection, state)
    await db.commit()  # Durable intent precedes inference; only this collection is dirty.
    return deepcopy(record), sources, (collection.tenant_id, state)


async def finish(db, collection_id: str, record: dict, bundle: dict, actor) -> dict:
    collection, sources, _, fingerprint = await load_sources(db, collection_id, record['source_revision_ids'], actor, lock=True)
    if fingerprint != record['source_set_hash']:
        raise invalid('source_changed_during_build')
    state = registry(collection)
    current = state['jobs'][record['id']]
    if current['version'] != 1 or current['status'] != 'running':
        raise invalid('build_ownership_lost')
    await asyncio.to_thread(validate_result, bundle, sources, collection_id, actor)
    check_lineage(state, bundle.get('reused_job_ids', []))
    reference = await save_object(collection_id, bundle)
    for packet in [*bundle['packet_results'], *bundle['topic_results']]:
        if packet.get('kind') == 'topic' or packet['review']['complete']:
            state['packets'][packet['key']] = {'job_id': record['id'], 'reference': await save_object(collection_id, packet)}
    current.update(status='ready_for_review' if bundle['machine_complete'] else 'needs_attention',
        artifact=reference, proposal_hash=bundle['binding']['proposal_hash'], version=2,
        reused_job_ids=bundle.get('reused_job_ids', []))
    await append_event(collection_id, current, {'type': 'automated_verification', 'policy_version': POLICY,
        'machine_complete': bundle['machine_complete'], 'artifact_sha256': reference['sha256'],
        'proposal_hash': current['proposal_hash']})
    assign(collection, state)
    await db.commit()
    return deepcopy(current)


async def fail(db, collection_id: str, job_id: str, actor, code: str, metrics: list | None = None) -> None:
    await db.rollback()
    collection = await get_scoped_collection(db, collection_id, actor=actor, for_update=True)
    state = registry(collection)
    current = state['jobs'][job_id]
    if current['status'] == 'running':
        current.update(status='uncertain', failure_code=code, version=current['version'] + 1)
        await append_event(collection_id, current, {'type': 'execution_incomplete', 'code': code,
            'automatic_retry': False, 'model_calls': metrics or []})
        assign(collection, state)
        await db.commit()


async def create(db, collection_id: str, request, actor) -> dict:
    require(actor, 'ai.knowledge.upload')
    require(actor, 'ai.knowledge.view')
    clean_transaction(db)
    route = await resolve_route(db)
    config = configuration_hash(route, CompilerPolicy().model_dump())
    record, sources, context = await reserve(db, collection_id, request, actor, config)
    if sources is None:
        return public_record(record)
    metrics = []
    try:
        tenant_id, state = context
        cached = await available_packets(collection_id, state)
        bundle = await compile_topic(sources, collection_id, request.topic, actor,
            generator(route, tenant_id, metrics), config, cached,
            read_cache=lambda reference: read_object(collection_id, reference))
        bundle['reused_job_ids'] = sorted({state['packets'][p['key']]['job_id']
            for p in [*bundle['packet_results'], *bundle['topic_results']] if p['key'] in cached})
        bundle['model_calls'] = metrics
        bundle['sha256'] = digest({k: v for k, v in bundle.items() if k != 'sha256'})
        if configuration_hash(await resolve_route(db), CompilerPolicy().model_dump()) != config:
            raise invalid('model_configuration_changed_during_build')
        return public_record(await finish(db, collection_id, record, bundle, actor))
    except (Exception, asyncio.CancelledError) as exc:
        code = getattr(exc, 'code', 'KNOWLEDGE_COMPILATION_CANCELLED' if isinstance(exc, asyncio.CancelledError)
                       else 'KNOWLEDGE_COMPILATION_FAILED')
        try:
            await asyncio.shield(fail(db, collection_id, record['id'], actor, code, metrics))
        except Exception:
            logger.error('compilation_receipt_unconfirmed job=%s code=%s', record['id'], code)
        if isinstance(exc, (AppException, asyncio.CancelledError)):
            raise
        raise AppException('Biên soạn chưa hoàn tất; xem biên nhận, không gửi lại tự động.',
            code='KNOWLEDGE_COMPILATION_FAILED', status_code=502) from exc


def public_record(record: dict) -> dict:
    status = record['status']
    age = (datetime.now(UTC) - datetime.fromisoformat(record['created_at'])).total_seconds()
    if status == 'running' and age > CompilerPolicy().timeout_seconds + 30:
        status = 'uncertain'
    return ({key: record[key] for key in ('id', 'version', 'topic', 'source_revision_ids', 'source_set_hash')}
        | {'status': status, 'proposal_hash': record.get('proposal_hash'), 'failure_code': record.get('failure_code'),
           'usage': 'review_only', 'publication': 'unpublished'})


async def list_compilations(db, collection_id: str, actor) -> dict:
    require(actor, 'ai.knowledge.review')
    require(actor, 'ai.knowledge.view')
    collection = await get_scoped_collection(db, collection_id, actor=actor)
    if not collection.is_active:
        raise invalid('collection_inactive')
    return {'items': [public_record(row) for row in registry(collection)['jobs'].values()],
            'snapshot_status': 'not_checked', 'usage': 'review_only'}


async def read(db, collection_id: str, job_id: str, actor) -> dict:
    require(actor, 'ai.knowledge.review')
    require(actor, 'ai.knowledge.view')
    collection = await get_scoped_collection(db, collection_id, actor=actor)
    state = registry(collection)
    record = state['jobs'].get(job_id)
    if not record:
        raise invalid('job_not_found', 404)
    result = public_record(record)
    try:
        check_lineage(state, record.get('reused_job_ids', []))
        _, sources, _, fingerprint = await load_sources(db, collection_id, record['source_revision_ids'], actor)
        if fingerprint != record['source_set_hash']:
            raise invalid('stale_source_set')
    except AppException as exc:
        if exc.status_code != 409:
            raise
        return {**result, 'status': 'stale', 'bundle': None, 'stale_reason': exc.details.get('reason')}
    events = await audit_events(collection_id, record)
    bundle = await read_object(collection_id, record['artifact']) if record.get('artifact') else None
    if bundle:
        await asyncio.to_thread(validate_result, bundle, sources, collection_id)
        if bundle['binding']['proposal_hash'] != record['proposal_hash']:
            raise invalid('stored_proposal_hash')
        _, _, _, fresh = await load_sources(db, collection_id, record['source_revision_ids'], actor)
        if fresh != fingerprint:
            return {**result, 'status': 'stale', 'bundle': None, 'stale_reason': 'changed_during_read'}
    return {**result, 'bundle': bundle, 'audit': events}


async def decide(db, collection_id: str, job_id: str, request, actor) -> dict:
    require(actor, 'ai.knowledge.review')
    require(actor, 'ai.knowledge.view')
    clean_transaction(db)
    collection = await get_scoped_collection(db, collection_id, actor=actor, for_update=True)
    state = registry(collection)
    record = state['jobs'].get(job_id)
    if not record:
        raise invalid('job_not_found', 404)
    token = digest([actor.actor_id, actor.username, request.idempotency_key])
    signature = digest(request.model_dump(exclude={'idempotency_key'}))
    old = record['action_receipts'].get(token)
    if old:
        if old['signature'] != signature:
            raise invalid('idempotency_conflict')
        return old['response']
    if request.expected_version != record['version'] or request.expected_proposal_hash != record.get('proposal_hash'):
        raise invalid('stale_review_version')
    if request.decision == 'revoked':
        if record['status'] in {'running', 'uncertain', 'revoked'} or not record.get('artifact'):
            raise invalid('review_not_current')
        await audit_events(collection_id, record)
        await read_object(collection_id, record['artifact'])
    else:
        # Keep the exact source/binding rows locked through the human decision commit.
        _, _, _, fingerprint = await load_sources(db, collection_id, record['source_revision_ids'], actor, lock=True)
        if fingerprint != record['source_set_hash']:
            raise invalid('stale_source_set')
        current = await read(db, collection_id, job_id, actor)
        if current['status'] in {'stale', 'running', 'uncertain', 'revoked'} or current['bundle'] is None:
            raise invalid('review_not_current')
        if request.decision == 'approved' and not current['bundle']['machine_complete']:
            raise invalid('unresolved_evidence')
        if request.decision == 'approved' and current['bundle']['policy_version'] != POLICY:
            raise invalid('review_policy_requires_new_build')
    record['status'] = {'approved': 'reviewed', 'rejected': 'rejected', 'revoked': 'revoked'}[request.decision]
    record['version'] += 1
    await append_event(collection_id, record, {'type': 'user_decision', 'actor_id': actor.actor_id,
        'decision': request.decision, 'comment': request.comment, 'proposal_hash': record['proposal_hash'],
        'policy_version': POLICY, 'publication_granted': False})
    response = public_record(record)
    record['action_receipts'][token] = {'signature': signature, 'response': response}
    assign(collection, state)
    await db.commit()
    return response
