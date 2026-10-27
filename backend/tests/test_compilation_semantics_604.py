"""Source/year isolation, directed relations and honest coverage reconciliation."""
from copy import deepcopy

import pytest

from app.modules.knowledge.compilation_runtime_schemas import POLICY, PacketCheck, SynthesisCheck
from app.modules.knowledge.services.compilation_validation import check_packet, check_synthesis


def item(aid='a1', pid='p1', year=2024):
    return {'id': aid, 'entity_id': 'e1', 'attribute': 'Chỉ tiêu', 'value': '100',
        'value_state': 'present', 'unit': None, 'evidence_ids': [pid], 'condition_ids': [],
        'exception_ids': [], 'scope': [],
        'temporal': [{'role': 'data', 'years': [year], 'evidence_ids': [pid]}]}


def supported(assertion):
    return {'id': assertion['id'], 'verdict': 'supported', 'entity_scope': True,
        'temporal_roles': True, 'conditions_complete': True, 'evidence_ids': assertion['evidence_ids'],
        'reason': 'Fixture reviewer claims support; server still checks source invariants.'}


def section_check(assertions):
    return SynthesisCheck(sections=[{'index': 0, 'verdict': 'supported',
        'assertion_ids': [a['id'] for a in assertions], 'reason': 'Fixture positive semantic verdict.'}])


def test_unproved_compound_scope_cannot_be_supported_by_title_and_reviewer_boolean():
    assertion = item()
    assertion['scope'] = [{'dimension': 'source_status', 'value': 'phương hướng; dự thảo', 'evidence_ids': ['p1']}]
    result = check_packet({'assertions': [assertion], 'deferred_evidence_ids': []},
        PacketCheck(items=[supported(assertion)]), ['p1'],
        {'p1': {'source_revision_id': 's1', 'quote': 'Phương hướng tuyển sinh năm 2024: 100'}})
    assert result['complete'] is False


@pytest.mark.parametrize('different_source', [True, False])
def test_supported_section_cannot_mix_source_or_data_year_scope(different_source):
    assertions = [item(), item('a2', 'p2', 2025 if not different_source else 2024)]
    synthesis = {'relations': [], 'sections': [{'heading': 'Năm 2024', 'text': '100',
        'assertion_ids': ['a1', 'a2']}]}
    catalog = {'p1': {'source_revision_id': 's1', 'quote': 'Năm 2024: 100'},
        'p2': {'source_revision_id': 's2' if different_source else 's1', 'quote': 'Năm 2025: 100'}}
    result = check_synthesis({'assertions': assertions}, synthesis, section_check(assertions), catalog)
    assert result['complete'] is False


def test_heading_cannot_invent_a_year_absent_from_its_assertion_scopes():
    assertion = item()
    synthesis = {'relations': [], 'sections': [{'heading': 'Năm 2027', 'text': '100', 'assertion_ids': ['a1']}]}
    result = check_synthesis({'assertions': [assertion]}, synthesis, section_check([assertion]),
        {'p1': {'source_revision_id': 's1', 'quote': 'Năm 2024: 100'}})
    assert result['complete'] is False


@pytest.mark.parametrize('value', ['Dự thảo', 'nhóm A', '2024'])
def test_atomic_literal_scope_preserves_source_spelling(value):
    assertion = item()
    assertion['scope'] = [{'dimension': 'scope', 'value': value, 'evidence_ids': ['p1']}]
    result = check_packet({'assertions': [assertion], 'deferred_evidence_ids': []},
        PacketCheck(items=[supported(assertion)]), ['p1'],
        {'p1': {'source_revision_id': 's1', 'quote': 'Dự thảo, nhóm A năm 2024: 100'}})
    assert result['complete']


def test_publication_and_data_time_roles_can_coexist_without_merging_years():
    assertions = [item(), item('issued', 'date')]
    assertions[1]['temporal'] = [{'role': 'publication', 'years': [2023], 'evidence_ids': ['date']}]
    synthesis = {'relations': [], 'sections': [{'heading': 'Dữ liệu 2024; ban hành 2023',
        'text': '100', 'assertion_ids': ['a1', 'issued']}]}
    result = check_synthesis({'assertions': assertions}, synthesis, section_check(assertions),
        {'p1': {'source_revision_id': 's1', 'quote': 'Năm 2024: 100'},
         'date': {'source_revision_id': 's1', 'quote': 'Ban hành 2023'}})
    assert result['complete']


@pytest.mark.parametrize('proposed_new_first', [True, False])
def test_supersedes_direction_must_agree_with_blind_source_witness(proposed_new_first):
    from app.modules.knowledge.compilation_runtime_schemas import RelationDirections
    from app.modules.knowledge.services.compilation_semantics import (
        check_directions,
        direction_payload,
    )
    new, old = item('new'), item('old', 'p2')
    group = {'relations': [{'id': 'r', 'kind': 'supersedes',
        'source_id': 'new' if proposed_new_first else 'old', 'target_id': 'old' if proposed_new_first else 'new'}]}
    evidence = {'p1': {'source_revision_id': 's1', 'quote': 'Mức mới 100 thay mức cũ 90.'}}
    payload = direction_payload({'assertions': [new, old]}, group, evidence)
    assert payload['pairs'] == [{'id': 'r', 'kind': 'supersedes', 'endpoint_set': {'new': True, 'old': True}}]
    assert 'source_id' not in payload['pairs'][0] and 'target_id' not in payload['pairs'][0]
    witness = RelationDirections(items=[{'id': 'r', 'verdict': 'supported', 'source_id': 'new',
        'target_id': 'old', 'evidence_ids': ['p1'], 'reason': 'Explicit source replacement clause.'}])
    result = check_directions(group, witness, evidence)
    assert result['complete'] is proposed_new_first


def test_blind_endpoint_membership_survives_transport_without_encoding_proposed_direction():
    from app.modules.knowledge.compilation_runtime_schemas import RelationDirections
    from app.modules.knowledge.services.compilation_semantics import direction_payload
    from app.modules.knowledge.services.compilation_transport import mapped, prepare
    assertions = [item('new'), item('old', 'p2')]
    evidence = {'p1': {'source_revision_id': 's1', 'quote': '100 thay thế 90.'}}
    relation = {'id': 'r', 'kind': 'supersedes', 'source_id': 'new', 'target_id': 'old'}
    payload = direction_payload({'assertions': assertions}, {'relations': [relation]}, evidence)
    reversed_payload = direction_payload({'assertions': assertions}, {'relations': [
        {**relation, 'source_id': 'old', 'target_id': 'new'}]}, evidence)
    assert payload == reversed_payload
    contract, wire, reverse = prepare(RelationDirections, payload)
    assert wire['pairs'][0]['endpoint_set'] == {'claim0': True, 'claim1': True}
    assert mapped(wire, reverse) == payload
    witness = contract.model_validate({'items': [{'id': 'rel0', 'verdict': 'supported',
        'source_id': 'claim0', 'target_id': 'claim1', 'evidence_ids': ['u0'], 'reason': 'Raw replacement clause.'}]})
    restored = RelationDirections.model_validate(mapped(witness.model_dump(), reverse))
    assert (restored.items[0].source_id, restored.items[0].target_id) == ('new', 'old')


@pytest.mark.parametrize('verdict', ['unresolved', 'contradicted'])
def test_later_date_does_not_prove_supersession(verdict):
    from app.modules.knowledge.compilation_runtime_schemas import RelationDirections
    from app.modules.knowledge.services.compilation_semantics import check_directions
    group = {'relations': [{'id': 'r', 'kind': 'supersedes', 'source_id': 'new', 'target_id': 'old'}]}
    witness = RelationDirections(items=[{'id': 'r', 'verdict': verdict, 'reason': 'Dates without a replacement clause.'}])
    assert not check_directions(group, witness, {})['complete']


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'foreign_proof', 'self'])
def test_direction_review_cannot_omit_duplicate_or_invent_proofs(mutation):
    from app.core.exceptions import AppException
    from app.modules.knowledge.compilation_runtime_schemas import RelationDirections
    from app.modules.knowledge.services.compilation_semantics import check_directions
    group = {'relations': [{'id': 'r', 'kind': 'supersedes', 'source_id': 'new', 'target_id': 'old'}]}
    entry = {'id': 'r', 'verdict': 'supported', 'source_id': 'new', 'target_id': 'old',
             'evidence_ids': ['p1'], 'reason': 'Fixture.'}
    entries = [entry]
    if mutation == 'duplicate': entries *= 2
    if mutation == 'missing': entries = []
    if mutation == 'foreign_proof': entry['evidence_ids'] = ['foreign']
    if mutation == 'self': group['relations'][0]['target_id'] = 'new'
    if mutation == 'self':
        assert not check_directions(group, RelationDirections(items=entries), {'p1': {}})['complete']
    else:
        with pytest.raises(AppException):
            check_directions(group, RelationDirections(items=entries), {'p1': {}})


def test_scope_cannot_assemble_a_literal_from_different_proofs():
    assertion = item()
    assertion['evidence_ids'] = ['p1', 'p2']
    assertion['scope'] = [{'dimension': 'status', 'value': 'Bản dự thảo', 'evidence_ids': ['p1', 'p2']}]
    result = check_packet({'assertions': [assertion], 'deferred_evidence_ids': []},
        PacketCheck(items=[supported(assertion)]), ['p1', 'p2'],
        {'p1': {'quote': 'Bản', 'source_revision_id': 's1'}, 'p2': {'quote': 'dự thảo', 'source_revision_id': 's1'}})
    assert not result['complete']


def test_short_handle_roundtrip_maps_singular_coverage_id_but_never_literal_values():
    from app.modules.knowledge.services.compilation_transport import mapped
    value = {'items': [{'evidence_id': 'u1', 'reason': 'u1', 'value': 'u1', 'assertion_ids': ['a1']}]}
    actual = mapped(value, {'u1': 'proof-real'})
    assert actual['items'][0] == {'evidence_id': 'proof-real', 'reason': 'u1', 'value': 'u1', 'assertion_ids': ['a1']}


@pytest.mark.asyncio
@pytest.mark.parametrize('role', ['supporting_context', 'unrelated', 'required_assertion', 'unresolved', 'disagreement'])
async def test_missed_evidence_reconciles_without_changing_original_review_or_fabricating_fact(role):
    from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit
    from app.modules.knowledge.services.compilation_coverage import reconcile
    assertion = item()
    initial = {'draft': {'entities': [], 'assertions': [assertion], 'deferred_evidence_ids': ['p2']},
        'review': {'items': [supported(assertion)], 'missed_evidence_ids': ['p2'], 'complete': False}}
    before = deepcopy(initial)
    payload = {'topic': 'Chỉ tiêu', 'primary_evidence_ids': ['p1', 'p2'],
        'evidence': {'p1': {'source_revision_id': 's1', 'quote': 'Năm 2024: 100'},
                     'p2': {'source_revision_id': 's1', 'quote': 'Danh mục hoặc ngày ban hành 2023'}}}
    count, repairs = 0, []
    async def classify(contract, instruction, offered):
        nonlocal count
        count += 1
        assert contract is CoverageAudit and offered['missed_evidence_ids'] == ['p2']
        selected = 'unrelated' if role == 'disagreement' and count == 2 else 'supporting_context' if role == 'disagreement' else role
        return contract(items=[{'evidence_id': 'p2', 'role': selected,
            'assertion_ids': ['a1'] if selected == 'supporting_context' else [], 'reason': 'Independent fixture.'}])
    async def repair(offered, key):
        repairs.append(key)
        assert offered['primary_evidence_ids'] == ['p2'] and offered['existing_assertions'] == [assertion]
        added = item('a2', 'p2', 2023)
        added['temporal'][0]['role'] = 'publication'
        return {'draft': {'entities': [], 'assertions': [added], 'deferred_evidence_ids': []},
            'review': {'items': [supported(added)], 'missed_evidence_ids': [], 'complete': True}}
    result = await reconcile(payload, initial, classify, repair, 'key')
    assert initial == before and result['coverage_reconciliation']['initial_review'] == before['review']
    assert count == 2 and len(repairs) == int(role == 'required_assertion')
    assert len(result['draft']['assertions']) == (2 if role == 'required_assertion' else 1)
    assert result['review']['complete'] is (role not in {'unresolved', 'disagreement'})


@pytest.mark.parametrize('mutation', ['foreign_source', 'missing', 'duplicate', 'unknown_assertion', 'unsupported_context', 'unrelated_with_assertion'])
def test_coverage_requires_exact_ledger_and_same_source_association(mutation):
    from app.core.exceptions import AppException
    from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit, CoverageItem
    from app.modules.knowledge.services.compilation_coverage import validate_audit
    entry = {'evidence_id': 'p2', 'role': 'supporting_context', 'assertion_ids': ['a1'], 'reason': 'Fixture.'}
    entries = [entry]
    evidence = {'p1': {'source_revision_id': 's1'}, 'p2': {'source_revision_id': 's1'}}
    if mutation == 'foreign_source': evidence['p2']['source_revision_id'] = 's2'
    if mutation == 'missing': entries = []
    if mutation == 'duplicate': entries *= 2
    if mutation == 'unknown_assertion': entry['assertion_ids'] = ['unknown']
    if mutation == 'unsupported_context': entry['assertion_ids'] = []
    if mutation == 'unrelated_with_assertion': entry['role'] = 'unrelated'
    # Exercise the server backstop for persisted/untyped input as well as the new JSON boundary guard.
    audit = CoverageAudit.model_construct(items=[CoverageItem.model_validate(item) for item in entries])
    with pytest.raises(AppException):
        validate_audit(audit, ['p2'], {'assertions': [item()]}, evidence)


@pytest.mark.asyncio
async def test_handler_blocks_admin_approval_when_scope_is_literal_unproved_despite_positive_model():
    from unittest.mock import patch

    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services import compilation_service as service
    from tests.test_compilation_lifecycle_603 import action, build, environment
    async with environment() as (client, _, cid, items, _, model, _):
        async def bad_scope(contract, instruction, payload):
            response = await model(contract, instruction, payload)
            if contract is PacketDraft:
                response.assertions[0].scope = []
                data = response.model_dump()
                data['assertions'][0]['scope'] = [{'dimension': 'source_status',
                    'value': 'Unproved source draft status', 'evidence_ids': data['assertions'][0]['evidence_ids']}]
                return PacketDraft.model_validate(data)
            return response
        with patch.object(service, 'generator', return_value=bad_scope):
            record, _ = await build(client, cid, items)
        assert record['status'] == 'needs_attention'
        path = f'/knowledge/collections/{cid}/compilations/{record["id"]}'
        fetched = await client.get(path)
        bundle = fetched.json()['bundle']
        assert not bundle['machine_complete'] and bundle['policy_version'] == POLICY
        assert bundle['packet_results'][0]['review']['mechanical_issues']
        denied = await client.post(path + '/decisions', json=action(record))
        assert denied.status_code == 409 and denied.json()['details']['reason'] == 'unresolved_evidence'
        reread = (await client.get(path)).json()
        assert reread['status'] == 'needs_attention' and len(reread['audit']) == 2


@pytest.mark.asyncio
async def test_rehashing_machine_ready_flag_cannot_bypass_persisted_review_ledger():
    from app.core.exceptions import AppException
    from app.modules.knowledge.services.compilation_engine import compile_topic
    from app.modules.knowledge.services.compilation_validation import validate_result
    from app.modules.knowledge.services.wiki_compiler import digest
    from tests.test_compilation_engine_603 import ACTOR, Model, sample
    model = Model()
    model.unresolved = True
    source = sample()
    bundle = await compile_topic([source], 'c603', 'Chỉ tiêu', ACTOR, model, 'test')
    bundle['machine_complete'] = True
    bundle['sha256'] = digest({k: v for k, v in bundle.items() if k != 'sha256'})
    with pytest.raises(AppException) as exc:
        validate_result(bundle, [source], 'c603')
    assert exc.value.details['reason'] == 'machine_verdict_drift'


def test_coverage_transport_limits_claim_ids_and_restores_them_without_touching_literals():
    from pydantic import ValidationError

    from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit
    from app.modules.knowledge.services.compilation_transport import mapped, prepare
    payload = {'evidence': {'proof-real': {'quote': 'assertion-long'}}, 'missed_evidence_ids': ['proof-real'],
        'existing_assertions': [{'id': 'assertion-long', 'entity_id': 'entity-long', 'value': 'assertion-long',
            'evidence_ids': ['proof-real']}]}
    contract, wire, reverse = prepare(CoverageAudit, payload)
    assert wire['existing_assertions'][0]['id'] == 'claim0'
    assert wire['existing_assertions'][0]['value'] == wire['evidence']['u0']['quote'] == 'assertion-long'
    valid = {'items': [{'evidence_id': 'u0', 'role': 'supporting_context', 'assertion_ids': ['claim0'], 'reason': 'fixture'}]}
    decoded = mapped(contract.model_validate(valid).model_dump(), reverse)
    assert decoded['items'][0]['assertion_ids'] == ['assertion-long']
    assert decoded['items'][0]['evidence_id'] == 'proof-real'
    valid['items'][0]['assertion_ids'] = ['invented-claim']
    with pytest.raises(ValidationError):
        contract.model_validate(valid)


def test_empty_assertion_catalog_cannot_invent_a_supporting_claim():
    from pydantic import ValidationError

    from app.modules.knowledge.compilation_runtime_schemas import CoverageAudit
    from app.modules.knowledge.services.compilation_transport import prepare
    contract, _, _ = prepare(CoverageAudit, {'evidence': {'p': {'quote': 'raw'}},
        'missed_evidence_ids': ['p'], 'existing_assertions': []})
    with pytest.raises(ValidationError):
        contract.model_validate({'items': [{'evidence_id': 'u0', 'role': 'supporting_context',
            'assertion_ids': ['claim0'], 'reason': 'fixture'}]})


def test_extraction_does_not_remap_new_local_ids_to_prior_assertions():
    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services.compilation_transport import mapped, prepare
    _, _, reverse = prepare(PacketDraft, {'evidence': {'proof': {'quote': 'claim0'}},
        'existing_assertions': [{'id': 'old-assertion'}]})
    assert mapped({'id': 'claim0', 'value': 'u0'}, reverse) == {'id': 'claim0', 'value': 'u0'}


def test_navigation_hint_status_never_becomes_source_authored_or_publication_status():
    from app.modules.knowledge.services.compilation_engine import navigation_temporal
    temporal = {'p': {'status': 'proposed', 'data_years': [2024]}, 'none': {}}
    before = deepcopy(temporal)
    value = navigation_temporal(temporal, temporal)
    assert value == {'p': {'origin': 'server_derived_navigation_hint',
        'authority': 'not_source_authored_status_or_legal_verification', 'scope_hint': temporal['p']}}
    assert temporal == before


@pytest.mark.asyncio
@pytest.mark.parametrize('overlap', [True, False])
async def test_optional_context_association_disagreement_is_only_candidate_never_effective_fact(overlap):
    from app.modules.knowledge.services.compilation_coverage import reconcile
    assertions = [item(), item('a2')]
    initial = {'draft': {'entities': [], 'assertions': assertions, 'deferred_evidence_ids': ['p2']},
        'review': {'items': [supported(a) for a in assertions], 'missed_evidence_ids': ['p2'], 'complete': False}}
    payload = {'primary_evidence_ids': ['p1', 'p2'], 'evidence': {
        'p1': {'source_revision_id': 's', 'quote': 'Năm 2024: 100'}, 'p2': {'source_revision_id': 's', 'quote': 'Tên đơn vị'}}}
    calls = 0
    async def classify(contract, _instruction, _payload):
        nonlocal calls
        calls += 1
        return contract(items=[{'evidence_id': 'p2', 'role': 'supporting_context',
            'assertion_ids': ['a1'] if calls == 1 else ['a1', 'a2'] if overlap else ['a2'], 'reason': 'support-only'}])
    async def no_repair(*_):
        raise AssertionError('Supporting context must never create a fact or trigger extraction.')
    result = await reconcile(payload, initial, classify, no_repair, 'key')
    history = result['coverage_reconciliation']
    assert result['review']['complete'] and result['draft']['assertions'] == assertions
    assert history['unbound_supporting_context'][0]['effective'] is False
    assert history['unbound_supporting_context'][0]['usage'] == 'candidate_only'
    assert history['accepted_context_or_unrelated'] == ([{**history['classifications'][0]['items'][0],
        'assertion_ids': ['a1']}] if overlap else [])


@pytest.mark.asyncio
async def test_unresolved_actual_fact_still_blocks_despite_any_optional_context_policy():
    from app.modules.knowledge.services.compilation_coverage import reconcile
    initial = {'draft': {'entities': [], 'assertions': [item()], 'deferred_evidence_ids': ['p2']},
        'review': {'items': [supported(item())], 'missed_evidence_ids': ['p2'], 'complete': False}}
    payload = {'primary_evidence_ids': ['p1', 'p2'], 'evidence': {
        'p1': {'source_revision_id': 's', 'quote': 'Năm 2024: 100'}, 'p2': {'source_revision_id': 's', 'quote': 'Ngoại lệ chưa rõ'}}}
    async def classify(contract, _instruction, _payload):
        return contract(items=[{'evidence_id': 'p2', 'role': 'required_assertion', 'reason': 'Missing source exception.'}])
    async def unsuccessful_repair(_payload, _key):
        return {'draft': {'entities': [], 'assertions': [], 'deferred_evidence_ids': ['p2']},
            'review': {'items': [], 'missed_evidence_ids': ['p2'], 'complete': False}}
    result = await reconcile(payload, initial, classify, unsuccessful_repair, 'key')
    assert not result['review']['complete'] and result['review']['missed_evidence_ids'] == ['p2']


def test_offered_context_deferred_is_audited_separately_without_dropping_primary_or_guessing_relevance():
    from app.modules.knowledge.services.compilation_engine import reconcile_packet_inventory
    draft = {'assertions': [{'evidence_ids': ['body']}], 'deferred_evidence_ids': ['context']}
    ledger = reconcile_packet_inventory(draft, ['body', 'missing'], ['body', 'missing', 'context'])
    assert draft['deferred_evidence_ids'] == ['missing']
    assert ledger == {'unassigned_evidence_ids': ['missing'], 'scope_proofs_previously_deferred': [],
                      'offered_context_declared_deferred': ['context']}
    assert 'unrelated' not in ledger and len(draft['assertions']) == 1


def test_deferring_an_unoffered_proof_still_fails_in_context_aware_inventory():
    from app.core.exceptions import AppException
    from app.modules.knowledge.services.compilation_engine import reconcile_packet_inventory
    with pytest.raises(AppException):
        reconcile_packet_inventory({'assertions': [], 'deferred_evidence_ids': ['foreign']}, ['body'], ['body', 'context'])


@pytest.mark.asyncio
@pytest.mark.parametrize('version', ['v1', 'v2'])
async def test_legacy_policy_remains_readable_but_cannot_gain_new_v3_approval(version):
    from unittest.mock import patch

    from app.modules.knowledge.services import compilation_service as service
    from app.modules.knowledge.services.wiki_compiler import digest
    from tests.test_compilation_lifecycle_603 import action, build, environment
    actual_compile = service.compile_topic
    async def legacy(*args, **kwargs):
        bundle = await actual_compile(*args, **kwargs)
        bundle['policy_version'] = 'qnu-compilation-review/' + version
        bundle['sha256'] = digest({k: v for k, v in bundle.items() if k != 'sha256'})
        return bundle
    async with environment() as (client, _, cid, items, _, _, _):
        with patch.object(service, 'compile_topic', side_effect=legacy):
            record, _ = await build(client, cid, items)
        path = f'/knowledge/collections/{cid}/compilations/{record["id"]}'
        assert (await client.get(path)).status_code == 200
        response = await client.post(path + '/decisions', json=action(record))
        assert response.status_code == 409
        assert response.json()['details']['reason'] == 'review_policy_requires_new_build'
        rejected = await client.post(path + '/decisions', json=action(record, 'rejected', 'reject-old-policy'))
        assert rejected.status_code == 200 and rejected.json()['status'] == 'rejected'


@pytest.mark.parametrize('mutation', ['foreign_section', 'foreign_endpoint', 'foreign_proof', 'missing_proof'])
def test_synthesis_reference_contract_rejects_unknown_or_missing_ids_before_semantic_binding(mutation):
    from pydantic import ValidationError

    from app.modules.knowledge.compilation_runtime_schemas import SynthesisDraft
    from app.modules.knowledge.services.compilation_transport import prepare
    contract, wire, _ = prepare(SynthesisDraft, {'evidence': {'p1': {'quote': 'literal'}},
        'draft': {'entities': [{'id': 'e1'}], 'assertions': [{'id': 'a1', 'entity_id': 'e1'}]}})
    assert wire['draft']['assertions'][0]['id'] == 'claim0'
    data = {'sections': [{'heading': 'Scope', 'text': 'Literal', 'assertion_ids': ['claim0']}],
        'relations': [{'id': 'r', 'source_id': 'claim0', 'target_id': 'ent0', 'kind': 'supports', 'evidence_ids': ['u0']}]}
    assert contract.model_validate(data)
    if mutation == 'foreign_section': data['sections'][0]['assertion_ids'] = ['claim99']
    if mutation == 'foreign_endpoint': data['relations'][0]['target_id'] = 'ent99'
    if mutation == 'foreign_proof': data['relations'][0]['evidence_ids'] = ['u99']
    if mutation == 'missing_proof': del data['relations'][0]['evidence_ids']
    with pytest.raises(ValidationError):
        contract.model_validate(data)


def test_complete_budget_matches_exact_prepared_reference_contract_and_transport_instruction():
    from app.modules.knowledge.compilation_runtime_schemas import SynthesisDraft
    from app.modules.knowledge.services.compilation_transport import (
        TRANSPORT_NOTE,
        prepare,
        request_budget,
    )
    from app.modules.knowledge.services.wiki_budget import request_usage
    from app.modules.knowledge.wiki_schemas import WikiPolicy
    payload = {'evidence': {'p1': {'quote': 'raw'}}, 'draft': {'entities': [{'id': 'e1'}], 'assertions': [{'id': 'a1'}]}}
    contract, wire, _ = prepare(SynthesisDraft, payload)
    assert request_budget(SynthesisDraft, 'instruction', payload, WikiPolicy()) == request_usage(
        contract, 'instruction' + TRANSPORT_NOTE, wire, WikiPolicy())


def test_qualifier_view_is_exact_existing_binding_not_an_invented_exception_or_condition():
    from app.modules.knowledge.services.compilation_engine import bound_qualifiers
    from app.modules.knowledge.services.compilation_transport import prepare
    first, second = item(), item('a2')
    first['condition_ids'] = ['p1']
    second['exception_ids'] = ['p1']
    draft = {'assertions': [first, second]}
    raw = 'Measurement is capacity-based; allocation is decided separately.\nKeep this exact clause.'
    evidence = {'p1': {'quote': raw}, 'unused': {'quote': 'Not a dependency.'}}
    before = deepcopy(draft)
    view = bound_qualifiers(draft, evidence)
    assert view == [{'evidence_id': 'p1', 'quote': raw,
        'condition_for_assertion_ids': ['a1'], 'exception_for_assertion_ids': ['a2']}]
    assert draft == before
    _, wire, _ = prepare(PacketCheck, {'evidence': evidence, 'draft': draft, 'bound_qualifiers': view})
    assert wire['bound_qualifiers'] == [{'evidence_id': 'u0', 'quote': raw,
        'condition_for_assertion_ids': ['claim0'], 'exception_for_assertion_ids': ['claim1']}]


def test_empty_dependencies_cannot_gain_qualifier_bindings_from_nearby_raw_text():
    from app.modules.knowledge.services.compilation_engine import bound_qualifiers
    assert bound_qualifiers({'assertions': [item()]}, {'p1': {'quote': 'Possible nearby exception.'}}) == []


def test_revision_date_uses_existing_event_role_without_changing_v1_binding_schema():
    from app.modules.knowledge.compilation_runtime_schemas import TEMPORAL_ROLES
    from app.modules.knowledge.compilation_schemas import CompilationTime
    from app.modules.knowledge.services.compilation_engine import packet_payload
    time = CompilationTime(role='event', years=[2026], evidence_ids=['p'])
    assert time.role == 'event' and 'version' in TEMPORAL_ROLES['event']
    payload = packet_payload('Versions', ['p'], {'p': {'source_revision_id': 's', 'quote': 'Version 18/09/2026'}}, {})
    assert payload['temporal_role_definitions']['publication'] != payload['temporal_role_definitions']['event']
    assert 'explicitly' in payload['temporal_role_definitions']['publication'].lower()


def test_synthesis_keeps_fitting_source_data_and_issue_date_in_one_context_group():
    from app.modules.knowledge.services.compilation_engine import synthesis_batches
    first, issued, other = item(), item('issued', 'date'), item('other', 'p2', 2026)
    issued['temporal'] = [{'role': 'publication', 'years': [2023], 'evidence_ids': ['date']}]
    catalog = {'p1': {'source_revision_id': 's1', 'quote': 'Data 2024: 100'},
        'date': {'source_revision_id': 's1', 'quote': 'Issued 2023'}, 'p2': {'source_revision_id': 's2', 'quote': 'Data 2026: 100'}}
    draft = {'entities': [], 'assertions': [first, other, issued]}
    batches = synthesis_batches('Dates and data years', draft, catalog)
    assert {a['id'] for batch in batches for a in batch['draft']['assertions']} == {'a1', 'other', 'issued'}
    assert any({'a1', 'issued'} <= {a['id'] for a in batch['draft']['assertions']} for batch in batches)
