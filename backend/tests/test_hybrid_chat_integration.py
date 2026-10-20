"""Real handler/persistence tests on the task-owned test database, never production."""
import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppException
from app.modules.assistants.router import chat_router
from app.modules.assistants.schemas import AssistantLifecycleConfig, AssistantPersonaScope
from app.modules.assistants.services.assistant_history import recent_knowledge_history
from app.modules.auth.schemas import AuthActor
from app.modules.conversations.models import ConversationMessageModel, ConversationThreadModel
from app.modules.knowledge.models import KnowledgeCollection


@pytest.fixture
async def chat_db():
    engine=create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        transaction=await conn.begin()
        async with AsyncSession(bind=conn,expire_on_commit=False,join_transaction_mode='create_savepoint') as db:
            yield db
        await transaction.rollback()
    await engine.dispose()


async def seed_assistant(db):
    suffix=uuid.uuid4().hex[:12]
    col=KnowledgeCollection(id=f'chat_col_{suffix}',name='Fixture Knowledge',module_code='fixture')
    db.add(col);await db.commit()
    return SimpleNamespace(id=f'assistant_{suffix}',code=f'custom_{suffix}',name='Trợ lý chương trình thử nghiệm',
        is_active=True,tenant_id='tenant_qnu',collection_id=col.id,updated_at=None,sample_questions=[],
        system_prompt='Only use permitted source evidence.',config=AssistantLifecycleConfig(execution_mode='rag',
            persona_scope=AssistantPersonaScope(allowed_topics=['Chương trình đào tạo'])))


def app_for(db):
    app=FastAPI()
    from app.core.exceptions import register_exception_handlers
    register_exception_handlers(app)
    app.include_router(chat_router)
    async def session():yield db
    app.dependency_overrides[get_db]=session
    return app


@pytest.mark.asyncio
@pytest.mark.parametrize('stream',[False,True])
@pytest.mark.parametrize('debug',[False,True])
async def test_handler_social_persists_and_authorized_debug_only(chat_db,stream,debug):
    record=await seed_assistant(chat_db);conversation='conv_'+uuid.uuid4().hex[:12]
    actor=AuthActor(username='fixture-admin',roles=['AI.Admin'])
    from app.modules.rag.service import rag_service
    with (patch('app.modules.assistants.services.assistant_chat_service._get_assistant_service') as lifecycle,
          patch('app.modules.assistants.router.get_current_actor',AsyncMock(return_value=actor)),
          patch.object(rag_service,'_ask',AsyncMock(side_effect=AssertionError('Knowledge called for social'))) as knowledge):
        lifecycle.return_value.get_assistant=AsyncMock(return_value=record)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(chat_db)),base_url='http://test') as client:
            response=await client.post(f'/assistants/{record.code}/chat'+('?debug=true' if debug else ''),
                json={'message':'Xin chào','conversation_id':conversation,'stream':stream})
    assert response.status_code==200,response.text
    if stream:
        assert 'event: done' in response.text and 'event: citation' not in response.text
        assert 'retrieving' not in response.text
        payload=json.loads(response.text.split('event: done\ndata: ')[1].split('\n\n')[0])
    else:payload=response.json()
    assert record.name in payload['answer'] and 'Chương trình đào tạo' in payload['answer']
    assert payload['status']=='answered' and not payload['citations']
    trace=(payload.get('retrieval_diagnostics') or {}).get('intent_routing')
    assert bool(trace)==debug
    if debug:assert trace['intent']=='SOCIAL' and trace['router_model_calls']==0 and trace['rag_invoked'] is False
    knowledge.assert_not_awaited()
    assert response.headers.get('X-Conversation-Token')
    messages=(await chat_db.scalars(select(ConversationMessageModel).where(ConversationMessageModel.thread_id==payload['conversation_id']))).all()
    assert len(messages)==2 and {m.sender for m in messages}=={'user','assistant'}


@pytest.mark.asyncio
@pytest.mark.parametrize('stream',[False,True])
async def test_viewer_cannot_enable_routing_debug_or_write_messages(chat_db,stream):
    record=await seed_assistant(chat_db)
    viewer=AuthActor(username='viewer',roles=['AI.Viewer'],permissions=['ai.assistants.view'])
    with patch('app.modules.assistants.router.get_current_actor',AsyncMock(return_value=viewer)):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(chat_db)),base_url='http://test') as client:
            response=await client.post(f'/assistants/{record.code}/chat?debug=true',json={'message':'Xin chào','stream':stream})
    assert response.status_code==403
    assert await chat_db.scalar(select(func.count()).select_from(ConversationMessageModel))==0


async def seed_history(db,code,turns):
    thread=ConversationThreadModel(id='conv_'+uuid.uuid4().hex[:12],assistant_code=code,assistant_name='Fixture')
    db.add(thread);await db.flush()
    start=datetime(2025,1,1,tzinfo=UTC).replace(tzinfo=None)
    for i,(sender,text) in enumerate(turns):
        db.add(ConversationMessageModel(thread_id=thread.id,sender=sender,text=text,created_at=start+timedelta(seconds=i)))
    await db.commit();return thread


@pytest.mark.asyncio
async def test_many_social_turns_cannot_push_out_knowledge_context(chat_db):
    turns=[('user','Môn học ngành Alpha năm 2026?'),('assistant','Source answer')]
    turns += [('user','Cảm ơn'),('assistant','Rất vui được hỗ trợ')] * 40
    thread=await seed_history(chat_db,'fixture',turns)
    history=await recent_knowledge_history(chat_db,thread.id,'fixture')
    assert [turn['content'] for turn in history if turn['role']=='user']==['Môn học ngành Alpha năm 2026?']
    assert not any(turn['content']=='Cảm ơn' for turn in history)


@pytest.mark.asyncio
async def test_history_is_scoped_to_thread_assistant_and_config_revision(chat_db):
    a=await seed_history(chat_db,'first',[('user','Ngành Alpha năm 2026?')])
    b=await seed_history(chat_db,'second',[('user','Ngành Beta năm 2025?')])
    with pytest.raises(AppException) as error:await recent_knowledge_history(chat_db,a.id,'second')
    assert error.value.status_code==404
    assert (await recent_knowledge_history(chat_db,b.id,'second'))[0]['content']=='Ngành Beta năm 2025?'
    assert await recent_knowledge_history(chat_db,a.id,'first',scope_since=datetime(2025,1,2,tzinfo=UTC))==[]


@pytest.mark.asyncio
async def test_history_database_failure_is_not_silently_treated_as_no_context():
    with pytest.raises(AppException) as error:
        await recent_knowledge_history(AsyncMock(execute=AsyncMock(side_effect=OSError('offline'))),'conv','fixture')
    assert error.value.code=='CONVERSATION_HISTORY_UNAVAILABLE' and error.value.status_code==503


@pytest.mark.asyncio
async def test_conversation_id_alone_does_not_authorize_another_browser_session(chat_db):
    record=await seed_assistant(chat_db)
    thread=await seed_history(chat_db,record.code,[('user','Private previous question')])
    viewer=AuthActor(username='student',roles=['Student'],permissions=['ai.chat.access'])
    with (patch('app.modules.assistants.router.get_current_actor',AsyncMock(return_value=viewer)),
          patch('app.modules.assistants.services.assistant_chat_service._get_assistant_service') as lifecycle):
        lifecycle.return_value.get_assistant=AsyncMock(return_value=record)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(chat_db)),base_url='http://test') as client:
            response=await client.post(f'/assistants/{record.code}/chat',json={'message':'Xin chào','conversation_id':thread.id})
    assert response.status_code==404
    assert await chat_db.scalar(select(func.count()).select_from(ConversationMessageModel).where(ConversationMessageModel.thread_id==thread.id))==1


@pytest.mark.asyncio
async def test_public_client_can_continue_its_own_signed_conversation(chat_db):
    record=await seed_assistant(chat_db)
    with patch('app.modules.assistants.services.assistant_chat_service._get_assistant_service') as lifecycle:
        lifecycle.return_value.get_assistant=AsyncMock(return_value=record)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(chat_db)),base_url='http://test') as client:
            first=await client.post(f'/assistants/{record.code}/chat',json={'message':'Xin chào'})
            assert first.status_code==200
            grant=first.headers['X-Conversation-Token'];cid=first.json()['conversation_id']
            second=await client.post(f'/assistants/{record.code}/chat',json={'message':'Cảm ơn','conversation_id':cid},headers={'X-Conversation-Token':grant})
    assert second.status_code==200 and second.json()['conversation_id']==cid
    assert await chat_db.scalar(select(func.count()).select_from(ConversationMessageModel).where(ConversationMessageModel.thread_id==cid))==4


@pytest.mark.parametrize('wrong_assistant,wrong_conversation',[(True,False),(False,True)])
def test_conversation_capability_cannot_cross_assistant_or_session(wrong_assistant,wrong_conversation):
    from app.modules.assistants.services.conversation_access import issue_grant, verify_grant
    token=issue_grant('assistant-a','conversation-a')
    with pytest.raises(AppException):
        verify_grant(token,'assistant-b' if wrong_assistant else 'assistant-a','conversation-b' if wrong_conversation else 'conversation-a')


def test_conversation_capability_is_not_a_platform_access_token():
    from app.core.security import decode_access_token
    from app.modules.assistants.services.conversation_access import issue_grant
    with pytest.raises((AppException,ValueError)):
        decode_access_token(issue_grant('assistant-a','conversation-a'))


@pytest.mark.asyncio
@pytest.mark.parametrize('path',['/conversations','/conversations/private-conversation'])
async def test_chat_only_actor_cannot_bypass_ownership_through_admin_history_api(chat_db,path):
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.conversations.router import router
    app=app_for(chat_db);app.include_router(router)
    async def student():return AuthActor(username='student',roles=['Student'],permissions=['ai.chat.access'])
    app.dependency_overrides[get_current_actor]=student
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        result=await client.get(path)
    assert result.status_code==403


@pytest.mark.asyncio
async def test_deleted_thread_cannot_be_resurrected_by_an_old_capability(chat_db):
    from app.modules.assistants.services.conversation_access import (
        authorize_conversation,
        issue_grant,
    )
    token=issue_grant('fixture','conv_gone')
    with pytest.raises(AppException) as error:await authorize_conversation(chat_db,'fixture','conv_gone',token)
    assert error.value.status_code==404


@pytest.mark.asyncio
async def test_new_anonymous_clients_do_not_share_a_client_chosen_conversation_id(chat_db):
    from app.modules.assistants.services.conversation_access import authorize_conversation
    first,_=await authorize_conversation(chat_db,'fixture','shared-client-id',None)
    second,_=await authorize_conversation(chat_db,'fixture','shared-client-id',None)
    assert first!=second and first!='shared-client-id' and second!='shared-client-id'
