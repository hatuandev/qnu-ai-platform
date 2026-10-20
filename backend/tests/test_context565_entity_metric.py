"""Source-backed code, quantity and year selection; values here are synthetic."""

from copy import deepcopy

import pytest

from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.services.source_artifact import build_source_artifact, cell_context
from app.modules.knowledge.services.table_context import extract_context_tables, row_identities
from app.modules.rag.query_router import query_classifier
from app.modules.rag.temporal_answer import decide_table_answer


@pytest.mark.parametrize('question', ['Năm 2026 có 100 SV', 'Học phí 1000000 đồng', 'Điểm 6.8'])
def test_numbers_are_not_source_verified_codes(question):
    from app.modules.knowledge.entity_codes import code_candidates
    assert code_candidates(question) == []


@pytest.mark.parametrize('label', ['mã', 'mã chương trình', 'mã ngành', 'mã nhiệm vụ', 'mã CT'])
def test_code_label_words_are_never_candidates(label):
    from app.modules.knowledge.entity_codes import code_candidates
    assert code_candidates(f'Chỉ tiêu {label} zx-0007 năm 2026?') == ['ZX-0007']

MARKDOWN = """| Mã chương trình | Tên chương trình | 2025 / Ghi nhận / Số lượng (SV) | 2026 / Quy mô / Chỉ tiêu (SV) | 2026 / Ghi nhận / Số lượng (SV) | 2027 / Quy mô / Chỉ tiêu (SV) |
| --- | --- | --- | --- | --- | --- |
| ZX-0007 | Chương trình thử A | 80 | 100 | 92 | 110 |
| ZX-0070 | Chương trình thử B | 70 | 78 | 74 | 83 |
"""


@pytest.mark.parametrize('code', ['ZX-0007', 'zx-0007', '0012', 'AB_0120', '7480107'])
def test_explicit_code_candidates_keep_identity_and_leading_zeroes(code):
    analysis = query_classifier.analyze(f'Chỉ tiêu mã {code} năm 2026?')
    assert code.upper() in analysis.entity_codes
    assert '2026' not in analysis.entity_codes


@pytest.mark.parametrize('headers,row,name,code', [
    (['Mã chương trình', 'Tên chương trình', 'Chỉ tiêu'], ['ZX-0007', 'Chương trình A', '100'], 'Chương trình A', 'ZX-0007'),
    (['Tên chương trình', 'Mã chương trình', 'Chỉ tiêu'], ['Chương trình A', 'ZX-0007', '100'], 'Chương trình A', 'ZX-0007'),
    (['Mã', 'Chỉ tiêu'], ['0012', '100'], '0012', '0012'),
    (['Mã', 'Chỉ tiêu'], ['ZX-0007', '100'], 'ZX-0007', 'ZX-0007'),
])
def test_code_column_is_not_a_name_or_metric(headers, row, name, code):
    table = {'header_paths': [[h] for h in headers], 'rows': [row]}
    identities = row_identities(row, table)
    assert len(identities) == 1
    assert identities[0][2:] == (name, code)


@pytest.mark.parametrize('header,role,attribute', [
    ('2026 / Quy mô / Chỉ tiêu (SV)', 'quota', 'expected_quota'),
    ('2026 / Ghi nhận / Số lượng (SV)', 'reported_count', 'reported_count'),
    ('2025 / Ghi nhận / Số lượng (SV)', 'reported_count', 'reported_count'),
    ('2027 / Dự báo / Số lượng ước tính', 'estimate', 'estimated_count'),
    ('2026 / Tỷ lệ (%)', 'rate', 'rate'),
    ('2026 / Số lượng (SV)', None, None),
    ('2026 / Ghi nhận / Chỉ tiêu (SV)', None, None),
])
def test_header_path_disambiguates_quantities(header, role, attribute):
    assert detect_column_role(header)[0] == role
    assert cell_context(header)['attribute_code'] == attribute


@pytest.mark.parametrize('question,expected', [
    ('Chỉ tiêu mã ZX-0007 năm 2026?', ['100']),
    ('Số lượng ghi nhận mã ZX-0007 năm 2026?', ['92']),
    ('Số lượng ghi nhận mã ZX-0007 năm 2025?', ['80']),
    ('Chỉ tiêu mã ZX-0070 năm 2026?', ['78']),
    ('Chỉ tiêu mã ZX-0007 năm 2025?', []),
    ('Chỉ tiêu mã ZX-0007 năm 2098?', []),
    ('Chỉ tiêu mã ZX-0099 năm 2026?', []),
])
def test_derivation_through_temporal_selection_preserves_requested_tuple(question, expected):
    artifact = build_source_artifact(MARKDOWN, 1, {})
    frozen = deepcopy(artifact)
    decision = decide_table_answer(question, artifact['facts'])
    assert decision is not None
    assert [claim['value'] for claim in decision['claim_bindings']] == expected
    assert decision['status'] == ('supported' if expected else 'missing')
    assert artifact == frozen


def test_explicit_code_does_not_inject_static_major_alias():
    analysis = query_classifier.analyze('Chỉ tiêu ngành Công nghệ thông tin mã ZX-0007 năm 2026?')
    assert analysis.entity_codes == ['ZX-0007']


def test_alphanumeric_code_cross_page_continuation_is_source_bound():
    markdown = """<!-- Trang 1 -->
| STT | Mã chương trình | Tên chương trình | Chỉ tiêu 2026 |
| --- | --- | --- | --- |
| 1 | ZX-0007 | Chương trình A | 100 |

<!-- Trang 2 -->
2 | ZX-0070 | Chương trình B | 78 |
"""
    tables = extract_context_tables(markdown, 2)
    assert len(tables) == 2
    assert row_identities(tables[1]['rows'][0], tables[1])[0][3] == 'ZX-0070'


@pytest.fixture
async def legacy_scope():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from test_review536_findings import build_state, snapshot

    from app.modules.rag.evidence_blocks import load_published_blocks
    from app.modules.rag.source_fact_resolution import FactScope

    state = build_state(c4_value='27')
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(all=lambda: [(state.source, state.index, state.binding)])
    blocks = await load_published_blocks(db, snapshot())
    scope = FactScope(['0012345'], blocks=blocks)
    scope.add_source(state.approved, state.index.id, state.source.id)
    expected = next(f for f in state.approved['facts'] if f['raw_data'].get('column_id') == 'c4'
                    and f['raw_data'].get('qnu_block_id') == 'r1')
    record = SimpleNamespace(**{key: deepcopy(expected[key]) for key in ('id', 'entity_name', 'attribute_name', 'attribute_value')},
        entity_code=None, binding_id=state.binding.id, index_revision_id=state.index.id,
        raw_data={**deepcopy(expected['raw_data']), 'source_revision_id': state.source.id})
    return scope, record, state


@pytest.mark.asyncio
async def test_legacy_resolution_keeps_source_and_review_status(legacy_scope):
    scope, record, state = legacy_scope
    original = deepcopy((record.__dict__, state.approved))
    bound = scope.bind(record)
    assert bound['entity_code'] == '0012345'
    assert bound['attribute_value'] == '27'
    assert bound['raw_data']['temporal_context'] == record.raw_data['temporal_context']
    assert bound['raw_data']['source_resolution']['review_status_preserved'] is None
    assert (record.__dict__, state.approved) == original


@pytest.mark.parametrize('key,value', [('source_revision_id', 'other'), ('content_hash', 'b' * 64),
    ('source_unit_id', 'missing'), ('column_id', 'c3'), ('field_state', 'ambiguous'),
    ('unit_manifest_hash', 'wrong'), ('raw_value', '999')])
@pytest.mark.asyncio
async def test_legacy_wrong_coordinates_stay_blocked(legacy_scope, key, value):
    from app.core.exceptions import AppException
    scope, record, _ = legacy_scope
    record.raw_data[key] = value
    with pytest.raises(AppException) as error:
        scope.bind(record)
    assert error.value.code == 'FACT_SOURCE_INVALID'


@pytest.mark.asyncio
async def test_legacy_wrong_binding_or_index_cannot_borrow_a_row(legacy_scope):
    from app.core.exceptions import AppException
    scope, record, _ = legacy_scope
    record.binding_id = 'unpublished-binding'
    with pytest.raises(AppException):
        scope.bind(record)


@pytest.mark.asyncio
async def test_explicit_human_metric_override_is_preserved(legacy_scope):
    scope, record, _ = legacy_scope
    row = next(iter(scope.rows.values()))
    expected = row['expected'][(record.raw_data['source_unit_id'], 'c4')]
    expected['raw_data']['context_review'] = {'status': 'verified', 'actor_id': 'fixture-reviewer'}
    expected['raw_data']['attribute_code'] = 'reported_count'
    record.raw_data = {**deepcopy(expected['raw_data']), 'source_revision_id': record.raw_data['source_revision_id']}
    bound = scope.bind(record)
    assert bound['raw_data']['attribute_code'] == 'reported_count'
    assert bound['raw_data']['context_review'] == expected['raw_data']['context_review']


@pytest.mark.parametrize('question', ['Chỉ tiêu (lớp) mã ZX-0007 năm 2026?', 'Chỉ tiêu mã ZX-0007?'])
def test_wrong_unit_or_missing_year_never_selects_an_adjacent_quantity(question):
    decision = decide_table_answer(question, build_source_artifact(MARKDOWN, 1, {})['facts'])
    assert decision and decision['status'] == 'missing' and not decision['claim_bindings']


def test_current_metric_and_unit_override_stale_rewritten_constraints():
    facts = build_source_artifact(MARKDOWN, 1, {})['facts']
    rewritten = ('Chỉ tiêu (SV) mã ZX-0007 năm 2026?\n'
                 'Yêu cầu hiện tại cần giữ nguyên: Còn số lượng ghi nhận (SV)?')
    decision = decide_table_answer(rewritten, facts, requested_metric='reported_count', requested_unit='SV')
    assert [claim['value'] for claim in decision['claim_bindings']] == ['92']
    wrong_unit = decide_table_answer(rewritten, facts, requested_metric='reported_count', requested_unit='lớp')
    assert wrong_unit['status'] == 'missing' and not wrong_unit['claim_bindings']


def test_code_and_year_do_not_turn_a_narrative_condition_into_a_quantity():
    assert decide_table_answer('Điều kiện áp dụng cho mã ZX-0007 năm 2026 là gì?',
                               build_source_artifact(MARKDOWN, 1, {})['facts']) is None


def test_cutoff_method_is_not_a_quantity_unit():
    context = cell_context('Điểm chuẩn 2026 (THPT)')
    assert context['unit'] is None and context['qualifiers']['method'] == 'THPT'
    md = ('| Mã | Tên | Điểm chuẩn 2026 (THPT) | Điểm chuẩn 2026 (Học bạ) |\n'
          '| --- | --- | --- | --- |\n| ZX-0007 | Chương trình A | 20 | 25 |')
    decision = decide_table_answer('Điểm chuẩn mã ZX-0007 năm 2026 (THPT)?', build_source_artifact(md, 1, {})['facts'])
    assert [claim['value'] for claim in decision['claim_bindings']] == ['20']


def test_row_anchor_exact_codes_are_case_insensitive_and_do_not_match_metric_values():
    from app.modules.rag.source_rows import _matches_row
    header = '| Mã | Tên | Chỉ tiêu 2026 |\n| --- | --- | --- |'
    assert _matches_row(header, '| ZX-0007 | Chương trình A | 100 |', 'Chỉ tiêu mã zx-0007 năm 2026?')
    assert not _matches_row(header, '| ZX-0070 | Chương trình B | ZX-0007 |', 'Chỉ tiêu mã ZX-0007 năm 2026?')
    assert not _matches_row(header, '| ZX-00070 | Chương trình A | 100 |', 'Chỉ tiêu mã ZX-0007 năm 2026?')
    assert not _matches_row(header, '| ZX-0070 | Chương trình A | 100 |', 'Chỉ tiêu Chương trình A mã ZX-0007 năm 2026?')


def test_multi_entity_partial_coverage_is_not_supported():
    artifact = build_source_artifact(MARKDOWN, 1, {})
    facts = [f for f in artifact['facts'] if f['raw_data']['entity_code'] == 'ZX-0007']
    decision = decide_table_answer('Chỉ tiêu mã ZX-0007 và ZX-0070 năm 2026?', facts)
    assert decision['status'] == 'missing'
    assert decision['missing_constraints'] == [{'entity_code': 'ZX-0070', 'attribute': 'expected_quota', 'year': 2026}]


def test_two_source_units_require_explicit_unit():
    md = ('| Mã | Tên | Chỉ tiêu 2026 (SV) | Chỉ tiêu 2026 (lớp) |\n'
          '| --- | --- | --- | --- |\n| ZX-0007 | Chương trình A | 100 | 2 |')
    decision = decide_table_answer('Chỉ tiêu mã ZX-0007 năm 2026?', build_source_artifact(md, 1, {})['facts'])
    assert decision['status'] == 'ambiguous' and not decision['claim_bindings']


def test_fact_resolution_debug_is_not_in_public_telemetry():
    from app.modules.rag.intent_debug import intent_debug_scope
    from app.modules.rag.retrieval_diagnostics import attach_diagnostics
    from app.modules.rag.schemas import AskRequest, AskResponse
    request = AskRequest(question='Chỉ tiêu ZX-0007 năm 2026?', collection_id='fixture')
    request._retrieval_diagnostics = {'fact_resolution': {'selected_fact_ids': ['server-private']}}
    response = AskResponse(answer='Chưa đủ căn cứ', status='insufficient_context', latency_ms=0)
    assert 'fact_resolution' not in attach_diagnostics(request, response).retrieval_diagnostics
    with intent_debug_scope(True):
        assert attach_diagnostics(request, response).retrieval_diagnostics['fact_resolution']['selected_fact_ids'] == ['server-private']


@pytest.mark.parametrize('legacy_attribute', ['reported_count', 'expected_quota'])
@pytest.mark.asyncio
async def test_exact_identity_and_legacy_metric_are_filtered_before_sql_limit(legacy_scope, legacy_attribute):
    from uuid import uuid4

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.database import engine
    from app.modules.knowledge.models import KnowledgeCollection, KnowledgeFact
    from app.modules.rag.facts import fact_layer

    scope, record, _ = legacy_scope
    expected = next(iter(scope.rows.values()))['expected'][(record.raw_data['source_unit_id'], 'c4')]
    expected['raw_data']['attribute_code'] = legacy_attribute
    record.raw_data['attribute_code'] = legacy_attribute
    collection = 'context565-' + uuid4().hex[:12]
    assert engine.url.database.startswith('qnu_test_')
    isolated_engine = create_async_engine(engine.url, poolclass=NullPool)
    async with isolated_engine.connect() as conn:
        transaction = await conn.begin()
        try:
            async with AsyncSession(bind=conn) as db:
                db.add(KnowledgeCollection(id=collection, name='Context565 isolated fixture', module_code='test'))
                await db.flush()
                for number in range(20):
                    db.add(KnowledgeFact(id=f'early-{collection}-{number:03}', collection_id=collection,
                        binding_id=record.binding_id, index_revision_id=record.index_revision_id,
                        entity_name='Other identity', entity_type='table_row', attribute_name='Chỉ tiêu 2026',
                        attribute_value='999', raw_data={'source_unit_id': 'other-row'}))
                db.add(KnowledgeFact(**{k: getattr(record, k) for k in ('entity_name', 'attribute_name', 'attribute_value',
                    'raw_data', 'binding_id', 'index_revision_id')}, id='last-' + collection,
                    collection_id=collection, entity_type='table_row'))
                await db.flush()
                facts = await fact_layer.lookup_facts(db, collection, entity_codes=['0012345'],
                    fact_attributes=['expected_quota'], active_index_revision_ids={record.index_revision_id},
                    source_scope=scope, limit=1)
                assert len(facts) == 1 and facts[0]['id'] == 'last-' + collection
                assert facts[0]['entity_code'] == '0012345'
                assert facts[0]['raw_data']['attribute_code'] == 'expected_quota'
        finally:
            await transaction.rollback()
    await isolated_engine.dispose()
