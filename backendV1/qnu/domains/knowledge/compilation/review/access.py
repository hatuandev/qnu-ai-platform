"""Authorize review access and pin the source/draft target a review may touch."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import CompilationRun, utcnow
from qnu.domains.knowledge.compilation.review import artifacts, refinement, text_spans
from qnu.domains.knowledge.compilation.review.material import ReviewMaterial, load_material
from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
)
from qnu.domains.knowledge.compilation.service import get_run
from qnu.domains.knowledge.policies.access import READ_ROLES, load_collection
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore

REVIEW_ROLES = ("admin", "editor", "reviewer")


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
    layout = row.trace.get(text_spans.VERSION)
    if layout:
        return text_spans.apply_layout(material, layout)
    return material


async def can_resume_segmented(db: AsyncSession, previous: CompilationReview) -> bool:
    if previous.status not in {"failed", "uncertain"}:
        return False
    has_manifest = bool((previous.trace.get("segmentation") or {}).get("manifest_sha256"))
    if not has_manifest:
        return await untouched(db, previous.id)
    if previous.status == "uncertain" or await untouched(db, previous.id):
        return True
    segments = list(
        (
            await db.scalars(
                select(CompilationReviewSegment)
                .where(CompilationReviewSegment.review_id == previous.id)
                .order_by(CompilationReviewSegment.segment_index)
            )
        ).all()
    )
    if not segments:
        return False
    leaves = refinement.ordered_leaves(segments)
    if any(leaf.status == "uncertain" for leaf in leaves):
        return False
    return any(
        leaf.status in {"pending", "running", "received"}
        or refinement.refine_reason(leaf) is not None
        for leaf in leaves
    )


async def untouched(db: AsyncSession, review_id: str) -> bool:
    """True only when no part ever reached the provider, so a replay cannot duplicate work."""
    segments = list(
        (
            await db.scalars(
                select(CompilationReviewSegment).where(
                    CompilationReviewSegment.review_id == review_id
                )
            )
        ).all()
    )
    if not segments:
        return False
    for segment in segments:
        if segment.attempt_count or segment.request_started_at is not None:
            return False
        for kind in ("raw_response", "assessment_json"):
            if await artifacts.segment_artifact(db, segment.id, kind) is not None:
                return False
    return True


async def checkpoint(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, row: CompilationReview, run: CompilationRun
) -> None:
    await authorize(db, actor, row.workspace_id, row.collection_id, write=True)
    await db.refresh(row, with_for_update=True)
    if row.status != "running" or row.expires_at <= utcnow():
        raise Conflict("Lượt review đã hết thời gian chờ.", code="compilation_review_expired")
    await target_matches(db, blob, row, run)
