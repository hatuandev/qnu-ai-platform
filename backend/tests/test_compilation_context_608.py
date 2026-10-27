"""Empty drafts retain coverage debt; partial time never becomes a full date or no year."""
from copy import deepcopy

import pytest

from app.modules.knowledge.compilation_runtime_schemas import (
    CoverageAudit,
    PacketCheck,
    PacketDraft,
)
from app.modules.knowledge.services.compilation_engine import compile_topic
from app.modules.knowledge.services.compilation_validation import validate_result
from tests.test_compilation_engine_603 import ACTOR, Model, sample


class EmptyModel(Model):
    def __init__(self, roles, repair=True):
        super().__init__()
        self.roles, self.repair = iter(roles), repair
        self.empty_once = False
        self.coverage_inputs = []

    async def __call__(self, contract, instruction, payload):
        empty_source = next(iter(payload.get('evidence', {}).values()), {}).get('source_revision_id') == 's1'
        if contract is PacketDraft and empty_source and (not self.empty_once or not self.repair):
            self.calls.append('PacketDraft')
            self.empty_once = True
            return contract()  # Intentionally omits even the deferred ledger.
        if contract is PacketCheck and not payload['draft']['assertions']:
            raise AssertionError('An empty draft must go to coverage, never item verification')
        if contract is CoverageAudit:
            self.calls.append('CoverageAudit')
            self.coverage_inputs.append(deepcopy(payload))
            role = next(self.roles)
            return contract(items=[{'evidence_id': pid, 'role': role, 'assertion_ids': [],
                'reason': 'Independent coverage classification.'} for pid in payload['missed_evidence_ids']])
        return await super().__call__(contract, instruction, payload)


@pytest.mark.asyncio
async def test_empty_draft_reaches_two_coverage_audits_and_one_targeted_repair():
    sources = [sample(1), sample(2)]
    before = deepcopy([vars(s) for s in sources])
    model = EmptyModel(['required_assertion'] * 2)
    bundle = await compile_topic(sources, 'c603', 'Chỉ tiêu từng năm', ACTOR, model, '608')
    assert bundle['machine_complete'] and len(bundle['binding']['proposal']['assertions']) == 2
    assert model.calls.count('CoverageAudit') == 2 and model.calls.count('PacketDraft') == 3
    packet = bundle['packet_results'][0]
    assert packet['coverage_reconciliation']['initial_review']['items'] == []
    assert not packet['coverage_reconciliation']['initial_review']['complete']
    assert all(p['existing_assertions'] == [] for p in model.coverage_inputs)
    assert model.coverage_inputs[0]['missed_evidence_ids'] == packet['primary_evidence_ids']
    assert bundle['publication'] == 'unpublished' and bundle['usage'] == 'review_only'
    validate_result(bundle, sources, 'c603')
    assert [vars(s) for s in sources] == before


@pytest.mark.asyncio
@pytest.mark.parametrize('roles', [('unresolved', 'unresolved'), ('unrelated', 'required_assertion')])
async def test_empty_draft_coverage_disagreement_or_ambiguity_remains_incomplete(roles):
    model = EmptyModel(roles)
    bundle = await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu', ACTOR, model, '608')
    assert not bundle['machine_complete'] and model.calls.count('CoverageAudit') == 2
    packet = bundle['packet_results'][0]
    assert packet['review']['missed_evidence_ids'] == packet['primary_evidence_ids']
    assert packet['draft']['assertions'] == []


@pytest.mark.asyncio
async def test_repeated_empty_repair_keeps_required_omissions_without_recursive_model_calls():
    model = EmptyModel(['required_assertion'] * 2, repair=False)
    bundle = await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu', ACTOR, model, '608')
    assert not bundle['machine_complete']
    assert model.calls.count('CoverageAudit') == 2 and model.calls.count('PacketDraft') == 3
    assert bundle['packet_results'][0]['coverage_reconciliation']['remaining_evidence_ids']


@pytest.mark.asyncio
async def test_empty_packet_is_excluded_only_after_both_coverage_audits_agree_unrelated():
    model = EmptyModel(['unrelated'] * 2)
    sources = [sample(1), sample(2)]
    bundle = await compile_topic(sources, 'c603', 'Chỉ tiêu', ACTOR, model, '608')
    assert bundle['machine_complete']
    assert model.calls.count('CoverageAudit') == 2 and model.calls.count('PacketDraft') == 2
    assert len(bundle['binding']['proposal']['assertions']) == 1
    packet = bundle['packet_results'][0]
    assert len(packet['coverage_reconciliation']['accepted_context_or_unrelated']) == 1
    assert packet['review']['items'] == [] and packet['review']['missed_evidence_ids'] == []
    validate_result(bundle, sources, 'c603')


@pytest.mark.parametrize('role', ['data', 'publication', 'effective', 'event', None])
def test_review_targets_preserve_literal_year_without_filling_missing_date_or_assigning_role(role):
    from app.modules.knowledge.services.compilation_review import packet_review_payload
    from app.modules.knowledge.services.compilation_transport import prepare
    draft = PacketDraft(entities=[{'id':'e','label':'Source','evidence_ids':['p']}],
        assertions=[{'id':'a','entity_id':'e','attribute':'Complete date','value_state':'unknown','value':None,
            'evidence_ids':['p'], 'temporal': ([{'role':role,'years':[2033],'evidence_ids':['p']}] if role else [])}]).model_dump()
    payload = {'evidence': {'p': {'source_revision_id':'s','quote':'Ngày ... tháng ... năm 2033'}},
               'primary_evidence_ids':['p'], 'temporal_context':{'p':{'role':'data','years':[2033]}}}
    before = deepcopy((payload,draft))
    review = packet_review_payload(payload, draft, {})
    target = review['temporal_review_targets'][0]
    assert target['id'] == 'a' and target['claimed_scopes'] == draft['assertions'][0]['temporal']
    assert target['source_year_literals'] == [{'literal':'2033','evidence_ids':['p']}]
    assert 'temporal_context' not in review  # Navigation classifier is not an authored time claim.
    assert review['draft']['assertions'][0]['value'] is None
    _, wire, _ = prepare(PacketCheck,review)
    assert wire['temporal_review_targets'][0]['id'] == 'claim0'
    assert wire['temporal_review_targets'][0]['source_year_literals'][0]['evidence_ids'] == ['u0']
    assert (payload,draft) == before


def test_time_literal_hints_do_not_cross_to_other_offered_proofs_or_infer_a_role():
    from app.modules.knowledge.services.compilation_review import packet_review_payload
    draft = PacketDraft(entities=[{'id':'e','label':'Source','evidence_ids':['p']}],
        assertions=[{'id':'a','entity_id':'e','attribute':'Complete date','value_state':'unknown','value':None,
            'evidence_ids':['p']}]).model_dump()
    payload = {'evidence': {'p': {'source_revision_id':'s1','quote':'Date: ...'},
                            'other': {'source_revision_id':'s2','quote':'năm 2039'}}}
    target = packet_review_payload(payload,draft,{})['temporal_review_targets'][0]
    assert target['source_year_literals'] == [] and target['claimed_scopes'] == []


def test_review_protocol_change_invalidates_cached_packets_without_changing_model(monkeypatch):
    from app.modules.knowledge.services import compilation_review
    from app.modules.knowledge.services.compilation_modelops import configuration_hash
    route = {'preferred_provider_id':'fixture','preferred_model_name':'fixture'}
    before = configuration_hash(route,{})
    monkeypatch.setattr(compilation_review,'REVIEW_PROTOCOL',compilation_review.REVIEW_PROTOCOL+'/changed')
    assert configuration_hash(route,{}) != before
    assert route == {'preferred_provider_id':'fixture','preferred_model_name':'fixture'}


@pytest.mark.asyncio
async def test_separated_time_review_does_not_override_a_negative_temporal_verdict():
    from app.modules.knowledge.services.compilation_review import packet_review_payload
    from app.modules.knowledge.services.compilation_validation import check_packet
    draft = PacketDraft(entities=[{'id':'e','label':'Source','evidence_ids':['p']}],
        assertions=[{'id':'a','entity_id':'e','attribute':'Date','value_state':'unknown','value':None,
            'evidence_ids':['p']}]).model_dump()
    payload = packet_review_payload({'evidence':{'p':{'source_revision_id':'s','quote':'năm 2031'}}}, draft, {})
    review = PacketCheck(items=[{'id':'a','verdict':'supported','entity_scope':True,'temporal_roles':False,
        'conditions_complete':True,'evidence_ids':['p'],'reason':'Unsupported implicit time claim.'}])
    assert not check_packet(draft,review,['p'],payload['evidence'])['complete']
