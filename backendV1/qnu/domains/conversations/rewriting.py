"""Route every turn through ModelOps and resolve source-bound follow-ups in one call."""

import asyncio

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.conversations.access import checkpoint
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.conversations.routing import ROUTING_VERSION, RoutedTurn, messages_for
from qnu.domains.conversations.schemas import DirectReply
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict
from qnu.ports.chat_model import ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage


async def resolve_turn(
    db: AsyncSession,
    actor: AuthActor,
    conversation: Conversation,
    turn: ConversationTurn,
    model: ChatModel,
) -> tuple[DirectReply | None, str]:
    config = conversation.assistant_snapshot
    count = config["history_turns"]
    rows = (
        list(
            (
                await db.scalars(
                    select(ConversationTurn)
                    .where(
                        ConversationTurn.conversation_id == conversation.id,
                        ConversationTurn.turn_no < turn.turn_no,
                        ConversationTurn.status == "completed",
                        ConversationTurn.result["status"].as_string() != "direct_reply",
                    )
                    .order_by(ConversationTurn.turn_no.desc())
                    .limit(count)
                )
            ).all()
        )
        if count
        else []
    )
    rows.reverse()
    turn.history_turn_ids = [r.id for r in rows]
    history = [r.question for r in rows]
    if sum(len(q.encode()) for q in history) > get_settings().CONVERSATION_HISTORY_MAX_BYTES:
        raise AppException(
            "Lịch sử vượt budget; mở hội thoại mới hoặc giảm history_turns.",
            code="conversation_history_limit",
            status_code=422,
        )
    messages = messages_for(turn.question, history, config)
    await checkpoint(db, actor, turn)
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        conversation.workspace_id,
        messages,
        provider_id=config["chat_provider_id"],
        task="answer",
        reasoning_task="answer",
        max_output_tokens=config["max_output_tokens"],
        output_schema=RoutedTurn.model_json_schema(),
    )
    inference_hash = runtime.inference_configuration_hash("answer")
    usage = await usage_service.reserve(
        db,
        actor,
        conversation.workspace_id,
        "chat",
        "route:" + turn.id,
        digest(
            {
                "messages": [m.content for m in messages],
                "config": inference_hash,
                "version": ROUTING_VERSION,
            }
        ),
        budget.total_reserved_tokens,
        runtime.provider_id,
    )
    turn.rewrite_trace = {
        "version": ROUTING_VERSION,
        "routing": list(runtime.routing_trace),
        "usage_id": usage.id,
        "provider_id": runtime.provider_id,
        "model_name": runtime.model_name,
        "configuration_hash": runtime.configuration_hash,
        "inference_configuration_hash": inference_hash,
        "reasoning": runtime.reasoning_trace("answer"),
    }
    try:
        await checkpoint(db, actor, turn)
        await _check_runtime(db, conversation, runtime.provider_id, inference_hash)
        await db.commit()
    except (Exception, asyncio.CancelledError):
        await usage_service.settle(db, usage.id, total_tokens=0, failed=True)
        raise
    try:
        result = await model.complete(messages, bind_usage(request, usage.id))
    except ChatResponseError as exc:
        await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
        raise
    except (Exception, asyncio.CancelledError):
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
    await checkpoint(db, actor, turn)
    await _check_runtime(db, conversation, runtime.provider_id, inference_hash)
    try:
        value = RoutedTurn.model_validate_json(result.content)
    except (ValidationError, ValueError) as exc:
        raise AppException(
            "Model trả kết quả điều phối hội thoại không hợp lệ.",
            code="conversation_route_invalid",
            status_code=502,
            title="Phản hồi mô hình không hợp lệ",
        ) from exc
    turn.rewrite_trace = {
        **turn.rewrite_trace,
        "total_tokens": result.total_tokens,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "output_budget": result.budget_trace,
        "route": value.route,
        "needs_clarification": value.needs_clarification,
    }
    if value.needs_clarification:
        raise Conflict(
            "Câu hỏi nối tiếp chưa rõ chủ thể; cần hỏi đầy đủ hơn.",
            code="conversation_clarification_required",
        )
    turn.resolved_question = value.standalone_question.strip() if history else turn.question
    await db.commit()
    reply = (
        DirectReply(id=turn.id, route=value.route, answer=value.answer.strip())
        if value.route != "knowledge" and value.answer is not None
        else None
    )
    return reply, runtime.provider_id


async def _check_runtime(
    db: AsyncSession, conversation: Conversation, provider_id: str, inference_hash: str
) -> None:
    current = await resolve_chat_runtime(db, conversation.workspace_id, provider_id)
    if current.inference_configuration_hash("answer") != inference_hash:
        raise Conflict("Model đã đổi khi điều phối hội thoại.", code="chat_provider_changed")
