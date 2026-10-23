"""Compilation proposal binding never grants semantic approval or publication."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.services.compilation_contracts import bind_draft, evidence_catalog
from app.modules.knowledge.services.wiki_compiler import digest
from tests.test_foundation_602 import source


def fixture():
    item = source('Ngành X có chỉ tiêu năm 2024: ?. Chỉ áp dụng nhóm A; ngoại lệ nhóm B.')
    item.collection_id = 'c'
    catalog = evidence_catalog([item], 'c')
    proof = next(iter(catalog))
    payload = {'snapshot_hash': digest(catalog),
        'entities': [{'id': 'entity', 'label': 'Ngành X', 'evidence_ids': [proof]}],
        'assertions': [{'id': 'assertion', 'entity_id': 'entity', 'attribute': 'Chỉ tiêu',
            'value_state': 'unknown', 'evidence_ids': [proof],
            'temporal': [{'role': 'data', 'years': [2024], 'evidence_ids': [proof]}],
            'scope': [{'dimension': 'nhóm', 'value': 'A', 'evidence_ids': [proof]}],
            'condition_ids': [proof], 'exception_ids': [proof]}],
        'sections': [{'heading': 'Chỉ tiêu', 'text': 'Nguồn chưa xác định chỉ tiêu.',
                      'assertion_ids': ['assertion']}]}
    actor = AuthActor(username='fixture', permissions=['ai.knowledge.upload'])
    return item, payload, actor


def test_bound_unknown_keeps_evidence_and_cannot_be_used_for_serving():
    item, payload, actor = fixture()
    before = deepcopy(vars(item))
    receipt = bind_draft(payload, [item], 'c', actor)
    assert receipt['state'] == 'evidence_bound' and receipt['usage'] == 'review_only'
    assert receipt['semantic_verification'] == 'not_run' and receipt['publication'] == 'unpublished'
    assert receipt['proposal']['assertions'][0]['value'] is None
    assert '?' in next(iter(receipt['evidence'].values()))['quote']
    assert vars(item) == before
    assert bind_draft(payload, [item], 'c', actor) == receipt  # Pure, deterministic, no persistence.


@pytest.mark.parametrize('mutation', ['wrong_hash', 'wrong_revision', 'wrong_canonical', 'foreign_collection',
    'missing_proof', 'invented_year', 'unknown_endpoint', 'duplicate_id', 'wrong_entity',
    'scope_missing_proof', 'missing_condition'])
def test_invalid_source_scope_and_dependencies_are_rejected(mutation):
    item, payload, actor = fixture()
    assertion = payload['assertions'][0]
    if mutation == 'wrong_hash': payload['snapshot_hash'] = 'b'*64
    if mutation == 'wrong_revision': item.id = 'new-revision'
    if mutation == 'wrong_canonical': item.canonical_hash = 'b'*64
    if mutation == 'foreign_collection': item.collection_id = 'foreign'
    if mutation == 'missing_proof': assertion['evidence_ids'] = ['foreign']
    if mutation == 'invented_year': assertion['temporal'][0]['years'] = [2027]
    if mutation == 'unknown_endpoint': payload['relations'] = [{'id': 'rel', 'source_id': 'assertion',
        'target_id': 'foreign', 'kind': 'supports', 'evidence_ids': assertion['evidence_ids']}]
    if mutation == 'duplicate_id': assertion['id'] = 'entity'
    if mutation == 'wrong_entity': assertion['entity_id'] = 'foreign'
    if mutation == 'scope_missing_proof': assertion['scope'][0]['evidence_ids'] = ['foreign']
    if mutation == 'missing_condition': assertion['condition_ids'] = ['foreign']
    with pytest.raises((AppException, ValueError)):
        bind_draft(payload, [item], 'c', actor)


@pytest.mark.parametrize('value', ['0', '12', '?'])
def test_unknown_cannot_be_replaced_with_a_scalar(value):
    item, payload, actor = fixture()
    payload['assertions'][0]['value'] = value
    with pytest.raises(ValidationError):
        bind_draft(payload, [item], 'c', actor)


@pytest.mark.parametrize('field,value', [('status', 'approved'), ('publication', 'published'), ('actor_id', 'admin')])
def test_model_cannot_self_approve_or_choose_actor(field, value):
    item, payload, actor = fixture()
    payload[field] = value
    with pytest.raises(ValidationError):
        bind_draft(payload, [item], 'c', actor)


def test_missing_permission_is_rejected_before_reading_sources():
    item, payload, _ = fixture()
    with pytest.raises(AppException) as exc:
        bind_draft(payload, [item], 'c', AuthActor(username='viewer', permissions=['ai.knowledge.view']))
    assert exc.value.status_code == 403


def test_relation_remains_candidate_even_when_evidence_exists():
    item, payload, actor = fixture()
    payload['relations'] = [{'id': 'r', 'source_id': 'entity', 'target_id': 'assertion',
        'kind': 'supports', 'evidence_ids': payload['assertions'][0]['evidence_ids']}]
    receipt = bind_draft(payload, [item], 'c', actor)
    assert receipt['usage'] == 'review_only' and receipt['semantic_verification'] == 'not_run'


def test_one_assertion_cannot_borrow_condition_from_another_revision():
    item, payload, actor = fixture()
    other = source('Điều kiện riêng nguồn 2025.')
    other.collection_id, other.id, other.binding_id = 'c', 'other', 'other-binding'
    catalog = evidence_catalog([item, other], 'c')
    payload['snapshot_hash'] = digest(catalog)
    payload['assertions'][0]['condition_ids'] = [ref for ref, proof in catalog.items()
                                               if proof['source_revision_id'] == 'other']
    with pytest.raises(AppException):
        bind_draft(payload, [item, other], 'c', actor)
