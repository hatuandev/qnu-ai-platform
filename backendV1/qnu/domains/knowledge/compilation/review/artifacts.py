"""Review outputs stay immutable and separate from original compiler artifacts."""

import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.review.models import (
    CompilationReview,
    CompilationReviewSegment,
    CompilationReviewSegmentArtifact,
    ReviewArtifact,
)
from qnu.domains.ocr.ids import new_id
from qnu.platform.errors import Conflict, DependencyUnavailable, EntityNotFound
from qnu.ports.blob_store import BlobStore

TYPES = {
    "input_snapshot": "application/json",
    "raw_response": "application/octet-stream",
    "report_json": "application/json",
    "markdown": "text/markdown; charset=utf-8",
    "segment_manifest": "application/json",
}

SEGMENT_TYPES = {
    "raw_response": "application/octet-stream",
    "assessment_json": "application/json",
}


async def store(
    db: AsyncSession, blob: BlobStore, row: CompilationReview, kind: str, payload: bytes
) -> ReviewArtifact:
    sha = hashlib.sha256(payload).hexdigest()
    previous = await db.scalar(
        select(ReviewArtifact).where(
            ReviewArtifact.review_id == row.id, ReviewArtifact.kind == kind
        )
    )
    if previous:
        if previous.sha256 != sha:
            raise Conflict(
                "Artifact review đã có nội dung khác.", code="compilation_review_artifact_conflict"
            )
        return previous
    key = f"v1/workspaces/{row.workspace_id}/compilation-review/{row.id}/{kind}/{sha}"
    try:
        await blob.put_bytes(key, payload, TYPES[kind])
        saved = await blob.get_bytes(key)
        if saved != payload:
            raise ValueError("readback mismatch")
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được đầy đủ artifact review.", code="storage_unavailable"
        ) from exc
    artifact = ReviewArtifact(
        id=new_id("rva"),
        review_id=row.id,
        kind=kind,
        blob_key=key,
        sha256=sha,
        size_bytes=len(payload),
        content_type=TYPES[kind],
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def read(
    db: AsyncSession, blob: BlobStore, row: CompilationReview, kind: str
) -> tuple[ReviewArtifact, bytes]:
    artifact = await db.scalar(
        select(ReviewArtifact).where(
            ReviewArtifact.review_id == row.id, ReviewArtifact.kind == kind
        )
    )
    if artifact is None:
        raise EntityNotFound("Chưa có artifact review.", code="compilation_review_artifact_missing")
    try:
        payload = await blob.get_bytes(artifact.blob_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được artifact review.", code="storage_unavailable"
        ) from exc
    if (
        len(payload) != artifact.size_bytes
        or hashlib.sha256(payload).hexdigest() != artifact.sha256
    ):
        raise DependencyUnavailable(
            "Artifact review không khớp hash.", code="compilation_review_artifact_integrity"
        )
    return artifact, payload


async def segment_artifact(
    db: AsyncSession, segment_id: str, kind: str
) -> CompilationReviewSegmentArtifact | None:
    return await db.scalar(
        select(CompilationReviewSegmentArtifact).where(
            CompilationReviewSegmentArtifact.segment_id == segment_id,
            CompilationReviewSegmentArtifact.kind == kind,
        )
    )


async def store_segment(
    db: AsyncSession,
    blob: BlobStore,
    row: CompilationReview,
    segment: CompilationReviewSegment,
    kind: str,
    payload: bytes,
) -> CompilationReviewSegmentArtifact:
    sha = hashlib.sha256(payload).hexdigest()
    previous = await segment_artifact(db, segment.id, kind)
    if previous is not None:
        if previous.sha256 != sha:
            raise Conflict(
                "Artifact phần review đã có nội dung khác.",
                code="compilation_review_segment_artifact_conflict",
            )
        return previous
    key = (
        f"v1/workspaces/{row.workspace_id}/compilation-review/{row.id}/segments/"
        f"{segment.segment_index:04d}/{kind}/{sha}"
    )
    try:
        await blob.put_bytes(key, payload, SEGMENT_TYPES[kind])
        saved = await blob.get_bytes(key)
        if saved != payload:
            raise ValueError("readback mismatch")
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được đầy đủ artifact phần review.", code="storage_unavailable"
        ) from exc
    artifact = CompilationReviewSegmentArtifact(
        id=new_id("rva"),
        segment_id=segment.id,
        kind=kind,
        blob_key=key,
        sha256=sha,
        size_bytes=len(payload),
        content_type=SEGMENT_TYPES[kind],
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def read_segment(
    db: AsyncSession,
    blob: BlobStore,
    segment: CompilationReviewSegment,
    kind: str,
) -> tuple[CompilationReviewSegmentArtifact, bytes]:
    artifact = await segment_artifact(db, segment.id, kind)
    if artifact is None:
        raise EntityNotFound(
            "Chưa có artifact phần review.", code="compilation_review_segment_artifact_missing"
        )
    try:
        payload = await blob.get_bytes(artifact.blob_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được artifact phần review.", code="storage_unavailable"
        ) from exc
    if (
        len(payload) != artifact.size_bytes
        or hashlib.sha256(payload).hexdigest() != artifact.sha256
    ):
        raise DependencyUnavailable(
            "Artifact phần review không khớp hash.",
            code="compilation_review_segment_artifact_integrity",
        )
    return artifact, payload
