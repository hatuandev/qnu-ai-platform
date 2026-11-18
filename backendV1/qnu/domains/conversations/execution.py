"""Persist first, call existing answer pipeline once, then commit only a current owned turn."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.schemas import AssistantRagPolicy
from qnu.domains.conversations.access import checkpoint
from qnu.domains.conversations.history import readable
from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.conversations.rewriting import resolve_turn
from qnu.domains.conversations.schemas import TurnRequest, TurnResponse
from qnu.domains.conversations.service import reserve_turn
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import answer
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

logger = get_logger(__name__)


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
        collection_ids = config.get("collection_ids") or [conversation.collection_id]

        async def check():
            await checkpoint(db, actor, turn)

        reply, provider_id = await resolve_turn(db, actor, conversation, turn, chat)
        if reply is None:
            policy = AssistantRagPolicy.model_validate(config.get("rag_policy", {})).model_dump(
                mode="json", exclude={"guardrail_policy"}
            )
            policy["metadata_filter"] = turn.metadata_filter or {}
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
