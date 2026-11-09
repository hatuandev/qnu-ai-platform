"""Preparation intents: accept, persist, advance through OCR, compile, read and cancel.

Every step re-reads authority and lifecycle from the database. A queue delivery is
only a hint: the row, its pinned hashes and the run-level idempotency keys decide
whether work may continue, so a duplicate delivery cannot create a second model
call and a revoked member cannot start the next step.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.background import background_actor
from qnu.domains.knowledge.compilation import service as compilation_service
from qnu.domains.knowledge.compilation.models import CompilationRun
from qnu.domains.knowledge.compilation.schemas import CompilationRequest
from qnu.domains.knowledge.models import KBSource, KBSourceRevision, utcnow
from qnu.domains.knowledge.policies.access import (
    READ_ROLES,
    WRITE_ROLES,
    load_revision,
    load_source,
)
from qnu.domains.knowledge.preparation import plan as preparation_plan
from qnu.domains.knowledge.preparation.models import (
    ACTIVE_PREPARATION_STATUSES,
    TERMINAL_PREPARATION_STATUSES,
    PreparationIntent,
)
from qnu.domains.knowledge.preparation.schemas import PreparationRequest
from qnu.domains.knowledge.public_api import resolve_revision_scope
from qnu.domains.modelops.public_api import assert_provider_allowed
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review.models import TextVersion
from qnu.domains.ocr.service import processing_service
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.platform.logging import get_logger
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

logger = get_logger(__name__)
TASK_NAME = "preparation_job"
LEASE_SECONDS = 180
ADVANCING_OCR_STATUSES = ("queued", "running")
FAILED_OCR_STATUSES = ("failed", "uncertain", "cancelled")
@dataclass(frozen=True, slots=True)
class PreparationOutcome:
    intent: PreparationIntent
    created: bool
    dispatched: bool


async def create_intent(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    req: PreparationRequest,
    idempotency_key: str,
    queue: JobQueue | None,
) -> PreparationOutcome:
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    source = await load_source(db, workspace_id, collection_id, source_id, for_update=True)
    revision = await _pin_revision(db, workspace_id, collection_id, source, req.revision_id)
    topic = ((req.topic or "").strip() or source.title)[:2000]
    if not topic:
        raise AppException(
            "Thiếu chủ đề chuẩn bị.", code="preparation_topic_required", status_code=422
        )

    request_hash = preparation_plan.request_hash(collection_id, source_id, revision.id, req, topic)
    ref = actor_ref(actor)
    existing = await db.scalar(
        select(PreparationIntent).where(
            PreparationIntent.workspace_id == workspace_id,
            PreparationIntent.requested_by == ref,
            PreparationIntent.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            # One-release bridge: before automatic preparation became the default,
            # an omitted mode hashed as "source". A retry of that exact durable
            # key must still return its intent instead of conflicting.
            legacy = (
                "mode" not in req.model_fields_set
                and existing.mode == "source"
                and preparation_plan.request_hash(
                    collection_id, source_id, revision.id, req, topic, mode="source"
                )
            )
            if existing.request_hash != legacy:
                raise Conflict(
                    "Idempotency-Key đã dùng cho một yêu cầu khác.",
                    code="idempotency_conflict",
                )
        if existing.status in ACTIVE_PREPARATION_STATUSES:
            # A retried request may recover an enqueue that failed earlier; the
            # row and its hashes still decide whether the step may run.
            return PreparationOutcome(existing, False, await dispatch(db, existing, queue))
        return PreparationOutcome(existing, False, existing.dispatched_at is not None)

    if req.mode == "ai":
        await assert_provider_allowed(db, actor, workspace_id, "chat", req.provider_id)
    provider_id = req.provider_id
    policy: dict | None = None
    if req.mode == "auto":
        policy, provider_id = await preparation_plan.auto_policy(db, actor, workspace_id)
    await _check_pinned_run(db, workspace_id, collection_id, revision, req)
    text_version_id, text_canonical_sha256 = await _saved_version(
        db, workspace_id, collection_id, req
    )
    intent = PreparationIntent(
        id=new_id("prep"),
        workspace_id=workspace_id,
        collection_id=collection_id,
        source_id=source_id,
        revision_id=revision.id,
        revision_no=revision.revision_no,
        revision_sha256=revision.sha256,
        requested_by=ref,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        mode=req.mode,
        status="queued",
        topic=topic,
        text_version=req.text_version,
        text_version_id=text_version_id,
        text_canonical_sha256=text_canonical_sha256,
        provider_id=provider_id,
        max_output_tokens=req.max_output_tokens,
        config={
            "workflow_version": "qnu.preparation/v1",
            **preparation_plan.plan_flags(req.mode, policy),
            **({"policy": policy} if policy is not None else {}),
        },
        ocr_run_id=req.ocr_run_id,
    )
    db.add(intent)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="source.preparation_requested",
        detail={
            "intent_id": intent.id,
            "collection_id": collection_id,
            "source_id": source_id,
            "revision_id": revision.id,
            "revision_no": revision.revision_no,
            "revision_sha256": revision.sha256,
            "mode": req.mode,
            "text_version": req.text_version,
            "ocr_run_id": req.ocr_run_id,
        },
    )
    await db.commit()
    await db.refresh(intent)
    dispatched = await dispatch(db, intent, queue)
    return PreparationOutcome(intent, True, dispatched)


async def dispatch(db: AsyncSession, intent: PreparationIntent, queue: JobQueue | None) -> bool:
    """Enqueue one advance; the row stays the source of truth if the queue is down."""
    if queue is None or intent.status not in ACTIVE_PREPARATION_STATUSES:
        return False
    try:
        await queue.enqueue(
            TASK_NAME, intent.id, job_id=f"qnu:v1:preparation:{intent.id}:{uuid.uuid4().hex[:12]}"
        )
    except Exception:
        logger.warning("preparation_dispatch_pending", intent_id=intent.id)
        return False
    await db.execute(
        update(PreparationIntent)
        .where(
            PreparationIntent.id == intent.id,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
        .values(dispatched_at=utcnow())
    )
    await db.commit()
    return True


async def get_intent(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    intent_id: str,
) -> PreparationIntent:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    intent = await db.scalar(
        select(PreparationIntent).where(
            PreparationIntent.id == intent_id,
            PreparationIntent.workspace_id == workspace_id,
            PreparationIntent.collection_id == collection_id,
        )
    )
    if intent is None:
        raise EntityNotFound(
            "Không tìm thấy yêu cầu chuẩn bị nội dung.", code="preparation_not_found"
        )
    return intent


async def list_intents(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    limit: int = 20,
) -> list[PreparationIntent]:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    await load_source(db, workspace_id, collection_id, source_id)
    return list(
        (
            await db.scalars(
                select(PreparationIntent)
                .where(
                    PreparationIntent.workspace_id == workspace_id,
                    PreparationIntent.collection_id == collection_id,
                    PreparationIntent.source_id == source_id,
                )
                .order_by(PreparationIntent.created_at.desc(), PreparationIntent.id)
                .limit(limit)
            )
        ).all()
    )


async def cancel(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    intent_id: str,
) -> PreparationIntent:
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    intent = await db.scalar(
        select(PreparationIntent)
        .where(
            PreparationIntent.id == intent_id,
            PreparationIntent.workspace_id == workspace_id,
            PreparationIntent.collection_id == collection_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if intent is None:
        raise EntityNotFound(
            "Không tìm thấy yêu cầu chuẩn bị nội dung.", code="preparation_not_found"
        )
    if intent.status in TERMINAL_PREPARATION_STATUSES:
        return intent
    intent.status = "cancelled"
    intent.error_code = "preparation_cancelled"
    intent.finished_at = utcnow()
    intent.lease_expires_at = None
    intent.worker_id = None
    if intent.compilation_run_id:
        # Conditional update: a run that already settled is never rewritten as cancelled.
        await db.execute(
            update(CompilationRun)
            .where(
                CompilationRun.id == intent.compilation_run_id,
                CompilationRun.workspace_id == workspace_id,
                CompilationRun.status.in_(ADVANCING_OCR_STATUSES),
            )
            .values(
                status="cancelled",
                error_code="compilation_cancelled",
                finished_at=utcnow(),
                lease_expires_at=None,
                worker_id=None,
            )
        )
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="source.preparation_cancelled",
        detail={"intent_id": intent.id, "source_id": intent.source_id},
    )
    await db.commit()
    await db.refresh(intent)
    return intent


async def notify_for_ocr_run(db: AsyncSession, run_id: str, queue: JobQueue | None) -> bool:
    intent = await db.scalar(
        select(PreparationIntent).where(
            PreparationIntent.ocr_run_id == run_id,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
    )
    if intent is None:
        return False
    return await dispatch(db, intent, queue)


async def notify_for_compilation(db: AsyncSession, run_id: str, queue: JobQueue | None) -> bool:
    intent = await db.scalar(
        select(PreparationIntent).where(
            PreparationIntent.compilation_run_id == run_id,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
    )
    if intent is None:
        return False
    return await dispatch(db, intent, queue)


async def execute_intent(
    db: AsyncSession,
    blob: BlobStore,
    queue: JobQueue | None,
    intent_id: str,
    worker_id: str,
) -> str:
    """Claim, re-authorize and advance one step; failures are recorded on the row."""
    now = utcnow()
    token = worker_id[:80] + ":" + uuid.uuid4().hex
    claimed = await db.scalar(
        update(PreparationIntent)
        .where(
            PreparationIntent.id == intent_id,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
            PreparationIntent.lease_expires_at.is_(None)
            | (PreparationIntent.lease_expires_at < now),
        )
        .values(
            worker_id=token,
            lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
            started_at=func.coalesce(PreparationIntent.started_at, now),
        )
        .returning(PreparationIntent.id)
    )
    await db.commit()
    if claimed is None:
        return "not_claimed"
    intent = await db.get(PreparationIntent, intent_id, populate_existing=True)
    try:
        status = await _advance(db, blob, intent, queue)
    except asyncio.CancelledError:
        await db.rollback()
        await _release(db, intent_id, token)
        raise
    except AppException as exc:
        await db.rollback()
        status = await _finish(
            db, intent_id, token, "failed", exc.code, exc.detail
        )
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "preparation_advance_failed",
            intent_id=intent_id,
            error_type=type(exc).__name__,
            error=str(exc)[:300],
        )
        status = await _finish(
            db,
            intent_id,
            token,
            "uncertain",
            "preparation_advance_interrupted",
            "Không xác định được kết quả bước chuẩn bị.",
        )
    await _release(db, intent_id, token)
    return status


async def reconcile(db: AsyncSession, queue: JobQueue | None) -> int:
    """Re-enqueue active intents whose lease expired or whose delivery was lost."""
    if queue is None:
        return 0
    now = utcnow()
    rows = (
        await db.scalars(
            select(PreparationIntent.id)
            .where(
                PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
                PreparationIntent.lease_expires_at.is_(None)
                | (PreparationIntent.lease_expires_at < now),
            )
            .order_by(PreparationIntent.created_at)
            .limit(50)
        )
    ).all()
    count = 0
    for intent_id in rows:
        try:
            queued = await queue.enqueue(
                TASK_NAME,
                intent_id,
                job_id=f"qnu:v1:preparation:{intent_id}:reconcile:{uuid.uuid4().hex[:12]}",
            )
        except Exception:
            logger.warning("preparation_reconcile_failed", intent_id=intent_id)
            continue
        if queued:
            await db.execute(
                update(PreparationIntent)
                .where(
                    PreparationIntent.id == intent_id,
                    PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
                )
                .values(dispatched_at=utcnow())
            )
            count += 1
    await db.commit()
    return count


# --------------------------------------------------------------------------- internals
async def _pin_revision(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    source: KBSource,
    revision_id: str | None,
) -> KBSourceRevision:
    if revision_id is None:
        revision = await db.scalar(
            select(KBSourceRevision).where(
                KBSourceRevision.source_id == source.id,
                KBSourceRevision.workspace_id == workspace_id,
                KBSourceRevision.revision_no == source.latest_revision_no,
            )
        )
        if revision is None:
            raise EntityNotFound("Không tìm thấy phiên bản tài liệu.", code="revision_not_found")
    else:
        revision = await load_revision(db, workspace_id, source.id, revision_id)
    if revision.collection_id != collection_id:
        raise EntityNotFound("Không tìm thấy phiên bản tài liệu.", code="revision_not_found")
    return revision


async def _check_pinned_run(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    revision: KBSourceRevision,
    req: PreparationRequest,
) -> None:
    if not req.ocr_run_id:
        return
    run = await db.scalar(
        select(OcrProcessingRun).where(
            OcrProcessingRun.id == req.ocr_run_id,
            OcrProcessingRun.workspace_id == workspace_id,
            OcrProcessingRun.collection_id == collection_id,
            OcrProcessingRun.revision_id == revision.id,
        )
    )
    if run is None:
        raise EntityNotFound(
            "Không tìm thấy lượt đọc nội dung đã chọn.", code="preparation_ocr_run_not_found"
        )
    if run.status in FAILED_OCR_STATUSES:
        raise Conflict(
            "Lượt đọc nội dung đã chọn không có kết quả dùng được.",
            code="preparation_ocr_run_unusable",
        )
    if req.text_version > 0 and run.status != "completed":
        raise Conflict(
            "Bản văn bản chỉ dùng được khi lượt đọc đã hoàn tất.",
            code="preparation_text_version_not_ready",
        )


async def _saved_version(
    db: AsyncSession, workspace_id: str, collection_id: str, req: PreparationRequest
) -> tuple[str | None, str | None]:
    if req.text_version == 0:
        return None, None
    row = await db.scalar(
        select(TextVersion).where(
            TextVersion.run_id == req.ocr_run_id,
            TextVersion.version == req.text_version,
            TextVersion.workspace_id == workspace_id,
            TextVersion.collection_id == collection_id,
        )
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy bản văn bản đã lưu của lượt đọc này.",
            code="preparation_text_version_not_found",
        )
    return row.id, row.canonical_sha256


async def _pinned_run(
    db: AsyncSession,
    intent: PreparationIntent,
    workspace_id: str,
    collection_id: str,
) -> OcrProcessingRun:
    run = await db.scalar(
        select(OcrProcessingRun).where(
            OcrProcessingRun.id == intent.ocr_run_id,
            OcrProcessingRun.workspace_id == workspace_id,
            OcrProcessingRun.collection_id == collection_id,
            OcrProcessingRun.revision_id == intent.revision_id,
        )
    )
    if run is None:
        raise EntityNotFound(
            "Không tìm thấy lượt đọc nội dung đã ghim.", code="preparation_ocr_run_missing"
        )
    return run


async def _advance(
    db: AsyncSession,
    blob: BlobStore,
    intent: PreparationIntent,
    queue: JobQueue | None,
) -> str:
    actor = background_actor(intent.requested_by)
    workspace_id, collection_id = intent.workspace_id, intent.collection_id
    await resolve_workspace_access(db, actor, workspace_id, required_roles=WRITE_ROLES)
    await load_source(db, workspace_id, collection_id, intent.source_id)
    revision = await load_revision(db, workspace_id, intent.source_id, intent.revision_id)
    if (
        revision.sha256 != intent.revision_sha256
        or revision.revision_no != intent.revision_no
    ):
        return await _fail(
            db,
            intent,
            "preparation_source_changed",
            "Phiên bản nguồn đã thay đổi; không dùng nội dung cũ.",
        )
    if intent.mode == "auto":
        await preparation_plan.verify_auto_policy(db, intent, workspace_id)

    if intent.ocr_run_id:
        run = await _pinned_run(db, intent, workspace_id, collection_id)
    else:
        scope = await resolve_revision_scope(
            db, workspace_id, collection_id, intent.source_id, intent.revision_id
        )
        try:
            outcome = await processing_service.request_run(
                db,
                actor,
                scope,
                provider_id=None,
                job_queue=None,
                strategy="auto",
                force=False,
            )
        except Conflict as exc:
            if exc.code != "processing_run_active":
                raise
            waiting = await _advance_status(db, intent, "waiting_ocr")
            return waiting
        run = outcome.run
        intent.ocr_run_id = run.id
        await db.commit()

    if run.status in ADVANCING_OCR_STATUSES:
        waiting = await _advance_status(db, intent, "waiting_ocr")
        if waiting != "waiting_ocr":
            return waiting
        await processing_service.dispatch(db, run, queue)
        return waiting
    if run.status in FAILED_OCR_STATUSES:
        return await _fail(
            db,
            intent,
            f"preparation_ocr_{run.status}",
            "Đọc nội dung không hoàn tất; chỉnh cấu hình đọc rồi thử lại.",
        )
    if run.status != "completed":
        return await _fail(
            db, intent, "preparation_ocr_invalid", "Lượt đọc nội dung không dùng được."
        )
    await _verify_text_version(db, intent, run, workspace_id, collection_id)

    if intent.compilation_run_id:
        compilation = await db.get(CompilationRun, intent.compilation_run_id)
        if compilation is None:
            return await _fail(
                db,
                intent,
                "preparation_compilation_missing",
                "Mất lượt chuẩn bị nội dung đã ghim.",
            )
    else:
        compilation = None
        reuse_key = None
        if intent.mode == "auto":
            reuse_key = preparation_plan.reuse_key(intent, run)
            compilation = await preparation_plan.reusable_compilation(db, intent, reuse_key)
        if compilation is not None:
            intent.compilation_run_id = compilation.id
            intent.config = {**intent.config, "reused": True}
            await db.commit()
        else:
            outcome = await compilation_service.request_run(
                db,
                blob,
                actor,
                workspace_id,
                collection_id,
                _compilation_request(intent, run),
                f"prep:{intent.id}",
                None,
                reuse_key=reuse_key,
            )
            compilation = outcome.run
            intent.compilation_run_id = compilation.id
            await db.commit()

    if compilation.status in ADVANCING_OCR_STATUSES:
        compiling = await _advance_status(db, intent, "compiling")
        if compiling != "compiling":
            return compiling
        await compilation_service.dispatch(db, compilation, queue)
        return compiling
    if compilation.status == "completed":
        return await _settle(db, intent, "ready", None, None)
    if compilation.status in FAILED_OCR_STATUSES:
        return await _fail(
            db,
            intent,
            f"preparation_compilation_{compilation.status}",
            "Chuẩn bị nội dung không hoàn tất; xem chi tiết ở lượt chuẩn bị.",
        )
    return await _fail(
        db, intent, "preparation_compilation_invalid", "Trạng thái chuẩn bị không rõ."
    )


def _compilation_request(intent: PreparationIntent, run: OcrProcessingRun) -> CompilationRequest:
    versions = {run.id: intent.text_version} if intent.text_version else {}
    flags = preparation_plan.plan_flags(intent.mode, intent.config.get("policy"))
    uses_ai = flags["ai_supplement"] or flags["selective_supplement"]
    return CompilationRequest(
        topic=intent.topic,
        ocr_run_ids=[run.id],
        text_versions=versions,
        provider_id=intent.provider_id if uses_ai else None,
        max_output_tokens=intent.max_output_tokens if flags["ai_supplement"] else None,
        **flags,
    )


async def _verify_text_version(
    db: AsyncSession,
    intent: PreparationIntent,
    run: OcrProcessingRun,
    workspace_id: str,
    collection_id: str,
) -> None:
    if intent.text_version == 0:
        return
    row = await db.scalar(
        select(TextVersion).where(
            TextVersion.run_id == run.id,
            TextVersion.version == intent.text_version,
            TextVersion.workspace_id == workspace_id,
            TextVersion.collection_id == collection_id,
        )
    )
    if row is None or (
        intent.text_canonical_sha256 is not None
        and row.canonical_sha256 != intent.text_canonical_sha256
    ):
        raise Conflict(
            "Bản văn bản đã lưu không còn khớp lượt đọc.", code="preparation_text_version_invalid"
        )
    intent.text_version_id = row.id
    intent.text_canonical_sha256 = row.canonical_sha256


async def _fail(
    db: AsyncSession, intent: PreparationIntent, code: str, detail: str | None
) -> str:
    return await _settle(db, intent, "failed", code, detail)


async def _settle(
    db: AsyncSession,
    intent: PreparationIntent,
    status: str,
    error_code: str | None,
    error_detail: str | None,
) -> str:
    """Finish an intent only while it is still active.

    A user cancel commits from another session; an in-flight worker holding a
    stale ORM row must not overwrite the stop with a later terminal status.
    """
    result = await db.execute(
        update(PreparationIntent)
        .where(
            PreparationIntent.id == intent.id,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
        .values(
            status=status,
            error_code=error_code,
            error_detail=(error_detail or "")[:500] or None,
            finished_at=utcnow(),
            lease_expires_at=None,
            worker_id=None,
        )
        .returning(PreparationIntent.status)
    )
    await db.commit()
    settled = result.scalar_one_or_none()
    if settled is not None:
        return settled
    return await _current_status(db, intent.id) or status


async def _advance_status(
    db: AsyncSession, intent: PreparationIntent, status: str
) -> str:
    """Publish an intermediate step without reviving a cancelled intent."""
    result = await db.execute(
        update(PreparationIntent)
        .where(
            PreparationIntent.id == intent.id,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
        .values(status=status)
        .returning(PreparationIntent.status)
    )
    await db.commit()
    applied = result.scalar_one_or_none()
    if applied is not None:
        return applied
    return await _current_status(db, intent.id) or status


async def _current_status(db: AsyncSession, intent_id: str) -> str | None:
    return await db.scalar(
        select(PreparationIntent.status).where(PreparationIntent.id == intent_id)
    )


async def _finish(
    db: AsyncSession,
    intent_id: str,
    token: str,
    status: str,
    error_code: str | None,
    error_detail: str | None,
) -> str:
    await db.execute(
        update(PreparationIntent)
        .where(
            PreparationIntent.id == intent_id,
            PreparationIntent.worker_id == token,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
        .values(
            status=status,
            error_code=error_code,
            error_detail=(error_detail or "")[:500] or None,
            finished_at=utcnow(),
            lease_expires_at=None,
            worker_id=None,
        )
    )
    await db.commit()
    return status


async def _release(db: AsyncSession, intent_id: str, token: str) -> None:
    await db.execute(
        update(PreparationIntent)
        .where(
            PreparationIntent.id == intent_id,
            PreparationIntent.worker_id == token,
            PreparationIntent.status.in_(ACTIVE_PREPARATION_STATUSES),
        )
        .values(lease_expires_at=None, worker_id=None)
    )
    await db.commit()
