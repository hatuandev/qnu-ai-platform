"""Regression for source paragraph fidelity, literal inventory and year scope."""
import hashlib
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document
from app.modules.knowledge.services.wiki_compiler import compile_wiki, digest, validate_wiki_bundle
from app.modules.knowledge.wiki_schemas import WikiPolicy, WikiSelection
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.evidence_validation import validate_plan_years


@pytest.mark.parametrize('question,years', [
    ('So sánh phương hướng2024 và kế hoạch2026', [2024, 2026]),
    ('báo cáo2025 viện dẫn văn bản2024', [2024, 2025]),
    ('Có dữ liệu năm2027 không?', [2027]),
    ('năm2024–2026', [2024, 2025, 2026]),
    ('Ngày 22/12/2023', [2023]),
])
def test_attached_year_scope(question, years):
    validate_plan_years(QueryPlan(query=question, years=years), question, [], None)


@pytest.mark.parametrize('question', ['AM-2024', 'Mã20241234', '2024A', '1.2024', 'X_2024_Y'])
def test_identifier_is_not_permission_to_invent_a_year(question):
    with pytest.raises(ValueError):
        validate_plan_years(QueryPlan(query=question, years=[2024]), question, [], None)


def test_search_variant_cannot_add_an_attached_year_and_history_is_only_used_when_requested():
    with pytest.raises(ValueError):
        validate_plan_years(QueryPlan(query='năm2027', years=[2024]), 'năm2024', [], None)
    validate_plan_years(QueryPlan(query='tiếp tục', years=[2024], uses_history=True),
        'tiếp tục', [{'content': 'năm2024'}], None)


def document(parts, native):
    items = [SimpleNamespace(label='text', text=p, parent=SimpleNamespace(cref='#/body',
        resolve=lambda doc: SimpleNamespace(label='body')),
        self_ref=f'#/texts/{i}') for i, p in enumerate(parts)]
    engine = SimpleNamespace(iterate_items=lambda: [(item, 1) for item in items], tables=[])
    evidence = {'paragraphs': [{'text': text, 'locator': f'word/document.xml#p{i}',
        'style': [], 'numbering': None, 'notes': [], 'table': None} for i, text in enumerate(native, 1)]}
    return build_qnu_structured_document(engine, filename='fixture.docx', sha256='a'*64,
        projection_markdown='\n\n'.join(parts), source_evidence=evidence)


def test_fragments_rejoin_only_a_unique_complete_native_paragraph_and_keep_raw_proof():
    parts = ['Ngày ', '25', '/05/2024 (', 'bản dự thảo', ').']
    source = 'Ngày 25/05/2024 (bản dự thảo).'
    result = document(parts, [source])
    assert [b.body for b in result.blocks] == [source]
    proof = result.blocks[0].source_data['native_paragraph_reconciliation']
    assert [p['text'] for p in proof['fragments']] == parts
    assert proof['locator'] == 'word/document.xml#p1'
    assert proof['sha256'] == hashlib.sha256(source.encode()).hexdigest()


@pytest.mark.parametrize('native', [['Alpha', 'North'], ['AlphaNorth', 'AlphaNorth'], ['Alpha East'],
                                   ['Alpha', 'North', 'AlphaNorth']])
def test_no_merging_across_native_paragraphs_duplicates_or_missing_text(native):
    assert [b.body for b in document(['Alpha', 'North'], native).blocks] == ['Alpha', 'North']


def source(text):
    from app.modules.knowledge.services.source_artifact import build_source_artifact
    return SimpleNamespace(id='r602', binding_id='b602', canonical_markdown=text,
        canonical_hash=hashlib.sha256(text.encode()).hexdigest(),
        snapshot_metadata={'title': 'Nguồn kiểm thử'}, parse_provenance={
            'structured_artifact': build_source_artifact(text, 1, {})})


async def selector(contract, instruction, payload):
    return WikiSelection(pages=[{'kind': 'source', 'title': payload['source']['title'],
        'unit_ids': [payload['units'][0]['id']]}])


@pytest.mark.asyncio
async def test_long_inventory_is_paged_without_dropped_units_and_tamper_is_rejected():
    from app.modules.knowledge.services.wiki_compiler import source_units
    item = source('\n\n'.join(f'Đoạn văn độc lập thứ {i}.' for i in range(520)))
    policy = WikiPolicy(render_mode='extractive', compiler_version='qnu-wiki-compiler/v3')
    bundle = await compile_wiki(item, 'c602', policy, selector)
    pages = [p for p in bundle['pages'] if p['kind'] == 'source']
    assert len(pages) == 2 and all(len(p['sections']) <= 512 for p in pages)
    expected = {u.id for u in source_units(item) if not u.is_container}
    assert {s['excerpt_unit_id'] for p in pages for s in p['sections']} == expected
    assert pages[0]['next_page_id'] == pages[1]['id']
    validate_wiki_bundle(bundle, item, 'c602')
    changed = deepcopy(bundle)
    changed['pages'][0]['next_page_id'] = 'foreign'
    changed['sha256'] = digest({k: v for k, v in changed.items() if k != 'sha256'})
    with pytest.raises(AppException):
        validate_wiki_bundle(changed, item, 'c602')


@pytest.mark.asyncio
async def test_legitimate_short_literal_is_retained_without_turning_into_a_fact():
    item = source('Dấu nguồn chưa định nghĩa.\n\n?\n\n0')
    bundle = await compile_wiki(item, 'c602', WikiPolicy(render_mode='extractive'), selector)
    text = '\n'.join(s['text'] for p in bundle['pages'] for s in p['sections'])
    assert '?' in text and '0' in text and bundle['usage'] == 'navigation_only'
    validate_wiki_bundle(bundle, item, 'c602')
