"""Persist first, call existing answer pipeline once, then commit only a current owned turn."""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.assistants.schemas import AssistantRagPolicy
from qnu.domains.conversations.access import checkpoint
from qnu.domains.conversations.document_export import (
    NO_KNOWLEDGE_GROUNDING_POLICY,
    DirectHistoryEntry,
    DocumentDraft,
    ExportFormat,
    active_draft_prompt_context,
    dialogue_turn_policy,
    disabled_format_refusal_message,
    disabled_requested_format,
    enabled_export_formats,
    export_policy_prompt_addon,
    extract_document_draft,
    is_abnormally_truncated_reply,
    requested_export_format,
    resolve_preferred_format,
    strip_document_markers,
    trim_direct_history,
    vietnam_time_context,
)
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


async def _live_export_formats(db: AsyncSession, conversation) -> list[ExportFormat]:
    """Read live Assistant export toggles so mid-conversation toggle changes apply immediately."""
    assistant = await db.scalar(
        select(Assistant).where(Assistant.id == conversation.assistant_id)
    )
    if assistant is not None:
        return enabled_export_formats({"rag_policy": assistant.rag_policy})
    return enabled_export_formats(conversation.assistant_snapshot)


def _latest_turn_draft(turns: list[ConversationTurn]) -> DocumentDraft | None:
    """Return the most recent DocumentDraft produced in prior completed turns."""
    for row in reversed(turns):
        if row.status != "completed":
            continue
        trace = row.rewrite_trace if isinstance(row.rewrite_trace, dict) else None
        raw = trace.get("document_draft") if trace else None
        if isinstance(raw, dict):
            try:
                return DocumentDraft.model_validate(raw)
            except Exception as exc:
                logger.debug("conversation_prior_draft_invalid", turn_id=row.id, error=str(exc))
    return None


def _extract_direct_text(raw: str) -> str:
    raw_content = (raw or "").strip()
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
    cleaned, _hygiene = clean_text(answer_text)
    return cleaned


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
    completed_turns = [t for t in all_turns if t.status == "completed"]
    trimmed_history = trim_direct_history(
        [
            DirectHistoryEntry(
                turn_id=t.id,
                question=t.question,
                answer=_history_answer(t.result) or "",
            )
            for t in completed_turns
        ],
        max_turns=count,
    )
    turn.history_turn_ids = [h.turn_id for h in trimmed_history if h.turn_id is not None]

    system_prompt = (
        config.get("persona")
        or "Bạn là trợ lý AI của Trường Đại học Quy Nhơn (QNU). Hãy hỗ trợ người dùng chu đáo, thân thiện và chuẩn mực sư phạm."
    )
    export_formats = await _live_export_formats(db, conversation)
    latest_draft = _latest_turn_draft(all_turns) if export_formats else None
    system_prompt += (
        NO_KNOWLEDGE_GROUNDING_POLICY
        + export_policy_prompt_addon(export_formats)
        + active_draft_prompt_context(latest_draft)
        + vietnam_time_context()
        + dialogue_turn_policy(len(trimmed_history))
    )
    messages = [ChatMessage(role="system", content=system_prompt)]
    for h in trimmed_history:
        messages.append(ChatMessage(role="user", content=h.question))
        if h.answer:
            messages.append(ChatMessage(role="assistant", content=h.answer))
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

    async def _run_completion(key_prefix: str, version_tag: str):
        usage = await usage_service.reserve(
            db,
            actor,
            workspace_id,
            "chat",
            key_prefix + turn.id,
            digest(
                {
                    "messages": [m.content for m in messages],
                    "config": inference_hash,
                    "version": version_tag,
                }
            ),
            budget.total_reserved_tokens,
            runtime.provider_id,
        )
        try:
            completion = await chat.complete(messages, bind_usage(request, usage.id))
        except ChatResponseError as exc:
            await usage_service.settle(db, usage.id, total_tokens=exc.usage_tokens, failed=True)
            raise
        except (Exception, asyncio.CancelledError):
            await usage_service.settle(db, usage.id, total_tokens=None, failed=True)
            raise
        await usage_service.settle(db, usage.id, total_tokens=completion.total_tokens)
        return completion

    result_chat = await _run_completion("direct_chat:", "direct_chat/v1")
    total_tokens = result_chat.total_tokens
    answer_text = _extract_direct_text(result_chat.content)
    retried_truncated = False
    if is_abnormally_truncated_reply(answer_text, effective_question):
        logger.warning(
            "direct_chat_truncated_reply_retry",
            turn_id=turn.id,
            provider_id=runtime.provider_id,
            raw_len=len(answer_text.strip()),
        )
        retried_truncated = True
        retry_chat = await _run_completion("direct_chat_retry:", "direct_chat_retry/v1")
        if total_tokens is not None or retry_chat.total_tokens is not None:
            total_tokens = (total_tokens or 0) + (retry_chat.total_tokens or 0)
        retry_text = _extract_direct_text(retry_chat.content)
        if retry_text.strip():
            answer_text = retry_text

    if not answer_text.strip() or answer_text.strip() == "{}":
        answer_text = (
            "Tôi đã ghi nhận câu hỏi của bạn. Về nội dung này, bạn có thể diễn đạt cụ thể hơn "
            "hoặc cung cấp thêm chi tiết để mình hỗ trợ chính xác nhất nhé."
        )
    draft_payload = None
    disabled_fmt = disabled_requested_format(turn.question, export_formats)
    if disabled_fmt is not None:
        answer_text = (
            strip_document_markers(answer_text, remove_blocks=True)
            or disabled_format_refusal_message(disabled_fmt)
        )
    elif export_formats:
        answer_text, draft = extract_document_draft(answer_text, turn.question)
        if draft is None and latest_draft is not None:
            req_fmt = requested_export_format(turn.question)
            if req_fmt is not None and req_fmt in export_formats:
                draft = latest_draft
        if draft is not None:
            draft = resolve_preferred_format(draft, turn.question, export_formats)
            draft_payload = draft.model_dump(mode="json")
    else:
        answer_text = strip_document_markers(answer_text, remove_blocks=True)

    turn.rewrite_trace = {
        **(turn.rewrite_trace or {}),
        "mode": "direct_llm",
        "provider_id": runtime.provider_id,
        "model_name": runtime.model_name,
        "total_tokens": total_tokens,
        **({"retried_truncated": True} if retried_truncated else {}),
        **({"document_draft": draft_payload} if draft_payload is not None else {}),
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

        if not collection_ids:
            # Persona-direct assistants (no knowledge collection) converse naturally
            # with full turn history in _direct_llm_turn — skip the RAG query-rewrite
            # router so follow-up drafting requests never trip conversation_clarification_required.
            reply = None
            provider_id = config.get("chat_provider_id")
            turn.resolved_question = turn.question
        else:
            reply, provider_id = await resolve_turn(db, actor, conversation, turn, chat)
        if reply is None:
            live_formats = await _live_export_formats(db, conversation)
            early_disabled_fmt = disabled_requested_format(turn.question, live_formats)
            if early_disabled_fmt is not None:
                result = DirectReply(
                    id=turn.id,
                    status="direct_reply",
                    route="direct_chat",
                    answer=disabled_format_refusal_message(early_disabled_fmt),
                )
            elif not collection_ids:
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
                export_formats = live_formats
                prior_turns = list(
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
                latest_draft = _latest_turn_draft(prior_turns) if export_formats else None
                policy = AssistantRagPolicy.model_validate(config.get("rag_policy", {})).model_dump(
                    mode="json",
                    exclude={
                        "guardrail_policy",
                        "suggested_prompts",
                        "allow_export_docx",
                        "allow_export_pdf",
                        "allow_export_xlsx",
                    },
                )
                policy["metadata_filter"] = turn.metadata_filter or {}
                conv_mem = (turn.rewrite_trace or {}).get("conversation_memory")
                effective_persona = (
                    (config["persona"] or "")
                    + export_policy_prompt_addon(export_formats)
                    + active_draft_prompt_context(latest_draft)
                )
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
                    persona=effective_persona,
                    checkpoint=check,
                    reranker=reranker,
                    compose_insufficient_message=True,
                    collection_ids=collection_ids,
                )
                raw_rag_text = (
                    "\n".join(s.text for s in result.statements)
                    if result.statements
                    else (result.answer or "")
                )
                disabled_rag_fmt = disabled_requested_format(turn.question, export_formats)
                if disabled_rag_fmt is not None:
                    if "<<<" in raw_rag_text:
                        cleaned_rag = (
                            strip_document_markers(raw_rag_text, remove_blocks=True)
                            or disabled_format_refusal_message(disabled_rag_fmt)
                        )
                        result = result.model_copy(
                            update={"answer": cleaned_rag, "statements": []}
                        )
                elif export_formats and result.status == "answered":
                    display_rag_text, draft = extract_document_draft(raw_rag_text, turn.question)
                    if draft is None and latest_draft is not None:
                        req_fmt = requested_export_format(turn.question)
                        if req_fmt is not None and req_fmt in export_formats:
                            draft = latest_draft
                    if draft is not None:
                        draft = resolve_preferred_format(draft, turn.question, export_formats)
                        turn.rewrite_trace = {
                            **(turn.rewrite_trace or {}),
                            "document_draft": draft.model_dump(mode="json"),
                        }
                    if "<<<" in raw_rag_text:
                        result = result.model_copy(
                            update={"answer": display_rag_text, "statements": []}
                        )
                elif "<<<" in raw_rag_text:
                    result = result.model_copy(
                        update={
                            "answer": strip_document_markers(raw_rag_text, remove_blocks=True),
                            "statements": [],
                        }
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
