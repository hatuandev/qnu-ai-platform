"""Metric names must retain source roles even when a model approves a wrong label."""
from copy import deepcopy

import pytest

from app.modules.knowledge.compilation_runtime_schemas import PacketCheck
from app.modules.knowledge.services.compilation_validation import check_packet


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket

    def blocked(*args, **kwargs):
        raise AssertionError('Focused metric regression must not access a database/provider/storage endpoint')

    monkeypatch.setattr(socket, 'create_connection', blocked)
    import httpx
    from sqlalchemy.ext.asyncio import AsyncEngine

    monkeypatch.setattr(AsyncEngine, 'connect', blocked)
    monkeypatch.setattr(httpx.AsyncClient, 'send', blocked)


def metric_case(value='153'):
    catalog = {
        'row': {'source_revision_id': 's', 'quote': f'| Total | {value} | 100% |',
                'structural_evidence': {'role': 'table_row', 'table_id': 't',
                    'header_status': 'declared', 'header_evidence_ids': ['header'],
                    'table_preamble_evidence_ids': ['intro'],
                    'header_paths': [['Group'], ['Count'], ['Rate']]}},
        'header': {'source_revision_id': 's', 'quote': '| Group | Count | Rate |\n| --- | --- | --- |',
                   'structural_evidence': {'role': 'table_header', 'table_id': 't',
                       'header_status': 'declared', 'header_paths': [['Group'], ['Count'], ['Rate']],
                       'table_preamble_evidence_ids': ['intro']}},
        'intro': {'source_revision_id': 's', 'quote': 'People who completed registration'},
        'other': {'source_revision_id': 's', 'quote': 'Planned capacity'},
    }
    assertion = {'id': 'a', 'entity_id': 'e', 'attribute': 'Count', 'value': value,
        'value_state': 'present', 'evidence_ids': ['row', 'header', 'intro'], 'temporal': [],
        'scope': [{'dimension': 'source_metric', 'value': catalog['intro']['quote'], 'evidence_ids': ['intro']},
                  {'dimension': 'source_column', 'value': 'Count', 'evidence_ids': ['header']}],
        'condition_ids': [], 'exception_ids': []}
    draft = {'entities': [{'id': 'e', 'label': catalog['intro']['quote'], 'evidence_ids': ['intro']}],
             'assertions': [assertion], 'deferred_evidence_ids': []}
    review = PacketCheck(items=[{'id': 'a', 'verdict': 'supported', 'entity_scope': True,
        'temporal_roles': True, 'conditions_complete': True, 'evidence_ids': assertion['evidence_ids'],
        'reason': 'The model says the number proves the proposed metric.'}])
    return catalog, draft, review


@pytest.mark.parametrize('mutation', ['missing_binding', 'renamed_entity', 'renamed_attribute',
    'wrong_column', 'wrong_value', 'unresolved_header', 'foreign_preamble', 'duplicate_cell',
    'entity_proof_missing', 'invented_unit_suffix'])
def test_wrong_metric_stays_blocked_despite_supported_model_review(mutation):
    catalog, draft, review = metric_case()
    assertion = draft['assertions'][0]
    if mutation == 'missing_binding':
        assertion['scope'] = []
    elif mutation == 'renamed_entity':
        draft['entities'][0]['label'] = 'Planned capacity'
    elif mutation == 'renamed_attribute':
        assertion['attribute'] = 'planned_target'
    elif mutation == 'wrong_column':
        assertion['scope'][1]['value'] = assertion['attribute'] = 'Rate'
    elif mutation == 'wrong_value':
        assertion['value'] = '999'
    elif mutation == 'unresolved_header':
        catalog['row']['structural_evidence']['header_status'] = 'unresolved'
    elif mutation == 'foreign_preamble':
        assertion['scope'][0].update(value='Planned capacity', evidence_ids=['other'])
        draft['entities'][0].update(label='Planned capacity', evidence_ids=['other'])
        assertion['evidence_ids'].append('other')
        review.items[0].evidence_ids.append('other')
    elif mutation == 'duplicate_cell':
        catalog['row']['quote'] = '| Total | 153 | 153 |'
    elif mutation == 'entity_proof_missing':
        draft['entities'][0]['evidence_ids'] = ['row']
    else:
        assertion['value'] = '153 people'
    result = check_packet(draft, review, ['row'], catalog)
    assert not result['complete'], result
    assert any(item['reason'].startswith('metric_') for item in result['mechanical_issues'])


@pytest.mark.parametrize('value', ['153', '0'])
def test_exact_source_metric_and_column_preserve_value_without_mutating_evidence(value):
    catalog, draft, review = metric_case(value)
    before = deepcopy((catalog, draft, review))
    assert check_packet(draft, review, ['row'], catalog)['complete']
    assert (catalog, draft, review) == before


def test_unknown_remains_null_and_does_not_invent_a_metric_value():
    catalog, draft, review = metric_case()
    draft['assertions'][0].update(value_state='unknown', value=None, scope=[])
    assert check_packet(draft, review, ['row'], catalog)['complete']


def test_supporting_body_row_does_not_become_a_second_value_owner():
    catalog, draft, review = metric_case()
    catalog['other'] = {**deepcopy(catalog['row']), 'quote': '| Subgroup | 52 | 34% |'}
    draft['assertions'][0]['evidence_ids'].append('other')
    review.items[0].evidence_ids.append('other')
    assert check_packet(draft, review, ['row'], catalog)['complete']


def test_old_review_ledger_remains_readable_without_retroactive_reclassification():
    catalog, draft, review = metric_case()
    draft['assertions'][0]['scope'] = []
    assert check_packet(draft, review, ['row'], catalog, metric_bindings=False)['complete']
    assert not check_packet(draft, review, ['row'], catalog)['complete']


def test_new_policy_cannot_drop_the_binding_protocol_to_skip_its_checks():
    from app.core.exceptions import AppException
    from app.modules.knowledge.services.compilation_validation import validate_result

    with pytest.raises(AppException) as error:
        validate_result({'compiler': 'qnu-topic-compiler/v1', 'policy_version': 'qnu-compilation-review/v4'}, [], 'c')
    assert error.value.details['reason'] == 'metric_protocol_missing'


def test_row_specific_binding_choices_keep_proof_handles_and_candidate_status():
    from app.modules.knowledge.compilation_runtime_schemas import PacketDraft
    from app.modules.knowledge.services.compilation_engine import packet_payload
    from app.modules.knowledge.services.compilation_transport import prepare

    catalog, _, _ = metric_case()
    catalog['row']['structural_evidence']['header_status'] = 'unresolved'
    payload = packet_payload('What does the value describe?', ['row'], catalog, {'row': ['header', 'intro']})
    target = payload['metric_binding_targets'][0]
    assert target['header_status'] == 'unresolved'
    assert target['metric_context'] == [{'evidence_id': 'intro', 'quote': 'People who completed registration'}]
    assert target['cells'][0] == {'column_index': 1, 'value': '153',
        'column_candidates': [{'evidence_id': 'header', 'value': 'Count'}]}
    _, wire, reverse = prepare(PacketDraft, payload)
    target = wire['metric_binding_targets'][0]
    assert reverse[target['evidence_id']] == 'row'
    assert reverse[target['cells'][0]['column_candidates'][0]['evidence_id']] == 'header'


def test_synthesis_cannot_drop_the_literal_metric_even_with_supported_section_review():
    from app.modules.knowledge.compilation_runtime_schemas import SynthesisCheck
    from app.modules.knowledge.services.compilation_validation import check_synthesis

    catalog, draft, _ = metric_case()
    synthesis = {'relations': [], 'sections': [{'heading': 'Results',
        'text': 'Planned capacity: 153.', 'assertion_ids': ['a']}]}
    review = SynthesisCheck(sections=[{'index': 0, 'verdict': 'supported', 'assertion_ids': ['a'],
        'reason': 'The value exists in the source.'}])
    assert not check_synthesis(draft, synthesis, review, catalog)['complete']


@pytest.mark.asyncio
async def test_compiler_runtime_and_persisted_recheck_use_the_same_metric_binding():
    from app.modules.knowledge.compilation_runtime_schemas import (
        PacketDraft,
        SynthesisDraft,
        TopicSelection,
    )
    from app.modules.knowledge.services.compilation_engine import compile_topic
    from app.modules.knowledge.services.compilation_validation import validate_result
    from tests.test_compilation_engine_603 import ACTOR, Model
    from tests.test_compilation_structure_614 import structured_source

    class BoundModel(Model):
        async def __call__(self, contract, instruction, payload):
            if contract is TopicSelection:
                relevant = [pid for pid, ref in payload['evidence'].items() if ref['quote'].startswith('| Alpha |')]
                return contract(relevant_evidence_ids=relevant,
                    unrelated_evidence_ids=sorted(set(payload['evidence']) - set(relevant)))
            if contract is PacketDraft:
                row = payload['primary_evidence_ids'][0]
                header = payload['evidence'][row]['structural_evidence']['header_evidence_ids'][0]
                return contract(entities=[{'id': 'e', 'label': 'Nhập học', 'evidence_ids': [header]}],
                    assertions=[{'id': 'a', 'entity_id': 'e', 'attribute': 'Nhập học', 'value': '416',
                        'value_state': 'present', 'evidence_ids': [row, header],
                        'scope': [{'dimension': d, 'value': 'Nhập học', 'evidence_ids': [header]}
                                  for d in ('source_metric', 'source_column')]}])
            if contract is SynthesisDraft:
                return contract(sections=[{'heading': 'Kết quả', 'text': 'Nhập học: 416.',
                    'assertion_ids': [payload['draft']['assertions'][0]['id']]}])
            return await super().__call__(contract, instruction, payload)

    sources = [structured_source()]
    bundle = await compile_topic(sources, 'c603', 'Số liệu trong bảng', ACTOR, BoundModel(), 'metric615')
    assert bundle['machine_complete'] and bundle['metric_protocol']
    from app.modules.knowledge.compilation_runtime_schemas import POLICY

    assert bundle['policy_version'] == POLICY
    validate_result(bundle, sources, 'c603')
