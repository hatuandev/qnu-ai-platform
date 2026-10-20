"""Attribution and prerequisite answers keep their own bounded source evidence."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.evidence_claims import propose_bound_claims
from app.modules.rag.evidence_passages import passage_catalog
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan, QuoteReference
from app.modules.rag.evidence_validation import bind_quote
from app.modules.rag.evidence_verification import verify_bound_answer
from app.modules.rag.schemas import AskRequest


def block(key, text, start=0, kind='paragraph', parent=None, **identity):
    return EvidenceBlock(id=key, unit_id=key, parent_id=parent, text=text, start=start,
        end=start + len(text), title='Fixture', binding_id=identity.get('binding_id', 'b'),
        index_revision_id=identity.get('index_revision_id', 'i'),
        source_revision_id=identity.get('source_revision_id', 'r'),
        canonical_hash=identity.get('canonical_hash', 'hash'), fact_context={'source_kind': kind})


def row(code='RULE-X', key='alias', **identity):
    b = block(key, f'| {code} | Hồ sơ thiết bị |', 400, 'table', **identity)
    b.header_context = '| Mã quy tắc | Đối tượng |\n| --- | --- |'
    return b


async def propose(blocks, question):
    body = next(b for b in blocks if b.id == 'body')
    catalog = passage_catalog(blocks)
    key = next(k for k, v in catalog.items() if v.block_id == body.id and '.' not in k)

    async def select(db, req, contract, instruction, payload, **kwargs):
        return contract.model_validate({'status': 'supported', 'claims': [
            {'id': 'c', 'text': 'Quy định nguồn', 'evidence_ids': [key], 'context_ids': []}],
            'missing_constraints': []})

    req = AskRequest(question=question, collection_id='collection')
    with patch('app.modules.rag.evidence_claims.structured_call', AsyncMock(side_effect=select)):
        _, claims, rejected, _ = await propose_bound_claims(None, req,
            {'question': question, 'requested': {}, 'compact_passages': True}, blocks)
    assert not rejected and len(claims) == 1 and claims[0]['text'] == body.text
    return claims[0]


@pytest.mark.asyncio
@pytest.mark.parametrize('code', ['RULE-X', 'RA-21', '0024'])
async def test_quote_keeps_unique_source_code_identity_and_actual_ancestor_headings(code):
    root = block('root', '## Quy định về hồ sơ', kind='heading')
    owner = block('owner', '### Hồ sơ thiết bị', 50, 'heading', 'root')
    body = block('body', 'Cần văn bản kiểm tra và quyết định có chữ ký.', 100, parent='owner')
    alias = row(code)
    claim = await propose([root, owner, body, alias], f'Nếu hồ sơ mã {code} thiếu quyết định thì sao?')
    assert {'owner', 'root', 'alias'} <= {r['block_id'] for r in claim['references'][1:]}
    assert claim['references'][0]['block_id'] == 'body'
    assert claim['references'][0]['quote'] == body.text
    assert all(r['source_revision_id'] == 'r' and r['canonical_hash'] == 'hash' for r in claim['references'])
    assert len(claim['references']) <= 4


@pytest.mark.asyncio
@pytest.mark.parametrize('foreign', ['binding_id', 'index_revision_id', 'source_revision_id', 'canonical_hash'])
async def test_same_code_from_another_immutable_source_cannot_supply_scope(foreign):
    body = block('body', 'Cần quyết định có chữ ký.', 100)
    claim = await propose([body, row(**{foreign: 'other'})], 'Hồ sơ RULE-X có điều kiện gì?')
    assert [r['block_id'] for r in claim['references']] == ['body']


@pytest.mark.asyncio
@pytest.mark.parametrize('question', ['Hồ sơ RULE có điều kiện gì?', 'Hồ sơ RULE-XX có điều kiện gì?'])
async def test_alias_match_cannot_drop_or_extend_code_characters(question):
    claim = await propose([block('body', 'Cần quyết định có chữ ký.', 100), row()], question)
    assert [r['block_id'] for r in claim['references']] == ['body']


@pytest.mark.asyncio
async def test_duplicate_source_code_rows_do_not_pick_an_arbitrary_scope():
    duplicate = row(key='ambiguous')
    duplicate.start, duplicate.end = 500, 500 + len(duplicate.text)
    claim = await propose([block('body', 'Cần quyết định có chữ ký.', 100), row(), duplicate],
                          'Hồ sơ RULE-X có điều kiện gì?')
    assert [r['block_id'] for r in claim['references']] == ['body']


@pytest.mark.asyncio
@pytest.mark.parametrize('broken', ['missing', 'duplicate', 'cycle', 'foreign'])
async def test_ancestry_does_not_guess_through_invalid_or_foreign_units(broken):
    body = block('body', 'Cần quyết định có chữ ký.', 100, parent='owner')
    owner = block('owner', '### Hồ sơ thiết bị', 30, 'heading')
    blocks = [body]
    if broken == 'duplicate':
        blocks += [owner, owner.model_copy(update={'id': 'duplicate', 'start': 60, 'end': 60 + len(owner.text)})]
    elif broken == 'cycle':
        blocks += [owner.model_copy(update={'parent_id': 'owner'})]
    elif broken == 'foreign':
        blocks += [owner.model_copy(update={'canonical_hash': 'foreign'})]
    claim = await propose(blocks, 'Hồ sơ có điều kiện gì?')
    assert [r['block_id'] for r in claim['references']] == ['body']


@pytest.mark.asyncio
async def test_identity_context_cannot_override_an_independent_negative_scope_verdict():
    body = block('body', 'Cần quyết định có chữ ký.', 100)
    alias = row()
    blocks = [body, alias]
    question = 'Hồ sơ RULE-X thuộc nhóm khác đã được chấp thuận chưa?'
    claim = await propose(blocks, question)
    plan = QueryPlan(query=question, requested_topics=['Đủ điều kiện thực tế'])

    async def reject(db, req, contract, instruction, payload, **kwargs):
        return contract.model_validate({'verdicts': [{'claim_id': claim['id'], 'entailed': True,
            'relevant': True, 'scope_compatible': False, 'reason': 'Chưa chứng minh đối tượng thuộc phạm vi.'}],
            'complete': False, 'conflict': False, 'missing_constraints': ['Thiếu phạm vi'],
            'topic_coverage': {'Đủ điều kiện thực tế': False}})

    with patch('app.modules.rag.evidence_verification.structured_call', AsyncMock(side_effect=reject)):
        verified = await verify_bound_answer(None, AskRequest(question=question, collection_id='collection'),
            {'question': question, 'requested': plan.model_dump()}, [claim], blocks, plan, [])
    assert not verified.complete and not verified.claims and verified.errors


@pytest.mark.asyncio
async def test_oversized_identity_row_does_not_crash_quote_binding():
    alias = row()
    # Each catalog sentence fits the quote contract; the WHOLE identity row does
    # not. Test context augmentation rather than an unsupported single huge quote.
    alias.text = '| RULE-X | ' + 'Hồ sơ ' * 380 + '. ' + 'Hồ sơ ' * 380 + '|'
    alias.end = alias.start + len(alias.text)
    claim = await propose([block('body', 'Cần quyết định có chữ ký.', 100), alias], 'Hồ sơ RULE-X thì sao?')
    assert [r['block_id'] for r in claim['references']] == ['body']


@pytest.mark.asyncio
async def test_repeated_code_inside_one_row_is_not_two_different_identity_records():
    alias = row()
    alias.text = '| RULE-X | RULE-X |'
    alias.end = alias.start + len(alias.text)
    claim = await propose([block('body', 'Cần quyết định có chữ ký.', 100), alias], 'Hồ sơ RULE-X thì sao?')
    assert [r['block_id'] for r in claim['references']] == ['body', 'alias']


@pytest.mark.asyncio
async def test_unknown_hash_does_not_authorize_additional_source_scope():
    claim = await propose([block('body', 'Cần quyết định có chữ ký.', 100, canonical_hash=''),
                           row(canonical_hash='')], 'Hồ sơ RULE-X thì sao?')
    assert [r['block_id'] for r in claim['references']] == ['body']


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['literal', 'incomplete', 'scope', 'conflict', 'foreign_context'])
async def test_literal_field_is_source_reporting_but_audit_failures_still_block(fault):
    from app.modules.rag.row_answer import answer_from_rows
    from app.modules.rag.row_answer_contract import build_catalog
    from app.modules.rag.schemas import RetrievalSnapshot
    from app.modules.rag.source_rows import source_rows
    from tests.test_rag_rows_stage3 import fixture_source

    question = ('Theo bảng, điều kiện của mã ZX-018 là gì?' if fault == 'literal' else
                'Hồ sơ ZX-018 đã đủ điều kiện được duyệt chưa?')
    md = '| Mã | Công việc | Điều kiện |\n| --- | --- | --- |\n| ZX-018 | Đối soát | Theo đủ điều kiện Phụ lục IV. |'
    rows = source_rows(*fixture_source(md), question)
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='cc', binding_revisions={'binding_a': 'index_a'})
    catalog = build_catalog(rows, snap, question)
    cells = [k for k, c in catalog.cells.items() if c.value == 'Theo đủ điều kiện Phụ lục IV.']
    assert len(cells) == 1

    async def reader(db, req, contract, instruction, payload, **kwargs):
        if contract.__name__ == 'RowMetricScope':
            return contract.model_validate({'context_ids': [c['id'] for c in payload['introductions']], 'answer_mode': 'cells'})
        if contract.__name__ == 'RowSelection':
            return contract.model_validate({'status': 'selected', 'cell_ids': cells})
        return contract.model_validate({'compatible': True, 'scope_supported': fault != 'scope',
            'complete': fault != 'incomplete', 'conflict': fault == 'conflict', 'required_cell_ids': cells,
            'required_context_ids': ['foreign'] if fault == 'foreign_context' else [],
            'missing_constraints': ['Chưa có bằng chứng hồ sơ đáp ứng quy định.'] if fault == 'incomplete' else []})

    with patch('app.modules.rag.row_answer.structured_call', AsyncMock(side_effect=reader)):
        response = await answer_from_rows(None, AskRequest(question=question, collection_id='cc'), snap, rows)
    assert (response.status == 'answered') is (fault == 'literal')
    if fault == 'literal':
        assert 'Theo đủ điều kiện Phụ lục IV.' in response.answer and response.citations
        assert response.answer_decision['cells'][0]['value'] == 'Theo đủ điều kiện Phụ lục IV.'
    else:
        assert not response.citations


@pytest.mark.asyncio
@pytest.mark.parametrize('foreign,negative_audit,complete', [(False, False, True), (True, False, False), (False, True, False)])
async def test_exact_public_clause_requires_bound_owner_but_not_a_model_written_link(foreign, negative_audit, complete):
    body = block('p', 'Chỉ hồ sơ thiết bị; cần quyết định hợp lệ.', 100)
    clauses = ['Chỉ hồ sơ thiết bị;', 'cần quyết định hợp lệ.']
    claims = [{'id': key, 'text': quote,
        'references': [bind_quote(QuoteReference(block_id=body.id, quote=quote), {body.id: body})]}
        for key, quote in zip(['a', 'b'], clauses)]
    if foreign:
        for c in claims:
            c['references'][0]['canonical_hash'] = 'another'
    plan = QueryPlan(query='Quy định nào?', requested_topics=['Điều kiện'])

    async def reader(db, req, contract, instruction, payload, **kwargs):
        if 'verdicts' in contract.model_fields:
            data = {'verdicts': [{'claim_id': c['id'], 'entailed': True, 'relevant': True,
                'scope_compatible': True, 'reason': ''} for c in claims], 'complete': True,
                'conflict': False, 'missing_constraints': [], 'topic_coverage': {'Điều kiện': True}}
        else:
            data = {'claims': [{'claim_id': c['id'], 'all_assertions_supported': True} for c in claims],
                'essential_conditions': [], 'complete': not negative_audit, 'missing_constraints': [],
                'source_conditions': [{'clause_id': key, 'required': True, 'retained_by': []}
                    for key in payload['source_conditions']]}
        return contract.model_validate(data)

    with patch('app.modules.rag.evidence_verification.structured_call', AsyncMock(side_effect=reader)):
        result = await verify_bound_answer(None, AskRequest(question=plan.query, collection_id='collection'),
            {'question': plan.query, 'requested': plan.model_dump()}, claims, [body], plan, [])
    assert result.complete is complete


@pytest.mark.parametrize('mutation', ['', 'binding_id', 'index_revision_id', 'source_revision_id', 'canonical_hash', 'span', 'text', 'duplicate'])
def test_clause_owner_hints_require_the_actual_public_span_and_full_identity(mutation):
    from app.modules.rag.evidence_indexed_audit import audit_payload

    body = block('p', 'Chỉ hồ sơ thiết bị; cần quyết định hợp lệ.', 100)
    quote = 'Chỉ hồ sơ thiết bị;'
    claim = {'id': 'a', 'text': quote,
        'references': [bind_quote(QuoteReference(block_id=body.id, quote=quote), {body.id: body})]}
    blocks = [body]
    if mutation in {'binding_id', 'index_revision_id', 'source_revision_id', 'canonical_hash'}:
        claim['references'][0][mutation] = 'another'
    elif mutation == 'span':
        claim['references'][0]['start'] += 1
    elif mutation == 'text':
        claim['text'] = 'Tất cả hồ sơ.'
    elif mutation == 'duplicate':
        blocks.append(body.model_copy())
    payload, _ = audit_payload({'claims': [claim]}, blocks)
    owners = payload.get('source_condition_claims', {})
    target = next(key for key, text in payload['source_conditions'].items() if text == quote)
    assert (owners.get(target) == ['a']) is (not mutation)


@pytest.mark.parametrize('ids,hint,expected_gap', [
    ([], ['a'], False), (['b'], ['a'], False), (['unknown'], ['a'], True),
    ([], ['unknown'], True), ([], ['b'], True), ([], [], True),
])
def test_literal_condition_id_repair_never_accepts_unknown_ids_or_absent_text(ids, hint, expected_gap):
    from app.modules.rag.source_scope_audit import SourceConditionCheck, condition_gaps

    clauses = {'e1.c0': 'Không miễn xác nhận an toàn.'}
    public = {'a': clauses['e1.c0'], 'b': 'Một quy định khác.'}
    checks = [SourceConditionCheck(clause_id='e1.c0', required=True, retained_by=ids)]
    assert bool(condition_gaps(clauses, checks, public, {'e1.c0': hint})) is expected_gap


@pytest.mark.parametrize('projection', ['block', 'passage', 'compact_passage', 'reference'])
def test_model_table_projection_preserves_position_without_calling_it_a_subject_scope(projection):
    from app.modules.rag.evidence_context import compact_claim_context, model_context
    from app.modules.rag.evidence_passages import compact_passage_payload, passage_payload

    b = row('RULE-X')
    b.section = 'Quy định nhóm khác / Vị trí bảng tổng hợp'
    claim = {'id': 'c', 'text': b.text,
        'references': [bind_quote(QuoteReference(block_id=b.id, quote=b.text), {b.id: b})]}
    original = b.model_dump()
    catalog = passage_catalog([b])
    if projection == 'block':
        result = model_context([b])['evidence'][0]
    elif projection == 'passage':
        result = passage_payload([b], catalog)[0]
    elif projection == 'compact_passage':
        result = compact_passage_payload([b], catalog)[0]
    else:
        result = compact_claim_context({}, [claim])['reference_catalog']['ref0']
    assert 'section' not in result
    assert result['document_position']['section'] == b.section
    assert result['document_position']['role'] == 'location_only'
    assert result['table_row']['cells'] == ['RULE-X', 'Hồ sơ thiết bị']
    assert result['table_row']['scope_authority'] == 'explicit_row_and_applicable_source_rules'
    assert claim['references'][0]['section'] == b.section and b.model_dump() == original
