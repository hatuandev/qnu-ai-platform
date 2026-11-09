"""Read projections for compilation results, drafts, progress and segment artifacts."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation import outputs as compilation_outputs
from qnu.domains.knowledge.compilation import refinement
from qnu.domains.knowledge.compilation.access import get_run
from qnu.domains.knowledge.compilation.artifacts import (
    artifact,
    json_bytes,
    read,
    read_segment,
)
from qnu.domains.knowledge.compilation.models import (
    CompilationArtifact,
    CompilationRun,
    CompilationSegment,
    CompilationSegmentArtifact,
    utcnow,
)
from qnu.domains.knowledge.compilation.scheduler import effective_concurrency
from qnu.domains.knowledge.compilation.schemas import (
    CompilationProgress,
    CompilationSegmentProgress,
)
from qnu.domains.knowledge.source_sections import reading_groups
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


async def read_result(
    db: AsyncSession,
    blob: BlobStore,
    run: CompilationRun,
    kind: str,
) -> tuple[CompilationArtifact | CompilationSegmentArtifact, bytes]:
    if run.status != "completed" and kind in {"draft_json", "markdown"}:
        raise Conflict(
            "Lượt biên soạn chưa có bản nháp hoàn tất.", code="compilation_not_completed"
        )
    if kind == "raw_response" and await artifact(db, run.id, kind) is None:
        # Preserve the single-source raw API; multi-root runs use per-node artifacts.
        roots = list(
            (
                await db.scalars(
                    select(CompilationSegment)
                    .where(
                        CompilationSegment.run_id == run.id,
                        CompilationSegment.parent_segment_id.is_(None),
                    )
                    .limit(2)
                )
            ).all()
        )
        if len(roots) == 1:
            return await read_segment(db, blob, roots[0], kind)
    return await read(db, blob, run, kind)


async def read_draft_view(
    db: AsyncSession, blob: BlobStore, run: CompilationRun
) -> tuple[str, dict]:
    _, payload = await read_result(db, blob, run, "draft_json")
    return await _group_draft(db, blob, run, payload)


async def _group_draft(
    db: AsyncSession, blob: BlobStore, run: CompilationRun, payload: bytes
) -> tuple[str, dict]:
    snapshot, raw_input = await read(db, blob, run, "input_snapshot")
    if snapshot.sha256 != run.input_sha256:
        raise Conflict("Snapshot Compiler khác nguồn đã ghim.", code="compilation_source_mismatch")
    content = json.loads(payload)
    content["reading_groups"] = reading_groups(content, json.loads(raw_input)["documents"])
    return hashlib.sha256(json_bytes(content)).hexdigest(), content


async def progress(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
) -> CompilationProgress:
    """Report only durable part states and provider-observed token counts."""
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    segments = list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(CompilationSegment.run_id == run.id)
                .where(CompilationSegment.parent_segment_id.is_(None))
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )
    latest = await compilation_outputs.latest(db, run.id)
    nodes = list(
        (
            await db.scalars(
                select(CompilationSegment)
                .where(
                    CompilationSegment.run_id == run.id,
                )
                .order_by(CompilationSegment.segment_index)
            )
        ).all()
    )
    counts: dict[str, int] = {}
    for segment in segments:
        counts[segment.status] = counts.get(segment.status, 0) + 1
    segmented = bool(run.config.get("segmentation")) or bool(segments)
    if segmented:
        completed = counts.get("completed", 0)
        pending = counts.get("pending", 0)
        # A received part already has provider bytes but is still being validated.
        running = counts.get("running", 0) + counts.get("received", 0)
        failed = counts.get("failed", 0)
        uncertain = counts.get("uncertain", 0)
        cancelled = counts.get("cancelled", 0)
        observed = [
            segment.usage_tokens for segment in segments if segment.usage_tokens is not None
        ]
        active = [
            segment.segment_index
            for segment in segments
            if segment.status in {"running", "received"}
        ]
        concurrency = effective_concurrency(run.config)
    else:
        # A single-call run is one durable request; map its status without inventing parts.
        completed = int(run.status == "completed")
        pending = int(run.status == "queued")
        running = int(run.status == "running")
        failed = int(run.status == "failed")
        uncertain = int(run.status == "uncertain")
        cancelled = int(run.status == "cancelled")
        observed = []
        active = []
        concurrency = 1
    usage_tokens = sum(observed) if observed else run.usage_tokens
    if run.config.get("refinement"):
        usage_tokens = refinement.total_usage(nodes)
    elapsed_seconds = (
        round(((run.finished_at or utcnow()) - run.started_at).total_seconds(), 1)
        if run.started_at is not None
        else None
    )
    return CompilationProgress(
        refinement_timeout_seconds=(run.config.get("refinement") or {}).get("max_seconds", 0),
        nodes=[
            {
                "id": node.id,
                "parent_id": node.parent_segment_id,
                "index": node.segment_index,
                "status": node.status,
                "error_code": node.error_code,
                "request_usage_tokens": refinement.request_usage(node),
            }
            for node in nodes
        ],
        run_id=run.id,
        status=run.status,
        workflow_version=str(run.config.get("workflow_version", "qnu.compiler.workflow/v1")),
        segmented=segmented,
        total=len(segments) if segmented else 1,
        completed=completed,
        pending=pending,
        running=running,
        failed=failed,
        uncertain=uncertain,
        cancelled=cancelled,
        usage_tokens=usage_tokens,
        started_at=run.started_at,
        finished_at=run.finished_at,
        latest_output_generation=latest.generation if latest is not None else None,
        latest_output_partial=latest.partial if latest is not None else None,
        segments=[
            CompilationSegmentProgress(
                index=segment.segment_index,
                status=segment.status,
                attempt_count=segment.attempt_count,
                usage_tokens=segment.usage_tokens,
                error_code=segment.error_code,
                started_at=segment.started_at,
                finished_at=segment.finished_at,
                duration_seconds=(
                    round((segment.finished_at - segment.started_at).total_seconds(), 1)
                    if segment.started_at is not None and segment.finished_at is not None
                    else None
                ),
            )
            for segment in segments
        ],
        received=counts.get("received", 0) if segmented else 0,
        concurrency=concurrency,
        active_segments=active,
        elapsed_seconds=elapsed_seconds,
        planner_version=(run.config.get("segmentation") or {}).get("planner_version"),
        queue_timeout_seconds=get_settings().MODEL_CHAT_QUEUE_TIMEOUT_SECONDS,
    )


async def read_partial_draft(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    *,
    group_by_source: bool = False,
) -> tuple[str, bytes]:
    """Latest partial JSON generation; never the final publication pointer."""
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    row = await compilation_outputs.latest(db, run.id, partial=True)
    if row is None:
        raise EntityNotFound("Chưa có bản nháp từng phần.", code="compilation_partial_not_found")
    draft, _ = await compilation_outputs.read_output(db, blob, row)
    if group_by_source:
        sha, content = await _group_draft(db, blob, run, draft)
        return sha, json_bytes(content)
    return row.draft_sha256, draft


async def read_segment_raw(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    segment_index: int,
    kind: str = "raw_response",
) -> tuple[str, str, bytes]:
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    segment = await db.scalar(
        select(CompilationSegment).where(
            CompilationSegment.run_id == run.id,
            CompilationSegment.segment_index == segment_index,
        )
    )
    if segment is None:
        raise EntityNotFound("Không tìm thấy phần biên soạn.", code="compilation_segment_not_found")
    if kind not in {"raw_response", "draft_json", "markdown"}:
        raise EntityNotFound("Không có loại artifact này.", code="compilation_artifact_not_found")
    artifact, payload = await read_segment(db, blob, segment, kind)
    return artifact.content_type, artifact.sha256, payload
