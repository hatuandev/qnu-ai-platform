"""HTTP API for OCR processing runs of one stored revision.

Routes are thin: authorization and the whole workspace → collection → source →
revision chain are resolved here, then one service call does the work. Reading an
artifact never accepts a storage path — the artifact kind is the address.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.policies.access import READ_ROLES
from qnu.domains.knowledge.public_api import WRITE_ROLES, RevisionScope, resolve_revision_scope
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.schemas import (
    EvidenceSnapshotResponse,
    PageStatusResponse,
    ProcessingRunCreatedResponse,
    ProcessingRunDetailResponse,
    ProcessingRunRequest,
    ProcessingRunResponse,
)
from qnu.domains.ocr.service import processing_service
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

router = APIRouter(
    prefix=(
        "/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}"
        "/revisions/{revision_id}/processing-runs"
    ),
    tags=["Knowledge · OCR processing"],
)


async def _scope(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    roles: tuple[str, ...],
) -> RevisionScope:
    await resolve_workspace_access(
        db, actor, workspace_id, required_roles=roles, for_update=roles == WRITE_ROLES
    )
    return await resolve_revision_scope(db, workspace_id, collection_id, source_id, revision_id)


@router.post(
    "",
    response_model=ProcessingRunCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo yêu cầu xử lý OCR cho một phiên bản đã lưu (admin/editor)",
)
async def request_processing_run(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    response: Response,
    body: ProcessingRunRequest | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    job_queue: JobQueue | None = Depends(get_job_queue),
) -> ProcessingRunCreatedResponse:
    scope = await _scope(
        db, actor, workspace_id, collection_id, source_id, revision_id, WRITE_ROLES
    )
    outcome = await processing_service.request_run(
        db,
        actor,
        scope,
        provider_id=body.provider_id if body else None,
        job_queue=job_queue,
        force=body.force if body else False,
    )
    if not outcome.created:
        response.status_code = status.HTTP_200_OK
    return ProcessingRunCreatedResponse(
        run=ProcessingRunResponse.from_run(outcome.run),
        created=outcome.created,
        dispatched=outcome.dispatched,
    )


@router.get(
    "",
    response_model=Page[ProcessingRunResponse],
    summary="Các lượt xử lý của phiên bản (mới nhất trước)",
)
async def list_processing_runs(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[ProcessingRunResponse]:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    runs, total = await processing_service.list_runs(
        db, scope.workspace_id, scope.revision_id, page, page_size
    )
    return Page[ProcessingRunResponse](
        items=[ProcessingRunResponse.from_run(run) for run in runs],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/{run_id}",
    response_model=ProcessingRunDetailResponse,
    summary="Trạng thái và tiến độ thật của một lượt xử lý",
)
async def get_processing_run(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> ProcessingRunDetailResponse:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    rows = await processing_service.page_rows(db, run.id)
    return ProcessingRunDetailResponse(
        **ProcessingRunResponse.from_run(run).model_dump(),
        pages=[
            PageStatusResponse(
                page_number=row.page_number,
                status=row.status,
                image_sha256=row.image_sha256,
                blocks_count=row.blocks_count,
                has_tables=row.has_tables,
                error_code=row.error_code,
                usage_tokens=row.usage_tokens,
            )
            for row in rows.values()
        ],
    )


@router.post(
    "/{run_id}/dispatch",
    response_model=ProcessingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gửi lại lượt xử lý đang chờ (admin/editor)",
)
async def dispatch_processing_run(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    job_queue: JobQueue | None = Depends(get_job_queue),
) -> ProcessingRunResponse:
    scope = await _scope(
        db, actor, workspace_id, collection_id, source_id, revision_id, WRITE_ROLES
    )
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    await processing_service.dispatch(db, run, job_queue)
    return ProcessingRunResponse.from_run(run)


@router.get(
    "/{run_id}/document",
    response_class=Response,
    responses={200: {"content": {"application/json": {}}}},
    summary="Canonical JSON đã ghim của lượt xử lý",
)
async def read_document(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob_store: BlobStore = Depends(get_blob_store),
) -> Response:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run: OcrProcessingRun = await processing_service.get_run(
        db, scope.workspace_id, scope.revision_id, run_id
    )
    sha256, payload = await processing_service.read_document(db, blob_store, run)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"ETag": f'"{sha256}"', "X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/{run_id}/markdown",
    response_class=Response,
    responses={200: {"content": {"text/markdown": {}}}},
    summary="Markdown dẫn xuất của lượt xử lý",
)
async def read_markdown(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob_store: BlobStore = Depends(get_blob_store),
) -> Response:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    payload = await processing_service.read_markdown(db, blob_store, run)
    return Response(
        content=payload,
        media_type="text/markdown; charset=utf-8",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get(
    "/{run_id}/manifest",
    summary="Manifest artifact và báo cáo kiểm tra kỹ thuật",
)
async def read_manifest(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob_store: BlobStore = Depends(get_blob_store),
) -> dict:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    return await processing_service.read_manifest(db, blob_store, run)


@router.get(
    "/{run_id}/evidence",
    response_model=EvidenceSnapshotResponse,
    summary="Snapshot bằng chứng đã ghim (revision + generation + hash) cho Compiler",
)
async def read_evidence(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob_store: BlobStore = Depends(get_blob_store),
) -> EvidenceSnapshotResponse:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    return EvidenceSnapshotResponse(**await processing_service.snapshot(db, blob_store, run))


@router.get(
    "/{run_id}/pages/{page_number}/raw",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
    summary="Raw response nguyên bản của trang, kể cả lượt xử lý thất bại",
)
async def read_page_raw(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob_store: BlobStore = Depends(get_blob_store),
) -> Response:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    sha256, payload = await processing_service.read_page_raw(db, blob_store, run, page_number)
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "ETag": f'"{sha256}"',
            "Content-Length": str(len(payload)),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{run_id}/pages/{page_number}/image",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    summary="Ảnh trang đã render của lượt xử lý",
)
async def read_page_image(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob_store: BlobStore = Depends(get_blob_store),
) -> Response:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    run = await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)
    sha256, payload = await processing_service.read_page_image(db, blob_store, run, page_number)
    return Response(
        content=payload,
        media_type="image/png",
        headers={
            "ETag": f'"{sha256}"',
            "Content-Length": str(len(payload)),
            "X-Content-Type-Options": "nosniff",
        },
    )
