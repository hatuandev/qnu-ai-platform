"""Navigation must not crowd out explicit source addresses or rule prerequisites."""
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.evidence_policy import EvidencePolicy
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from tests.test_source_answer_scope_575 import block


@pytest.mark.asyncio
async def test_wiki_context_cannot_displace_explicit_article_and_complete_numbered_rule():
    from app.modules.rag.evidence_pipeline import select_context

    heading = block('article', '## Điều 4. Hồ sơ gia hạn', 1000, 'heading')
    rule = [block('condition', '1. Chỉ hồ sơ bị chậm do nơi tiếp nhận tạm đóng.', 1100, 'list', 'article'),
            block('permission', '2. Được dùng xác nhận trực tuyến không quá 21 ngày.', 1200, 'list', 'article'),
            block('exception', '3. Không miễn xác nhận an toàn.', 1300, 'list', 'article')]
    navigation = [block('wiki'+str(i), 'Thông tin chung về hồ sơ và gia hạn '+str(i)+'.', i*100) for i in range(4)]
    req = AskRequest(collection_id='c', question='Điều 4 cho phép gia hạn như thế nào?', reranker_policy={'enabled':False})
    plan = QueryPlan(query=req.question, attribute='gia hạn', question_scope='source_content')
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c', knowledge_wiki_enabled=True)
    with patch('app.modules.rag.evidence_pipeline.retrieve_anchors', AsyncMock(return_value=[])), \
         patch('app.modules.rag.evidence_pipeline.load_published_blocks', AsyncMock(return_value=[*navigation, heading, *rule])), \
         patch('app.modules.rag.evidence_pipeline.reviewed_fact_blocks', AsyncMock(return_value=[])), \
         patch('app.modules.rag.wiki_context.read_wiki_context', AsyncMock(return_value=navigation)):
        selected = await select_context(None, req, snap, plan, EvidencePolicy(context_limit=5), candidate_mode=True)
    assert {b.id for b in rule} <= {b.id for b in selected}


def test_table_body_keeps_its_exact_caption_as_locator_without_borrowing_foreign_caption():
    from app.modules.rag.evidence_blocks import structural_context

    caption = block('cap', 'Bảng 23. Danh sách mã', 10)
    header = block('t:header', '| Mã | Giá trị |\n| --- | --- |', 60, 'table', 't')
    row = block('row', '| ZX-04 | / |', 120, 'table', 't')
    row.header_context = header.text
    foreign = block('foreign', 'Bảng 23. Khác', 50, revision='foreign')
    selected = structural_context([caption, foreign, header, row], row)
    assert caption in selected and foreign not in selected


def test_directed_table_note_cannot_inject_only_one_clause_of_a_numbered_rule():
    from app.modules.rag.evidence_blocks import pack_context

    owner = block('owner', '## Nhánh điều kiện', 10, 'heading')
    rule = [block('p1', '1. Chỉ hồ sơ đã xác thực thuộc phạm vi này.', 100, 'list', 'owner'),
            block('p2', '2. Có thể gia hạn khi có văn bản cho phép.', 200, 'list', 'owner'),
            block('p3', '3. Không miễn yêu cầu an toàn.', 300, 'list', 'owner')]
    table = block('row', '| ZX | 21 ngày |', 500, 'table', 'table')
    table.fact_context['context_unit_ids'] = ['p3']
    selected = pack_context([owner, *rule, table], [table], [], 5, 15000)
    assert {b.id for b in rule} <= {b.id for b in selected}


def test_figure_caption_stops_a_preceding_numbered_rules_unmarked_continuation():
    from app.modules.rag.evidence_dependencies import dependency_groups

    rule = block('rule', '2. Đơn vị phải trả lời đúng hạn.', 10, 'list')
    caption = block('cap', 'Hình 8. Luồng kiểm tra', 100)
    figure = block('image-text', 'Đơn vị A → Đơn vị B → Hội đồng.', 200)
    groups = dependency_groups([rule, caption, figure])
    assert rule not in groups.get(figure.id, [])


def test_source_declaration_styled_as_heading_can_only_be_public_when_explicitly_selected_as_primary():
    from app.modules.rag.evidence_passages import source_grounded_claims
    from tests.test_source_answer_scope_575 import bound

    declaration = block('scope', '## Tài liệu giả lập, không có giá trị áp dụng.', kind='heading')
    content = block('body', 'Phạm vi chỉ là môi trường kiểm thử.', 100)
    claim = bound(declaration)
    assert source_grounded_claims([claim], [declaration]) == []
    selected = source_grounded_claims([claim], [declaration], allow_primary_heading=True)
    assert selected[0]['text'] == declaration.text
    body_claim = bound(content)
    body_claim['references'].extend(claim['references'])
    assert len(source_grounded_claims([body_claim], [declaration,content], allow_primary_heading=True)) == 1


@pytest.mark.asyncio
async def test_reading_document_does_not_inherit_persona_ownership_or_default_year():
    from app.modules.rag import evidence_pipeline as pipeline

    question = 'Điều 4 nêu điều kiện gì?'
    plan = QueryPlan(query='Configured institution rules', question_scope='source_content')
    req = AskRequest(collection_id='c', question=question)
    snap = RetrievalSnapshot(snapshot_id='s', collection_id='c')
    roles = {'target_basis':'assistant_scope', 'target_institution':'Configured institution', 'exam_organizer':None}
    with patch.object(pipeline, 'reference_year', return_value=2037), \
         patch.object(pipeline, 'resolve_institution_scope', AsyncMock(return_value=roles)), \
         patch.object(pipeline, 'structured_call', AsyncMock(return_value=plan)), \
         patch('app.modules.rag.glossary_expansion.resolve_glossary_queries', AsyncMock(return_value=([], {}))), \
         patch.object(pipeline, 'select_context', AsyncMock(return_value=[])):
        result = await pipeline._answer(None, req, snap, EvidencePolicy(), time.perf_counter(), True)
    requested = result.answer_decision['requested']
    assert requested['query'] == question and requested['years'] == [] and requested['target_institution'] is None


def test_table_claim_audit_checks_retrieved_policy_conditions_not_only_its_summary():
    from app.modules.rag.evidence_indexed_audit import audit_payload
    from tests.test_source_answer_scope_575 import bound

    row = block('row', '| ZX | 21 ngày |', kind='table', parent='table')
    condition = block('policy', 'Chỉ được gia hạn khi có xác nhận gốc.', 100, 'list', 'policy-owner')
    foreign = block('foreign', 'Chỉ thuộc nguồn khác.', 200, 'list', revision='other')
    payload, _ = audit_payload({'claims':[bound(row)]}, [row,condition,foreign])
    assert condition.text in payload['source_conditions'].values()
    assert foreign.text not in payload['source_conditions'].values()


@pytest.mark.asyncio
@pytest.mark.parametrize('topic_complete', [False, True])
async def test_evidence_condition_completion_copies_exact_source_then_requires_new_verdict(topic_complete):
    from app.modules.rag.evidence_verification import complete_source_conditions
    from tests.test_source_answer_scope_575 import bound

    b = block('policy', 'Được gia hạn khi có xác nhận. Không miễn an toàn.')
    claim = bound(b, 'Được gia hạn khi có xác nhận.')
    verifier = SimpleNamespace(conflict=False,topic_coverage={'scope':topic_complete})
    first = SimpleNamespace(complete=False,claims=[claim],errors=[],verifier=verifier,
        source_condition_gaps={'e1.c1':'Không miễn an toàn.'},source_qualifier_gaps=[])
    final = SimpleNamespace(complete=True)
    req = AskRequest(collection_id='c',question='Quy định gia hạn?')
    with patch('app.modules.rag.evidence_verification.verify_bound_answer',AsyncMock(return_value=final)) as verify:
        result = await complete_source_conditions(None,req,{},first,[b],QueryPlan(query=req.question,requested_topics=['scope']),[])
    assert result is (final if topic_complete else first)
    assert verify.await_count == int(topic_complete)
    if topic_complete:
        assert any(c['text']=='Không miễn an toàn.' for c in verify.await_args.args[3])


def test_caption_does_not_displace_an_atomic_rule_while_still_retained_and_byte_budgeted():
    from app.modules.rag.evidence_blocks import pack_context

    owner=block('owner','## Quy định',0,'heading')
    rules=[block('p1','1. Hồ sơ phải có xác nhận gốc.',100,'list','owner'),
           block('p2','2. Chỉ gia hạn khi đã có văn bản.',200,'list','owner'),
           block('p3','3. Không miễn yêu cầu an toàn.',300,'list','owner')]
    caption=block('cap','Bảng 23. Tổng hợp quy định',400)
    header=block('t:header','| Mã | Thời gian |\n| --- | --- |',450,'table','t')
    row=block('row','| ZX | 21 ngày |',550,'table','t');row.header_context=header.text
    row.fact_context['context_unit_ids']=['p3','t:header']
    blocks=[owner,*rules,caption,header,row]
    selected=pack_context(blocks,[row],[],4,16000)
    assert {b.id for b in [*rules,caption,row,header]} <= {b.id for b in selected}
    assert pack_context(blocks,[row],[],4,100)==[]
