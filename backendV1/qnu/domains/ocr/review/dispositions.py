"""Persisted reviewer dismissals; they hide suggestions without altering text."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review import detection
from qnu.domains.ocr.review.models import SpellingDisposition, SpellingRun
from qnu.domains.ocr.review.schemas import (
    DetectionResponse,
    IgnoredSuggestion,
    SpellingDispositionBatch,
    SpellingDispositionRequest,
)
from qnu.domains.ocr.review.service import authorize
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict, EntityNotFound


def _known(row: SpellingRun, req: IgnoredSuggestion | SpellingDispositionRequest) -> bool:
    candidates = list(row.suggestions) + list(row.trace.get("withheld_suggestions", []))
    key = (req.evidence_id, req.start, req.end)
    return any((item["evidence_id"], item["start"], item["end"]) == key for item in candidates)


async def reviewable_check(db: AsyncSession, run: OcrProcessingRun, check_id: str) -> SpellingRun:
    row = await db.scalar(
        select(SpellingRun).where(
            SpellingRun.id == check_id,
            SpellingRun.run_id == run.id,
            SpellingRun.workspace_id == run.workspace_id,
            SpellingRun.collection_id == run.collection_id,
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy lượt kiểm tra.", code="ocr_spelling_not_found")
    if "automatic_parent" in row.trace:
        raise Conflict(
            "Lượt kiểm tra này không phải bản rà soát độc lập.",
            code="ocr_spelling_check_not_reviewable",
        )
    if row.status != "completed":
        raise Conflict(
            "Chỉ ghi nhận bỏ qua trên lượt kiểm tra đã hoàn tất.",
            code="ocr_spelling_check_not_ready",
        )
    return row


async def set_ignored(
    db: AsyncSession,
    actor: AuthActor,
    run: OcrProcessingRun,
    check_id: str,
    req: SpellingDispositionRequest,
) -> DetectionResponse:
    await authorize(db, actor, run, write=True, lock=True)
    row = await reviewable_check(db, run, check_id)
    if not _known(row, req):
        raise EntityNotFound(
            "Không tìm thấy gợi ý trong lượt kiểm tra.",
            code="ocr_spelling_suggestion_not_found",
        )
    scope = {
        "check_id": check_id,
        "evidence_id": req.evidence_id,
        "span_start": req.start,
        "span_end": req.end,
    }
    if req.ignored:
        result = await db.execute(
            insert(SpellingDisposition)
            .values(
                id=new_id("splign"),
                run_id=run.id,
                workspace_id=run.workspace_id,
                collection_id=run.collection_id,
                created_by=actor_ref(actor),
                created_at=utcnow(),
                **scope,
            )
            .on_conflict_do_nothing(
                index_elements=["check_id", "evidence_id", "span_start", "span_end"]
            )
        )
        action = "ocr.spelling_ignored"
    else:
        result = await db.execute(
            delete(SpellingDisposition).where(
                SpellingDisposition.check_id == check_id,
                SpellingDisposition.evidence_id == req.evidence_id,
                SpellingDisposition.span_start == req.start,
                SpellingDisposition.span_end == req.end,
            )
        )
        action = "ocr.spelling_ignore_undone"
    if result.rowcount:
        await record_workspace_event(
            db,
            workspace_id=run.workspace_id,
            actor=actor,
            action=action,
            detail={
                "run_id": run.id,
                "check_id": check_id,
                "version": row.version,
                "evidence_id": req.evidence_id,
                "start": req.start,
                "end": req.end,
            },
        )
    await db.commit()
    return await detection.get_check(db, run, check_id)


async def ignore_all(
    db: AsyncSession,
    actor: AuthActor,
    run: OcrProcessingRun,
    check_id: str,
    req: SpellingDispositionBatch,
) -> DetectionResponse:
    await authorize(db, actor, run, write=True, lock=True)
    row = await reviewable_check(db, run, check_id)
    for item in req.suggestions:
        if not _known(row, item):
            raise EntityNotFound(
                "Không tìm thấy gợi ý trong lượt kiểm tra.",
                code="ocr_spelling_suggestion_not_found",
            )
    now = utcnow()
    await db.execute(
        insert(SpellingDisposition)
        .values(
            [
                {
                    "id": new_id("splign"),
                    "run_id": run.id,
                    "workspace_id": run.workspace_id,
                    "collection_id": run.collection_id,
                    "check_id": check_id,
                    "evidence_id": item.evidence_id,
                    "span_start": item.start,
                    "span_end": item.end,
                    "created_by": actor_ref(actor),
                    "created_at": now,
                }
                for item in req.suggestions
            ]
        )
        .on_conflict_do_nothing(
            index_elements=["check_id", "evidence_id", "span_start", "span_end"]
        )
    )
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="ocr.spelling_ignored_bulk",
        detail={
            "run_id": run.id,
            "check_id": check_id,
            "version": row.version,
            "count": len(req.suggestions),
        },
    )
    await db.commit()
    return await detection.get_check(db, run, check_id)
