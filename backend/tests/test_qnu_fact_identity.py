import copy

import pytest

from app.modules.knowledge.models import KnowledgeFact
from app.modules.knowledge.normalization.qnu_markdown import QnuSourceLocation
from app.modules.knowledge.normalization.qnu_projection import digest, project_document
from app.modules.knowledge.services.fact_identity import build_fact_identity
from app.modules.knowledge.services.source_context import query_projection
from tests.test_qnu_serving import document, reference

POLICY = 'final-cell-provenance/v1'


def spanning_document(*, policy=POLICY):
    model = document()
    row = next(b for b in model.blocks if b.id == 'r')
    row.source_locations = [QnuSourceLocation(page=3, locator='physical/3/row/1')]
    if policy:
        model.document_meta['fact_identity_policy'] = policy
    return model


def test_final_provenance_identity_survives_orm_materialization_without_changes():
    _, artifact = project_document(spanning_document(), reference(), {})
    assert artifact['facts']
    for fact in artifact['facts']:
        raw = fact['raw_data']
        assert raw['page_number'] == 3
        persisted = KnowledgeFact(**copy.deepcopy(fact), **query_projection(raw))
        assert persisted.entity_key == fact['entity_key']
        assert persisted.entity_label == fact['entity_label']
        assert persisted.entity_text == fact['entity_text']
        assert persisted.attribute_value == fact['attribute_value']
    assert artifact['fact_set_hash'] == digest(artifact['facts'])


def test_legacy_projection_is_not_silently_rewritten():
    _, artifact = project_document(spanning_document(policy=None), reference(), {})
    fact = artifact['facts'][0]
    legacy_raw = {**fact['raw_data'], 'page_number': 2}
    assert fact['entity_key'] == build_fact_identity(fact['entity_text'], raw_data=legacy_raw).entity_key
    assert fact['entity_key'] != build_fact_identity(fact['entity_text'], raw_data=fact['raw_data']).entity_key


def test_new_identity_is_deterministic_and_preserves_zero_and_code():
    model = spanning_document()
    first = project_document(model, reference(), {})[1]
    second = project_document(model, reference(), {})[1]
    assert first['facts'] == second['facts'] and first['fact_set_hash'] == second['fact_set_hash']
    assert any(f['attribute_value'] == '0' for f in first['facts'])
    assert first['tables'][0]['rows'][0][0] == '0012345'


def test_unknown_identity_policy_fails_closed():
    with pytest.raises(ValueError, match='FACT_IDENTITY_POLICY_UNSUPPORTED'):
        project_document(spanning_document(policy='unrecognized-policy'), reference(), {})


def test_final_identity_is_not_constant_across_distinct_source_pages():
    a = spanning_document()
    b = a.model_copy(deep=True)
    next(x for x in b.blocks if x.id == 'r').source_locations[0].page = 4
    facts_a = project_document(a, reference(), {})[1]['facts']
    facts_b = project_document(b, reference(), {})[1]['facts']
    assert facts_a[0]['entity_key'] != facts_b[0]['entity_key']
