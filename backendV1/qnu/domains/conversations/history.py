"""Persisted text is historical; source snapshots are revalidated before returning answers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.conversations.access import owned
from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.conversations.schemas import TurnResponse
from qnu.domains.conversations.service import expire
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.knowledge.index.validation import validate_results
from qnu.platform.errors import AppException, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorStore


async def readable(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    turn: ConversationTurn,
    document_ids: list[str] | None,
) -> TurnResponse:
    value = TurnResponse.model_validate(turn)
    if value.result and value.result.sources:
        result = value.result
        retrieved = SearchResponse(
            index_run_id=result.index_run_id,
            generation=result.generation,
            status="results",
            hits=[
                SearchHit.model_validate(s.model_dump(exclude={"evidence_id"}))
                for s in result.sources
            ],
            eligible_documents=len({s.document_id for s in result.sources}),
        )
        try:
            await validate_results(
                db,
                blob,
                vectors,
                actor,
                turn.workspace_id,
                turn.collection_id,
                retrieved,
                document_ids,
            )
        except AppException as exc:
            if exc.code in {
                "resource_unavailable",
                "answer_evidence_changed",
                "index_outdated",
                "index_configuration_changed",
                "embedding_dimension_stale",
                "provider_inactive",
                "provider_not_found",
                "publication_source_stale",
                "published_compilation_not_found",
            }:
                value.result = None
                value.source_status = "unavailable"
            else:
                raise
    return value


async def list_turns(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    limit: int,
    offset: int,
) -> list[TurnResponse]:
    conversation = await owned(db, actor, workspace_id, conversation_id)
    await expire(db, conversation)
    rows = list(
        (
            await db.scalars(
                select(ConversationTurn)
                .where(ConversationTurn.conversation_id == conversation.id)
                .order_by(ConversationTurn.turn_no)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    result = [await readable(db, blob, vectors, actor, r, conversation.document_ids) for r in rows]
    await db.commit()
    return result


async def get_turn(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
) -> TurnResponse:
    conversation = await owned(db, actor, workspace_id, conversation_id)
    await expire(db, conversation)
    row = await db.scalar(
        select(ConversationTurn).where(
            ConversationTurn.id == turn_id, ConversationTurn.conversation_id == conversation.id
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy lượt hỏi.", code="conversation_turn_not_found")
    result = await readable(db, blob, vectors, actor, row, conversation.document_ids)
    await db.commit()
    return result
