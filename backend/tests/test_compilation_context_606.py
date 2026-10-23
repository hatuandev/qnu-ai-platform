"""Source limitations stay source-bound/null, and policy edits invalidate reuse.

Inference here is deterministic. Real Qwen relevance controls are separately recorded.
"""
import json
from copy import deepcopy

import pytest

from app.modules.knowledge.compilation_runtime_schemas import PacketDraft, SynthesisDraft
from app.modules.knowledge.services.compilation_engine import compile_topic
from app.modules.knowledge.services.compilation_validation import validate_result
from tests.test_compilation_engine_603 import ACTOR, Model, sample
from tests.test_foundation_602 import source


def test_default_packet_plan_leaves_output_headroom_without_discarding_selected_proofs():
    from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
    from app.modules.knowledge.services.compilation_contracts import evidence_catalog
    from app.modules.knowledge.services.compilation_engine import plan_packets
    item=source('\n\n'.join(f'Chỉ số {i}: {i+10}; áp dụng riêng nhóm {i}.' for i in range(12)))
    item.id,item.binding_id,item.collection_id='s606','b606','c606'
    catalog=evidence_catalog([item],'c606')
    assert len(catalog)==12
    packets=plan_packets('Các chỉ số theo nhóm',catalog,{},CompilerPolicy())
    assert max(len(p['primary_evidence_ids']) for p in packets)<=4
    assigned=[pid for p in packets for pid in p['primary_evidence_ids']]
    assert len(assigned)==len(set(assigned))==len(catalog) and set(assigned)==set(catalog)


@pytest.mark.parametrize('maximum',[1,2,4])
def test_packet_output_policy_splits_primary_work_and_keeps_dependency_proofs(maximum):
    from app.modules.knowledge.compilation_runtime_schemas import CompilerPolicy
    from app.modules.knowledge.services.compilation_contracts import evidence_catalog
    from app.modules.knowledge.services.compilation_engine import plan_packets
    item=source('\n\n'.join(f'Mục {i}: {i+1}.' for i in range(9)))
    item.id,item.binding_id,item.collection_id='s606','b606','c606'
    catalog=evidence_catalog([item],'c606');ids=list(catalog)
    dependencies={pid:[ids[0]] for pid in ids[1:]}
    packets=plan_packets('Các mục',catalog,dependencies,CompilerPolicy(max_primary_per_packet=maximum))
    assert all(len(p['primary_evidence_ids'])<=maximum for p in packets)
    assert {pid for p in packets for pid in p['primary_evidence_ids']}==set(ids)
    for packet in packets:
        if any(pid in dependencies for pid in packet['primary_evidence_ids']):
            assert ids[0] in packet['evidence']


@pytest.mark.parametrize('mutation',['missing_entities','foreign_entity','duplicate_entity','duplicate_assertion','orphan_entity'])
def test_packet_contract_rejects_invalid_local_entity_graph_before_semantic_review(mutation):
    from pydantic import ValidationError
    data={'entities':[{'id':'e1','label':'Văn bản','evidence_ids':['p1']}],
        'assertions':[{'id':'a1','entity_id':'e1','attribute':'Ngày đầy đủ','value_state':'unknown',
                       'value':None,'evidence_ids':['p1']}], 'deferred_evidence_ids':[]}
    if mutation=='missing_entities':data['entities']=[]
    if mutation=='foreign_entity':data['assertions'][0]['entity_id']='p1'
    if mutation=='duplicate_entity':data['entities']*=2
    if mutation=='duplicate_assertion':data['assertions']*=2
    if mutation=='orphan_entity':data['assertions']=[]
    with pytest.raises(ValidationError):
        PacketDraft.model_validate(data)


@pytest.mark.parametrize(('state','value','code'),[
    ('present',None,'compilation_present_requires_scalar'),
    ('present','  ','compilation_present_requires_scalar'),
    ('unknown','0','compilation_unresolved_cannot_hold_scalar'),
    ('conflict','unclear','compilation_unresolved_cannot_hold_scalar'),
])
def test_scalar_state_rejection_has_actionable_code_without_source_text(state,value,code):
    from pydantic import ValidationError

    from app.modules.knowledge.compilation_schemas import CompilationAssertion
    with pytest.raises(ValidationError) as error:
        CompilationAssertion(id='a',entity_id='e',attribute='field',value=value,value_state=state,evidence_ids=['p'])
    assert error.value.errors(include_input=False)[0]['type']==code


@pytest.mark.asyncio
async def test_invalid_local_graph_is_known_adapter_contract_error_without_retry_or_raw_output_leak():
    from unittest.mock import AsyncMock, patch

    from app.core.exceptions import AppException
    from app.modules.knowledge.services.wiki_build import generate_object
    from app.modules.knowledge.wiki_schemas import WikiPolicy
    from app.modules.modelops.schemas import LLMGenerateResponse
    raw={'entities':[],'assertions':[{'id':'claim','entity_id':'proof-handle','attribute':'PRIVATE_FIELD',
        'value_state':'unknown','value':None,'evidence_ids':['p1']}]}
    response=LLMGenerateResponse(content=json.dumps(raw),provider='fixture',model='fixture',finish_reason='stop')
    generate=AsyncMock(return_value=response)
    with (patch('app.modules.modelops.service.modelops_service.generate',generate),
          pytest.raises(AppException) as error):
        await generate_object(None,'default',{'preferred_provider_id':'fixture'},WikiPolicy(),[],
                              PacketDraft,'Instruction',{})
    assert error.value.code=='KNOWLEDGE_WIKI_INVALID'
    assert 'compilation_packet_entity_missing' in str(error.value.details)
    assert 'PRIVATE_FIELD' not in repr(error.value.details)
    generate.assert_awaited_once()


class UnknownModel(Model):
    async def __call__(self, contract, instruction, payload):
        if contract is PacketDraft:
            self.calls.append(contract.__name__)
            pid=payload['primary_evidence_ids'][0]
            return contract(entities=[{'id':'document','label':'Văn bản nguồn','evidence_ids':[pid]}],
                assertions=[{'id':'missing','entity_id':'document','attribute':'Trường chưa xác định',
                    'value_state':'unknown','value':None,'evidence_ids':[pid],
                    'temporal':[{'role':'unknown','years':[],'evidence_ids':[]}]}])
        if contract is SynthesisDraft:
            self.calls.append(contract.__name__)
            return contract(sections=[{'heading':'Giới hạn nguồn','text':'Nguồn chưa xác định trường được hỏi.',
                'assertion_ids':[a['id'] for a in payload['draft']['assertions']]}])
        return await super().__call__(contract,instruction,payload)


@pytest.mark.asyncio
@pytest.mark.parametrize('literal',[
    'Ngày ban hành: ngày     tháng      năm 2032.',
    'Mức tối đa: — (chưa được nguồn xác định).',
    'Ký hiệu ◇ chưa có phần định nghĩa trong nguồn.',
    'Khoảng áp dụng: từ ngày ... đến ngày ...; chỉ có năm tham khảo 2034.',
])
async def test_explicit_source_limitation_survives_compilation_and_reload_without_scalar_or_invented_time(literal):
    item=source(literal)
    item.id,item.binding_id,item.collection_id='source606','binding606','collection606'
    before=deepcopy(vars(item))
    result=await compile_topic([item],'collection606','Trường nào chưa được nguồn xác định?',ACTOR,UnknownModel(),'config606')
    reloaded=json.loads(json.dumps(result))
    validate_result(reloaded,[item],'collection606')
    assertion=reloaded['binding']['proposal']['assertions'][0]
    assert assertion['value'] is None and assertion['value_state']=='unknown'
    assert assertion['temporal']==[{'role':'unknown','years':[],'evidence_ids':[]}]
    assert reloaded['binding']['evidence'][assertion['evidence_ids'][0]]['quote']==literal
    assert reloaded['machine_complete'] and reloaded['usage']=='review_only' and reloaded['publication']=='unpublished'
    assert reloaded['binding']['semantic_verification']=='not_run'
    assert vars(item)==before


@pytest.mark.asyncio
async def test_unknown_value_does_not_override_unresolved_evidence_review():
    item=source('Ngày ban hành: ngày ... tháng ... năm 2031.')
    item.id,item.binding_id,item.collection_id='source606','binding606','collection606'
    model=UnknownModel();model.unresolved=True
    result=await compile_topic([item],'collection606','Ngày ban hành đầy đủ là gì?',ACTOR,model,'config606')
    assert not result['machine_complete']
    assert result['packet_results'][0]['review']['items'][0]['verdict']=='unresolved'
    assert result['binding']['proposal']['assertions'][0]['value'] is None


@pytest.mark.asyncio
@pytest.mark.parametrize('changed',['source_limitations','extraction_instruction'])
async def test_source_limitation_policy_change_invalidates_cached_extractions_and_keeps_previous_bundle(monkeypatch,changed):
    from app.modules.knowledge.services import compilation_modelops as modelops
    route={'preferred_provider_id':'fixture','preferred_model_name':'fixture-model'}
    before_hash=modelops.configuration_hash(route,{})
    model=Model();items=[sample()]
    first=await compile_topic(items,'c603','Chỉ tiêu',ACTOR,model,before_hash)
    saved=deepcopy(first)
    cache={p['key']:p for p in [*first['packet_results'],*first['topic_results']]}
    if changed=='source_limitations':
        monkeypatch.setattr(modelops,'SOURCE_LIMITATIONS',modelops.SOURCE_LIMITATIONS+'\nChanged policy text.')
    else:
        from app.modules.knowledge.services import compilation_engine as instructions
        monkeypatch.setattr(instructions,'DRAFT',instructions.DRAFT+'\nChanged extraction instruction.')
    after_hash=modelops.configuration_hash(route,{})
    assert before_hash!=after_hash
    second=await compile_topic(items,'c603','Chỉ tiêu',ACTOR,model,after_hash,cache)
    assert second['reused_packets']==0 and second['reused_topic_packets']==0
    assert first==saved


def test_model_value_state_alias_is_round_tripped_without_changing_raw_text_or_temporal_unknown():
    from app.modules.knowledge.services.compilation_transport import prepare, restore
    payload={'evidence':{'p1':{'quote':'unknown source_unspecified unresolved'}},
        'draft':{'entities':[], 'assertions':[{'id':'a1','entity_id':'e1','attribute':'unknown',
            'value_state':'unknown','value':None,'evidence_ids':['p1'],
            'temporal':[{'role':'unknown','years':[],'evidence_ids':[]}]}]}}
    before=deepcopy(payload)
    _,wire,reverse=prepare(PacketDraft,payload)
    assert wire['draft']['assertions'][0]['value_state']=='source_unspecified'
    assert wire['draft']['assertions'][0]['temporal'][0]['role']=='unknown'
    assert wire['evidence']['u0']['quote']==payload['evidence']['p1']['quote']
    assert wire['draft']['assertions'][0]['attribute']=='unknown'
    assert restore(wire,reverse)==payload and payload==before


@pytest.mark.parametrize(('state','value','accepted'),[
    ('source_unspecified',None,True),('source_unspecified','0',False),
    ('present','0',True),('present',None,False),('unknown',None,False),
    ('unresolved',None,False),('conflict',None,True),
])
def test_model_assertion_schema_separates_source_unspecified_from_review_verdict(state,value,accepted):
    from pydantic import ValidationError

    from app.modules.knowledge.services.compilation_transport import prepare, restore
    contract,_,reverse=prepare(PacketDraft,{'evidence':{'p1':{'quote':'Unspecified field'}}})
    raw={'entities':[{'id':'e','label':'Source','evidence_ids':['u0']}],
        'assertions':[{'id':'a','entity_id':'e','attribute':'field','value_state':state,
            'value':value,'evidence_ids':['u0']}]}
    if not accepted:
        with pytest.raises(ValidationError):contract.model_validate(raw)
        return
    result=PacketDraft.model_validate(restore(contract.model_validate(raw).model_dump(),reverse))
    expected='unknown' if state=='source_unspecified' else state
    assert result.assertions[0].value_state==expected and result.assertions[0].value==value


@pytest.mark.asyncio
async def test_model_adapter_restores_legacy_state_before_durable_contract_validation(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.knowledge.services import compilation_modelops as modelops
    session=MagicMock();session.__aenter__=AsyncMock(return_value=None);session.__aexit__=AsyncMock()
    monkeypatch.setattr('app.core.database.AsyncSessionFactory',lambda:session)
    async def generated(db,tenant,route,policy,metrics,contract,instruction,payload):
        assert 'source_unspecified' in instruction
        metrics.append({'finish_reason':'stop'})
        return contract(entities=[{'id':'e','label':'Source','evidence_ids':['u0']}],
            assertions=[{'id':'a','entity_id':'e','attribute':'field','value_state':'source_unspecified',
                'value':None,'evidence_ids':['u0']}])
    monkeypatch.setattr(modelops,'generate_object',generated)
    result=await modelops.generator({},'default',[])(PacketDraft,'Extract',{'evidence':{'p1':{'quote':'blank'}}})
    assert result.assertions[0].value_state=='unknown' and result.assertions[0].evidence_ids==['p1']


def test_empty_draft_review_rejects_invented_items_and_keeps_missed_evidence():
    from pydantic import ValidationError

    from app.modules.knowledge.compilation_runtime_schemas import PacketCheck
    from app.modules.knowledge.services.compilation_transport import prepare, restore
    from app.modules.knowledge.services.compilation_validation import check_packet
    draft={'entities':[],'assertions':[],'deferred_evidence_ids':['p1']}
    evidence={'p1':{'source_revision_id':'s606','quote':'Metric: 37'}}
    contract,_,reverse=prepare(PacketCheck,{'draft':draft,'evidence':evidence})
    with pytest.raises(ValidationError):
        contract(items=[{'id':'invented','verdict':'supported','evidence_ids':['u0'],
            'conditions_complete':True,'reason':'Must not invent an assertion check'}])
    review=PacketCheck.model_validate(restore(contract(items=[],missed_evidence_ids=['u0']).model_dump(),reverse))
    result=check_packet(draft,review,['p1'],evidence)
    assert result['missed_evidence_ids']==['p1'] and not result['complete']
