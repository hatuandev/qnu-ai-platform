"""Shared chat routing regressions: external services must be unreachable for social turns."""
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.rag.schemas import AskRequest, AskResponse
from app.modules.rag.service import rag_service
from tests.intent_routing_cases import CASES


@pytest.mark.asyncio
@pytest.mark.parametrize('text', ['xin chào', 'Xin Chào!', 'chao ban', 'Hello', 'Cảm ơn bạn nhiều nhé', 'tạm biệt'])
async def test_pure_social_never_enters_knowledge_pipeline(text):
    request = AskRequest(question=text, collection_id='test-col', assistant_code='test-assistant')
    with patch.object(rag_service, '_ask', AsyncMock(return_value=AskResponse(
        status='insufficient_context', answer='No evidence'))) as knowledge:
        result = await rag_service.ask(AsyncMock(), request)
    knowledge.assert_not_awaited()
    assert result.status == 'answered' and result.answer and not result.citations


@pytest.mark.asyncio
async def test_social_stream_does_not_announce_document_retrieval():
    from app.modules.assistants.schemas import AssistantChatRequest
    from app.modules.assistants.services.assistant_rag_chat import stream_rag_chat

    with patch('app.modules.assistants.services.assistant_rag_chat.chat_with_rag', AsyncMock(
        return_value={'unused': True})):
        generator = stream_rag_chat(AsyncMock(), None, AssistantChatRequest(message='Xin chào'), None, [])
        first = await anext(generator)
        await generator.aclose()
    assert 'retrieving' not in first and 'tìm kiếm tài liệu' not in first


@pytest.mark.asyncio
@pytest.mark.parametrize('text,intent,requires_rag', CASES)
async def test_labeled_utterance_routes_without_a_model_for_certain_cases(text, intent, requires_rag):
    from app.modules.rag.conversation_router import route_turn

    req = AskRequest(question=text, collection_id='test-col', assistant_code='custom')
    with patch('app.modules.rag.conversation_resolution.structured_call', AsyncMock()) as model:
        _, resolution, direct = await route_turn(AsyncMock(), req)
    assert req._intent_trace['intent'] == intent
    assert req._intent_trace['requires_rag'] is requires_rag
    assert bool(direct) == (intent in {'SOCIAL', 'ASSISTANT_META'})
    assert bool(resolution) == (intent == 'CLARIFICATION')
    model.assert_not_awaited()


def test_dataset_has_at_least_one_hundred_distinct_utterances():
    assert len(CASES) >= 100 and len({text for text, _, _ in CASES}) == len(CASES)
