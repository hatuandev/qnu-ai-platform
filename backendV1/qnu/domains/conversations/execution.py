"""Persist first, call existing answer pipeline once, then commit only a current owned turn."""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.schemas import AssistantRagPolicy
from qnu.domains.conversations.access import checkpoint
from qnu.domains.conversations.history import readable
from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.conversations.rewriting import _history_answer, resolve_turn
from qnu.domains.conversations.schemas import DirectReply, TurnRequest, TurnResponse
from qnu.domains.conversations.service import reserve_turn
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import prepare_chat_request
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.rag.answer.hygiene import clean_text
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import answer
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatModel, ChatResponseError
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.provider_execution import bind_usage
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

logger = get_logger(__name__)


async def _direct_llm_turn(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    conversation,
    turn: ConversationTurn,
    chat: ChatModel,
    provider_id: str | None,
) -> DirectReply:
    config = conversation.assistant_snapshot
    count = config.get("history_turns", 3)
    all_turns = list(
        (
            await db.scalars(
                select(ConversationTurn)
                .where(
                    ConversationTurn.conversation_id == conversation.id,
                    ConversationTurn.turn_no < turn.turn_no,
                )
                .order_by(ConversationTurn.turn_no.asc())
            )
        ).all()
    )
    rows = [t for t in all_turns if t.status == "completed"][-count:] if count else []

    system_prompt = (
        config.get("persona")
        or "Bạn là trợ lý AI của Trường Đại học Quy Nhơn (QNU). Hãy hỗ trợ người dùng chu đáo, thân thiện và chuẩn mực sư phạm."
    )
    if rows:
        system_prompt += (
            "\n\n[LƯU Ý HỘI THOẠI]: Đây là lượt trò chuyện tiếp nối trong phiên. "
            "TUYỆT ĐỐI KHÔNG lặp lại lời chào xã giao ('Chào bạn', 'Xin chào...') hay giới thiệu lại danh tính trợ lý. "
            "Hãy đi thẳng vào giải đáp trọng tâm câu hỏi của người dùng một cách tự nhiên."
        )
    messages = [ChatMessage(role="system", content=system_prompt)]
    for r in rows:
        messages.append(ChatMessage(role="user", content=r.question))
        ans = _history_answer(r.result)
        if ans:
            messages.append(ChatMessage(role="assistant", content=ans))
    effective_question = turn.resolved_question or turn.question
    messages.append(ChatMessage(role="user", content=effective_question))

    temperature = config.get("rag_policy", {}).get("temperature")
    runtime, request, budget = await prepare_chat_request(
        db,
        actor,
        workspace_id,
        messages,
        provider_id=provider_id,
        task="chat",
        max_output_tokens=config.get("max_output_tokens"),
        temperature=temperature,
        json_mode=False,
    )
    inference_hash = runtime.inference_configuration_hash("chat")
    usage = await usage_service.reserve(
        db,
        actor,
        workspace_id,
        "chat",
        "direct_chat:" + turn.id,
        digest(
            {
                "messages": [m.content for m in messages],
                "config": inference_hash,
                "version": "direct_chat/v1",
            }
        ),
        budget.total_reserved_tokens,
        runtime.provider_id,
    )
    try:
        result_chat = await chat.complete(messages, bind_usage(request, usage.id))
    except ChatResponseError as exc:
        await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
        raise
    except (Exception, asyncio.CancelledError):
        await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
        raise

    await usage_service.settle(db, usage.id, total_tokens=result_chat.total_tokens)
    raw_content = result_chat.content.strip()
    answer_text = raw_content
    if raw_content.startswith("{") and raw_content.endswith("}"):
        try:
            parsed = json.loads(raw_content)
            if isinstance(parsed, dict):
                extracted = (
                    parsed.get("answer")
                    or parsed.get("message")
                    or parsed.get("content")
                    or parsed.get("text")
                )
                if extracted and isinstance(extracted, str):
                    answer_text = extracted.strip()
                elif not parsed or all(not v for v in parsed.values()):
                    answer_text = ""
        except Exception:
            pass

    answer_text, _hygiene = clean_text(answer_text)
    if not answer_text.strip() or answer_text.strip() == "{}":
        answer_text = (
            "Tôi đã ghi nhận câu hỏi của bạn. Về nội dung này, bạn có thể diễn đạt cụ thể hơn "
            "hoặc cung cấp thêm chi tiết để mình hỗ trợ chính xác nhất nhé."
        )
    turn.rewrite_trace = {
        **(turn.rewrite_trace or {}),
        "mode": "direct_llm",
        "provider_id": runtime.provider_id,
        "model_name": runtime.model_name,
        "total_tokens": result_chat.total_tokens,
    }
    return DirectReply(
        id=turn.id,
        status="direct_reply",
        route="direct_chat",
        answer=answer_text,
    )


async def send(
    db: AsyncSession,
    blob: BlobStore,
    embedding: EmbeddingModel,
    vectors: VectorStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    req: TurnRequest,
    key: str,
    *,
    reranker: Reranker | None = None,
) -> TurnResponse:
    conversation, turn, created = await reserve_turn(
        db, actor, workspace_id, conversation_id, req, key
    )
    turn_id = turn.id
    if not created:
        if turn.status != "completed":
            raise Conflict(
                "Lượt hỏi đã được nhận; xem trạng thái, không gửi lại model.",
                code="conversation_turn_" + turn.status,
            )
        value = await readable(db, blob, vectors, actor, turn, conversation.document_ids)
        if value.source_status != "current":
            raise Conflict("Nguồn của kết quả cũ đã thay đổi.", code="answer_evidence_changed")
        return value
    try:
        config = conversation.assistant_snapshot
        # Conversations created before multi-collection snapshots only carry the scalar
        # column; keep them answering from that single collection.
        raw_ids = config.get("collection_ids")
        if raw_ids is not None:
            collection_ids = [c for c in raw_ids if c]
        else:
            collection_ids = [conversation.collection_id] if conversation.collection_id else []

        async def check():
            await checkpoint(db, actor, turn)

        reply, provider_id = await resolve_turn(db, actor, conversation, turn, chat)
        if reply is None:
            if not collection_ids:
                result = await _direct_llm_turn(
                    db,
                    actor,
                    workspace_id,
                    conversation,
                    turn,
                    chat,
                    provider_id=provider_id,
                )
            else:
                policy = AssistantRagPolicy.model_validate(config.get("rag_policy", {})).model_dump(
                    mode="json", exclude={"guardrail_policy", "suggested_prompts"}
                )
                policy["metadata_filter"] = turn.metadata_filter or {}
                conv_mem = (turn.rewrite_trace or {}).get("conversation_memory")
                result = await answer(
                    db,
                    blob,
                    embedding,
                    vectors,
                    chat,
                    actor,
                    workspace_id,
                    conversation.collection_id,
                    AnswerRequest(
                        question=turn.question,
                        top_k=config["top_k"],
                        document_ids=conversation.document_ids,
                        provider_id=provider_id,
                        max_output_tokens=config["max_output_tokens"],
                        conversation_memory=conv_mem,
                        **policy,
                    ),
                    retrieval_query=turn.resolved_question,
                    clarify_source_reference=bool(
                        (turn.rewrite_trace or {}).get("needs_clarification")
                    ),
                    persona=config["persona"],
                    checkpoint=check,
                    reranker=reranker,
                    compose_insufficient_message=True,
                    collection_ids=collection_ids,
                )
        else:
            result = reply
        await check()
        turn.result = result.model_dump(mode="json")
        turn.status, turn.finished_at = "completed", utcnow()
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="conversation.turn_completed",
            detail={
                "conversation_id": conversation.id,
                "turn_id": turn.id,
                "answer_id": result.id,
                "status": result.status,
                **({"route": reply.route} if reply else {}),
            },
        )
        await db.commit()
        return TurnResponse.model_validate(turn)
    except (Exception, asyncio.CancelledError) as exc:
        await db.rollback()
        # Trusted internal finalization updates only the already authorized turn ID;
        # no data is returned after membership revocation.
        row = await db.get(ConversationTurn, turn_id, populate_existing=True)
        if row is not None and row.status == "running":
            code = exc.code if isinstance(exc, AppException) else "conversation_turn_failed"
            row.status = (
                "uncertain"
                if isinstance(exc, asyncio.CancelledError)
                or "uncertain" in code
                or row.lease_expires_at <= utcnow()
                else "failed"
            )
            row.error_code, row.finished_at = code, utcnow()
            await db.commit()
            logger.warning(
                "conversation_turn_stopped", turn_id=row.id, status=row.status, error_code=code
            )
        raise
