"""Prose selection and condition recovery retain canonical proof and full sentences."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.modules.rag.evidence_claims import propose_bound_claims, restore_condition_claims
from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference
from app.modules.rag.schemas import AskRequest


def block(text, **kwargs):
    return EvidenceBlock(id='body', binding_id='b', source_revision_id='r', index_revision_id='i',
        canonical_hash='a'*64, title='Nguồn', text=text, start=0, end=len(text), **kwargs)


def test_repair_uses_complete_owning_sentence_for_a_semicolon_clause():
    text = 'Giữ nguyên mã; kể cả số 0 đầu. Không tự suy đoán dữ kiện.'
    body = block(text)
    claims = restore_condition_claims({'e1.c1': 'kể cả số 0 đầu.'}, [body])
    assert claims[0]['text'] == 'Giữ nguyên mã; kể cả số 0 đầu.'
    assert claims[0]['references'][0]['start'] == 0
    assert claims[0]['references'][0]['end'] == text.index(' Không')


def test_repair_does_not_borrow_a_same_text_clause_from_another_source():
    body = block('Alpha; giữ nguyên mã.')
    with pytest.raises(ValueError):
        restore_condition_claims({'e9.c0': 'giữ nguyên mã.'}, [body])


@pytest.mark.asyncio
async def test_selector_uses_canonical_owner_instead_of_duplicate_derived_row():
    body = block('Ngoại lệ chỉ áp dụng nếu đủ chứng cứ.', unit_id='u')
    derived = body.model_copy(update={'id': 'fact', 'origin': 'reviewed_fact', 'fact_id': 'f',
        'text': 'Nhóm A: Ngoại lệ chỉ áp dụng nếu đủ chứng cứ.',
        'fact_context': {'entity_name': 'Nhóm A', 'source_unit_id': 'u'}})
    offered = []
    async def select(db, req, contract, instruction, payload, **kwargs):
        offered.extend(p['whole_passage_id'] for p in payload['passages'])
        return contract.model_validate({'status': 'supported', 'claims': [
            {'id': 'c', 'text': 'Ngoại lệ', 'evidence_ids': ['e1'], 'context_ids': []}]})
    req = AskRequest(question='Điều kiện ngoại lệ là gì?', collection_id='c')
    with patch('app.modules.rag.evidence_claims.structured_call', select):
        _, claims, rejected, _ = await propose_bound_claims(None, req,
            {'compact_passages': True, 'requested': {}}, [body, derived])
    assert offered == ['e1']
    assert not rejected and claims[0]['references'][0]['origin'] == 'canonical'


def test_condition_fragment_matches_one_sentence_or_remains_unresolved():
    body = block('Alpha; giữ nguyên mã. Beta; giữ nguyên mã.')
    with pytest.raises(ValueError):
        restore_condition_claims({}, [body], [QuoteReference(block_id='body', quote='giữ nguyên mã.')])


@pytest.mark.asyncio
async def test_second_missing_clause_in_same_block_can_be_restored_then_reverified():
    from app.modules.rag.evidence_schemas import QueryPlan
    from app.modules.rag.evidence_validation import bind_quote
    from app.modules.rag.evidence_verification import complete_source_conditions
    body = block('Alpha. Beta. Gamma.')
    first = bind_quote(QuoteReference(block_id='body', quote='Alpha.'), {'body': body})
    initial = [{'id': 'first', 'text': 'Alpha.', 'references': [first]}]
    def verdict(claims, quote, complete=False):
        return SimpleNamespace(claims=claims, complete=complete, source_condition_gaps={},
            source_qualifier_gaps=[QuoteReference(block_id='body', quote=quote)] if quote else [],
            errors=[], verifier=SimpleNamespace(conflict=False, topic_coverage={'topic': True}))
    calls = []
    async def verify(db, req, payload, claims, blocks, plan, rules):
        calls.append(claims)
        return verdict(claims, 'Gamma.' if len(calls) == 1 else None, len(calls) == 2)
    req = AskRequest(question='Nêu điều kiện.', collection_id='c')
    with patch('app.modules.rag.evidence_verification.verify_bound_answer', verify):
        result = await complete_source_conditions(None, req, {}, verdict(initial, 'Beta.'),
            [body], QueryPlan(query=req.question, requested_topics=['topic']), [])
    assert result.complete and len(calls) == 2
    assert {'Alpha.', 'Beta.', 'Gamma.'} == {c['text'] for c in result.claims}


def test_different_revision_derived_row_is_not_treated_as_a_duplicate():
    from app.modules.rag.evidence_recovery import canonical_selection_blocks
    body = block('Đúng nguồn.', unit_id='u')
    derived = body.model_copy(update={'id': 'fact', 'origin': 'reviewed_fact', 'source_revision_id': 'other',
        'fact_context': {'source_unit_id': 'u'}})
    assert canonical_selection_blocks([body, derived]) == [body, derived]
