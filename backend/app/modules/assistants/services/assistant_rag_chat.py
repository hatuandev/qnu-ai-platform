"""Knowledge chat orchestration without workflow execution or action dispatch."""

import json
import logging
import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.assistants.runtime import prepare_user_message, resolve_runtime_scope
from app.modules.assistants.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantResponse,
    AssistantRuntimeProfile,
)
from app.modules.conversations.schemas import ConversationCreateMessageRequest
from app.modules.conversations.service import conversation_service
from app.modules.rag.schemas import AskRequest
from app.modules.rag.service import rag_service

logger = logging.getLogger(__name__)


async def record_chat_message(db: AsyncSession, assistant: AssistantResponse,
                              conversation_id: str, sender: str, text: str) -> None:
    try:
        await conversation_service.record_message(db, ConversationCreateMessageRequest(
            thread_id=conversation_id, assistant_code=assistant.code,
            tenant_id=assistant.tenant_id,
            assistant_name=assistant.name, sender=sender, text=text))
    except AppException:
        raise
    except Exception as exc:
        logger.warning("rag_chat_persistence_failed sender=%s error_type=%s", sender, type(exc).__name__)


async def chat_with_rag(db: AsyncSession, assistant: AssistantResponse, request: AssistantChatRequest,
                        profile: AssistantRuntimeProfile, history: list[dict[str, str]],
                        conversation_id: str | None = None) -> AssistantChatResponse:
    tenant, workspace = await resolve_runtime_scope(db, assistant)
    if request.attachments:
        raise AppException("Chat RAG chỉ đối soát kho đã xuất bản. Hãy đưa tài liệu vào kho và xuất bản trước khi hỏi.",
            code="rag_attachments_unsupported", status_code=422)
    conversation_id = conversation_id or request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    profile = profile.model_copy(update={"tenant_id": tenant, "workspace_id": workspace})
    question = prepare_user_message(request.message, profile)
    # Previous turns are user data too: PII must not bypass preparation via history.
    history = [{**turn, "content": prepare_user_message(turn["content"], profile)} for turn in history]
    await record_chat_message(db, assistant, conversation_id, "user", request.message)
    models = profile.model_policy
    result = await rag_service.ask(db, AskRequest(
        question=question, collection_id=profile.collection_id, module_code=assistant.code,
        assistant_code=assistant.code, assistant_revision=profile.assistant_revision,
        tenant_id=tenant, workspace_id=workspace, conversation_id=conversation_id,
        runtime_policy=profile.model_dump(mode="json"), system_prompt=profile.system_prompt,
        history=history, temperature=models.temperature, max_tokens=models.max_tokens,
        thinking_budget=models.thinking_budget, preferred_provider_id=models.preferred_provider_id,
        preferred_model_name=models.primary_model, fallback_model=models.fallback_model,
        fallback_provider_id=models.fallback_provider_id,
        reranker_policy=profile.knowledge_policy.reranker_policy.model_dump(mode="json")))
    await record_chat_message(db, assistant, conversation_id, "assistant", result.answer)
    if result.status == "insufficient_context":
        from app.modules.evaluation.service import evaluation_service

        try:
            await evaluation_service.record_gap(db, assistant_code=assistant.code,
                collection_id=profile.collection_id, question=question)
        except Exception as exc:
            logger.warning("rag_chat_gap_record_failed error_type=%s", type(exc).__name__)
    logger.info("assistant_rag_completed assistant=%s conversation=%s status=%s latency_ms=%s",
                assistant.code, conversation_id, result.status, result.latency_ms)
    return AssistantChatResponse(assistant_code=assistant.code, assistant_name=assistant.name,
        conversation_id=conversation_id, answer=result.answer, status=result.status,
        citations=[citation.model_dump() for citation in result.citations],
        answer_decision=result.answer_decision, latency_ms=result.latency_ms,
        retrieval_diagnostics=result.retrieval_diagnostics,
        suggested_questions=result.suggested_questions or assistant.sample_questions[:3],
        execution_id=None, artifacts=[])


async def stream_rag_chat(db: AsyncSession, assistant: AssistantResponse, request: AssistantChatRequest,
                          profile: AssistantRuntimeProfile, history: list[dict[str, str]]) -> AsyncIterator[str]:
    conversation_id = request.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
    yield "event: status\ndata: " + json.dumps({"stage": "retrieving",
        "message": "Đang tìm kiếm tài liệu đối soát...", "conversation_id": conversation_id}, ensure_ascii=False) + "\n\n"
    try:
        result = await chat_with_rag(db, assistant, request, profile, history, conversation_id)
    except AppException as exc:
        yield "event: error\ndata: " + json.dumps({"code": exc.code,
            "message": exc.message, "conversation_id": conversation_id}, ensure_ascii=False) + "\n\n"
        return
    except Exception:
        logger.exception("rag_chat_stream_failed conversation=%s", conversation_id)
        yield "event: error\ndata: " + json.dumps({"code": "internal_error",
            "message": "Không thể hoàn tất câu trả lời. Vui lòng thử lại.",
            "conversation_id": conversation_id}, ensure_ascii=False) + "\n\n"
        return
    for citation in result.citations:
        yield "event: citation\ndata: " + json.dumps(citation, ensure_ascii=False) + "\n\n"
    # Only verified text is emitted; unverified model drafts never reach the browser.
    yield "event: token\ndata: " + json.dumps({"delta": result.answer}, ensure_ascii=False) + "\n\n"
    yield "event: done\ndata: " + json.dumps(result.model_dump(), ensure_ascii=False) + "\n\n"
