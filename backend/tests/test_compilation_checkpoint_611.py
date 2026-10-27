"""Resumable bounded inference, independent reviews, and exact model settings."""
import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import CompilationRequest, CompilerPolicy
from app.modules.knowledge.services.compilation_engine import compile_topic
from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from tests.test_compilation_engine_603 import ACTOR, Model, sample


class MemoryStages:
    def __init__(self):
        self.values = {}
        self.total_calls = 0

    async def lookup(self, key):
        return deepcopy(self.values.get(key))

    async def start(self, key, identity):
        assert key not in self.values
        self.values[key] = {'status': 'started', 'identity': identity}
        self.total_calls += 1

    async def complete(self, key, value):
        self.values[key].update(status='completed', value=deepcopy(value))

    async def reject(self, key, exc):
        self.values[key].update(status='rejected' if exc.code == 'KNOWLEDGE_WIKI_INVALID' else 'uncertain',
                                error={'code': exc.code, 'details': exc.details})


def test_medium_is_an_explicit_request_field_and_reaches_payload_without_numeric_guessing():
    req = LLMGenerateRequest(messages=[ChatMessage(role='user', content='Synthetic')],
                             max_tokens=8192, thinking_budget=0, reasoning_effort='medium')
    adapter = OpenAIAdapter('fixture-model', api_key='fixture')
    payload = adapter._payload(req.messages, 0, req.max_tokens, False, reasoning_effort=req.reasoning_effort)
    assert payload['reasoning_effort'] == 'medium' and payload['max_tokens'] == 8192


@pytest.mark.asyncio
async def test_checkpoint_resume_preserves_complete_bundle_without_repeating_completed_calls():
    stages, model, sources = MemoryStages(), Model(), [sample(1), sample(2, 2026, True)]
    policy = CompilerPolicy(max_calls=4, max_total_calls=32)
    with pytest.raises(AppException) as paused:
        await compile_topic(sources, 'c603', 'Chỉ tiêu', ACTOR, model, '611', policy=policy, checkpoints=stages)
    assert paused.value.code == 'KNOWLEDGE_COMPILATION_PAUSED'
    assert len(model.calls) == 4 and all(p['status'] == 'completed' for p in stages.values.values())
    while True:
        try:
            bundle = await compile_topic(sources, 'c603', 'Chỉ tiêu', ACTOR, model, '611',
                                         policy=policy, checkpoints=stages)
            break
        except AppException as exc:
            assert exc.code == 'KNOWLEDGE_COMPILATION_PAUSED' and len(model.calls) < 32
    assert bundle['machine_complete'] and len(model.calls) == 10
    assert model.calls.count('TopicSelection') == 4
    assert bundle['publication'] == 'unpublished'


@pytest.mark.asyncio
async def test_uncertain_stage_is_never_sent_again_on_resume():
    stages = MemoryStages()
    failed = AsyncMock(side_effect=AppException('timeout', code='PROVIDER_TIMEOUT', status_code=504))
    for _ in range(2):
        with pytest.raises(AppException):
            await compile_topic([sample(1)], 'c603', 'Chỉ tiêu', ACTOR, failed, '611', checkpoints=stages)
    assert failed.await_count == 1


def test_resume_requires_version_and_rejects_legacy_unknown_client_policy():
    body = {'topic': 'Chỉ tiêu', 'source_revision_ids': ['s1'], 'expected_source_set_hash': 'a' * 64,
            'idempotency_key': 'fixture-key-611', 'resume_from_job_id': 'kc_fixture'}
    with pytest.raises(ValueError):
        CompilationRequest.model_validate(body)
    parsed = CompilationRequest.model_validate({**body, 'expected_resume_version': 2})
    assert parsed.resume_from_job_id == 'kc_fixture'
    with pytest.raises(ValueError):
        CompilationRequest.model_validate({**body, 'expected_resume_version': 2, 'max_tokens': 99999})


@pytest.mark.asyncio
async def test_handler_pauses_then_resumes_completed_phases_and_keeps_idempotency():
    from app.modules.knowledge.services import compilation_service as service
    from tests.test_compilation_lifecycle_603 import environment, request_body

    async with environment() as (client, _, cid, items, _, model, _):
        route = {'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model',
                 '_compiler_policy': {'max_calls': 4, 'max_total_calls': 128}}
        with patch.object(service, 'resolve_route', AsyncMock(return_value=route)):
            body = await request_body(client, cid, items, key='611-first-build')
            first = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert first.status_code == 200, first.text
            old = first.json()
            assert old['status'] == 'paused' and old['resumable'] and len(model.calls) == 4
            repeated = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert repeated.json() == old and len(model.calls) == 4
            stale = {**body, 'idempotency_key': '611-stale-resume', 'resume_from_job_id': old['id'],
                     'expected_resume_version': old['version'] - 1}
            assert (await client.post(f'/knowledge/collections/{cid}/compilations', json=stale)).status_code == 409
            for number in range(1, 32):
                body = {**body, 'idempotency_key': f'611-resume-{number}', 'resume_from_job_id': old['id'],
                        'expected_resume_version': old['version']}
                response = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
                assert response.status_code == 200, response.text
                old = response.json()
                if old['status'] != 'paused':
                    break
            assert old['status'] == 'ready_for_review' and not old['resumable']
            assert model.calls.count('TopicSelection') == 6
            read = await client.get(f'/knowledge/collections/{cid}/compilations/{old["id"]}')
            assert read.status_code == 200 and read.json()['bundle']['machine_complete']
            assert read.json()['bundle']['publication'] == 'unpublished'


@pytest.mark.asyncio
async def test_two_identical_coverage_inputs_still_make_two_independent_calls():
    from tests.test_compilation_context_608 import EmptyModel
    stages = MemoryStages()
    model = EmptyModel(['unrelated', 'unrelated'])
    result = await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu', ACTOR, model, '611', checkpoints=stages)
    assert result['machine_complete'] and model.calls.count('CoverageAudit') == 2
    audits = [entry for entry in stages.values.values() if entry['identity']['contract'] == 'CoverageAudit']
    assert len(audits) == 2 and audits[0]['identity']['request'] == audits[1]['identity']['request']
    assert audits[0]['identity']['ordinal'] != audits[1]['identity']['ordinal']


@pytest.mark.asyncio
async def test_completed_schema_rejection_replays_feedback_without_resending_bad_call():
    stages, model, attempts = MemoryStages(), Model(), []

    async def malformed_once(contract, instruction, payload):
        attempts.append(contract.__name__)
        if len(attempts) == 1:
            raise AppException('Invalid JSON', code='KNOWLEDGE_WIKI_INVALID', status_code=502,
                               details={'reason': 'json_syntax'})
        return await model(contract, instruction, payload)

    policy = CompilerPolicy(max_calls=4, max_total_calls=32)
    for _ in range(8):
        try:
            result = await compile_topic([sample(1)], 'c603', 'Chỉ tiêu', ACTOR, malformed_once, '611',
                                         policy=policy, checkpoints=stages)
            break
        except AppException as exc:
            assert exc.code == 'KNOWLEDGE_COMPILATION_PAUSED'
    else:
        raise AssertionError('Did not finish within the configured total budget')
    assert result['machine_complete'] and len(attempts) == 7
    assert sum(v['status'] == 'rejected' for v in stages.values.values()) == 1


@pytest.mark.asyncio
async def test_total_budget_cannot_be_reset_by_replaying_checkpoints():
    model, stages = Model(), MemoryStages()
    policy = CompilerPolicy(max_calls=4, max_total_calls=4)
    for _ in range(2):
        with pytest.raises(AppException) as error:
            await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu', ACTOR, model, '611',
                                policy=policy, checkpoints=stages)
        assert error.value.details['reason'] == 'minimum_plan_exceeds_total_call_budget'
    assert len(model.calls) == stages.total_calls == 4


@pytest.mark.parametrize(('repeat', 'fits'), [(400, True), (600, True), (1000, False)])
def test_separate_request_budgets_do_not_double_charge_quotes_to_extraction(repeat, fits):
    from app.modules.knowledge.services.compilation_engine import packet_budget, packet_payload
    from app.modules.knowledge.wiki_schemas import WikiPolicy
    catalog = {'p': {'source_revision_id': 's', 'quote': 'Evidence ' * repeat}}
    payload = packet_payload('Topic', ['p'], catalog, {})
    budget = packet_budget(payload, WikiPolicy(max_output_tokens=8192))
    assert budget['fits'] is fits
    assert (budget['total_reserved'] <= 24000) is fits
    old_reserve = 5000 + 2 * len(catalog['p']['quote'].encode()) + 400
    assert budget['input_upper_bound'] + 8192 + old_reserve > 24000
    assert payload['evidence']['p']['quote'] == catalog['p']['quote']


@pytest.mark.asyncio
@pytest.mark.parametrize('missing', [False, True])
async def test_partitioned_reviews_keep_all_raw_context_and_require_every_item(missing):
    from app.modules.knowledge.compilation_runtime_schemas import PacketCheck, PacketDraft
    from app.modules.knowledge.services import compilation_review as review
    draft = PacketDraft(entities=[{'id': 'e', 'label': 'Unit', 'evidence_ids': ['p']}],
        assertions=[{'id': f'a{i}', 'entity_id': 'e', 'attribute': 'Metric', 'value': str(i),
                     'value_state': 'present', 'evidence_ids': ['p']} for i in range(3)],
        deferred_evidence_ids=['note']).model_dump()
    payload = {'evidence': {'p': {'source_revision_id': 's', 'quote': 'Metric applies only to group A'},
                           'note': {'source_revision_id': 's', 'quote': 'Exception group B'}},
               'primary_evidence_ids': ['p', 'note'], 'context_dependencies': {'p': ['note']}}
    observed = []

    async def bounded(contract, instruction, batch):
        observed.append(batch)
        assert batch['evidence'] == payload['evidence'] and batch['context_dependencies'] == payload['context_dependencies']
        assert len(batch['draft']['assertions']) == 1
        return PacketCheck(items=[] if missing else [{'id': batch['draft']['assertions'][0]['id'],
            'verdict': 'supported', 'entity_scope': True, 'temporal_roles': True, 'conditions_complete': True,
            'evidence_ids': ['p'], 'reason': 'Checked raw context.'}])

    def budget(contract, instruction, body, policy):
        return {'fits': len(body['draft']['assertions']) <= 1}

    with patch.object(review, 'request_budget', side_effect=budget):
        if missing:
            with pytest.raises(AppException) as exc:
                await review.review_packet(payload, draft, {}, bounded, 'Check')
            assert exc.value.details['reason'] == 'incomplete_batch_review'
        else:
            result = await review.review_packet(payload, draft, {}, bounded, 'Check')
            assert len(result.items) == len(observed) == 3
            assert result.missed_evidence_ids == ['note']


@pytest.mark.asyncio
@pytest.mark.parametrize('damage', ['source', 'config', 'uncertain', 'checksum', 'permission'])
async def test_persisted_resume_rejects_stale_or_untrusted_state_without_inference(damage):
    from sqlalchemy import select

    from app.modules.knowledge.models import KnowledgeCollection, KnowledgeSourceRevision
    from app.modules.knowledge.services import compilation_service as service
    from app.modules.knowledge.services.compilation_store import assign, registry
    from tests.test_compilation_lifecycle_603 import environment, request_body

    async with environment() as (client, factory, cid, items, actor, model, _):
        route = {'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model',
                 '_compiler_policy': {'max_calls': 4, 'max_total_calls': 128}}
        with patch.object(service, 'resolve_route', AsyncMock(side_effect=lambda _: deepcopy(route))):
            body = await request_body(client, cid, items, key='611-negative-start')
            old = (await client.post(f'/knowledge/collections/{cid}/compilations', json=body)).json()
            assert old['status'] == 'paused'
            body.update(idempotency_key='611-negative-resume', resume_from_job_id=old['id'], expected_resume_version=old['version'])
            if damage == 'config':
                route['_compiler_policy']['max_output_tokens'] = 8192
            elif damage == 'permission':
                actor.permissions = []
            else:
                async with factory() as db:
                    if damage == 'source':
                        source = (await db.scalars(select(KnowledgeSourceRevision).where(
                            KnowledgeSourceRevision.id.in_(old['source_revision_ids'])))).first()
                        source.lock_version += 1
                    else:
                        collection = await db.get(KnowledgeCollection, cid)
                        state = registry(collection)
                        entry = next(iter(state['jobs'][old['id']]['checkpoints'].values()))
                        if damage == 'uncertain':
                            entry['status'] = 'started'
                        else:
                            entry['reference']['sha256'] = '0' * 64
                        assign(collection, state)
                    await db.commit()
            response = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert response.status_code in (403, 409), response.text
            assert len(model.calls) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize('fresh_competitor', [False, True])
async def test_concurrent_resume_has_one_owner_and_no_duplicate_model_calls(fresh_competitor):
    from app.modules.knowledge.services import compilation_service as service
    from tests.test_compilation_lifecycle_603 import environment, request_body
    async with environment() as (client, _, cid, items, _, model, _):
        route = {'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model',
                 '_compiler_policy': {'max_calls': 4, 'max_total_calls': 128}}
        with patch.object(service, 'resolve_route', AsyncMock(return_value=route)):
            body = await request_body(client, cid, items, key='611-concurrent-start')
            old = (await client.post(f'/knowledge/collections/{cid}/compilations', json=body)).json()
            entered, release = asyncio.Event(), asyncio.Event()

            async def gated(contract, instruction, payload):
                entered.set()
                await release.wait()
                return await model(contract, instruction, payload)

            body.update(idempotency_key='611-concurrent-first', resume_from_job_id=old['id'],
                        expected_resume_version=old['version'])
            with patch.object(service, 'generator', return_value=gated):
                first = asyncio.create_task(client.post(f'/knowledge/collections/{cid}/compilations', json=body))
                await asyncio.wait_for(entered.wait(), timeout=10)
                competing = {**body, 'idempotency_key': '611-concurrent-second'}
                if fresh_competitor:
                    competing.pop('resume_from_job_id')
                    competing.pop('expected_resume_version')
                other = await client.post(f'/knowledge/collections/{cid}/compilations', json=competing)
                assert other.status_code == 409
                release.set()
                result = await first
            assert result.status_code == 200 and len(model.calls) == 8


def test_existing_assertion_factoring_is_lossless_and_retains_each_value_and_raw_proof():
    from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit
    from app.modules.knowledge.services import compilation_coverage as coverage
    from app.modules.knowledge.wiki_schemas import WikiPolicy
    assertions = [{'id': f'a{i}', 'entity_id': 'e', 'attribute': 'Metric', 'value_state': 'present',
        'value': str(i), 'scope': [{'dimension': 'group', 'value': 'A', 'evidence_ids': ['p']}],
        'temporal': [{'role': 'data', 'years': [2034], 'evidence_ids': ['p']}],
        'condition_ids': ['p'], 'exception_ids': ['note'], 'evidence_ids': ['p']} for i in range(8)]
    payload = {'existing_assertions': assertions, 'missed_evidence_ids': ['note'],
        'evidence': {'p': {'quote': 'Exact 2034 values for group A'}, 'note': {'quote': 'Exception group B'}},
        'temporal_context': {'p': {'classification': 'untrusted_navigation'}},
        'context_dependencies': {'p': ['note']}}
    before = deepcopy(payload)
    def fits(contract, instruction, body, policy):
        return {'fits': 'shared_assertion_contexts' in body}
    with patch.object(coverage, 'request_budget', side_effect=fits):
        instruction, compact = coverage.existing_assertion_request(CoverageAudit, 'Check', payload, WikiPolicy(max_output_tokens=8192))
    restored = []
    for item in compact['existing_assertions']:
        result = {k: v for k, v in item.items() if k != 'shared_context_ids'}
        for alias in item.get('shared_context_ids', []):
            result.update(compact['shared_assertion_contexts'][alias])
        restored.append(result)
    assert restored == assertions and payload == before
    assert compact['evidence'] == payload['evidence'] and compact['context_dependencies'] == payload['context_dependencies']
    assert 'temporal_context' not in compact and 'ALL raw evidence' in instruction


@pytest.mark.asyncio
async def test_failure_before_any_uncertain_call_can_resume_the_known_complete_prefix():
    from app.modules.knowledge.services import compilation_service as service
    from tests.test_compilation_lifecycle_603 import environment, request_body
    actual = service.compile_topic
    async def interrupted(*args, **kwargs):
        try:
            return await actual(*args, **kwargs)
        except AppException as exc:
            if exc.code == 'KNOWLEDGE_COMPILATION_PAUSED':
                raise AppException('Simulated deterministic boundary before a new call.',
                    code='KNOWLEDGE_COMPILATION_INVALID', status_code=422) from exc
            raise
    async with environment() as (client, _, cid, items, _, model, _):
        route = {'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model',
                 '_compiler_policy': {'max_calls': 4, 'max_total_calls': 128}}
        with patch.object(service, 'resolve_route', AsyncMock(return_value=route)):
            body = await request_body(client, cid, items, key='611-safe-boundary')
            with patch.object(service, 'compile_topic', side_effect=interrupted):
                response = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert response.status_code == 422 and len(model.calls) == 4
            old = (await client.get(f'/knowledge/collections/{cid}/compilations')).json()['items'][0]
            assert old['status'] == 'uncertain' and old['resumable'] and old['completed_stages'] == 4
            response = await client.post(f'/knowledge/collections/{cid}/compilations', json={**body,
                'idempotency_key': '611-safe-boundary-next', 'resume_from_job_id': old['id'],
                'expected_resume_version': old['version']})
            assert response.status_code == 200 and response.json()['status'] == 'paused'
            assert len(model.calls) == 8 and model.calls.count('TopicSelection') == 6


@pytest.mark.asyncio
async def test_new_packet_cache_entries_do_not_change_the_resumed_stage_sequence():
    from app.modules.knowledge.services import compilation_service as service
    from tests.test_compilation_lifecycle_603 import environment, request_body
    async with environment() as (client, _, cid, items, _, model, _):
        route = {'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model',
                 '_compiler_policy': {'max_calls': 4, 'max_total_calls': 128}}
        actual = service.compile_topic
        caches = []
        async def traced(*args, **kwargs):
            caches.append(deepcopy(args[6]))
            return await actual(*args, **kwargs)
        with (patch.object(service, 'resolve_route', AsyncMock(return_value=route)),
              patch.object(service, 'compile_topic', side_effect=traced)):
            body = await request_body(client, cid, items, key='611-cache-first')
            old = (await client.post(f'/knowledge/collections/{cid}/compilations', json=body)).json()
            assert old['status'] == 'paused'
            with patch.object(service, 'available_packets', AsyncMock(return_value={'new-unrelated': {'sha256': 'x'}})):
                response = await client.post(f'/knowledge/collections/{cid}/compilations', json={**body,
                    'idempotency_key': '611-cache-next', 'resume_from_job_id': old['id'],
                    'expected_resume_version': old['version']})
            assert response.status_code == 200 and response.json()['status'] == 'paused'
            assert caches == [{}, {}] and len(model.calls) == 8
