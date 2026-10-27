"""Persistence checks distinguish semantic replacement from subsequent coverage additions."""
import json
from copy import deepcopy

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import (
    CoverageAudit,
    PacketCheck,
    PacketCoverage,
)
from app.modules.knowledge.services.compilation_candidate_repair import PROTOCOL
from app.modules.knowledge.services.compilation_coverage import reconcile
from app.modules.knowledge.services.compilation_grounding import materialize_packet
from app.modules.knowledge.services.compilation_review import review_packet
from app.modules.knowledge.services.compilation_validation import (
    check_packet,
    validate_grounded_coverage,
    validate_semantic_repair,
)
from tests.test_compilation_grounding_616 import selected
from tests.test_compilation_metrics_615 import no_network  # noqa: F401


def payload():
    return {'topic':'Chỉ tiêu và thời điểm công bố','primary_evidence_ids':['value','date'],
        'evidence':{'value':{'quote':'Viện Alpha: Chỉ tiêu 416.', 'source_revision_id':'s',
            'structural_evidence':{'role':'paragraph'}},
            'date':{'quote':'Thông báo năm 2029.', 'source_revision_id':'s',
                'structural_evidence':{'role':'paragraph'}}}}


async def packet(offered, *, empty=False, contradicted=False, key='initial'):
    if empty:
        draft={'entities':[],'assertions':[],'deferred_evidence_ids':list(offered['primary_evidence_ids'])}
    else:
        pid=offered['primary_evidence_ids'][0]
        phrase='Viện Alpha' if pid=='value' else 'Thông báo năm'
        metric='Chỉ tiêu' if pid=='value' else phrase
        scalar='416' if pid=='value' else '2029'
        draft=materialize_packet({'claims':[{'id':key,'subject':selected(offered['evidence'],pid,phrase),
            'metric':selected(offered['evidence'],pid,metric),'scalar':selected(offered['evidence'],pid,scalar),
            'value_state':'present'}]},offered)
        used={p for a in draft['assertions'] for p in a['evidence_ids']}
        draft['deferred_evidence_ids']=sorted(set(offered['primary_evidence_ids'])-used)
    async def audit(contract,instruction,request):
        if contract is PacketCoverage:
            return contract(missed_evidence_ids=['date'] if 'value' in offered['primary_evidence_ids'] and len(offered['primary_evidence_ids'])>1 else [],
                reason='The source date remains a distinct relevant assertion.')
        assert contract is PacketCheck
        return contract(items=[{'id':a['id'],'verdict':'contradicted' if contradicted else 'supported',
            'entity_scope':True,'temporal_roles':True,'conditions_complete':True,'evidence_ids':a['evidence_ids'],
            'reason':'The source-bound assertion was independently checked.'} for a in draft['assertions']])
    ledger={}
    check=await review_packet(offered,draft,{},audit,'Independent truth review',record_coverage=ledger.update)
    return {'key':key,'draft':draft,'primary_evidence_ids':offered['primary_evidence_ids'],
        'column_role_reviews':{},'coverage_review':ledger,
        'review':check_packet(draft,check,offered['primary_evidence_ids'],offered['evidence'],column_roles={})}


async def complete_coverage(initial, offered):
    async def classify(contract,instruction,request):
        assert contract is CoverageAudit
        return contract(items=[{'evidence_id':p,'role':'required_assertion','assertion_ids':[],
            'reason':'This literal source statement needs its own assertion.'} for p in request['missed_evidence_ids']])
    async def extract(request,key):
        return await packet(request,key='added')
    return await reconcile(offered,initial,classify,extract,'scope623',column_roles={})


@pytest.mark.asyncio
async def test_empty_draft_records_all_primary_debt_and_readback_after_grounded_repair():
    offered=payload()
    offered['primary_evidence_ids']=['date']
    initial=await packet(offered,empty=True)
    assert not initial['review']['complete']
    result=await complete_coverage(initial,offered)
    assert result['review']['complete']
    validate_grounded_coverage(result,offered['evidence'])


@pytest.mark.asyncio
async def test_rejected_semantic_candidate_stays_rejected_when_coverage_adds_a_different_fact():
    offered=payload()
    initial=await packet(offered,contradicted=True)
    rejected=deepcopy(initial)
    rejected['semantic_repair']={'protocol':PROTOCOL,'outcome':'unchanged','initial':deepcopy(initial),
        'candidate':deepcopy(initial)}
    result=await complete_coverage(rejected,offered)
    assert not result['review']['complete']
    assert result['draft']['assertions'][0]==initial['draft']['assertions'][0]
    validate_grounded_coverage(result,offered['evidence'])
    validate_semantic_repair(result,offered['evidence'],{'native_table_evidence':{},'source_structure':{}})


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation',['drop_debt','fake_review','wrong_hash','changed_old_fact','changed_added_fact'])
async def test_stage_ledger_tampering_is_rejected(mutation):
    offered=payload()
    initial=await packet(offered,contradicted=True)
    initial['semantic_repair']={'protocol':PROTOCOL,'outcome':'unchanged','initial':deepcopy(initial),
        'candidate':deepcopy(initial)}
    result=json.loads(json.dumps(await complete_coverage(initial,offered)))
    if mutation=='drop_debt':result['coverage_review']['missed_evidence_ids']=[]
    elif mutation=='fake_review':result['coverage_review']['reviews']=[]
    elif mutation=='wrong_hash':result['coverage_review']['assertions_hash']='0'*64
    elif mutation=='changed_old_fact':result['draft']['assertions'][0]['value']='999'
    else:result['draft']['assertions'][-1]['value']='2030'
    with pytest.raises(AppException) as failure:
        validate_grounded_coverage(result,offered['evidence'])
        validate_semantic_repair(result,offered['evidence'],{'native_table_evidence':{},'source_structure':{}})
    expected={'drop_debt':'coverage_verdict_drift','fake_review':'coverage_primary_partition_drift',
        'wrong_hash':'coverage_assertion_scope_drift','changed_old_fact':'coverage_assertion_scope_drift',
        'changed_added_fact':'coverage_added_candidate_drift'}
    assert failure.value.details['reason']==expected[mutation]
