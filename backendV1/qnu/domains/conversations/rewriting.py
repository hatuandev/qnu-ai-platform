"""Route every turn through ModelOps and resolve source-bound follow-ups in one call."""

import asyncio

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.conversations import guardrails
from qnu.domains.conversations.access import checkpoint
from qnu.domains.conversations.models import Conversation, ConversationTurn
from qnu.domains.conversations.prefilter import classify_turn, compare_route
from qnu.domains.conversations.routing import (
    ROUTING_VERSION,
    RoutedTurn,
    messages_for,
    routed_turn_schema,
)
from qnu.domains.conversations.schemas import DirectReply
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.public_api import resolve_chat_runtime
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.rag.answer.hygiene import clean_text, has_vietnamese, looks_foreign
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, Conflict
from qnu.ports.chat_model import ChatMessage, ChatModel, ChatResponseError
from qnu.ports.provider_execution import bind_usage

HISTORY_ANSWER_MAX_CHARS = 600
HISTORY_NOTE = (
    "Một phần lịch sử hội thoại cũ đã được lược bớt do giới hạn ngân sách; "
    "không suy đoán nội dung đã lược bớt."
)
EMPTY_REPLY = "Mình chưa thể trả lời câu này ngay bây giờ. Bạn thử lại giúp mình nhé."


def _history_answer(result: dict | None) -> str:
    """Keep the assistant's own earlier wording for continuity, never as evidence."""
    if not result:
        return ""
    text = result.get("answer") or result.get("message") or ""
    return text.strip()[:HISTORY_ANSWER_MAX_CHARS]


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
    turns = list(zip(rows, [r.question for r in rows], [_history_answer(r.result) for r in rows]))
    limit = get_settings().CONVERSATION_HISTORY_MAX_BYTES
    total = sum(len(q.encode()) + len(a.encode()) for _, q, a in turns)
    dropped = 0
    while turns and total > limit:
        _, question, answer = turns.pop(0)
        total -= len(question.encode()) + len(answer.encode())
        dropped += 1
    turn.history_turn_ids = [row.id for row, _, _ in turns]
    history = [question for _, question, _ in turns]
    answers = [answer for _, _, answer in turns]
    prefilter = classify_turn(turn.question, has_history=bool(turns))
    guard_categories = guardrails.categories(config)
    schema = routed_turn_schema(guardrail=bool(guard_categories))
    messages = messages_for(
        turn.question,
        history,
        answers,
        config,
        HISTORY_NOTE if dropped else None,
        guard_categories or None,
    )
    await checkpoint(db, actor, turn)
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        conversation.workspace_id,
        messages,
        provider_id=config["chat_provider_id"],
        task="answer",
        max_output_tokens=config["max_output_tokens"],
        output_schema=schema,
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
        "reasoning": runtime.reasoning_trace(),
        "prefilter": prefilter,
    }
    if dropped:
        turn.rewrite_trace["history"] = {
            "limit_bytes": limit,
            "kept_turns": len(turns),
            "dropped_turns": dropped,
            "note": HISTORY_NOTE,
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
    prefilter["router_route"] = value.route
    prefilter["agreement"] = compare_route(prefilter["verdict"], value.route)
    if value.route == "guardrail" and value.guardrail_category not in guard_categories:
        raise AppException(
            "Model chọn nhóm guardrail không được bật cho trợ lý.",
            code="conversation_route_invalid",
            status_code=502,
            title="Phản hồi mô hình không hợp lệ",
        )
    if guard_categories:
        turn.rewrite_trace["guardrail"] = {
            "version": guardrails.VERSION,
            "policy": {"categories": guard_categories},
            "route": value.route,
            "category": value.guardrail_category,
        }
    if value.needs_clarification and turn.turn_no > 1:
        raise Conflict(
            "Câu hỏi nối tiếp chưa rõ chủ thể; cần hỏi đầy đủ hơn.",
            code="conversation_clarification_required",
        )
    turn.resolved_question = value.standalone_question.strip() if history else turn.question
    reply = None
    if value.route != "knowledge" and value.answer is not None:
        answer, hygiene = clean_text(value.answer)
        if not answer:
            answer = EMPTY_REPLY
            hygiene["fallback"] = True
        if value.route == "guardrail":
            answer, hygiene, guard_trace = await _guardrail_reply(
                db,
                actor,
                conversation,
                turn,
                model,
                messages,
                runtime=runtime,
                inference_hash=inference_hash,
                schema=schema,
                category=value.guardrail_category,
                answer=answer,
                hygiene=hygiene,
            )
            turn.rewrite_trace["guardrail"].update(guard_trace)
        hygiene["language_mismatch"] = has_vietnamese(turn.question) and looks_foreign(answer)
        turn.rewrite_trace["hygiene"] = hygiene
        reply = DirectReply(id=turn.id, route=value.route, answer=answer)
    await db.commit()
    return reply, runtime.provider_id


async def _guardrail_reply(
    db: AsyncSession,
    actor: AuthActor,
    conversation: Conversation,
    turn: ConversationTurn,
    model: ChatModel,
    messages: list[ChatMessage],
    *,
    runtime,
    inference_hash: str,
    schema: dict,
    category: str,
    answer: str,
    hygiene: dict,
) -> tuple[str, dict, dict]:
    found = guardrails.violations(answer)
    detail = {
        "checks": list(guardrails.CHECKS),
        "directive_only": list(guardrails.DIRECTIVE_ONLY),
        "violations": found,
        "retry": "none",
    }
    if not found:
        return answer, hygiene, detail
    config = conversation.assistant_snapshot
    retry_messages = [
        ChatMessage("system", messages[0].content + "\n" + guardrails.retry_note(found)),
        *messages[1:],
    ]
    _, request, budget = await prepare_chat_request(
        db,
        actor,
        conversation.workspace_id,
        retry_messages,
        provider_id=config["chat_provider_id"],
        task="answer",
        max_output_tokens=config["max_output_tokens"],
        output_schema=schema,
    )
    usage = await usage_service.reserve(
        db,
        actor,
        conversation.workspace_id,
        "chat",
        "guardrail:" + turn.id,
        digest(
            {
                "messages": [m.content for m in retry_messages],
                "config": inference_hash,
                "version": guardrails.VERSION,
                "category": category,
            }
        ),
        budget.total_reserved_tokens,
        runtime.provider_id,
    )
    await checkpoint(db, actor, turn)
    await db.commit()
    try:
        result = await model.complete(retry_messages, bind_usage(request, usage.id))
    except ChatResponseError as exc:
        await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
        raise
    except (Exception, asyncio.CancelledError):
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise
    await usage_service.settle(db, usage.id, total_tokens=result.total_tokens)
    await checkpoint(db, actor, turn)
    await _check_runtime(db, conversation, runtime.provider_id, inference_hash)
    detail["retry"] = "model"
    detail["retry_usage_id"] = usage.id
    detail["retry_total_tokens"] = result.total_tokens
    try:
        retried = RoutedTurn.model_validate_json(result.content)
    except (ValidationError, ValueError):
        detail["retry_result"] = "invalid"
        return _guardrail_fallback(detail)
    if (
        retried.route != "guardrail"
        or retried.guardrail_category != category
        or retried.answer is None
    ):
        detail["retry_result"] = "route_changed"
        return _guardrail_fallback(detail)
    retried_answer, retried_hygiene = clean_text(retried.answer)
    remaining = guardrails.violations(retried_answer) if retried_answer else ["empty"]
    if remaining:
        detail["retry_result"] = "still_violating"
        detail["retry_violations"] = remaining
        return _guardrail_fallback(detail)
    detail["retry_result"] = "clean"
    return retried_answer, retried_hygiene, detail


def _guardrail_fallback(detail: dict) -> tuple[str, dict, dict]:
    answer, hygiene = clean_text(guardrails.FALLBACK)
    hygiene["fallback"] = True
    return answer, hygiene, detail


async def _check_runtime(
    db: AsyncSession, conversation: Conversation, provider_id: str, inference_hash: str
) -> None:
    current = await resolve_chat_runtime(db, conversation.workspace_id, provider_id)
    if current.inference_configuration_hash("answer") != inference_hash:
        raise Conflict("Model đã đổi khi điều phối hội thoại.", code="chat_provider_changed")
