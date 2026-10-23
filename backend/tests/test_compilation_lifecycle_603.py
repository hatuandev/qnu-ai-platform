"""Real owned PostgreSQL + ASGI + LocalStorage; inference is explicitly deterministic."""
import asyncio
import hashlib
from collections import Counter
from contextlib import asynccontextmanager
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.core.database import get_db
from app.core.exceptions import AppException, register_exception_handlers
from app.core.storage import storage_service
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeCollection, KnowledgeFact
from app.modules.knowledge.router import router
from app.modules.knowledge.services import compilation_service as service
from tests.test_compilation_engine_603 import Model
from tests.test_wiki_snapshot_integration_600 import fixture


@asynccontextmanager
async def environment():
    async with fixture() as (factory, cid, items, engine):
        async with factory() as db:
            for original, _, _ in items:
                source = await db.get(type(original), original.id)
                raw = ('owned fixture603 raw ' + source.id).encode()
                path = f'fixtures603/{cid}/{source.id}.bin'
                await storage_service.save(path, raw)
                source.origin_file_hash = hashlib.sha256(raw).hexdigest()
                source.snapshot_storage_path = path
            await db.commit()
        actor = AuthActor(username='test603-admin', actor_id='test603-actor', permissions=['ai.access.admin'])
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router)

        async def database():
            async with factory() as db:
                yield db

        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_actor] = lambda: actor
        model = Model()
        with (patch.object(service, 'resolve_route', AsyncMock(return_value={
                    'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model'})),
              patch.object(service, 'generator', return_value=model)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://fixture') as client:
                yield client, factory, cid, items, actor, model, engine


async def request_body(client, cid, items, key='compile603-first'):
    ids = [item[0].id for item in items]
    response = await client.get(f'/knowledge/collections/{cid}/compilations/preview',
        params=[('source_revision_ids', value) for value in ids])
    assert response.status_code == 200, response.text
    return {'topic': 'Chỉ tiêu và phạm vi từng năm', 'source_revision_ids': ids,
        'expected_source_set_hash': response.json()['source_set_hash'], 'idempotency_key': key}


async def build(client, cid, items):
    body = await request_body(client, cid, items)
    response = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
    assert response.status_code == 200, response.text
    return response.json(), body


def action(record, decision='approved', key='decision603-first'):
    return {'expected_version': record['version'], 'expected_proposal_hash': record['proposal_hash'],
        'decision': decision, 'idempotency_key': key}


def assert_build_phases(model, full_builds=1, synthesis_builds=1):
    from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
    from app.modules.knowledge.services.wiki_compiler import source_units
    from tests.test_wiki_links_600 import source as fixture_source
    # Splitting must preserve every proof exactly once per build, including concurrent/reused builds.
    assert model.calls.count('TopicSelection') == 6 * full_builds
    assert model.calls.count('PacketDraft') == model.calls.count('PacketCheck') == len(model.primary_batches)
    assigned=Counter(pid for batch in model.primary_batches for pid in batch)
    expected=3*sum(not unit.is_container for unit in source_units(fixture_source()))
    assert len(assigned)==expected and set(assigned.values())=={full_builds}
    assert all(0<len(batch)<=CompilerPolicy().max_primary_per_packet for batch in model.primary_batches)
    assert model.calls.count('SynthesisDraft') == model.calls.count('SynthesisCheck') >= synthesis_builds
    assert set(model.calls) == {'TopicSelection', 'PacketDraft', 'PacketCheck', 'SynthesisDraft', 'SynthesisCheck'}


@pytest.mark.asyncio
async def test_handler_persists_readback_idempotent_human_review_without_publication_or_fact_writes():
    async with environment() as (client, factory, cid, items, actor, model, _):
        before = [(b.id, b.active_index_revision_id, b.active_source_revision_id) for _, _, b in items]
        async with factory() as db:
            facts_before = await db.scalar(select(func.count()).select_from(KnowledgeFact))
        record, body = await build(client, cid, items)
        assert record['status'] == 'ready_for_review'
        assert_build_phases(model)
        calls = model.calls[:]
        path = f'/knowledge/collections/{cid}/compilations/{record["id"]}'
        fetched = (await client.get(path)).json()
        assert fetched['bundle']['machine_complete'] and fetched['bundle']['publication'] == 'unpublished'
        assert fetched['bundle']['dependencies'] and fetched['bundle']['markdown']
        replay = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
        assert replay.json() == record and model.calls == calls
        actor.permissions = ['ai.knowledge.review', 'ai.knowledge.view']  # Read must not require/fabricate upload permission.
        decision = action(record)
        accepted = await client.post(path + '/decisions', json=decision)
        assert accepted.status_code == 200 and accepted.json()['status'] == 'reviewed'
        assert (await client.post(path + '/decisions', json=decision)).json() == accepted.json()
        readback = (await client.get(path)).json()  # Fresh SQL session, immutable Storage object read back.
        assert len(readback['audit']) == 3
        assert [e['type'] for e in readback['audit']] == ['compilation_requested', 'automated_verification', 'user_decision']
        assert readback['audit'][-1]['actor_id'] == actor.actor_id
        assert readback['audit'][-1]['publication_granted'] is False
        async with factory() as db:
            after = (await db.execute(select(KnowledgeBinding.id, KnowledgeBinding.active_index_revision_id,
                KnowledgeBinding.active_source_revision_id).where(KnowledgeBinding.collection_id == cid)
                .order_by(KnowledgeBinding.id))).all()
            assert sorted(before) == list(after)
            assert facts_before == await db.scalar(select(func.count()).select_from(KnowledgeFact))


@pytest.mark.asyncio
async def test_concurrent_creation_has_one_inference_owner_and_both_keys_are_idempotent():
    async with environment() as (client, _, cid, items, _, model, _):
        body = await request_body(client, cid, items)
        entered, release = asyncio.Event(), asyncio.Event()
        async def blocked(*args):
            if not entered.is_set():
                entered.set()
                await release.wait()
            return await model(*args)
        with patch.object(service, 'generator', return_value=blocked):
            first = asyncio.create_task(client.post(f'/knowledge/collections/{cid}/compilations', json=body))
            await asyncio.wait_for(entered.wait(), 10)
            second_body = {**body, 'idempotency_key': 'compile603-second'}
            second = await client.post(f'/knowledge/collections/{cid}/compilations', json=second_body)
            assert second.status_code == 200 and second.json()['status'] == 'running'
            release.set()
            completed = await asyncio.wait_for(first, 15)
            assert completed.json()['id'] == second.json()['id']
            assert_build_phases(model)
            calls = model.calls[:]
        repeated = await client.post(f'/knowledge/collections/{cid}/compilations', json=second_body)
        assert repeated.json()['id'] == completed.json()['id'] and model.calls == calls


@pytest.mark.asyncio
async def test_concurrent_review_uses_occ_and_does_not_duplicate_or_overwrite_audit():
    async with environment() as (client, _, cid, items, _, _, _):
        record, _ = await build(client, cid, items)
        path = f'/knowledge/collections/{cid}/compilations/{record["id"]}/decisions'
        replies = await asyncio.gather(client.post(path, json=action(record)),
            client.post(path, json=action(record, decision='rejected', key='decision603-second')))
        assert sorted(r.status_code for r in replies) == [200, 409]
        result = (await client.get(path.removesuffix('/decisions'))).json()
        assert len([e for e in result['audit'] if e['type'] == 'user_decision']) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('corruption', ['canonical', 'raw', 'binding', 'epoch'])
async def test_source_change_or_removal_blocks_review_and_returns_no_stale_derived_text(corruption):
    async with environment() as (client, factory, cid, items, _, _, _):
        record, _ = await build(client, cid, items)
        async with factory() as db:
            original, _, binding = items[0]
            if corruption == 'canonical':
                current = await db.get(type(original), original.id)
                current.canonical_hash = 'a' * 64
            elif corruption == 'raw':
                current = await db.get(type(original), original.id)
                await storage_service.save(current.snapshot_storage_path, b'changed fixture raw')
            elif corruption == 'binding':
                current = await db.get(KnowledgeBinding, binding.id)
                current.status = 'detached'
            else:
                current = await db.get(KnowledgeCollection, cid)
                current.index_epoch += 1
            await db.commit()
        path = f'/knowledge/collections/{cid}/compilations/{record["id"]}'
        fetched = await client.get(path)
        # Invalid canonical/manifest may use the existing wiki integrity error; never return derived content.
        assert fetched.status_code in {200, 409, 422}
        if fetched.status_code == 200:
            assert fetched.json()['status'] == 'stale' and fetched.json()['bundle'] is None
        denied = await client.post(path + '/decisions', json=action(record))
        assert denied.status_code in {409, 422}


@pytest.mark.asyncio
async def test_revocation_propagates_to_reused_derivative_and_never_reactivates_on_read():
    async with environment() as (client, _, cid, items, _, model, _):
        first, body = await build(client, cid, items)
        next_body = {**body, 'idempotency_key': 'compile603-another'}
        second = (await client.post(f'/knowledge/collections/{cid}/compilations', json=next_body)).json()
        path = f'/knowledge/collections/{cid}/compilations/'
        second_read = (await client.get(path + second['id'])).json()
        assert second_read['bundle']['reused_packets'] == len(model.primary_batches)
        assert second_read['bundle']['reused_topic_packets'] == len(second_read['bundle']['topic_results'])
        assert_build_phases(model, synthesis_builds=2)
        revoked = await client.post(path + first['id'] + '/decisions', json=action(first, 'revoked'))
        assert revoked.status_code == 200 and revoked.json()['status'] == 'revoked'
        second_read = (await client.get(path + second['id'])).json()
        assert second_read['status'] == 'stale' and second_read['bundle'] is None
        assert (await client.post(path + second['id'] + '/decisions', json=action(second))).status_code == 409
        third = (await client.post(f'/knowledge/collections/{cid}/compilations',
            json={**body, 'idempotency_key': 'compile603-fresh-after-revoke'})).json()
        assert third['status'] == 'ready_for_review'
        assert_build_phases(model, full_builds=2, synthesis_builds=3)
        assert (await client.get(path + third['id'])).json()['bundle']['reused_packets'] == 0


@pytest.mark.asyncio
async def test_unresolved_semantics_cannot_be_approved_even_by_admin():
    async with environment() as (client, _, cid, items, _, model, _):
        model.unresolved = True
        record, _ = await build(client, cid, items)
        assert record['status'] == 'needs_attention'
        rejected = await client.post(f'/knowledge/collections/{cid}/compilations/{record["id"]}/decisions', json=action(record))
        assert rejected.status_code == 409 and rejected.json()['code'] == 'KNOWLEDGE_COMPILATION_INVALID'


@pytest.mark.asyncio
async def test_provider_failure_has_durable_uncertain_receipt_and_does_not_resend_same_intent():
    async with environment() as (client, _, cid, items, _, _, _):
        body = await request_body(client, cid, items)
        failed = AsyncMock(side_effect=AppException('Provider fixture unavailable', code='PROVIDER_UNAVAILABLE', status_code=503))
        with patch.object(service, 'generator', return_value=failed):
            first = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert first.status_code == 503
            retry = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert retry.status_code == 200 and retry.json()['status'] == 'uncertain'
            failed.assert_awaited_once()
            listed = (await client.get(f'/knowledge/collections/{cid}/compilations')).json()
            assert listed['items'][0]['id'] == retry.json()['id']


@pytest.mark.asyncio
async def test_handler_permissions_hash_foreign_source_and_generic_metadata_cannot_bypass_compiler():
    async with environment() as (client, _, cid, items, actor, model, _):
        body = await request_body(client, cid, items)
        url = f'/knowledge/collections/{cid}/compilations'
        bad = await client.post(url, json={**body, 'expected_source_set_hash': '0' * 64})
        assert bad.status_code == 409 and not model.calls
        assert (await client.post(url, json={**body, 'source_revision_ids': ['foreign']})).status_code == 409
        generic = await client.put(f'/knowledge/collections/{cid}', json={'metadata': {
            'knowledge_compilation_registry': {'jobs': {'fake': {'status': 'reviewed'}}}}})
        assert generic.status_code == 403
        generic_create = await client.post('/knowledge/collections', json={'name': 'Fixture603 invalid', 'module_code': 'general',
            'metadata': {'knowledge_compilation_registry': {}}})
        assert generic_create.status_code == 403
        actor.permissions = ['ai.knowledge.upload']
        assert (await client.post(url, json=body)).status_code == 403
        actor.permissions = ['ai.knowledge.view']
        assert (await client.post(url, json=body)).status_code == 403
        assert (await client.get(url)).status_code == 403
        assert not model.calls


@pytest.mark.asyncio
async def test_storage_corruption_never_becomes_approved_or_model_fallback():
    async with environment() as (client, factory, cid, items, _, model, _):
        record, _ = await build(client, cid, items)
        async with factory() as db:
            collection = await db.get(KnowledgeCollection, cid)
            reference = deepcopy(collection.collection_metadata['knowledge_compilation_registry']['jobs'][record['id']]['artifact'])
        await storage_service.save(reference['path'], b'{"corrupted":true}')
        response = await client.get(f'/knowledge/collections/{cid}/compilations/{record["id"]}')
        assert response.status_code == 409
        assert_build_phases(model)


@pytest.mark.asyncio
async def test_cancellation_keeps_a_durable_receipt_and_cannot_auto_resend():
    async with environment() as (client, _, cid, items, _, model, _):
        body = await request_body(client, cid, items)
        entered = asyncio.Event()
        async def cancelled(*_args):
            entered.set()
            await asyncio.Event().wait()
        with patch.object(service, 'generator', return_value=cancelled):
            task = asyncio.create_task(client.post(f'/knowledge/collections/{cid}/compilations', json=body))
            await asyncio.wait_for(entered.wait(), 10)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        records = (await client.get(f'/knowledge/collections/{cid}/compilations')).json()['items']
        assert len(records) == 1 and records[0]['status'] == 'uncertain'
        repeat = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
        assert repeat.json()['id'] == records[0]['id'] and not model.calls


@pytest.mark.asyncio
async def test_source_change_while_inference_runs_does_not_commit_ready_artifact():
    async with environment() as (client, factory, cid, items, _, model, _):
        body = await request_body(client, cid, items)
        entered, release = asyncio.Event(), asyncio.Event()
        async def blocked(*args):
            if not entered.is_set():
                entered.set()
                await release.wait()
            return await model(*args)
        with patch.object(service, 'generator', return_value=blocked):
            task = asyncio.create_task(client.post(f'/knowledge/collections/{cid}/compilations', json=body))
            await asyncio.wait_for(entered.wait(), 10)
            async with factory() as db:
                collection = await db.get(KnowledgeCollection, cid)
                collection.index_epoch += 1
                await db.commit()
            release.set()
            response = await asyncio.wait_for(task, 15)
        assert response.status_code == 409
        async with factory() as db:
            collection = await db.get(KnowledgeCollection, cid)
            records = collection.collection_metadata['knowledge_compilation_registry']['jobs']
            assert len(records) == 1
            record = next(iter(records.values()))
            assert record['status'] == 'uncertain' and 'artifact' not in record


@pytest.mark.asyncio
async def test_changed_idempotency_payload_and_wrong_proposal_hash_cannot_override_review():
    async with environment() as (client, _, cid, items, _, model, _):
        record, body = await build(client, cid, items)
        calls = model.calls[:]
        url = f'/knowledge/collections/{cid}/compilations'
        assert (await client.post(url, json={**body, 'topic': 'Một chủ đề khác'})).status_code == 409
        assert model.calls == calls
        wrong = {**action(record), 'expected_proposal_hash': '0' * 64}
        assert (await client.post(url + f'/{record["id"]}/decisions', json=wrong)).status_code == 409
        assert (await client.get(url + f'/{record["id"]}')).json()['status'] == 'ready_for_review'


@pytest.mark.asyncio
async def test_failed_storage_write_is_visible_and_no_unconfirmed_artifact_pointer_is_saved():
    async with environment() as (client, factory, cid, items, _, model, _):
        body = await request_body(client, cid, items)
        actual = storage_service.save
        count = 0
        async def broken(path, value):
            nonlocal count
            count += 1
            if count == 2:  # Durable intent succeeds; bundle write fails; failure receipt can still be stored.
                raise OSError('fixture Storage unavailable')
            return await actual(path, value)
        with patch.object(storage_service, 'save', side_effect=broken):
            response = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
        assert response.status_code == 502
        async with factory() as db:
            collection = await db.get(KnowledgeCollection, cid)
            record = next(iter(collection.collection_metadata['knowledge_compilation_registry']['jobs'].values()))
            assert record['status'] == 'uncertain' and 'artifact' not in record
        assert_build_phases(model)
