"""Readable OCR review, explicit save and synchronized derivative downloads."""

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.policies.access import READ_ROLES
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review import detection, dispositions, service
from qnu.domains.ocr.review.schemas import (
    DetectionResponse,
    DetectRequest,
    RerunReviewRequest,
    RerunReviewResponse,
    ReviewDocument,
    SaveReview,
    SpellingDispositionBatch,
    SpellingDispositionRequest,
    SpellingStatusSummary,
    TextVersionSummary,
)
from qnu.domains.ocr.router import _scope
from qnu.domains.ocr.service import processing_service
from qnu.platform.errors import AppException
from qnu.ports.blob_store import BlobStore
from qnu.ports.chat_model import ChatModel
from qnu.ports.job_queue import JobQueue


def no_store(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


def get_chat_model(request: Request) -> ChatModel:
    return request.app.state.container.chat_model


router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}"
    "/revisions/{revision_id}/processing-runs/{run_id}/text-review",
    tags=["Knowledge · OCR text review"],
    dependencies=[Depends(no_store)],
)


async def scoped_run(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    revision_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> OcrProcessingRun:
    scope = await _scope(db, actor, workspace_id, collection_id, source_id, revision_id, READ_ROLES)
    return await processing_service.get_run(db, scope.workspace_id, scope.revision_id, run_id)


RequestKey = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


@router.get("", response_model=ReviewDocument)
async def read_text(
    run: OcrProcessingRun = Depends(scoped_run),
    version: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    blob: BlobStore = Depends(get_blob_store),
):
    return await service.read_review(db, blob, run, version)


@router.post("", response_model=ReviewDocument)
async def save_text(
    body: SaveReview,
    idempotency_key: str = RequestKey,
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
    blob: BlobStore = Depends(get_blob_store),
    actor: AuthActor = Depends(get_actor),
):
    return await service.save(db, blob, actor, run, body, idempotency_key)


@router.get("/document")
async def download_json(
    run: OcrProcessingRun = Depends(scoped_run),
    version: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    blob: BlobStore = Depends(get_blob_store),
):
    doc, _, row = await service.document(db, blob, run, version)
    payload = (
        await service.checked_bytes(blob, row.document_key, row.canonical_sha256)
        if row
        else service.json_bytes(doc)
    )
    return Response(
        payload,
        media_type="application/json",
        headers={
            "ETag": '"' + (row.canonical_sha256 if row else service.sha(payload)) + '"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/markdown")
async def download_markdown(
    run: OcrProcessingRun = Depends(scoped_run),
    version: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    blob: BlobStore = Depends(get_blob_store),
):
    doc, _, row = await service.document(db, blob, run, version)
    payload = (
        await service.checked_bytes(blob, row.markdown_key, row.markdown_sha256)
        if row
        else service.render_markdown(doc).encode("utf-8")
    )
    return Response(
        payload,
        media_type="text/markdown; charset=utf-8",
        headers={
            "ETag": '"' + service.sha(payload) + '"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/versions", response_model=list[TextVersionSummary])
async def list_versions(
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
):
    return await service.versions(db, run)


@router.get("/checks", response_model=list[DetectionResponse])
async def list_checks(
    run: OcrProcessingRun = Depends(scoped_run),
    version: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await detection.list_checks(db, run, version)


@router.post("/checks", response_model=DetectionResponse)
async def detect_text(
    body: DetectRequest,
    idempotency_key: str = RequestKey,
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
    blob: BlobStore = Depends(get_blob_store),
    chat: ChatModel = Depends(get_chat_model),
    actor: AuthActor = Depends(get_actor),
):
    return await detection.inspect(db, blob, chat, actor, run, body, idempotency_key)


@router.post(
    "/checks/rerun",
    response_model=RerunReviewResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def rerun_checks(
    body: RerunReviewRequest,
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    job_queue: JobQueue | None = Depends(get_job_queue),
):
    await service.authorize(db, actor, run, write=True)
    await service.version_row(db, run.id, body.version)
    existing = (await detection.list_checks(db, run, body.version))[:1]
    if existing:
        current = existing[0]
        if current.status in {"running", "completed", "cancelled"} or not body.retry:
            return RerunReviewResponse(run_id=run.id, version=body.version, status=current.status)
    if job_queue is None:
        raise AppException(
            "Hàng đợi xử lý chưa sẵn sàng; chưa thể soát lại.",
            code="spelling_queue_unavailable",
            status_code=503,
        )
    retry_of = existing[0].id if existing else None
    job_id = f"qnu:v1:spelling:{run.id}:{body.version}"
    if retry_of:
        job_id += f":retry:{retry_of}"
    try:
        await job_queue.enqueue(
            "spelling_check_job", run.id, body.version, retry_of is not None, job_id=job_id
        )
    except Exception as exc:
        raise AppException(
            "Chưa gửi được yêu cầu soát lại; hãy thử lại.",
            code="spelling_rerun_failed",
            status_code=503,
        ) from exc
    return RerunReviewResponse(run_id=run.id, version=body.version, status="queued")


@router.get("/checks/summary", response_model=SpellingStatusSummary)
async def check_summary(
    version: int = Query(..., ge=0),
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
):
    return await detection.status_summary(db, run, version)


@router.get("/checks/{check_id}", response_model=DetectionResponse)
async def read_check(
    check_id: str, run: OcrProcessingRun = Depends(scoped_run), db: AsyncSession = Depends(get_db)
):
    return await detection.get_check(db, run, check_id)


@router.post("/checks/{check_id}/dispositions/bulk", response_model=DetectionResponse)
async def set_dispositions_bulk(
    body: SpellingDispositionBatch,
    check_id: str,
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
):
    return await dispositions.ignore_all(db, actor, run, check_id, body)


@router.post("/checks/{check_id}/dispositions", response_model=DetectionResponse)
async def set_disposition(
    body: SpellingDispositionRequest,
    check_id: str,
    run: OcrProcessingRun = Depends(scoped_run),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
):
    return await dispositions.set_ignored(db, actor, run, check_id, body)
