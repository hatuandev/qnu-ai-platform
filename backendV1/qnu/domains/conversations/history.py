"""Persisted text is historical; source snapshots are revalidated before returning answers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.conversations.access import owned
from qnu.domains.conversations.models import ConversationTurn
from qnu.domains.conversations.schemas import (
    PromoteToBenchmarkRequest,
    PromoteToBenchmarkResponse,
    TurnFeedbackRequest,
    TurnResponse,
)
from qnu.domains.conversations.service import expire
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.index.multi import validate_collections
from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.knowledge.index.validation import validate_results
from qnu.domains.rag.answer.schemas import AnswerResponse
from qnu.platform.errors import AppException, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.vector_store import VectorStore

UNAVAILABLE_REASONS = {
    "resource_unavailable": "Nguồn của câu trả lời đã bị lưu trữ hoặc xóa.",
    "answer_evidence_changed": "Bằng chứng nguồn hoặc phiên bản xuất bản đã thay đổi.",
    "index_outdated": "Chỉ mục đã thay đổi so với lúc trả lời.",
    "index_configuration_changed": "Cấu hình chỉ mục hoặc mô hình embedding đã thay đổi.",
    "embedding_dimension_stale": "Mô hình embedding của chỉ mục không còn tương thích.",
    "provider_inactive": "Nhà cung cấp mô hình của chỉ mục đã ngừng hoạt động.",
    "provider_not_found": "Không còn nhà cung cấp mô hình của chỉ mục.",
    "publication_source_stale": "Nguồn dùng để xuất bản đã thay đổi.",
    "published_compilation_not_found": "Bản xuất bản nguồn không còn tồn tại.",
}


async def _revalidate(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    turn: ConversationTurn,
    retrieved: SearchResponse,
    document_ids: list[str] | None,
    retrieval_trace: dict,
) -> None:
    """A multi-collection answer carries its served records, one per collection."""
    served = [
        item for item in retrieval_trace.get("collections") or [] if item.get("status") == "served"
    ]
    if not served:
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
        return
    await validate_collections(
        db,
        blob,
        vectors,
        actor,
        turn.workspace_id,
        retrieved.model_copy(update={"trace": {"collections": served}}),
        document_ids,
        retrieval_trace.get("hit_scope") or {},
    )


async def readable(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    turn: ConversationTurn,
    document_ids: list[str] | None,
) -> TurnResponse:
    value = TurnResponse.model_validate(turn)
    if isinstance(value.result, AnswerResponse) and value.result.sources:
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
            await _revalidate(
                db,
                blob,
                vectors,
                actor,
                turn,
                retrieved,
                document_ids,
                result.trace.retrieval or {},
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
                value.source_status_reason = UNAVAILABLE_REASONS.get(
                    exc.code, "Nguồn của câu trả lời không còn khả dụng."
                )
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


async def set_feedback(
    db: AsyncSession,
    blob: BlobStore,
    vectors: VectorStore,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    body: TurnFeedbackRequest,
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

    if body.rating is None:
        row.feedback = None
    else:
        row.feedback = {
            "rating": body.rating,
            "reason": body.reason,
            "updated_at": utcnow().isoformat(),
        }

    await db.commit()
    await db.refresh(row)
    return await readable(db, blob, vectors, actor, row, conversation.document_ids)


async def promote_turn_to_benchmark(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    body: PromoteToBenchmarkRequest,
) -> PromoteToBenchmarkResponse:
    from qnu.domains.conversations.benchmarks import add_turn_to_benchmark, get_benchmark_path

    conversation = await owned(db, actor, workspace_id, conversation_id)
    await expire(db, conversation)
    row = await db.scalar(
        select(ConversationTurn).where(
            ConversationTurn.id == turn_id, ConversationTurn.conversation_id == conversation.id
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy lượt hỏi.", code="conversation_turn_not_found")

    return add_turn_to_benchmark(get_benchmark_path(), row, body)


