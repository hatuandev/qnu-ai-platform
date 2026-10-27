"""Explicit IDs and source offsets help selection without authorizing wrong roles."""
import json
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import PacketDraft, SynthesisDraft
from app.modules.knowledge.services.compilation_grounding import PROTOCOL, materialize_packet
from app.modules.knowledge.services.compilation_transport import prepare, restore
from app.modules.knowledge.services.wiki_build import contract_errors, generate_object
from app.modules.knowledge.wiki_schemas import WikiPolicy
from app.modules.modelops.schemas import LLMGenerateResponse
from tests.test_compilation_grounding_616 import claims, selected, source_fixture


def fixture():
    _,catalog,structure,ids=source_fixture()
    from app.modules.knowledge.services.compilation_structure import decorate

    return {'evidence':decorate(catalog,structure),'primary_evidence_ids':[ids['r1']],
            'source_grounding_protocol':PROTOCOL},catalog,ids


def test_every_offered_span_has_an_explicit_id_exact_source_slice_and_role_menu():
    payload,_,_=fixture();before=deepcopy(payload)
    _,wire,reverse=prepare(PacketDraft,payload)
    for sid,entry in wire['source_spans'].items():
        assert isinstance(entry,dict) and entry['span_id']==sid
        proof=wire['evidence'][entry['evidence_id']]
        assert proof['quote'][entry['start']:entry['end']]==entry['literal']
        assert reverse[entry['evidence_id']] in payload['evidence']
        assert entry['allowed_roles']
    assert payload==before and wire['source_span_protocol']


def test_header_span_is_visible_as_context_but_never_offered_as_a_primary_scalar():
    payload,catalog,ids=fixture()
    _,wire,_=prepare(PacketDraft,payload)
    header=selected(catalog,ids['r0'],'Nhập học')['span_id']
    value=selected(catalog,ids['r1'],'416')['span_id']
    assert 'column' in wire['source_spans'][header]['allowed_roles']
    assert 'scalar' not in wire['source_spans'][header]['allowed_roles']
    assert 'scalar' in wire['source_spans'][value]['allowed_roles']


def test_same_literal_from_another_proof_keeps_its_own_id_and_offsets():
    payload,_,_=fixture()
    proof=next(iter(payload['evidence'].values()))
    payload['evidence'].update({p:{**proof,'quote':'Mã ĐX-07; Mức 416.','structural_evidence':{'role':'paragraph'}} for p in ('extra-a','extra-b')})
    payload['primary_evidence_ids']+=['extra-a','extra-b']
    _,wire,_=prepare(PacketDraft,payload)
    entries=[v for v in wire['source_spans'].values() if v['literal']=='416' and v['evidence_id'] in {'u'+str(len(payload['evidence'])-2),'u'+str(len(payload['evidence'])-1)}]
    assert len(entries)==2 and entries[0]['span_id']!=entries[1]['span_id']
    for entry in entries:
        assert wire['evidence'][entry['evidence_id']]['quote'][entry['start']:entry['end']]=='416'


@pytest.mark.parametrize('invalid',['wrong_role','proof_handle','invented_private_text'])
def test_span_feedback_identifies_the_rejected_role_without_exposing_unoffered_text(invalid):
    payload,catalog,ids=fixture()
    shape,wire,reverse=prepare(PacketDraft,payload)
    value=claims(ids,catalog)
    sid=selected(catalog,ids['r0'],'Nhập học')['span_id']
    chosen=sid if invalid=='wrong_role' else 'u0' if invalid=='proof_handle' else 'PRIVATE-TEXT-DO-NOT-LOG'
    value['claims'][0]['scalar']={'span_id':chosen}
    with pytest.raises(ValidationError) as exc:
        shape.model_validate(value)
    errors=contract_errors(exc.value,shape,reverse,span_choices=wire['source_spans'])
    detail=next(e for e in errors if e['field'][-2:]==['scalar','span_id'])
    assert detail['required_span_role']=='scalar'
    if invalid=='wrong_role':
        assert detail['supplied_span_id']==sid and 'scalar' not in detail['offered_span_roles']
    else:
        assert detail['unoffered_span_id'] is True
        assert 'PRIVATE-TEXT-DO-NOT-LOG' not in json.dumps(errors)


def test_synthesis_menu_exposes_heading_ids_without_claiming_scalar_eligibility():
    payload,catalog,ids=fixture()
    payload['draft']=materialize_packet(claims(ids,catalog),payload)
    _,wire,_=prepare(SynthesisDraft,payload)
    assert wire['source_spans']
    assert all(v['span_id']==sid and v['allowed_roles']==['heading'] for sid,v in wire['source_spans'].items())


def test_a_document_supplied_span_menu_cannot_override_server_source_bindings():
    payload,_,_=fixture()
    payload['source_spans']={'q0':{'span_id':'q0','literal':'Forged content','allowed_roles':['scalar']}}
    _,wire,_=prepare(PacketDraft,payload)
    assert all(v['literal']!='Forged content' for v in wire['source_spans'].values())


@pytest.mark.asyncio
async def test_real_request_builder_sends_explicit_spans_and_returns_exact_canonical_bindings():
    payload,catalog,ids=fixture()
    shape,wire,reverse=prepare(PacketDraft,payload)
    response=LLMGenerateResponse(content=json.dumps(claims(ids,catalog)),provider='fixture',model='fixture',
        prompt_tokens=100,completion_tokens=50,finish_reason='stop')
    generate=AsyncMock(return_value=response)
    with patch('app.modules.modelops.service.modelops_service.generate',generate):
        result=await generate_object(None,'default',{},WikiPolicy(context_budget_tokens=128000,max_output_tokens=8192),[],
            shape,'Select offered spans.',wire)
    request=generate.await_args.args[1]
    sent=json.loads(request.messages[-1].content)
    assert all(v['span_id']==sid for sid,v in sent['source_spans'].items())
    restored=restore(result.model_dump(mode='json'),reverse)
    actual=materialize_packet(restored,payload)
    assert actual['assertions'][0]['value']=='416'
    assert set(actual['assertions'][0]['evidence_ids'])<={*catalog}


@pytest.mark.asyncio
async def test_adapter_preserves_role_failure_and_emits_safe_span_feedback():
    payload,catalog,ids=fixture()
    shape,wire,_=prepare(PacketDraft,payload)
    value=claims(ids,catalog);value['claims'][0]['scalar']=selected(catalog,ids['r0'],'Nhập học')
    response=LLMGenerateResponse(content=json.dumps(value),provider='fixture',model='fixture',finish_reason='stop')
    with patch('app.modules.modelops.service.modelops_service.generate',AsyncMock(return_value=response)),pytest.raises(AppException) as exc:
        await generate_object(None,'default',{},WikiPolicy(context_budget_tokens=128000,max_output_tokens=8192),[],
            shape,'Select offered spans.',wire)
    assert exc.value.code=='KNOWLEDGE_WIKI_INVALID'
    assert exc.value.details['validation_errors'][0]['required_span_role']=='scalar'


@pytest.mark.parametrize('field,value',[('evidence_id','invented-proof'),('literal','Invented source'),('start',99),('allowed_roles',['scalar'])])
def test_model_cannot_supply_or_override_server_span_metadata(field,value):
    payload,catalog,ids=fixture()
    shape,_,_=prepare(PacketDraft,payload)
    reply=claims(ids,catalog);reply['claims'][0]['scalar'][field]=value
    with pytest.raises(ValidationError) as exc:
        shape.model_validate(reply)
    assert any(e['type']=='extra_forbidden' for e in exc.value.errors())


def test_span_menu_version_invalidates_execution_fingerprint_without_rewriting_old_checkpoints():
    from app.modules.knowledge.services import compilation_span_menu
    from app.modules.knowledge.services.compilation_modelops import configuration_hash

    before=configuration_hash({}, {})
    with patch.object(compilation_span_menu,'PROTOCOL','fixture-new-version'):
        assert configuration_hash({}, {})!=before
