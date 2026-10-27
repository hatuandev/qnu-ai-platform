"""Existing ModelOps adapter contract, dynamic route and budget; no network/credentials."""
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import CompilationRequest, PacketDraft
from app.modules.knowledge.services.compilation_modelops import (
    configuration_hash,
    generator,
    resolve_route,
)
from app.modules.knowledge.services.wiki_build import generate_object
from app.modules.knowledge.wiki_schemas import WikiPolicy
from app.modules.modelops.schemas import LLMGenerateResponse


def defaults():
    return SimpleNamespace(default_chat_provider_id='primary', default_chat_model='selected-model',
        default_chat_mode='combo', chat_combo_chain=[
            SimpleNamespace(provider_id='disabled', model_name='disabled', is_active=False),
            SimpleNamespace(provider_id='primary', model_name='selected-model', is_active=True),
            SimpleNamespace(provider_id='backup', model_name='backup-model', is_active=True)])


@pytest.mark.asyncio
async def test_route_comes_from_modelops_and_rotation_changes_only_opaque_configuration_seal():
    item = SimpleNamespace(id='primary', created_at=datetime(2026, 1, 1, tzinfo=UTC),
        is_active=True,api_base_url='http://127.0.0.1:1/v1',extra_config={},
        api_key_encrypted='fake-encrypted-value', __table__=SimpleNamespace(columns=[
            SimpleNamespace(key='created_at'), SimpleNamespace(key='api_key_encrypted')]))
    db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [item])))
    with patch('app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults',
               AsyncMock(return_value=SimpleNamespace(defaults=defaults()))), patch(
               'app.modules.modelops.services.capacity_discovery.discover',AsyncMock(return_value={
                   'context_window_tokens':128000,'max_output_tokens':64000,'basis':'provider_reported'})):
        route = await resolve_route(db)
        assert route['preferred_model_name'] == 'selected-model' and route['fallback_provider_id'] == 'backup'
        assert 'fake-encrypted-value' not in repr(route) and len(route['_configuration_hash']) == 64
        first = configuration_hash(route, {})
        item.api_key_encrypted = 'rotated-fake-value'
        assert configuration_hash(await resolve_route(db), {}) != first


@pytest.mark.asyncio
async def test_missing_modelops_defaults_fails_without_constructing_an_inference_request():
    value = defaults()
    value.default_chat_model = None
    with patch('app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults',
               AsyncMock(return_value=SimpleNamespace(defaults=value))):
        with pytest.raises(AppException) as error:
            await resolve_route(None)
        assert error.value.code == 'KNOWLEDGE_COMPILATION_MODEL_REQUIRED'


@pytest.mark.asyncio
async def test_optional_fallback_discovery_does_not_block_or_probe_before_primary_dispatch():
    from app.modules.knowledge.services.compilation_modelops import execution_policy

    def provider(pid):
        return SimpleNamespace(id=pid,is_active=True,api_base_url='http://127.0.0.1:1/v1',extra_config={},
            __table__=SimpleNamespace(columns=[]))
    db=SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda:[provider('primary'),provider('backup')])))
    discovery=AsyncMock(return_value={'context_window_tokens':128000,'max_output_tokens':64000,'basis':'provider_reported'})
    with patch('app.modules.modelops.services.model_catalog_service.model_catalog_service.get_system_model_defaults',
            AsyncMock(return_value=SimpleNamespace(defaults=defaults()))),patch(
            'app.modules.modelops.services.capacity_discovery.discover',discovery):
        route=await resolve_route(db)
    assert discovery.await_count==1 and discovery.await_args.args[1]=='selected-model'
    assert execution_policy(route).context_budget_tokens==128000
    assert route['_token_limits'][1]['basis']=='discover_on_dispatch_unverified'


@pytest.mark.parametrize('field', ['preferred_provider_id', 'preferred_model_name', 'actor_id', 'publication'])
def test_client_cannot_choose_model_or_claim_approval_authority(field):
    with pytest.raises(ValidationError):
        CompilationRequest.model_validate({'topic': 'Chủ đề thử', 'source_revision_ids': ['r'],
            'expected_source_set_hash': 'a' * 64, 'idempotency_key': 'request603', field: 'untrusted'})


@pytest.mark.asyncio
async def test_existing_adapter_measures_full_request_and_propagates_provider_failure():
    metrics = []
    blocked = AsyncMock(side_effect=AppException('Fixture provider error', code='PROVIDER_UNAVAILABLE', status_code=503))
    route = {'preferred_provider_id': 'primary', 'preferred_model_name': 'selected-model'}
    with patch('app.modules.modelops.service.modelops_service.generate', blocked):
        with pytest.raises(AppException):
            await generate_object(None, 'default', route, WikiPolicy(), metrics, PacketDraft, 'Instruction', {'quote': 'đ' * 30000})
        blocked.assert_not_awaited()
        with pytest.raises(AppException) as error:
            await generate_object(None, 'default', route, WikiPolicy(), metrics, PacketDraft, 'Instruction', {})
        assert error.value.code == 'PROVIDER_UNAVAILABLE'
        blocked.assert_awaited_once()


@pytest.mark.asyncio
async def test_json_adapter_keeps_observed_usage_and_does_not_leak_bad_output_in_errors():
    metrics = []
    response = LLMGenerateResponse(content=PacketDraft().model_dump_json(), provider='fixture-provider',
        model='observed-model', prompt_tokens=123, completion_tokens=17, finish_reason='stop')
    fake = AsyncMock(return_value=response)
    route = {'preferred_provider_id': 'primary', 'preferred_model_name': 'selected-model'}
    with patch('app.modules.modelops.service.modelops_service.generate', fake):
        result = await generate_object(None, 'default', route, WikiPolicy(), metrics, PacketDraft, 'Instruction', {})
        assert result.assertions == []
        request = fake.await_args.args[1]
        assert request.preferred_model_name == 'selected-model' and request.temperature == 0
        assert metrics[-1]['prompt_tokens'] == 123 and metrics[-1]['completion_tokens'] == 17
        response.content = 'PRIVATE_UNTRUSTED_OUTPUT_NOT_JSON'
        with pytest.raises(AppException) as error:
            await generate_object(None, 'default', route, WikiPolicy(), metrics, PacketDraft, 'Instruction', {})
        assert 'PRIVATE_UNTRUSTED_OUTPUT' not in repr(error.value.details)


@pytest.mark.asyncio
async def test_truncated_structured_output_is_not_treated_as_complete_generation():
    class Session:
        async def __aenter__(self):
            return None
        async def __aexit__(self, *_):
            return None
    response = LLMGenerateResponse(content=PacketDraft().model_dump_json(), provider='fixture', model='fixture', finish_reason='length')
    with (patch('app.core.database.AsyncSessionFactory', return_value=Session()),
          patch('app.modules.modelops.service.modelops_service.generate', AsyncMock(return_value=response))):
        run = generator({'preferred_provider_id': 'p', 'preferred_model_name': 'm', '_configuration_hash': 'a' * 64}, 'default', [])
        with pytest.raises(AppException) as error:
            await run(PacketDraft, 'Instruction', {})
        assert error.value.code == 'KNOWLEDGE_COMPILATION_INCOMPLETE_OUTPUT'


def test_short_handle_transport_preserves_raw_literals_and_restores_nested_proofs():
    from app.modules.knowledge.compilation_runtime_schemas import TopicSelection
    from app.modules.knowledge.services.compilation_transport import mapped, prepare

    pid = 'proof_' + 'a' * 24
    second = 'proof_' + 'b' * 24
    payload = {'evidence': {pid: {'quote': pid}, second: {'quote': 'Raw second'}},
        'context_dependencies': {pid: [second]}, 'draft': {'assertions': [{'evidence_ids': [pid],
            'temporal': [{'evidence_ids': [second]}], 'value': pid}]}}
    contract, wire, reverse = prepare(TopicSelection, payload)
    assert wire['evidence']['u0']['quote'] == pid
    assert wire['draft']['assertions'][0]['value'] == pid
    assert wire['draft']['assertions'][0]['temporal'][0]['evidence_ids'] == ['u1']
    assert wire['context_dependencies'] == {'u0': ['u1']}
    output = contract(relevant_evidence_ids=['u1'], unrelated_evidence_ids=['u0'])
    restored = mapped(output.model_dump(), reverse)
    assert restored['relevant_evidence_ids'] == [second]
    with pytest.raises(ValidationError):
        contract(relevant_evidence_ids=['u999'])
