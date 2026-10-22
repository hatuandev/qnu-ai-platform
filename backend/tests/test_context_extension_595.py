"""Temporal roles, coordinated referents and bounded wiki views, using synthetic sources."""
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.knowledge.services.wiki_compiler import render_page
from app.modules.knowledge.wiki_schemas import WikiPage, WikiReadAction
from app.modules.rag.conversation_resolution import FollowupResolution, _valid_contextual_query
from app.modules.rag.conversation_router import route_turn
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.intent_contracts import ContextReferent
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.wiki_context import read_wiki_context


def resolution(query, refs):
    return FollowupResolution(mode='followup', intent='KNOWLEDGE_FOLLOWUP', antecedent_id=0,
        question=query, referents=[ContextReferent(field=field, value=value, source_turn=turn, quote=quote)
            for field, value, turn, quote in refs])


@pytest.mark.parametrize('old,current,rewritten,refs,valid', [
    (['Học phí ngành Delta năm 2030?'], 'Còn năm học 2031-2032?',
     'Học phí ngành Delta năm 2031-2032?', [('program','Delta',0,'Delta'),
        ('academic_year','2031-2032',-1,'năm học 2031-2032')], False),
    (['Học phí ngành Delta năm 2030?'], 'Còn năm học 2031-2032?',
     'Học phí ngành Delta năm học 2031-2032?', [('program','Delta',0,'Delta'),
        ('academic_year','2031-2032',-1,'năm học 2031-2032')], True),
    (['Học phí ngành Delta năm học 2031-2032?'], 'Còn học phí?',
     'Học phí ngành Delta năm 2031-2032?', [('program','Delta',0,'Delta'),
        ('academic_year','2031-2032',0,'năm học 2031-2032')], False),
    (['So sánh học phí ngành Delta và ngành Epsilon năm 2030?'], 'Còn học phí?',
     'So sánh học phí ngành Delta và ngành Epsilon năm 2030?',
     [('program','Delta',0,'Delta'),('program','Epsilon',0,'Epsilon'),('calendar_year','2030',0,'2030')], True),
    (['Bảng 4: học phí ngành Delta năm 2030?', 'Bảng 5: học phí ngành Delta năm 2030?'],
     'Đối chiếu Bảng 4 và Bảng 5 về học phí.',
     'Đối chiếu học phí ngành Delta năm 2030 trong Bảng 4 và Bảng 5.',
     [('program','Delta',1,'Delta'),('source_locator','Bảng 4',0,'Bảng 4'),
      ('source_locator','Bảng 5',1,'Bảng 5'),('calendar_year','2030',1,'2030')], True),
    (['Học phí ngành Delta năm 2030?', 'Học phí ngành Epsilon năm 2030?'],
     'So sánh học phí của hai ngành đó.', 'So sánh học phí ngành Delta và ngành Epsilon năm 2030?',
     [('program','Delta',0,'Delta'),('program','Epsilon',1,'Epsilon'),('calendar_year','2030',1,'2030')], True),
    (['Học phí ngành Delta năm 2030?', 'Học phí ngành Epsilon năm 2030?'],
     'Còn học phí?', 'Học phí ngành Delta và ngành Epsilon năm 2030?',
     [('program','Delta',0,'Delta'),('program','Epsilon',1,'Epsilon'),('calendar_year','2030',1,'2030')], False),
], ids=['explicit-academic-lost','explicit-academic-kept','inherited-academic-lost',
        'two-programs','two-tables','compare-across-turns','unrequested-comparison'])
def test_temporal_and_multi_referent_scope(old, current, rewritten, refs, valid):
    assert _valid_contextual_query(resolution(rewritten, refs), current, old) is valid


@pytest.mark.parametrize('role,label', [('academic_year','năm học'),('publication_year','năm ban hành'),
    ('effective_year','năm hiệu lực'),('event_year','năm tổ chức'),('data_year','năm dữ liệu')])
@pytest.mark.parametrize('inherited', [False,True])
def test_each_explicit_year_role_survives_a_current_or_inherited_scope(role,label,inherited):
    old=[f'Học phí ngành Delta {label} 2030?']
    current='Còn học phí?' if inherited else f'Còn {label} 2031?'
    year='2030' if inherited else '2031'
    refs=[('program','Delta',0,'Delta'),(role,year,0 if inherited else -1,label+' '+year)]
    good=f'Học phí ngành Delta {label} {year}?'
    assert _valid_contextual_query(resolution(good,refs),current,old)
    assert not _valid_contextual_query(resolution(good.replace(label,'năm'),refs),current,old)


def test_publication_and_data_years_cannot_be_swapped():
    old=['Học phí ngành Delta năm dữ liệu 2030, năm ban hành 2031?']
    refs=[('program','Delta',0,'Delta'),('data_year','2030',0,'năm dữ liệu 2030'),
          ('publication_year','2031',0,'năm ban hành 2031')]
    assert _valid_contextual_query(resolution(old[0],refs),'Còn học phí?',old)
    bad='Học phí ngành Delta năm dữ liệu 2031, năm ban hành 2030?'
    assert not _valid_contextual_query(resolution(bad,refs),'Còn học phí?',old)


def test_reference_role_itself_must_be_supported_by_the_quoted_user_turn():
    old=['Học phí ngành Delta năm học 2030-2031?']
    refs=[('program','Delta',0,'Delta'),('calendar_year','2030-2031',0,'năm học 2030-2031')]
    assert not _valid_contextual_query(resolution(old[0],refs),'Còn học phí?',old)


@pytest.mark.parametrize('field,label', [('program','ngành'),('institution','trường'),
                                       ('program_code','mã'),('source_locator','Bảng')])
def test_two_values_of_one_role_have_individual_proof_and_no_missing_member(field,label):
    a,b=('Bảng 4','Bảng 5') if field=='source_locator' else ('Delta','Epsilon')
    full_a=a if field=='source_locator' else label+' '+a
    full_b=b if field=='source_locator' else label+' '+b
    old=[f'So sánh học phí {full_a} và {full_b} năm 2030?']
    refs=[(field,a,0,a),(field,b,0,b),('calendar_year','2030',0,'2030')]
    assert _valid_contextual_query(resolution(old[0],refs),'Còn học phí?',old)
    assert not _valid_contextual_query(resolution(old[0].replace(full_b,'Omega'),refs),'Còn học phí?',old)


def test_unmarked_coordinated_names_can_use_individual_literal_proof():
    old=['So sánh học phí ngành Delta và Epsilon năm 2030?']
    refs=[('program','Delta',0,'Delta'),('program','Epsilon',0,'Epsilon'),('calendar_year','2030',0,'2030')]
    assert _valid_contextual_query(resolution(old[0],refs),'Còn học phí?',old)


def test_two_documents_keep_their_table_associations():
    old=['So sánh tài liệu "Atlas", Bảng 4; tài liệu "Boreal", Bảng 5: học phí ngành Delta năm 2030?']
    refs=[('source','Atlas',0,'Atlas'),('source','Boreal',0,'Boreal'),('source_locator','Bảng 4',0,'Bảng 4'),
        ('source_locator','Bảng 5',0,'Bảng 5'),('program','Delta',0,'Delta'),('calendar_year','2030',0,'2030')]
    assert _valid_contextual_query(resolution(old[0],refs),'Còn học phí?',old)
    bad=old[0].replace('Bảng 4','Bảng 9').replace('Bảng 5','Bảng 4').replace('Bảng 9','Bảng 5')
    assert not _valid_contextual_query(resolution(bad,refs),'Còn học phí?',old)


def test_comparison_retains_the_year_of_each_subject_across_turns():
    old=['Học phí ngành Delta năm 2030?','Học phí ngành Epsilon năm 2031?']
    refs=[('program','Delta',0,'Delta'),('program','Epsilon',1,'Epsilon'),
          ('calendar_year','2030',0,'2030'),('calendar_year','2031',1,'2031')]
    current='So sánh học phí của hai ngành đó.'
    good='So sánh học phí ngành Delta năm 2030 và ngành Epsilon năm 2031?'
    assert _valid_contextual_query(resolution(good,refs),current,old)
    bad='So sánh học phí ngành Delta năm 2031 và ngành Epsilon năm 2030?'
    assert not _valid_contextual_query(resolution(bad,refs),current,old)


def wiki_fixture(length=2600, name='a'):
    text = 'Nguyên tắc thử nghiệm. ' + 'x' * length + ' Ngoại lệ phải được giữ.'
    block = EvidenceBlock(id='r:'+name, unit_id=name, binding_id='b', index_revision_id='i',
        source_revision_id='r', canonical_hash='h', title='Nguồn', text=text, start=0, end=len(text))
    identity = {'collection_id':'c','binding_id':'b','source_revision_id':'r','canonical_hash':'h'}
    model = WikiPage(kind='concept', title='Nguyên tắc '+name, sections=[{'heading':'Quy tắc',
        'text':text, 'references':[{'unit_id':name,'quote':text}]}])
    page = {'id':'page-'+name,'title':model.title,'kind':model.kind,'sections':model.model_dump()['sections'],
        'markdown':render_page(model, identity),'identity':identity,'binding_id':'b','source_revision_id':'r',
        'block_ids':[block.id],'reference_blocks':{name:block.id}}
    return page, block


def request():
    return AskRequest(collection_id='c', question='Nguyên tắc thử nghiệm?')


def snapshot(**kwargs):
    return RetrievalSnapshot(snapshot_id='s', collection_id='c', binding_revisions={'b':'i'},
        knowledge_wiki_enabled=True, **kwargs)


@pytest.mark.asyncio
async def test_one_large_section_fits_global_navigation_without_three_way_split():
    page, block = wiki_fixture(5000)
    assert 14000//3 < len(page['markdown']) < 14000
    req = request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call', AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))):
        selected = await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
    assert selected == [block]
    assert req._wiki_context['pages'][0]['markdown'] == page['markdown']


@pytest.mark.asyncio
async def test_cached_page_is_repacked_when_budget_shrinks_without_resetting_calls():
    page, block = wiki_fixture(2500)
    assert 2000 < len(page['markdown']) < 14000//3
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call', AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))) as model:
        first=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
        second=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],
            candidate_mode=True,max_navigation_chars=2000)
    assert first == [block] and second == []
    assert not req._wiki_context.get('pages')
    assert model.await_count == 1 and req._retrieval_diagnostics['knowledge_wiki']['calls']==1


@pytest.mark.asyncio
async def test_missing_cached_reference_rejects_the_whole_section():
    page, block = wiki_fixture(100)
    note=block.model_copy(update={'id':'r:note','unit_id':'note','text':'Điều kiện không được mất.'})
    page['block_ids'].append(note.id)
    page['reference_blocks']['note']=note.id
    page['sections'][0]['references'].append({'unit_id':'note','quote':note.text})
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages', AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call', AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))) as model:
        await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block,note],candidate_mode=True)
        selected=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
    assert selected==[] and model.await_count==1


@pytest.mark.asyncio
async def test_budget_increase_reuses_selection_without_a_new_model_call():
    page,block=wiki_fixture(5000)
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))) as model:
        small=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],
            candidate_mode=True,max_navigation_chars=2000)
        big=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
    assert small==[] and big==[block] and model.await_count==1


@pytest.mark.asyncio
async def test_multiple_pages_share_real_budget_without_partial_conditions():
    first,a=wiki_fixture(5000,'a');second,b=wiki_fixture(1000,'b')
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[first,second])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[first['id'],second['id']]))):
        selected=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[a,b],
            candidate_mode=True,max_navigation_chars=6000)
    assert selected==[a] and req._wiki_context['pages'][0]['markdown']==first['markdown']
    assert sum(len(p['markdown']) for p in req._wiki_context['pages'])<=6000


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation',['text','hash','index','policy','disabled'])
async def test_cache_rechecks_current_source_and_effective_policy(mutation):
    page,block=wiki_fixture(2500)
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))) as model:
        first=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
        if mutation=='policy':
            req.runtime_policy={'knowledge_policy':{'wiki_read_policy':{'max_page_chars':2000}}}
        elif mutation=='disabled':
            req.runtime_policy={'knowledge_policy':{'wiki_read_policy':{'enabled':False}}}
        else:
            block=block.model_copy(update={ {'text':'text','hash':'canonical_hash','index':'index_revision_id'}[mutation]:'changed'})
        second=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
    assert first and second==[] and not req._wiki_context.get('pages') and model.await_count==1


@pytest.mark.asyncio
async def test_navigation_reserves_space_for_its_canonical_source_closure():
    page,block=wiki_fixture(5000)
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))):
        selected=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],
            candidate_mode=True,max_navigation_chars=14000,max_total_chars=7000)
    assert selected==[] and not req._wiki_context['pages']


@pytest.mark.asyncio
async def test_shared_cyclic_dependency_is_kept_once_and_never_pulls_another_table():
    page,a=wiki_fixture(100)
    a.fact_context={'context_unit_ids':['note']}
    note=a.model_copy(update={'id':'r:note','unit_id':'note','text':'Ngoại lệ nguồn.',
        'fact_context':{'context_unit_ids':['a']}})
    other=a.model_copy(update={'id':'r:other','unit_id':'other',
        'fact_context':{'context_unit_ids':['note']}})
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))):
        selected=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[a,note,other],candidate_mode=True)
    assert {b.id for b in selected}=={a.id,note.id}


@pytest.mark.asyncio
async def test_changed_snapshot_never_reuses_content_or_resets_model_call_limit():
    page,block=wiki_fixture(100)
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])) as loader, \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))) as model:
        await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[block],candidate_mode=True)
        req._retrieval_diagnostics['knowledge_wiki']['calls']=2
        changed=snapshot().model_copy(update={'binding_revisions':{'b':'other'}})
        assert await read_wiki_context(None,req,changed,QueryPlan(query=req.question),[block],candidate_mode=True)==[]
    assert model.await_count==loader.await_count==1 and not req._wiki_context


@pytest.mark.asyncio
async def test_multi_subject_followup_reaches_router_without_dropping_either_subject():
    old='So sánh học phí ngành Delta và ngành Epsilon năm 2030?'
    req=AskRequest(collection_id='c',assistant_code='fixture',question='Còn học phí?',
        history=[{'role':'user','content':old}])
    refs=[('program','Delta',0,'Delta'),('program','Epsilon',0,'Epsilon'),('calendar_year','2030',0,'2030')]
    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(return_value=resolution(old,refs))):
        effective,decision,_=await route_turn(AsyncMock(),req)
    assert decision['mode']=='followup' and 'Delta' in effective.question and 'Epsilon' in effective.question
    assert req._intent_trace['requires_rag']


@pytest.mark.asyncio
async def test_lost_academic_role_cannot_reach_retrieval_after_a_rejected_repair():
    old='Học phí ngành Delta năm học 2030-2031?'
    req=AskRequest(collection_id='c',assistant_code='fixture',question='Còn học phí?',
        history=[{'role':'user','content':old}])
    refs=[('program','Delta',0,'Delta'),('academic_year','2030-2031',0,'năm học 2030-2031')]
    with patch('app.modules.rag.conversation_resolution.structured_call',AsyncMock(return_value=
            resolution(old.replace('năm học','năm'),refs))) as model:
        _,decision,_=await route_turn(AsyncMock(),req)
    assert decision['mode']=='clarify' and not req._intent_trace['requires_rag'] and model.await_count==2


@pytest.mark.asyncio
async def test_two_sections_can_be_packed_as_one_whole_section_when_total_does_not_fit():
    page,a=wiki_fixture(3000,'a');other,b=wiki_fixture(3000,'b')
    page['sections'].extend(other['sections']);page['block_ids'].append(b.id)
    page['reference_blocks'].update(other['reference_blocks'])
    page['markdown']=render_page(WikiPage(kind=page['kind'],title=page['title'],sections=page['sections']),page['identity'])
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))):
        result=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[a,b],
            candidate_mode=True,max_navigation_chars=5000)
    assert len(result)==1 and len(req._wiki_context['pages'])==1
    assert result[0].text in req._wiki_context['pages'][0]['markdown']


@pytest.mark.asyncio
async def test_shared_note_removal_cannot_return_a_cached_partial_closure():
    page,a=wiki_fixture(100)
    note=a.model_copy(update={'id':'r:note','unit_id':'note','text':'Nguồn điều kiện.'})
    a.fact_context={'context_unit_ids':['note']}
    req=request()
    with patch('app.modules.rag.wiki_context.load_wiki_pages',AsyncMock(return_value=[page])), \
         patch('app.modules.rag.wiki_context.structured_call',AsyncMock(return_value=
               WikiReadAction(action='read_pages',page_ids=[page['id']]))) as model:
        first=await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[a,note],candidate_mode=True)
        with pytest.raises(Exception) as error:
            await read_wiki_context(None,req,snapshot(),QueryPlan(query=req.question),[a],candidate_mode=True)
    assert {b.id for b in first}=={a.id,note.id} and model.await_count==1
    assert getattr(error.value,'code',None)=='EVIDENCE_CONTEXT_MISSING'
