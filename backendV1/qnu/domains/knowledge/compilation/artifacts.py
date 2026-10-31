"""Content-addressed draft storage through the existing BlobStore port."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.compilation.models import (
    CompilationArtifact,
    CompilationRun,
    CompilationSegment,
    CompilationSegmentArtifact,
)
from qnu.domains.ocr.ids import new_id
from qnu.platform.errors import Conflict, DependencyUnavailable, EntityNotFound
from qnu.ports.blob_store import BlobStore

TYPES = {
    "input_snapshot": ("json", "application/json"),
    "raw_response": ("bin", "application/octet-stream"),
    "draft_json": ("json", "application/json"),
    "markdown": ("md", "text/markdown; charset=utf-8"),
    "segment_manifest": ("json", "application/json"),
}

SEGMENT_TYPES = {
    "markdown": ("md", "text/markdown; charset=utf-8"),
    "raw_response": ("bin", "application/octet-stream"),
    "draft_json": ("json", "application/json"),
}


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


async def artifact(db: AsyncSession, run_id: str, kind: str) -> CompilationArtifact | None:
    return await db.scalar(
        select(CompilationArtifact).where(
            CompilationArtifact.run_id == run_id,
            CompilationArtifact.kind == kind,
        )
    )


async def store(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    kind: str,
    payload: bytes,
) -> CompilationArtifact:
    sha = hashlib.sha256(payload).hexdigest()
    old = await artifact(db, run.id, kind)
    if old is not None:
        if old.sha256 != sha:
            raise Conflict(
                "Artifact Compiler đã có nội dung khác.", code="compilation_artifact_conflict"
            )
        return old
    extension, content_type = TYPES[kind]
    key = f"v1/workspaces/{run.workspace_id}/compilation/{run.id}/{kind}/{sha}.{extension}"
    try:
        await blob.put_bytes(key, payload, content_type)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được artifact Compiler.", code="storage_unavailable"
        ) from exc
    row = CompilationArtifact(
        id=new_id("cart"),
        run_id=run.id,
        kind=kind,
        blob_key=key,
        sha256=sha,
        size_bytes=len(payload),
        content_type=content_type,
    )
    db.add(row)
    await db.flush()
    return row


async def read(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    kind: str,
) -> tuple[CompilationArtifact, bytes]:
    row = await artifact(db, run.id, kind)
    if row is None:
        raise EntityNotFound("Chưa có artifact Compiler.", code="compilation_artifact_not_found")
    try:
        payload = await blob.get_bytes(row.blob_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được artifact Compiler.", code="compilation_artifact_missing"
        ) from exc
    if len(payload) != row.size_bytes or hashlib.sha256(payload).hexdigest() != row.sha256:
        raise DependencyUnavailable(
            "Artifact Compiler không khớp checksum.", code="compilation_artifact_mismatch"
        )
    return row, payload


async def segment_artifact(
    db: AsyncSession, segment_id: str, kind: str
) -> CompilationSegmentArtifact | None:
    return await db.scalar(
        select(CompilationSegmentArtifact).where(
            CompilationSegmentArtifact.segment_id == segment_id,
            CompilationSegmentArtifact.kind == kind,
        )
    )


async def store_segment(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    segment: CompilationSegment,
    kind: str,
    payload: bytes,
) -> CompilationSegmentArtifact:
    """Immutable per-part artifact; a retried part may only reuse identical bytes."""
    sha = hashlib.sha256(payload).hexdigest()
    old = await segment_artifact(db, segment.id, kind)
    if old is not None:
        if old.sha256 != sha:
            raise Conflict(
                "Artifact phần biên soạn đã có nội dung khác.",
                code="compilation_segment_artifact_conflict",
            )
        return old
    extension, content_type = SEGMENT_TYPES[kind]
    key = (
        f"v1/workspaces/{run.workspace_id}/compilation/{run.id}/segments/"
        f"{segment.segment_index:04d}/{kind}/{sha}.{extension}"
    )
    try:
        await blob.put_bytes(key, payload, content_type)
        saved = await blob.get_bytes(key)
        if saved != payload:
            raise ValueError("readback mismatch")
    except Exception as exc:
        raise DependencyUnavailable(
            "Không lưu được artifact phần biên soạn.", code="storage_unavailable"
        ) from exc
    row = CompilationSegmentArtifact(
        id=new_id("cart"),
        segment_id=segment.id,
        kind=kind,
        blob_key=key,
        sha256=sha,
        size_bytes=len(payload),
        content_type=content_type,
    )
    db.add(row)
    await db.flush()
    return row


async def read_segment(
    db: AsyncSession,
    blob: BlobStore,
    segment: CompilationSegment,
    kind: str,
) -> tuple[CompilationSegmentArtifact, bytes]:
    row = await segment_artifact(db, segment.id, kind)
    if row is None:
        raise EntityNotFound(
            "Chưa có artifact của phần biên soạn.", code="compilation_segment_artifact_not_found"
        )
    try:
        payload = await blob.get_bytes(row.blob_key)
    except Exception as exc:
        raise DependencyUnavailable(
            "Không đọc được artifact phần biên soạn.",
            code="compilation_segment_artifact_missing",
        ) from exc
    if len(payload) != row.size_bytes or hashlib.sha256(payload).hexdigest() != row.sha256:
        raise DependencyUnavailable(
            "Artifact phần biên soạn không khớp checksum.",
            code="compilation_segment_artifact_mismatch",
        )
    return row, payload
