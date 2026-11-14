"""Run small answer tests through the existing answer pipeline.

Reviews store observed answers and human labels beside, never inside, the
retrieval evaluation gold data.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.answer_review.models import AnswerReview, AnswerReviewItem
from qnu.domains.answer_review.schemas import (
    AnswerReviewCreate,
    AnswerReviewItemResponse,
    AnswerReviewLabelUpdate,
    AnswerReviewResponse,
)
from qnu.domains.assistants.schemas import AssistantConfig
from qnu.domains.assistants.service import assistant_readiness, get_assistant
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.ocr.ids import new_id
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse
from qnu.domains.rag.answer.service import answer
from qnu.domains.rag.policy import RagPolicy
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel
from qnu.ports.embedding_model import EmbeddingModel
from qnu.ports.reranker import Reranker
from qnu.ports.vector_store import VectorStore

LABEL_ROLES = ("admin", "editor", "reviewer")
REVIEWED_STATUSES = ("answered", "insufficient_evidence")


def _response(review: AnswerReview, items: list[AnswerReviewItem]) -> AnswerReviewResponse:
    return AnswerReviewResponse(
        id=review.id,
        workspace_id=review.workspace_id,
        collection_id=review.collection_id,
        assistant_id=review.assistant_id,
        assistant_revision=review.assistant_revision,
        requested_by=review.requested_by,
        question_count=review.question_count,
        status=review.status,
        error_code=review.error_code,
        created_at=review.created_at,
        finished_at=review.finished_at,
        items=[
            AnswerReviewItemResponse(
                id=item.id,
                review_id=item.review_id,
                ordinal=item.ordinal,
                question=item.question,
                status=item.status,
                error_code=item.error_code,
                result=AnswerResponse.model_validate(item.result) if item.result else None,
                index_run_id=item.index_run_id,
                generation=item.generation,
                label=item.label,
                label_note=item.label_note,
                labelled_by=item.labelled_by,
                labelled_at=item.labelled_at,
                created_at=item.created_at,
                finished_at=item.finished_at,
            )
            for item in sorted(items, key=lambda row: row.ordinal)
        ],
    )


async def _items(db: AsyncSession, review_id: str) -> list[AnswerReviewItem]:
    return list(
        (
            await db.scalars(
                select(AnswerReviewItem)
                .where(AnswerReviewItem.review_id == review_id)
                .order_by(AnswerReviewItem.ordinal)
                .execution_options(populate_existing=True)
            )
        ).all()
    )


async def _review(
    db: AsyncSession, workspace_id: str, assistant_id: str, review_id: str
) -> AnswerReview:
    row = await db.scalar(
        select(AnswerReview)
        .where(
            AnswerReview.id == review_id,
            AnswerReview.workspace_id == workspace_id,
            AnswerReview.assistant_id == assistant_id,
        )
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy lần kiểm thử.", code="answer_review_not_found")
    return row


async def create_review(
    db: AsyncSession,
    blob: BlobStore,
    embedding: EmbeddingModel,
    vectors: VectorStore,
    chat: ChatModel,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
    req: AnswerReviewCreate,
    key: str,
    *,
    reranker: Reranker | None = None,
) -> tuple[AnswerReviewResponse, bool]:
    assistant = await get_assistant(db, actor, workspace_id, assistant_id)
    if not assistant.is_active:
        raise Conflict("Trợ lý đã tạm dừng; không thể kiểm thử.", code="assistant_inactive")
    readiness = await assistant_readiness(db, blob, actor, workspace_id, assistant_id)
    if readiness.status == "empty":
        raise Conflict(
            "Kho tri thức chưa có tài liệu được xuất bản để kiểm thử.",
            code="assistant_no_published_sources",
        )
    request_sha256 = digest({"assistant_id": assistant.id, "questions": req.questions})
    replay = await db.scalar(
        select(AnswerReview).where(
            AnswerReview.workspace_id == workspace_id,
            AnswerReview.requested_by == actor_ref(actor),
            AnswerReview.idempotency_key == key,
        )
    )
    if replay is not None:
        if replay.request_sha256 != request_sha256:
            raise Conflict("Idempotency-Key đã dùng cho yêu cầu khác.", code="idempotency_conflict")
        return _response(replay, await _items(db, replay.id)), False
    config = AssistantConfig.model_validate(assistant, from_attributes=True).model_dump(
        mode="json"
    )
    review_id = new_id("arv")
    review = AnswerReview(
        id=review_id,
        workspace_id=workspace_id,
        collection_id=assistant.collection_id,
        assistant_id=assistant.id,
        assistant_revision=assistant.revision,
        assistant_snapshot=config,
        requested_by=actor_ref(actor),
        idempotency_key=key,
        request_sha256=request_sha256,
        question_count=len(req.questions),
        status="running",
    )
    db.add(review)
    items = [
        AnswerReviewItem(
            id=new_id("avi"),
            review_id=review.id,
            workspace_id=workspace_id,
            collection_id=assistant.collection_id,
            ordinal=ordinal,
            question=question,
            # A crash between requests leaves an explicit "not run" item instead
            # of a fabricated answer or a silently missing question.
            status="uncertain",
            error_code="answer_review_not_run",
        )
        for ordinal, question in enumerate(req.questions)
    ]
    db.add_all(items)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="assistant.answer_review_started",
        detail={
            "assistant_id": assistant.id,
            "review_id": review.id,
            "assistant_revision": assistant.revision,
            "question_count": len(req.questions),
        },
    )
    await db.commit()

    policy = RagPolicy.model_validate(config.get("rag_policy", {})).model_dump(mode="json")
    collection_id = assistant.collection_id
    item_ids = [item.id for item in items]
    for item_id, question in zip(item_ids, req.questions, strict=True):
        try:
            result = await answer(
                db,
                blob,
                embedding,
                vectors,
                chat,
                actor,
                workspace_id,
                collection_id,
                AnswerRequest(
                    question=question,
                    top_k=config["top_k"],
                    provider_id=config["chat_provider_id"],
                    max_output_tokens=config["max_output_tokens"],
                    **policy,
                ),
                persona=config["persona"],
                reranker=reranker,
                compose_insufficient_message=True,
            )
        except (Exception, asyncio.CancelledError) as exc:
            await db.rollback()
            cancelled = isinstance(exc, asyncio.CancelledError)
            code = (
                "answer_review_cancelled"
                if cancelled
                else exc.code
                if isinstance(exc, AppException)
                else "answer_review_failed"
            )
            row = await db.get(AnswerReviewItem, item_id, populate_existing=True)
            if row is not None:
                row.status = "uncertain" if cancelled or "uncertain" in code else "failed"
                row.error_code, row.finished_at = code, utcnow()
                await db.commit()
            if cancelled:
                await _finish(db, review_id, actor, workspace_id)
                raise
            continue
        row = await db.get(AnswerReviewItem, item_id, populate_existing=True)
        row.status = result.status
        row.result = result.model_dump(mode="json")
        row.index_run_id = result.index_run_id
        row.generation = result.generation
        row.finished_at = utcnow()
        await db.commit()
    await _finish(db, review_id, actor, workspace_id)
    return (
        _response(
            await _review(db, workspace_id, assistant_id, review_id),
            await _items(db, review_id),
        ),
        True,
    )


async def _finish(
    db: AsyncSession, review_id: str, actor: AuthActor, workspace_id: str
) -> None:
    row = await db.get(AnswerReview, review_id, populate_existing=True)
    if row is None:
        return
    items = await _items(db, review_id)
    statuses = {item.status for item in items}
    if "uncertain" in statuses:
        status = "uncertain"
    elif "failed" in statuses:
        status = "failed"
    elif statuses:
        status = "completed"
    else:
        status = "uncertain"
    row.status = status
    row.error_code = next(
        (item.error_code for item in items if item.status in {"failed", "uncertain"}), None
    )
    row.finished_at = utcnow()
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="assistant.answer_review_finished",
        detail={
            "assistant_id": row.assistant_id,
            "review_id": row.id,
            "status": row.status,
            "answered": sum(1 for item in items if item.status == "answered"),
            "insufficient_evidence": sum(
                1 for item in items if item.status == "insufficient_evidence"
            ),
            "failed": sum(1 for item in items if item.status == "failed"),
            "uncertain": sum(1 for item in items if item.status == "uncertain"),
        },
    )
    await db.commit()


async def list_reviews(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
    limit: int,
    offset: int,
) -> list[AnswerReviewResponse]:
    await get_assistant(db, actor, workspace_id, assistant_id)
    rows = list(
        (
            await db.scalars(
                select(AnswerReview)
                .where(
                    AnswerReview.workspace_id == workspace_id,
                    AnswerReview.assistant_id == assistant_id,
                )
                .order_by(AnswerReview.created_at.desc(), AnswerReview.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    grouped: dict[str, list[AnswerReviewItem]] = {row.id: [] for row in rows}
    if rows:
        for item in (
            await db.scalars(
                select(AnswerReviewItem)
                .where(AnswerReviewItem.review_id.in_(grouped))
                .order_by(AnswerReviewItem.ordinal)
            )
        ).all():
            grouped[item.review_id].append(item)
    return [_response(row, grouped[row.id]) for row in rows]


async def read_review(
    db: AsyncSession, actor: AuthActor, workspace_id: str, assistant_id: str, review_id: str
) -> AnswerReviewResponse:
    await get_assistant(db, actor, workspace_id, assistant_id)
    row = await _review(db, workspace_id, assistant_id, review_id)
    return _response(row, await _items(db, row.id))


async def label_item(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    assistant_id: str,
    review_id: str,
    item_id: str,
    req: AnswerReviewLabelUpdate,
) -> AnswerReviewResponse:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=LABEL_ROLES)
    await get_assistant(db, actor, workspace_id, assistant_id)
    review = await _review(db, workspace_id, assistant_id, review_id)
    item = await db.get(AnswerReviewItem, item_id, populate_existing=True)
    if item is None or item.review_id != review.id:
        raise EntityNotFound("Không tìm thấy câu hỏi kiểm thử.", code="answer_review_item_not_found")
    if item.status not in REVIEWED_STATUSES:
        raise Conflict(
            "Chỉ gắn nhãn câu hỏi đã có kết quả trả lời.", code="answer_review_item_not_ready"
        )
    item.label = req.label
    if req.label is None:
        item.label_note, item.labelled_by, item.labelled_at = None, None, None
    else:
        item.label_note = req.note or None
        item.labelled_by, item.labelled_at = actor_ref(actor), utcnow()
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="assistant.answer_review_labelled",
        detail={
            "assistant_id": assistant_id,
            "review_id": review.id,
            "item_id": item.id,
            "label": item.label,
        },
    )
    await db.commit()
    return _response(review, await _items(db, review.id))
