"""Authorize and pin review targets, persist request before quota can commit."""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import artifacts, parts
from qnu.domains.knowledge.compilation.review.material import ReviewMaterial, load_material
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
    ReviewArtifact,
)
from qnu.domains.knowledge.compilation.review.report import (
    PROMPT_VERSION,
    SYSTEM,
    VERSION,
    messages_for,
    output_schema,
)
from qnu.domains.knowledge.compilation.review.schemas import (
    ReviewProgress,
    ReviewRequest,
    ReviewSegmentProgress,
)
from qnu.domains.knowledge.compilation.service import get_run
from qnu.domains.knowledge.policies.access import READ_ROLES, load_collection
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.modelops.inference.service import (
    available_input_tokens,
    prepare_chat_limits,
    prepare_chat_request,
)
from qnu.domains.modelops.public_api import ChatRuntime, resolve_chat_runtime
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatMessage, ChatRequest

REVIEW_ROLES = ("admin", "editor", "reviewer")
SEGMENTED_CODES = {
    "model_context_limit_exceeded",
    "model_input_limit_exceeded",
    "model_output_limit_exceeded",
}


@dataclass(frozen=True, slots=True)
class PreparedReview:
    run: CompilationRun
    review: CompilationReview
    material: ReviewMaterial | None
    runtime: ChatRuntime | None
    request: ChatRequest | None = None
    messages: list[ChatMessage] | None = None
    segmented: bool = False


async def authorize(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    *,
    write: bool = False,
) -> None:
    await resolve_workspace_access(
        db,
        actor,
        workspace_id,
        required_roles=REVIEW_ROLES if write else READ_ROLES,
        for_update=write,
    )
    await load_collection(db, workspace_id, collection_id)


async def expire(db: AsyncSession, row: CompilationReview) -> None:
    if row.status == "running" and row.expires_at <= utcnow():
        await db.refresh(row, with_for_update=True)
        if row.status != "running" or row.expires_at > utcnow():
            return
        row.status, row.error_code, row.finished_at = (
            "uncertain",
            "compilation_review_interrupted",
            utcnow(),
        )
        await db.commit()


async def get_review(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
) -> CompilationReview:
    await get_run(db, actor, workspace_id, collection_id, run_id)
    row = await db.scalar(
        select(CompilationReview).where(
            CompilationReview.id == review_id,
            CompilationReview.compilation_run_id == run_id,
            CompilationReview.workspace_id == workspace_id,
            CompilationReview.collection_id == collection_id,
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy lượt review.", code="compilation_review_not_found")
    await expire(db, row)
    return row


async def list_reviews(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    limit: int,
    offset: int,
) -> list[CompilationReview]:
    await get_run(db, actor, workspace_id, collection_id, run_id)
    rows = list(
        (
            await db.scalars(
                select(CompilationReview)
                .where(
                    CompilationReview.compilation_run_id == run_id,
                    CompilationReview.workspace_id == workspace_id,
                    CompilationReview.collection_id == collection_id,
                )
                .order_by(CompilationReview.created_at.desc(), CompilationReview.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    for row in rows:
        await expire(db, row)
    return rows


async def target_matches(
    db: AsyncSession, blob: BlobStore, row: CompilationReview, run: CompilationRun
) -> ReviewMaterial:
    material = await load_material(db, blob, run)
    if (row.input_sha256, row.draft_sha256, row.bundle_sha256) != (
        material.bundle.input_sha256,
        material.bundle.draft_sha256,
        material.bundle.bundle_sha256,
    ):
        raise Conflict(
            "Nguồn hoặc bản nháp đã khác đối tượng review.",
            code="compilation_review_target_changed",
        )
    return material


async def checkpoint(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, row: CompilationReview, run: CompilationRun
) -> None:
    await authorize(db, actor, row.workspace_id, row.collection_id, write=True)
    await db.refresh(row, with_for_update=True)
    if row.status != "running" or row.expires_at <= utcnow():
        raise Conflict("Lượt review đã hết thời gian chờ.", code="compilation_review_expired")
    await target_matches(db, blob, row, run)


async def prepare(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    req: ReviewRequest,
    key: str,
) -> PreparedReview:
    await authorize(db, actor, workspace_id, collection_id, write=True)
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    if key == "auto:" + run_id:
        from qnu.domains.knowledge.compilation.workflow.models import AutoReviewJob

        parent = await db.get(AutoReviewJob, run_id, populate_existing=True)
        if parent is None or parent.status != "running":
            raise Conflict(
                "Review tự động không còn quyền thực thi.", code="compilation_auto_review_stopped"
            )
    request_hash = digest(
        {
            "run_id": run_id,
            "collection_id": collection_id,
            **req.model_dump(exclude={"structured_output"} if not req.structured_output else set()),
        }
    )
    previous = await db.scalar(
        select(CompilationReview).where(
            CompilationReview.workspace_id == workspace_id,
            CompilationReview.created_by == actor_ref(actor),
            CompilationReview.idempotency_key == key,
        )
    )
    if previous is not None:
        if previous.request_hash != request_hash:
            raise Conflict("Idempotency-Key đã dùng cho review khác.", code="idempotency_conflict")
        await expire(db, previous)
        # Never resume a request that may still be in flight; a concurrent replay
        # could send the same part twice. Only a stopped review can continue.
        if previous.status == "uncertain" and (
            previous.trace.get("segmentation") or {}
        ).get("manifest_sha256"):
            segment_count = await db.scalar(
                select(func.count())
                .select_from(CompilationReviewSegment)
                .where(CompilationReviewSegment.review_id == previous.id)
            )
            if segment_count:
                runtime = await resolve_chat_runtime(db, workspace_id, previous.provider_id)
                if runtime.configuration_hash != previous.trace.get("configuration_hash"):
                    raise Conflict(
                        "Model review đã thay đổi; không thể tiếp tục.",
                        code="compilation_review_provider_changed",
                    )
                material = await target_matches(db, blob, previous, run)
                previous.status = "running"
                previous.trace = {**previous.trace, "execution_token": new_id("rex")}
                previous.error_code = None
                previous.finished_at = None
                previous.expires_at = utcnow() + timedelta(
                    seconds=max(900, runtime.timeout_seconds + 60) * max(1, segment_count)
                )
                await db.commit()
                return PreparedReview(
                    run=run,
                    review=previous,
                    material=material,
                    runtime=runtime,
                    segmented=True,
                )
        await db.commit()
        return PreparedReview(run, previous, None, None)
    material = await load_material(db, blob, run)
    messages = messages_for(material.payload, structured=req.structured_output)
    schema = output_schema(material.payload) if req.structured_output else None
    runtime: ChatRuntime
    budget = None
    plans: list[parts.ReviewPartPlan] = []
    try:
        runtime, request, budget = await prepare_chat_request(
            db,
            actor,
            workspace_id,
            messages,
            provider_id=req.provider_id,
            task="compiler_review",
            max_output_tokens=req.max_output_tokens,
            output_schema=schema,
        )
        single_call = (request, messages)
    except AppException as exc:
        if exc.code not in SEGMENTED_CODES:
            raise
        runtime, budget = await prepare_chat_limits(
            db,
            actor,
            workspace_id,
            provider_id=req.provider_id,
            task="compiler_review",
            max_output_tokens=req.max_output_tokens,
        )
        capacity = available_input_tokens(runtime.token_limits, budget.max_output_tokens)
        if capacity is None:
            raise AppException(
                "Chưa xác định được ngân sách review.",
                code="model_capacity_required",
                status_code=422,
            ) from exc
        plans = await asyncio.to_thread(
            parts.plan_parts,
            material.payload, capacity=capacity, structured=req.structured_output
        )
        single_call = (None, None)
    assert budget is not None
    trace = {
        "execution_token": new_id("rex"),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": digest(SYSTEM),
        "provider_id": runtime.provider_id,
        "model_name": runtime.model_name,
        "configuration_hash": runtime.configuration_hash,
        "routing": list(runtime.routing_trace),
        "compiler_provider_id": run.provider_id,
        "source_unit_count": len(material.payload["source_units"]),
        "draft_unit_count": len(material.payload["draft_units"]),
        "max_output_tokens": budget.max_output_tokens,
        "total_reserved_tokens": budget.total_reserved_tokens,
        "structured_output": req.structured_output,
        "output_schema_sha256": digest(schema) if schema is not None else None,
    }
    if plans:
        trace.update(
            {
                "workflow_version": "qnu.compiler.review.workflow/v2",
                "segmentation": {
                    "planner_version": parts.PLANNER_VERSION,
                    "prompt_version": parts.SEGMENT_PROMPT_VERSION,
                    "segment_count": len(plans),
                    "input_capacity_tokens": available_input_tokens(
                        runtime.token_limits, budget.max_output_tokens
                    ),
                    "output_tokens": budget.max_output_tokens,
                    "manifest_sha256": None,
                },
            }
        )
    seconds = max(900, runtime.timeout_seconds + 60) * max(1, len(plans))
    row = CompilationReview(
        id=new_id("rvw"),
        compilation_run_id=run_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        created_by=actor_ref(actor),
        idempotency_key=key,
        request_hash=request_hash,
        status="running",
        provider_id=runtime.provider_id,
        input_sha256=material.bundle.input_sha256,
        draft_sha256=material.bundle.draft_sha256,
        bundle_sha256=material.bundle.bundle_sha256,
        expires_at=utcnow() + timedelta(seconds=seconds),
        trace=trace,
    )
    db.add(row)
    await db.flush()
    await artifacts.store(db, blob, row, "input_snapshot", artifacts_payload(material))
    if plans:
        await _store_segments(db, blob, row, run, plans, material, runtime, budget)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="compilation.review_requested",
        detail={
            "review_id": row.id,
            "compilation_run_id": run_id,
            "bundle_sha256": row.bundle_sha256,
            "provider_id": runtime.provider_id,
            "segments": len(plans),
        },
    )
    await db.commit()
    request, messages = single_call
    return PreparedReview(
        run=run,
        review=row,
        material=material,
        runtime=runtime,
        request=request,
        messages=messages,
        segmented=bool(plans),
    )


async def _store_segments(
    db: AsyncSession,
    blob: BlobStore,
    row: CompilationReview,
    run: CompilationRun,
    plans: list[parts.ReviewPartPlan],
    material: ReviewMaterial,
    runtime: ChatRuntime,
    budget,
) -> None:
    manifest = parts.manifest_for(
        row,
        plans,
        material.payload,
        capacity=available_input_tokens(runtime.token_limits, budget.max_output_tokens) or 0,
        output_tokens=budget.max_output_tokens,
    )
    payload = json_bytes(manifest)
    await artifacts.store(db, blob, row, "segment_manifest", payload)
    row.trace = {
        **row.trace,
        "segmentation": {
            **row.trace["segmentation"],
            "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        },
    }
    config = {
        "provider_id": runtime.provider_id,
        "configuration_hash": runtime.configuration_hash,
        "max_output_tokens": budget.max_output_tokens,
        "structured_output": bool(row.trace.get("structured_output")),
    }
    for plan in plans:
        db.add(
            CompilationReviewSegment(
                id=new_id("rvs"),
                review_id=row.id,
                segment_index=plan.index,
                status="pending",
                scope=plan.scope_dict(),
                input_sha256=plan.input_sha256,
                prompt_version=parts.SEGMENT_PROMPT_VERSION,
                schema_sha256=plan.schema_sha256,
                config=config,
                request_hash=digest(
                    {
                        "review_id": row.id,
                        "segment_index": plan.index,
                        "input_sha256": plan.input_sha256,
                        "schema_sha256": plan.schema_sha256,
                        "configuration_hash": runtime.configuration_hash,
                        "max_output_tokens": budget.max_output_tokens,
                        "structured_output": config["structured_output"],
                    }
                ),
            )
        )
    await db.flush()


def artifacts_payload(material: ReviewMaterial) -> bytes:
    return json_bytes(
        {
            "schema_version": VERSION,
            "bundle_sha256": material.bundle.bundle_sha256,
            **material.payload,
        }
    )


async def read_output(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    kind: str,
) -> tuple[ReviewArtifact, bytes]:
    row = await get_review(db, actor, workspace_id, collection_id, run_id, review_id)
    if kind in {"report_json", "markdown"}:
        if row.status != "completed":
            raise Conflict(
                "Review chưa có báo cáo hoàn tất.", code="compilation_review_not_completed"
            )
        run = await get_run(db, actor, workspace_id, collection_id, run_id)
        await target_matches(db, blob, row, run)
    return await artifacts.read(db, blob, row, kind)


async def progress(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
) -> ReviewProgress:
    """Report durable part states; token counts are provider-observed, not estimated."""
    row = await get_review(db, actor, workspace_id, collection_id, run_id, review_id)
    segments = list(
        (
            await db.scalars(
                select(CompilationReviewSegment)
                .where(CompilationReviewSegment.review_id == row.id)
                .order_by(CompilationReviewSegment.segment_index)
            )
        ).all()
    )
    counts: dict[str, int] = {}
    for segment in segments:
        counts[segment.status] = counts.get(segment.status, 0) + 1
    segmented = bool(row.trace.get("segmentation")) or bool(segments)
    if segmented:
        completed = counts.get("completed", 0)
        pending = counts.get("pending", 0)
        # A received part already has provider bytes but is still being validated.
        running = counts.get("running", 0) + counts.get("received", 0)
        failed = counts.get("failed", 0)
        uncertain = counts.get("uncertain", 0)
        cancelled = counts.get("cancelled", 0)
        observed = [segment.usage_tokens for segment in segments if segment.usage_tokens is not None]
    else:
        completed = int(row.status == "completed")
        pending = 0
        running = int(row.status == "running")
        failed = int(row.status == "failed")
        uncertain = int(row.status == "uncertain")
        cancelled = int(row.status == "cancelled")
        observed = []
    return ReviewProgress(
        review_id=row.id,
        status=row.status,
        verdict=row.verdict,
        segmented=segmented,
        total=len(segments) if segmented else 1,
        completed=completed,
        pending=pending,
        running=running,
        failed=failed,
        uncertain=uncertain,
        cancelled=cancelled,
        usage_tokens=sum(observed) if observed else row.usage_tokens,
        created_at=row.created_at,
        request_started_at=row.request_started_at,
        finished_at=row.finished_at,
        segments=[
            ReviewSegmentProgress(
                index=segment.segment_index,
                status=segment.status,
                attempt_count=segment.attempt_count,
                usage_tokens=segment.usage_tokens,
                error_code=segment.error_code,
                started_at=segment.started_at,
                finished_at=segment.finished_at,
            )
            for segment in segments
        ],
    )


async def read_segment_raw(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    segment_index: int,
) -> tuple[str, str, bytes]:
    row = await get_review(db, actor, workspace_id, collection_id, run_id, review_id)
    segment = await db.scalar(
        select(CompilationReviewSegment).where(
            CompilationReviewSegment.review_id == row.id,
            CompilationReviewSegment.segment_index == segment_index,
        )
    )
    if segment is None:
        raise EntityNotFound(
            "Không tìm thấy phần review.", code="compilation_review_segment_not_found"
        )
    artifact, payload = await artifacts.read_segment(db, blob, segment, "raw_response")
    return artifact.content_type, artifact.sha256, payload
