"""Actor-bound previews precede lifecycle changes; resource identifiers never grant authority."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.lifecycle import service
from qnu.domains.lifecycle.schemas import AcceptRequest, ActionResponse, PreviewRequest
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue


def no_store(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/workspaces/{workspace_id}/lifecycle",
    tags=["Lifecycle"],
    dependencies=[Depends(no_store)],
)
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]


@router.post("/previews", response_model=ActionResponse)
async def preview(workspace_id: str, body: PreviewRequest, db: DB, actor: Actor, blob: Blob):
    return await service.preview(db, blob, actor, workspace_id, body)


@router.post("/actions", response_model=ActionResponse)
async def accept(
    workspace_id: str,
    body: AcceptRequest,
    db: DB,
    actor: Actor,
    blob: Blob,
    request: Request,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"
        ),
    ],
    queue: JobQueue | None = Depends(get_job_queue),
):
    return await service.accept(
        db,
        blob,
        request.app.state.container.vector_store,
        queue,
        actor,
        workspace_id,
        body,
        idempotency_key,
    )


@router.get("/actions/{action_id}", response_model=ActionResponse)
async def action(workspace_id: str, action_id: str, db: DB, actor: Actor):
    return await service.detail(db, actor, workspace_id, action_id)


@router.get("/resources")
async def resources(
    workspace_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await service.resources(db, actor, workspace_id, limit, offset)


@router.get("/source-deletions", response_model=list[ActionResponse])
async def pending_source_deletions(workspace_id: str, collection_id: str, db: DB, actor: Actor):
    return await service.pending_source_deletions(db, actor, workspace_id, collection_id)
