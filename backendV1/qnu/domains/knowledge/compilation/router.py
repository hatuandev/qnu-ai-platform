"""Thin collection-scoped Compiler API; credentials and endpoints are never client options."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation import service
from qnu.domains.knowledge.compilation.models import CompilationRun
from qnu.domains.knowledge.compilation.schemas import (
    CompilationCreated,
    CompilationProgress,
    CompilationRequest,
    CompilationResponse,
)
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs",
    tags=["Knowledge · Compiler"],
)


@router.post("", response_model=CompilationCreated, status_code=201)
async def create_compilation(
    workspace_id: str,
    collection_id: str,
    body: CompilationRequest,
    response: Response,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
    queue: JobQueue | None = Depends(get_job_queue),
) -> CompilationCreated:
    outcome = await service.request_run(
        db, blob, actor, workspace_id, collection_id, body, idempotency_key, queue
    )
    if not outcome.created:
        response.status_code = 200
    return CompilationCreated(
        run=CompilationResponse.model_validate(outcome.run),
        created=outcome.created,
        dispatched=outcome.dispatched,
    )


@router.get("", response_model=list[CompilationResponse])
async def list_compilations(
    workspace_id: str,
    collection_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> list[CompilationRun]:
    return await service.list_runs(db, actor, workspace_id, collection_id, limit, offset)


@router.get("/{run_id}", response_model=CompilationResponse)
async def compilation_status(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> CompilationRun:
    return await service.get_run(db, actor, workspace_id, collection_id, run_id)


@router.get("/{run_id}/draft")
async def compilation_draft(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    response: Response,
    partial: bool = Query(False),
    group_by_source: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
) -> dict:
    if partial:
        sha256, payload = await service.read_partial_draft(
            db, blob, actor, workspace_id, collection_id, run_id
        )
        response.headers.update({"ETag": f'"{sha256}"', "Cache-Control": "private, no-store"})
        return json.loads(payload)
    run = await service.get_run(db, actor, workspace_id, collection_id, run_id)
    if group_by_source:
        sha, content = await service.read_draft_view(db, blob, run)
        response.headers.update({"ETag": f'"{sha}"', "Cache-Control": "private, no-store"})
        return content
    artifact, payload = await service.read_result(db, blob, run, "draft_json")
    response.headers.update({"ETag": f'"{artifact.sha256}"', "Cache-Control": "private, no-store"})
    return json.loads(payload)


@router.get("/{run_id}/progress", response_model=CompilationProgress)
async def compilation_progress(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> CompilationProgress:
    return await service.progress(db, actor, workspace_id, collection_id, run_id)


@router.get("/{run_id}/segments/{segment_index}/raw")
async def compilation_segment_raw(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    segment_index: int,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
) -> Response:
    content_type, sha256, payload = await service.read_segment_raw(
        db, blob, actor, workspace_id, collection_id, run_id, segment_index
    )
    return Response(
        payload,
        media_type=content_type,
        headers={
            "ETag": f'"{sha256}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{run_id}/segments/{segment_index}/artifacts/{kind}")
async def compilation_node_artifact(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    segment_index: int,
    kind: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
) -> Response:
    content_type, sha256, payload = await service.read_segment_raw(
        db,
        blob,
        actor,
        workspace_id,
        collection_id,
        run_id,
        segment_index,
        kind,
    )
    return Response(
        payload,
        media_type=content_type,
        headers={
            "ETag": f'"{sha256}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _raw_response(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    run_id: str,
    kind: str,
) -> Response:
    run = await service.get_run(db, actor, workspace_id, collection_id, run_id)
    artifact, payload = await service.read_result(db, blob, run, kind)
    return Response(
        payload,
        media_type=artifact.content_type,
        headers={
            "ETag": f'"{artifact.sha256}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{run_id}/markdown")
async def compilation_markdown(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
) -> Response:
    return await _raw_response(db, blob, actor, workspace_id, collection_id, run_id, "markdown")


@router.get("/{run_id}/raw")
async def compilation_raw(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
) -> Response:
    return await _raw_response(db, blob, actor, workspace_id, collection_id, run_id, "raw_response")
