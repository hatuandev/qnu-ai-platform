"""Compiler behavior and source-bound cache controls; deterministic inference, no provider."""
import hashlib
from copy import deepcopy

import pytest

from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.compilation_runtime_schemas import (
    CompilerPolicy,
    CoverageAudit,
    PacketCheck,
    PacketDraft,
    SynthesisCheck,
    SynthesisDraft,
    TopicSelection,
)
from app.modules.knowledge.services.compilation_engine import compile_topic, plan_packets
from app.modules.knowledge.services.compilation_validation import validate_result
from app.modules.knowledge.services.wiki_compiler import digest
from tests.test_foundation_602 import source

ACTOR = AuthActor(username='compiler-test', permissions=['ai.knowledge.upload', 'ai.knowledge.view', 'ai.knowledge.review'])


def sample(number=1, year=2024, unknown=False):
    item = source(f'Viện {number} có chỉ tiêu năm {year}: ' + ('?' if unknown else str(number * 100))
                  + '. Chỉ áp dụng nhóm A, ngoại lệ nhóm B.')
    item.id, item.binding_id, item.collection_id = f's{number}', f'b{number}', 'c603'
    return item


class Model:
    def __init__(self):
        self.calls = []
        self.primary_batches = []
        self.unresolved = False
        self.omit_review = False
        self.bad_time = False
        self.dropped_section = False

    async def __call__(self, contract, instruction, payload):
        self.calls.append(contract.__name__)
        if contract is TopicSelection:
            return contract(relevant_evidence_ids=list(payload['evidence']))
        if contract is CoverageAudit:
            return contract(items=[{'evidence_id': pid, 'role': 'unresolved', 'assertion_ids': [],
                'reason': 'Fixture deliberately leaves omitted evidence unresolved.'} for pid in payload['missed_evidence_ids']])
        if contract is PacketDraft:
            self.primary_batches.append(tuple(payload['primary_evidence_ids']))
            entities, assertions = [], []
            for index, pid in enumerate(payload['primary_evidence_ids']):
                ref = payload['evidence'][pid]
                entities.append({'id': f'e{index}', 'label': ref['quote'].split(' có ')[0], 'evidence_ids': [pid]})
                assertions.append({'id': f'a{index}', 'entity_id': f'e{index}', 'attribute': 'Chỉ tiêu',
                    'value_state': 'unknown' if '?' in ref['quote'] else 'present',
                    'value': None if '?' in ref['quote'] else ref['quote'], 'evidence_ids': [pid],
                    'condition_ids': [pid], 'exception_ids': [pid],
                    **({'temporal': [{'role': 'data', 'years': [2098], 'evidence_ids': [pid]}]} if self.bad_time else {})})
            return contract(entities=entities, assertions=assertions)
        if contract is PacketCheck:
            items = [{'id': a['id'], 'verdict': 'unresolved' if self.unresolved else 'supported',
                'entity_scope': True, 'temporal_roles': True, 'conditions_complete': not self.unresolved,
                'evidence_ids': a['evidence_ids'], 'reason': 'Đối chiếu nguồn của fixture.'} for a in payload['draft']['assertions']]
            return contract(items=items[:-1] if self.omit_review else items)
        if contract is SynthesisDraft:
            assertions = payload['draft']['assertions']
            if self.dropped_section:
                assertions = assertions[:1]
            return contract(sections=[{'heading': a['id'], 'text': a['value'] or 'Nguồn để ký hiệu ?, chưa xác định.',
                'assertion_ids': [a['id']]} for a in assertions])
        if contract is SynthesisCheck:
            return contract(sections=[{'index': i, 'verdict': 'supported', 'assertion_ids': s['assertion_ids'],
                'reason': 'Trích nguyên văn đúng assertion.'} for i, s in enumerate(payload['synthesis']['sections'])])
        raise AssertionError(contract)


@pytest.mark.asyncio
async def test_two_sources_same_entity_label_stay_separate_unknown_and_conditions_preserved():
    items = [sample(1), sample(2, 2026, True)]
    model = Model()
    before = deepcopy([vars(s) for s in items])
    result = await compile_topic(items, 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1')
    assert result['machine_complete'] and result['calls_this_run'] == 10
    assert result['usage'] == 'review_only' and result['publication'] == 'unpublished'
    assert len(result['binding']['proposal']['entities']) == 2
    assert [a['value_state'] for a in result['binding']['proposal']['assertions']] == ['present', 'unknown']
    assert '?' in result['markdown'] and 'nhóm A' in result['markdown'] and 'nhóm B' in result['markdown']
    assert {ref['source_revision_id'] for ref in result['binding']['evidence'].values()} == {'s1', 's2'}
    assert all(entry['assertions'] for entry in result['dependencies'].values())
    assert [vars(s) for s in items] == before
    validate_result(result, items, 'c603')


@pytest.mark.asyncio
async def test_incremental_rebuild_calls_only_changed_source_packets_and_preserves_prior_bundle():
    model = Model()
    sources = [sample(1), sample(2, 2025)]
    first = await compile_topic(sources, 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1')
    old = deepcopy(first)
    cache = {p['key']: p for p in [*first['packet_results'], *first['topic_results']]}
    changed = sample(2, 2026)
    changed.id = 's2-new'
    second = await compile_topic([sources[0], changed], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1', cache)
    assert second['reused_packets'] == 1 and second['calls_this_run'] == 6
    assert second['reused_topic_packets'] == 1
    assert first == old and first['binding']['proposal_hash'] != second['binding']['proposal_hash']
    assert second['binding']['snapshot_hash'] != first['binding']['snapshot_hash']


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation', ['omit_review', 'bad_time', 'dropped_section'])
async def test_invalid_generation_or_incomplete_independent_review_fails_closed(mutation):
    model = Model()
    setattr(model, mutation, True)
    with pytest.raises((AppException, ValueError)):
        await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1')


@pytest.mark.asyncio
async def test_unresolved_check_is_visible_and_never_auto_approved():
    model = Model()
    model.unresolved = True
    result = await compile_topic([sample()], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1')
    assert result['machine_complete'] is False
    assert result['binding']['semantic_verification'] == 'not_run'  # Binding receipt is unchanged.
    assert result['packet_results'][0]['review']['items'][0]['verdict'] == 'unresolved'


@pytest.mark.asyncio
async def test_corrupted_cache_and_wrong_revision_do_not_reuse_semantic_checks():
    model = Model()
    first = await compile_topic([sample()], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1')
    cache = {p['key']: deepcopy(p) for p in first['packet_results']}
    next(iter(cache.values()))['review']['complete'] = False
    with pytest.raises(AppException):
        await compile_topic([sample()], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1', cache)
    with pytest.raises(AppException):
        validate_result(first, [sample(2)], 'c603')


@pytest.mark.asyncio
async def test_oversized_unit_and_model_call_budget_fail_before_excess_inference():
    model = Model()
    big = sample()
    big.canonical_markdown = 'đ' * 30000
    big.canonical_hash = hashlib.sha256(big.canonical_markdown.encode()).hexdigest()
    from app.modules.knowledge.services.source_artifact import build_source_artifact
    big.parse_provenance['structured_artifact'] = build_source_artifact(big.canonical_markdown, 1, {})
    with pytest.raises(AppException):
        await compile_topic([big], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1')
    assert not model.calls
    with pytest.raises(AppException) as error:
        await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu từng năm', ACTOR, model, 'config1',
                            policy=CompilerPolicy(max_calls=4))
    assert error.value.details['reason'] == 'model_call_budget' and len(model.calls) == 4


def test_metadata_and_context_are_not_copied_as_business_conditions_by_server():
    from app.modules.knowledge.services.compilation_contracts import evidence_catalog
    item = sample()
    catalog = evidence_catalog([item], 'c603')
    packet = plan_packets('Chỉ tiêu', catalog, {}, CompilerPolicy())[0]
    assert set(packet['evidence']) == set(catalog)
    assert all(packet['evidence'][pid]['quote'] == catalog[pid]['quote'] for pid in catalog)
    assert 'condition_ids' not in packet  # Only proposal + independent review may assess applicability.
    assert digest(catalog) == digest(evidence_catalog([item], 'c603'))


@pytest.mark.parametrize('field', ['evidence_ids', 'condition_ids', 'exception_ids', 'scope', 'temporal'])
def test_valid_global_proof_not_offered_to_packet_cannot_be_borrowed(field):
    from app.modules.knowledge.services.compilation_engine import require_offered_references
    item = {'evidence_ids': ['offered'], 'condition_ids': [], 'exception_ids': [], 'scope': [], 'temporal': []}
    item[field] = [{'evidence_ids': ['foreign']}] if field in {'scope', 'temporal'} else ['foreign']
    with pytest.raises(AppException):
        require_offered_references([item], {'offered': {}})


@pytest.mark.asyncio
async def test_synthesis_batches_fit_without_dropping_assertions_or_removing_conditions():
    from app.modules.knowledge.services.source_artifact import build_source_artifact
    item = sample()
    item.canonical_markdown = '\n\n'.join(f'Mục {i} có quy định riêng: ' + ('nội dung có nguồn; ' * 22) for i in range(18))
    item.canonical_hash = hashlib.sha256(item.canonical_markdown.encode()).hexdigest()
    item.parse_provenance['structured_artifact'] = build_source_artifact(item.canonical_markdown, 1, {})
    result = await compile_topic([item], 'c603', 'Quy định có nguồn', ACTOR, Model(), 'config')
    assert len(result['binding']['proposal']['assertions']) == 18
    assert len(result['binding']['proposal']['sections']) == 18
    assert result['calls_this_run'] > 4 and result['machine_complete']
    assert all(a['condition_ids'] for a in result['binding']['proposal']['assertions'])


@pytest.mark.asyncio
async def test_cache_invalidates_when_semantic_manifest_changes_without_text_change():
    from app.modules.knowledge.services.source_artifact import get_source_artifact
    item = sample()
    first = await compile_topic([item], 'c603', 'Chỉ tiêu theo năm', ACTOR, Model(), 'config')
    changed = deepcopy(item)
    # A new verified context changes provenance even if canonical text remains byte-identical.
    changed.parse_provenance['annotation_context_revision'] = 'new-context'
    assert get_source_artifact(changed) == get_source_artifact(item)
    cached = {p['key']: p for p in first['packet_results']}
    second = await compile_topic([changed], 'c603', 'Chỉ tiêu theo năm', ACTOR, Model(), 'config', cached)
    assert second['reused_packets'] == 0 and second['calls_this_run'] == 6


@pytest.mark.asyncio
async def test_independent_topic_review_retains_relevant_evidence_excluded_by_first_pass():
    model = Model()
    count = 0
    async def selector(contract, instruction, payload):
        nonlocal count
        if contract is TopicSelection:
            count += 1
            if count == 1:
                return contract(unrelated_evidence_ids=list(payload['evidence']))
        return await model(contract, instruction, payload)
    result = await compile_topic([sample()], 'c603', 'Chỉ tiêu', ACTOR, selector, 'config')
    assert result['topic_selection']['selected'] and result['machine_complete']
    assert result['topic_selection']['excluded'] == []


@pytest.mark.asyncio
async def test_topic_selection_cannot_drop_unclassified_evidence():
    model = Model()
    async def incomplete(contract, instruction, payload):
        if contract is TopicSelection:
            return contract()
        return await model(contract, instruction, payload)
    result = await compile_topic([sample()], 'c603', 'Chỉ tiêu', ACTOR, incomplete, 'config')
    assert result['topic_selection']['selected'] and not result['topic_selection']['excluded']
    assert result['topic_selection']['reviews'][0]['unclassified_retained']
    assert result['binding']['proposal']['assertions']


@pytest.mark.asyncio
async def test_all_independently_unrelated_is_explicit_no_topic_evidence_not_fake_content():
    async def unrelated(contract, _instruction, payload):
        assert contract is TopicSelection
        return contract(unrelated_evidence_ids=list(payload['evidence']))
    with pytest.raises(AppException) as error:
        await compile_topic([sample()], 'c603', 'Chỉ tiêu', ACTOR, unrelated, 'config')
    assert error.value.details['reason'] == 'no_topic_evidence'


def test_explicit_scope_proof_closure_preserves_metadata_role_without_inventing_condition():
    from app.modules.knowledge.services.compilation_engine import close_explicit_scope_evidence
    item = {'evidence_ids': ['body'], 'condition_ids': [], 'exception_ids': [],
        'scope': [{'dimension': 'group', 'value': 'A', 'evidence_ids': ['heading']}],
        'temporal': [{'role': 'publication', 'years': [2023], 'evidence_ids': ['date']}]}
    close_explicit_scope_evidence([item])
    assert item['evidence_ids'] == ['body', 'heading', 'date']
    assert item['condition_ids'] == item['exception_ids'] == []
    assert item['temporal'][0]['role'] == 'publication'


@pytest.mark.asyncio
async def test_max_units_stops_before_any_topic_inference():
    model = Model()
    with pytest.raises(AppException) as error:
        await compile_topic([sample(1), sample(2)], 'c603', 'Chỉ tiêu', ACTOR, model, 'config',
                            policy=CompilerPolicy(max_units=1))
    assert error.value.details['reason'] == 'source_unit_budget' and not model.calls


@pytest.mark.asyncio
async def test_only_known_json_rejection_has_one_bounded_correction_counted_in_budget():
    model = Model()
    attempts = 0
    async def malformed_once(contract, instruction, payload):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise AppException('Invalid JSON fixture', code='KNOWLEDGE_WIKI_INVALID', status_code=502,
                               details={'reason': 'json_syntax'})
        if attempts == 2:
            assert payload['output_format_feedback']['reason'] == 'json_syntax'
        return await model(contract, instruction, payload)
    result = await compile_topic([sample()], 'c603', 'Chỉ tiêu', ACTOR, malformed_once, 'config')
    assert result['calls_this_run'] == 7 and attempts == 7


@pytest.mark.asyncio
async def test_repeated_bad_json_stops_after_one_correction_and_provider_error_has_none():
    count = 0
    async def broken(*_args):
        nonlocal count
        count += 1
        raise AppException('Fixture invalid JSON', code='KNOWLEDGE_WIKI_INVALID', status_code=502)
    with pytest.raises(AppException):
        await compile_topic([sample()], 'c603', 'Chỉ tiêu', ACTOR, broken, 'config')
    assert count == 2
    count = 0
    async def provider(*_args):
        nonlocal count
        count += 1
        raise AppException('Fixture provider error', code='PROVIDER_UNAVAILABLE', status_code=503)
    with pytest.raises(AppException):
        await compile_topic([sample()], 'c603', 'Chỉ tiêu', ACTOR, provider, 'config')
    assert count == 1


def test_inventory_accounting_never_creates_a_fact_or_marks_unassigned_as_verified():
    from app.modules.knowledge.services.compilation_engine import reconcile_packet_inventory
    draft = {'assertions': [{'id': 'a', 'evidence_ids': ['body', 'heading']}],
             'deferred_evidence_ids': ['heading']}
    result = reconcile_packet_inventory(draft, ['body', 'heading', 'unassigned'])
    assert result == {'unassigned_evidence_ids': ['unassigned'], 'scope_proofs_previously_deferred': ['heading']}
    assert draft['deferred_evidence_ids'] == ['unassigned'] and len(draft['assertions']) == 1
    with pytest.raises(AppException):
        reconcile_packet_inventory({'assertions': [], 'deferred_evidence_ids': ['foreign']}, ['body'])


@pytest.mark.asyncio
async def test_unassigned_relevant_proof_reported_by_independent_review_blocks_approval_readiness():
    item = sample()
    second = source(item.canonical_markdown + '\n\nNgoại lệ bổ sung chưa được bóc tách.')
    second.id, second.binding_id, second.collection_id = item.id, item.binding_id, item.collection_id
    model = Model()
    async def incomplete(contract, instruction, payload):
        answer = await model(contract, instruction, payload)
        if contract is PacketDraft:
            answer.assertions = answer.assertions[:1]
            answer.entities = answer.entities[:1]
        if contract is PacketCheck:
            assert payload['server_inventory_accounting']['unassigned_evidence_ids']
            answer.missed_evidence_ids = payload['server_inventory_accounting']['unassigned_evidence_ids']
        return answer
    result = await compile_topic([second], 'c603', 'Chỉ tiêu', ACTOR, incomplete, 'config')
    assert result['machine_complete'] is False
    assert result['packet_results'][0]['review']['missed_evidence_ids']
