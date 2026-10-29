"""HTTP API for knowledge sources and their immutable file revisions.

The file is stored as uploaded bytes. The source service atomically records a
native-first extraction intent for PDF/DOCX; processing remains a separate run.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.contracts.idempotency import idempotency_key as idempotency_key_dep
from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.artifacts.files import content_disposition, read_limited
from qnu.domains.knowledge.models import KBSource, KBSourceRevision
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES
from qnu.domains.knowledge.sources.schemas import (
    RevisionResponse,
    SourceMoveRequest,
    SourceRenameRequest,
    SourceResponse,
    SourceUploadResponse,
)
from qnu.domains.knowledge.sources.service import source_service
from qnu.domains.ocr.schemas import ProcessingRunResponse
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/sources",
    tags=["Knowledge · Sources"],
)


def _revision_out(revision: KBSourceRevision) -> RevisionResponse:
    return RevisionResponse(
        id=revision.id,
        source_id=revision.source_id,
        revision_no=revision.revision_no,
        file_name=revision.file_name,
        content_type=revision.content_type,
        size_bytes=revision.size_bytes,
        sha256=revision.sha256,
        created_by=revision.created_by,
        created_at=revision.created_at,
    )


def _source_out(source: KBSource, revision: KBSourceRevision, processing=None) -> SourceResponse:
    return SourceResponse(
        id=source.id,
        workspace_id=source.workspace_id,
        collection_id=source.collection_id,
        folder_id=source.folder_id,
        title=source.title,
        status=source.status,
        revision_count=source.latest_revision_no,
        current_revision_no=revision.revision_no,
        serving_revision_no=source.serving_revision_no,
        file_name=revision.file_name,
        content_type=revision.content_type,
        size_bytes=revision.size_bytes,
        sha256=revision.sha256,
        created_by=source.created_by,
        created_at=source.created_at,
        updated_at=source.updated_at,
        processing=ProcessingRunResponse.from_run(processing) if processing else None,
    )


@router.post(
    "",
    response_model=SourceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải tệp trực tiếp vào kho tri thức (admin/editor)",
)
async def upload_source(
    workspace_id: str,
    collection_id: str,
    response: Response,
    file: UploadFile = File(..., description="Tệp gốc cần lưu"),
    title: str | None = Form(None, max_length=255),
    folder_id: str | None = Form(None, description="Thư mục lưu trữ"),
    auto_extract: bool = Form(True, description="Tự bóc tách PDF/DOCX sau khi lưu"),
    idempotency_key: str | None = Depends(idempotency_key_dep),
    db: AsyncSession = Depends(get_db),
    blob_store: BlobStore = Depends(get_blob_store),
    actor: AuthActor = Depends(get_actor),
    job_queue: JobQueue | None = Depends(get_job_queue),
) -> SourceUploadResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    settings = get_settings()
    payload = await read_limited(file, settings.MAX_UPLOAD_BYTES)
    outcome = await source_service.upload(
        db,
        blob_store,
        workspace,
        collection_id,
        file_name=file.filename or "",
        title=title,
        payload=payload,
        max_bytes=settings.MAX_UPLOAD_BYTES,
        actor=actor,
        idempotency_key=idempotency_key,
        folder_id=folder_id,
        auto_extract=auto_extract,
        job_queue=job_queue,
    )
    if outcome.replayed:
        response.status_code = status.HTTP_200_OK
    processing = await source_service.processing_for_revisions(db, [outcome.revision.id])
    return SourceUploadResponse(
        source=_source_out(outcome.source, outcome.revision, processing.get(outcome.revision.id)),
        revision=_revision_out(outcome.revision),
    )


@router.get(
    "",
    response_model=Page[SourceResponse],
    summary="Nguồn tài liệu trong kho (thành viên đang hoạt động)",
)
async def list_sources(
    workspace_id: str,
    collection_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    folder_id: str | None = Query(
        None, description="Mã thư mục, hoặc 'root' để lấy tài liệu ở gốc"
    ),
    all_folders: bool = Query(False, description="Nếu true, lấy toàn bộ tài liệu bất kể thư mục"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[SourceResponse]:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    rows, total = await source_service.list_page(
        db, workspace, collection_id, page, page_size, folder_id=folder_id, all_folders=all_folders
    )
    processing = await source_service.processing_for_revisions(db, [r.id for _, r in rows])
    return Page[SourceResponse](
        items=[
            _source_out(source, revision, processing.get(revision.id)) for source, revision in rows
        ],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.post(
    "/{source_id}/move",
    response_model=SourceResponse,
    summary="Di chuyển tài liệu sang thư mục khác (hoặc về gốc)",
)
async def move_source(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    req: SourceMoveRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> SourceResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    source, revision = await source_service.move(
        db, workspace, collection_id, source_id, req.target_folder_id, actor
    )
    return _source_out(source, revision)


@router.patch(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Đổi tên / tiêu đề tài liệu",
)
async def rename_source(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    req: SourceRenameRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> SourceResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    source, revision = await source_service.rename(
        db, workspace, collection_id, source_id, req.title, actor
    )
    return _source_out(source, revision)


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Chi tiết nguồn tài liệu",
)
async def get_source(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> SourceResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    source, revision = await source_service.get(db, workspace, collection_id, source_id)
    processing = await source_service.processing_for_revisions(db, [revision.id])
    return _source_out(source, revision, processing.get(revision.id))


@router.get(
    "/{source_id}/revisions",
    response_model=list[RevisionResponse],
    summary="Danh sách phiên bản của nguồn (mới nhất trước)",
)
async def list_revisions(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> list[RevisionResponse]:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    revisions = await source_service.list_revisions(db, workspace, collection_id, source_id)
    return [_revision_out(item) for item in revisions]


@router.post(
    "/{source_id}/revisions",
    response_model=SourceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm phiên bản mới cho nguồn đã có (admin/editor)",
)
async def add_revision(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    response: Response,
    request: Request,
    file: UploadFile = File(..., description="Tệp của phiên bản mới"),
    staged: bool = Form(
        False, description="Giữ bản đang phục vụ đến khi thay thế nguyên tử cùng chỉ mục mới"
    ),
    auto_extract: bool = Form(True, description="Tự bóc tách phiên bản PDF/DOCX mới"),
    idempotency_key: str | None = Depends(idempotency_key_dep),
    db: AsyncSession = Depends(get_db),
    blob_store: BlobStore = Depends(get_blob_store),
    actor: AuthActor = Depends(get_actor),
    job_queue: JobQueue | None = Depends(get_job_queue),
) -> SourceUploadResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    if "title" in await request.form():
        raise AppException(
            "API thêm phiên bản không hỗ trợ thay tiêu đề nguồn.",
            code="revision_title_not_supported",
            status_code=422,
        )
    settings = get_settings()
    payload = await read_limited(file, settings.MAX_UPLOAD_BYTES)
    outcome = await source_service.upload(
        db,
        blob_store,
        workspace,
        collection_id,
        file_name=file.filename or "",
        title=None,
        payload=payload,
        max_bytes=settings.MAX_UPLOAD_BYTES,
        actor=actor,
        idempotency_key=idempotency_key,
        source_id=source_id,
        staged=staged,
        auto_extract=auto_extract,
        job_queue=job_queue,
    )
    if outcome.replayed:
        response.status_code = status.HTTP_200_OK
    processing = await source_service.processing_for_revisions(db, [outcome.revision.id])
    return SourceUploadResponse(
        source=_source_out(outcome.source, outcome.revision, processing.get(outcome.revision.id)),
        revision=_revision_out(outcome.revision),
    )


@router.get(
    "/{source_id}/revisions/{revision_id}/content",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
    summary="Tải lại đúng tệp gốc của một phiên bản",
)
async def download_revision(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    blob_store: BlobStore = Depends(get_blob_store),
    actor: AuthActor = Depends(get_actor),
) -> Response:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    revision, payload = await source_service.read_content(
        db, blob_store, workspace, collection_id, source_id, revision_id
    )
    return Response(
        content=payload,
        media_type=revision.content_type,
        headers={
            "Content-Disposition": content_disposition(revision.file_name),
            "Content-Length": str(len(payload)),
            "ETag": f'"{revision.sha256}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
