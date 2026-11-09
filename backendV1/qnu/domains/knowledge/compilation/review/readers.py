"""Read projections for durable reviews and their segmented artifacts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.artifacts import json_bytes
from qnu.domains.knowledge.compilation.review import artifacts, refinement
from qnu.domains.knowledge.compilation.review.access import get_review, target_matches
from qnu.domains.knowledge.compilation.review.material import ReviewMaterial
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
    ReviewArtifact,
)
from qnu.domains.knowledge.compilation.review.report import VERSION
from qnu.domains.knowledge.compilation.review.schemas import (
    ReviewProgress,
    ReviewSegmentProgress,
)
from qnu.domains.knowledge.compilation.service import get_run
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


def artifacts_payload(material: ReviewMaterial) -> bytes:
    return json_bytes(
        {
            "schema_version": VERSION,
            "bundle_sha256": material.bundle.bundle_sha256,
            **material.payload,
        }
    )


def segment_progress_status(
    review: CompilationReview, segment: CompilationReviewSegment
) -> str:
    if review.status != "cancelled":
        return segment.status
    if segment.status == "running" and segment.request_started_at is not None:
        return "uncertain"
    if segment.status in {"pending", "running", "received"}:
        return "cancelled"
    return segment.status


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
    leaves = refinement.ordered_leaves(segments)
    parent_ids = refinement.parent_ids_for(segments)
    counts: dict[str, int] = {}
    for segment in leaves:
        status = segment_progress_status(row, segment)
        counts[status] = counts.get(status, 0) + 1
    segmented = bool(row.trace.get("segmentation")) or bool(segments)
    if segmented:
        completed = counts.get("completed", 0)
        pending = counts.get("pending", 0)
        # A received part already has provider bytes but is still being validated.
        running = counts.get("running", 0) + counts.get("received", 0)
        failed = counts.get("failed", 0)
        uncertain = counts.get("uncertain", 0)
        cancelled = counts.get("cancelled", 0)
        any_called = any(refinement.request_usage(segment)[0] for segment in segments)
        usage_tokens = refinement.total_usage(segments) if any_called else row.usage_tokens
    else:
        completed = int(row.status == "completed")
        pending = int(row.status == "queued")
        running = int(row.status == "running")
        failed = int(row.status == "failed")
        uncertain = int(row.status == "uncertain")
        cancelled = int(row.status == "cancelled")
        usage_tokens = row.usage_tokens
    return ReviewProgress(
        review_id=row.id,
        status=row.status,
        verdict=row.verdict,
        segmented=segmented,
        total=len(leaves) if segmented else 1,
        completed=completed,
        pending=pending,
        running=running,
        failed=failed,
        uncertain=uncertain,
        cancelled=cancelled,
        usage_tokens=usage_tokens,
        created_at=row.created_at,
        request_started_at=row.request_started_at,
        finished_at=row.finished_at,
        segments=[
            ReviewSegmentProgress(
                id=segment.id,
                index=segment.segment_index,
                parent_segment_id=segment.parent_segment_id,
                depth=refinement.segment_depth(segment),
                is_leaf=segment.id not in parent_ids,
                status=segment_progress_status(row, segment),
                attempt_count=segment.attempt_count,
                usage_tokens=segment.usage_tokens,
                error_code=segment.error_code,
                started_at=segment.started_at,
                finished_at=segment.finished_at,
            )
            for segment in segments
        ],
    )


async def read_segment_artifact(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    segment_index: int,
    kind: str,
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
    if kind in {"assessment_json", "markdown"} and segment.status != "completed":
        raise Conflict(
            "Phần review chưa hoàn tất.", code="compilation_review_segment_not_completed"
        )
    artifact, payload = await artifacts.read_segment(db, blob, segment, kind)
    return artifact.content_type, artifact.sha256, payload


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
    return await read_segment_artifact(
        db,
        blob,
        actor,
        workspace_id,
        collection_id,
        run_id,
        review_id,
        segment_index,
        "raw_response",
    )
