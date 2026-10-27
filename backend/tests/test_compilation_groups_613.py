"""Group-scoped model limits and lossless global manifests, without live inference."""
from copy import deepcopy

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
from app.modules.knowledge.services import compilation_engine as engine
from app.modules.knowledge.services.compilation_modelops import execution_policy
from app.modules.knowledge.services.compilation_validation import validate_result
from app.modules.knowledge.wiki_schemas import WikiPolicy
from app.modules.modelops.schemas import LLMGenerateRequest, ModelCapabilityConfig
from app.modules.modelops.services.token_limits import (
    configured_token_limits,
    validate_output_budget,
)
from tests.test_compilation_checkpoint_611 import MemoryStages
from tests.test_compilation_engine_603 import ACTOR, Model, sample


def test_model_budget_uses_resolved_limits_instead_of_global_24k_8192_caps():
    route = {'preferred_provider_id': 'p', 'preferred_model_name': 'large',
             '_token_limits': [{'provider_id': 'p', 'model': 'large',
                'context_window_tokens': 131072, 'max_output_tokens': 16384,
                'basis': 'operator_configured'}]}
    policy = execution_policy(route)
    assert policy.context_budget_tokens == 131072
    assert policy.max_output_tokens == 16384


def test_large_output_request_and_capacity_profile_roundtrip_are_endpoint_bound():
    limits = {'endpoint': 'http://127.0.0.1:1/v1', 'context_window_tokens': 131072,
              'max_output_tokens': 16384}
    capability = ModelCapabilityConfig(token_limits=limits).model_dump(mode='json')
    extra = {'model_capabilities': {'large': capability}}
    req = LLMGenerateRequest(messages=[{'role': 'user', 'content': 'Synthetic'}], max_tokens=16384)
    assert req.max_tokens == 16384
    assert configured_token_limits(extra, 'large', limits['endpoint'])['context_window_tokens'] == 131072
    assert configured_token_limits(extra, 'another-alias', limits['endpoint']) is None
    with pytest.raises(AppException) as changed:
        configured_token_limits(extra, 'large', 'http://127.0.0.1:2/v1')
    assert changed.value.code == 'MODEL_TOKEN_LIMITS_STALE'
    with pytest.raises(AppException) as output:
        validate_output_budget(extra, 'large', limits['endpoint'], 16385)
    assert output.value.code == 'MODEL_OUTPUT_LIMIT_EXCEEDED'
    assert ModelCapabilityConfig(token_limits={**limits, 'max_output_tokens': 131072}).token_limits.max_output_tokens == 131072
    with pytest.raises(ValueError):
        ModelCapabilityConfig(token_limits={**limits, 'max_output_tokens': 131073})
    with pytest.raises(ValueError):
        ModelCapabilityConfig(token_limits={**limits, 'endpoint':'http://fixture-user:fixture-secret@127.0.0.1:1/v1'})


def test_fallback_is_sized_for_its_own_profile_and_unknown_capacity_is_explicit():
    route = {'_token_limits': [
        {'provider_id': 'a', 'model': 'large', 'context_window_tokens': 131072, 'max_output_tokens': 16384},
        {'provider_id': 'b', 'model': 'small', 'context_window_tokens': 32768, 'max_output_tokens': 4096}]}
    policy = execution_policy(route)
    assert (policy.context_budget_tokens, policy.max_output_tokens) == (131072, 16384)
    assert policy.token_budget_basis == 'configured_primary_model_capacity'
    assert 'unverified' in execution_policy({}).token_budget_basis
    limited = execution_policy({**route, '_compiler_policy': {'max_output_tokens': 2048}})
    assert limited.max_output_tokens == 2048
    route['_token_limits'][1] = {'provider_id': 'b', 'model': 'unknown'}
    assert execution_policy(route).context_budget_tokens == 131072
    route['_token_limits'][0] = {'provider_id': 'a', 'model': 'unknown'}
    with pytest.raises(AppException) as unknown:
        execution_policy(route)
    assert unknown.value.code == 'MODEL_TOKEN_CAPACITY_REQUIRED'


def test_thinking_separate_from_output_requires_a_confirmed_budget_not_a_numeric_guess():
    with pytest.raises(AppException) as error:
        execution_policy({'_compiler_policy': {'reasoning_effort': 'medium'}, '_token_limits': [
            {'context_window_tokens': 32768, 'max_output_tokens': 8192,
             'reasoning_in_output_budget': False}]})
    assert error.value.code == 'MODEL_REASONING_BUDGET_UNVERIFIED'


def test_label_overlap_is_only_a_candidate_and_search_exhaustion_remains_unknown():
    from app.modules.knowledge.services.compilation_cross_source import (
        PROTOCOL,
        relation_candidates,
        validate_cross_ledger,
    )

    catalog={'p1':{'source_revision_id':'s1'},'p2':{'source_revision_id':'s2'}}
    proposal={'entities':[{'id':'e1','label':'Annual admissions quota','evidence_ids':['p1']},
                          {'id':'e2','label':'Annual admissions quota 2025','evidence_ids':['p2']}],
              'assertions':[{'entity_id':'e1'},{'entity_id':'e2'}]}
    pairs,total=relation_candidates(proposal,catalog,10)
    assert total==1 and pairs[0]['basis']=='label_overlap_candidate_only_not_identity'
    assert 'relations' not in proposal  # Discovery never adds an effective fact.
    proposal={'entities':[{'id':f'e{s}-{i}','label':f'Shared metric source {i}','evidence_ids':[f'p{s}']}
                          for s in (1,2) for i in range(20)],
              'assertions':[{'entity_id':f'e{s}-{i}'} for s in (1,2) for i in range(20)]}
    pairs,total=relation_candidates(proposal,catalog,1,search_budget=64)
    assert len(pairs)==1 and total is None
    ledger={'protocol':PROTOCOL,'candidate_limit':1,'candidates':pairs,'total_candidates':None,
            'search_budget_exhausted':True,'search_pair_budget':64,'examined':[pairs[0]['id']],'pending':[]}
    assert not validate_cross_ledger(proposal,catalog,ledger)


def test_synthesis_can_pack_a_single_complete_request_without_fixed_5000_reserve():
    catalog = {'p': {'source_revision_id': 's', 'quote': 'Evidence. ' * 500}}
    draft = {'snapshot_hash': 'a' * 64, 'entities': [{'id': 'e', 'label': 'Entity', 'evidence_ids': ['p']}],
             'assertions': [{'id': 'a', 'entity_id': 'e', 'attribute': 'Metric', 'value': 'Evidence',
                'value_state': 'present', 'evidence_ids': ['p'], 'temporal': [], 'scope': [],
                'condition_ids': [], 'exception_ids': []}]}
    policy = WikiPolicy(max_output_tokens=8192, context_budget_tokens=24000)
    payload = engine.synthesis_payload('Evidence', draft, draft['assertions'], catalog)
    actual = engine.request_usage(engine.SynthesisDraft, engine.SYNTHESIZE, payload, policy)
    assert actual['fits']
    assert not engine.request_usage(engine.SynthesisDraft, engine.SYNTHESIZE, payload, policy,
                                    feedback_reserve=5000)['fits']
    assert engine.synthesis_batches('Evidence', draft, catalog, policy)


@pytest.mark.asyncio
@pytest.mark.parametrize('claims_per_unit', [1, 2])
async def test_large_compilation_keeps_all_objects_sections_checks_and_resume_checkpoints(claims_per_unit):
    from app.modules.knowledge.services.source_artifact import build_source_artifact

    source = sample()
    source.canonical_markdown = '\n\n'.join(
        f'Đơn vị {i} có chỉ tiêu năm 2024: {i + 1}. Chỉ áp dụng nhóm A, ngoại lệ nhóm B.'
        for i in range(70))
    from hashlib import sha256
    source.canonical_hash = sha256(source.canonical_markdown.encode()).hexdigest()
    source.parse_provenance['structured_artifact'] = build_source_artifact(source.canonical_markdown, 1, {})
    original = deepcopy(vars(source))
    base_model, stages = Model(), MemoryStages()
    async def model(contract, instruction, payload):
        result = await base_model(contract, instruction, payload)
        if contract.__name__ == 'PacketDraft' and claims_per_unit == 2:
            data = result.model_dump()
            data['assertions'] += [{**a, 'id': a['id'] + '-second', 'attribute': 'Another source metric'}
                                   for a in data['assertions']]
            result = contract.model_validate(data)
        return result
    policy = CompilerPolicy(max_calls=64, max_total_calls=256)
    for _ in range(8):
        try:
            result = await engine.compile_topic([source], 'c603', 'Chỉ tiêu từng đơn vị', ACTOR, model,
                '613', policy=policy, checkpoints=stages)
            break
        except AppException as exc:
            assert exc.code == 'KNOWLEDGE_COMPILATION_PAUSED'
    else:
        raise AssertionError('Compilation did not complete within its execution budget')
    proposal = result['binding']['proposal']
    assert proposal['version'] == 'qnu-knowledge-compilation/v2'
    assert len(proposal['entities']) == 70
    assert len(proposal['assertions']) == len(proposal['sections']) == 70 * claims_per_unit
    assert len(proposal['groups']) > 1 and result['machine_complete']
    assert all(a['condition_ids'] and a['exception_ids'] for a in proposal['assertions'])
    assert result['publication'] == 'unpublished' and vars(source) == original
    validate_result(result, [source], 'c603')
    corrupt = deepcopy(result)
    corrupt['binding']['proposal']['groups'][0]['assertion_ids'].pop()
    with pytest.raises((ValueError, AppException)):
        validate_result(corrupt, [source], 'c603')
    from app.modules.knowledge.services.compilation_manifest import validate_groups
    from app.modules.knowledge.services.wiki_compiler import digest
    manifest = deepcopy(proposal)
    manifest['groups'][0]['section_indices'].pop()
    g = manifest['groups'][0]
    g['id'] = 'group_' + digest([manifest['snapshot_hash'], {k:v for k,v in g.items() if k != 'id'}])[:24]
    with pytest.raises(AppException) as incomplete:
        validate_groups(manifest, result['binding']['evidence'])
    assert incomplete.value.details['reason'] == 'manifest_incomplete_coverage'


@pytest.mark.asyncio
async def test_capacity_failure_through_handler_has_explicit_stage_and_no_retry_or_publication():
    from unittest.mock import AsyncMock, patch

    from app.modules.knowledge.services import compilation_service as service
    from tests.test_compilation_lifecycle_603 import environment, request_body

    async with environment() as (client, _, cid, items, _, model, _):
        route = {'preferred_provider_id': 'fixture', 'preferred_model_name': 'fixture-model',
                 '_compiler_policy': {'max_manifest_objects': 1}}
        with patch.object(service, 'resolve_route', AsyncMock(return_value=route)):
            body = await request_body(client, cid, items, key='613-capacity')
            response = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert response.status_code == 422
            assert response.json()['code'] == 'KNOWLEDGE_COMPILATION_CAPACITY'
            records = (await client.get(f'/knowledge/collections/{cid}/compilations')).json()['items']
            blocked = records[0]
            assert blocked['status'] == 'capacity_blocked' and not blocked['resumable']
            assert blocked['failure_details']['stage'] == 'manifest'
            count = len(model.calls)
            repeat = await client.post(f'/knowledge/collections/{cid}/compilations', json=body)
            assert repeat.status_code == 200 and len(model.calls) == count
            assert repeat.json()['publication'] == 'unpublished'


@pytest.mark.asyncio
@pytest.mark.parametrize('verdict', ['supported', 'unresolved'])
async def test_partitioned_synthesis_review_keeps_raw_context_and_exact_global_coverage(verdict):
    from app.modules.knowledge.compilation_runtime_schemas import SynthesisCheck
    from app.modules.knowledge.services.compilation_synthesis import review_group
    from app.modules.knowledge.services.compilation_validation import check_synthesis

    proof = {'source_revision_id': 'source', 'quote': 'Raw source context ' * 180}
    assertions = [{'id': f'a{i}', 'entity_id': 'e', 'attribute': 'Metric', 'value': 'Source ' * 140,
        'value_state': 'present', 'evidence_ids': ['p'], 'temporal': [], 'scope': [],
        'condition_ids': ['p'], 'exception_ids': []} for i in range(16)]
    payload = {'topic': 'Source metrics', 'evidence': {'p': proof},
        'draft': {'snapshot_hash': 'a' * 64, 'entities': [{'id': 'e', 'label': 'Entity', 'evidence_ids': ['p']}],
                  'assertions': assertions}}
    synthesis = {'relations': [], 'sections': [{'heading': a['id'], 'text': a['value'],
        'assertion_ids': [a['id']]} for a in assertions]}
    calls = []
    async def bounded(contract, instruction, fragment):
        calls.append(fragment)
        assert fragment['evidence'] == payload['evidence']
        return contract(sections=[{'index': i, 'verdict': verdict, 'assertion_ids': s['assertion_ids'],
            'reason': 'Independent synthetic audit'} for i,s in enumerate(fragment['synthesis']['sections'])])
    policy = WikiPolicy()
    assert not engine.request_usage(SynthesisCheck, engine.VERIFY_SYNTHESIS,
                                    {**payload, 'synthesis': synthesis}, policy)['fits']
    reviewed = await review_group(payload, synthesis, bounded, engine.VERIFY_SYNTHESIS, policy)
    assert len(calls) > 1 and [s.index for s in reviewed.sections] == list(range(16))
    checked = check_synthesis(payload['draft'], synthesis, reviewed, payload['evidence'])
    assert checked['complete'] == (verdict == 'supported')


@pytest.mark.asyncio
async def test_provider_update_persists_capacity_and_old_forms_cannot_silently_clear_it():
    from uuid import uuid4

    from sqlalchemy import delete

    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.schemas import ProviderConfigUpdate
    from app.modules.modelops.services.provider_service import provider_service
    from tests.test_wiki_snapshot_integration_600 import fixture

    async with fixture() as (factory, _, _, _):
        provider_id = '613-capacity-' + uuid4().hex[:16]
        limits = {'endpoint': 'http://127.0.0.1:1/v1', 'context_window_tokens': 65536,
                  'max_output_tokens': 16384}
        async with factory() as db:
            db.add(ModelProviderConfig(id=provider_id, name='Owned capacity fixture', provider_type='custom',
                model_name='fixture', api_base_url=limits['endpoint'], is_active=False,
                extra_config={'models':['fixture'], 'model_capabilities':{
                    'fixture':ModelCapabilityConfig(token_limits=limits).model_dump(mode='json')}}))
            await db.commit()
            try:
                await provider_service.update_provider(db, provider_id, ProviderConfigUpdate(
                    model_capabilities={'fixture':ModelCapabilityConfig(reasoning=True)}))
                row = await db.get(ModelProviderConfig,provider_id,populate_existing=True)
                assert configured_token_limits(row.extra_config,'fixture',row.api_base_url)['max_output_tokens'] == 16384
                await provider_service.update_provider(db, provider_id, ProviderConfigUpdate(
                    model_capabilities={'fixture':ModelCapabilityConfig(token_limits=None)}))
                row = await db.get(ModelProviderConfig,provider_id,populate_existing=True)
                assert configured_token_limits(row.extra_config,'fixture',row.api_base_url) is None
            finally:
                await db.execute(delete(ModelProviderConfig).where(ModelProviderConfig.id==provider_id))
                await db.commit()


@pytest.mark.asyncio
async def test_cross_group_shared_names_require_raw_evidence_and_independent_verdict():
    from hashlib import sha256

    from app.modules.knowledge.compilation_runtime_schemas import (
        CrossRelationCheck,
        CrossRelationDraft,
    )
    from app.modules.knowledge.services.compilation_cross_source import validate_cross_ledger
    from app.modules.knowledge.services.source_artifact import build_source_artifact

    sources = [sample(1), sample(2)]
    for n, source in enumerate(sources):
        source.canonical_markdown = '\n\n'.join(
            f'{"Đơn vị" if n == 0 or i < 2 else "Khối riêng"} {i} có chỉ tiêu năm {2024 + n}: {i + 1}. '
            'Chỉ áp dụng nhóm A, ngoại lệ nhóm B.' for i in range(40))
        source.canonical_hash = sha256(source.canonical_markdown.encode()).hexdigest()
        source.parse_provenance['structured_artifact'] = build_source_artifact(source.canonical_markdown, 1, {})
    base = Model()
    calls, stages = [], MemoryStages()
    async def model(contract, instruction, payload):
        if contract is CrossRelationDraft:
            calls.append('proposal')
            assert len({p['source_revision_id'] for p in payload['evidence'].values()}) == 2
            left, right = payload['draft']['entities']
            return contract(relations=[{'id':'hypothesis','kind':'same_entity','source_id':left['id'],
                'target_id':right['id'],'evidence_ids':list(payload['evidence'])[:2]}])
        if contract is CrossRelationCheck:
            calls.append('review')
            return contract(items=[{'id':r['id'],'verdict':'unresolved','entity_scope':False,
                'temporal_roles':True,'conditions_complete':True,'evidence_ids':r['evidence_ids'],
                'reason':'Matching labels alone do not establish cross-source identity.'}
                for r in payload['synthesis']['relations']])
        return await base(contract,instruction,payload)
    policy = CompilerPolicy(max_calls=64,max_total_calls=128)
    for _ in range(3):
        try:
            result=await engine.compile_topic(sources,'c603','Chỉ tiêu theo nguồn',ACTOR,model,'cross-613',
                                               policy=policy,checkpoints=stages)
            break
        except AppException as exc:
            assert exc.code=='KNOWLEDGE_COMPILATION_PAUSED'
    else:
        raise AssertionError('Did not finish within bounded executions')
    assert calls==['proposal','review','proposal','review']
    assert len(result['binding']['proposal']['assertions'])==80
    assert not result['machine_complete'] and result['publication']=='unpublished'
    assert len(result['binding']['proposal']['relations'])==2
    assert all(r['verdict']=='unresolved' for r in result['synthesis_review']['relations'])
    assert any(g.get('kind')=='relations' for g in result['binding']['proposal']['groups'])
    validate_result(result,sources,'c603')
    bad=deepcopy(result['cross_source_review']);bad['examined'].pop()
    with pytest.raises(AppException):
        validate_cross_ledger(result['binding']['proposal'],result['binding']['evidence'],bad)


@pytest.mark.asyncio
@pytest.mark.parametrize('blocked_stage', ['review', 'direction'])
async def test_cross_relation_budget_deferral_keeps_candidate_without_effective_relation(blocked_stage):
    from unittest.mock import patch

    from app.modules.knowledge.compilation_runtime_schemas import (
        CrossRelationCheck,
        CrossRelationDraft,
        RelationDirections,
    )
    from app.modules.knowledge.services import compilation_cross_source as cross
    from app.modules.knowledge.services.compilation_contracts import evidence_catalog
    from app.modules.knowledge.services.wiki_compiler import digest

    sources=[sample(1),sample(2)]
    catalog=evidence_catalog(sources,'c603')
    proofs=[next(p for p,r in catalog.items() if r['source_revision_id']==s.id) for s in sources]
    proposal={'snapshot_hash':digest(catalog),
        'entities':[{'id':f'e{i}','label':'Shared source metric','evidence_ids':[p]} for i,p in enumerate(proofs)],
        'assertions':[{'id':f'a{i}','entity_id':f'e{i}','attribute':'Metric','value':catalog[p]['quote'],
            'value_state':'present','evidence_ids':[p],'temporal':[],'scope':[],
            'condition_ids':[],'exception_ids':[]} for i,p in enumerate(proofs)]}
    calls=[]
    async def bounded(contract,instruction,payload):
        calls.append(contract)
        if contract is CrossRelationDraft:
            return contract(relations=[{'id':'candidate','kind':'supports','source_id':'e0','target_id':'e1',
                                        'evidence_ids':proofs}])
        if contract is CrossRelationCheck and blocked_stage=='direction':
            return contract(items=[{'id':'candidate','verdict':'supported','entity_scope':True,
                'temporal_roles':True,'conditions_complete':True,'evidence_ids':proofs,'reason':'Synthetic review'}])
        raise AssertionError('A request known not to fit must never reach inference')
    actual=cross.request_budget
    def budget(contract,*args,**kwargs):
        value=actual(contract,*args,**kwargs)
        if contract is (CrossRelationCheck if blocked_stage=='review' else RelationDirections):
            return {**value,'fits':False}
        return value
    with patch.object(cross,'request_budget',side_effect=budget):
        result=await cross.review_cross_source('Source metric',proposal,catalog,{},WikiPolicy(),bounded,
                                               CompilerPolicy(),sources,'c603',ACTOR)
    assert result['relations']==[] and len(result['ledger']['pending'])==1
    assert len(result['ledger']['unverified_proposals'])==1
    assert result['ledger']['unverified_proposals'][0]['usage']=='candidate_only'
    assert not cross.validate_cross_ledger(proposal,catalog,result['ledger'])
