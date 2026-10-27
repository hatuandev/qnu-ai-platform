"""Collection-scoped workflow status, text edit context, preview and explicit acceptance."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.schemas import CompilationCreated, CompilationResponse
from qnu.domains.knowledge.compilation.workflow import automatic, edits
from qnu.domains.knowledge.compilation.workflow.schemas import (
    AcceptEdit,
    AutoReviewResponse,
    EditRequest,
)
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue


def no_store(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs/{run_id}",
    tags=["Knowledge · Compiler workflow"],
    dependencies=[Depends(no_store)],
)


@router.get("/auto-review", response_model=AutoReviewResponse)
async def auto_review(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
):
    return await automatic.status(db, actor, workspace_id, collection_id, run_id)


@router.get("/edit-context")
async def edit_context(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
):
    return await edits.context(db, blob, actor, workspace_id, collection_id, run_id)


@router.post("/edit-previews")
async def edit_preview(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    body: EditRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
):
    return await edits.preview(db, blob, actor, workspace_id, collection_id, run_id, body)


@router.post("/edits", response_model=CompilationCreated, status_code=201)
async def accept_edit(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    body: AcceptEdit,
    response: Response,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    blob: BlobStore = Depends(get_blob_store),
    queue: JobQueue | None = Depends(get_job_queue),
):
    run, created = await edits.accept(
        db, blob, actor, workspace_id, collection_id, run_id, body, idempotency_key, queue
    )
    if not created:
        response.status_code = 200
    return CompilationCreated(
        run=CompilationResponse.model_validate(run), created=created, dispatched=False
    )
