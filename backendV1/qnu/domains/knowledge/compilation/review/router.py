"""Start one review explicitly and read durable status, reports or original model bytes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.review import service
from qnu.domains.knowledge.compilation.review.execution import execute
from qnu.domains.knowledge.compilation.review.models import CompilationReview
from qnu.domains.knowledge.compilation.review.schemas import (
    ReviewProgress,
    ReviewRequest,
    ReviewResponse,
)
from qnu.platform.errors import Conflict
from qnu.ports.blob_store import BlobStore


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs/{run_id}/reviews",
    tags=["Knowledge · Compiler review"],
    dependencies=[Depends(no_store)],
)
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


@router.post("", response_model=ReviewResponse)
async def create(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    body: ReviewRequest,
    request: Request,
    db: DB,
    actor: Actor,
    blob: Blob,
    idempotency_key: Key,
) -> ReviewResponse:
    if idempotency_key.startswith("auto:"):
        raise Conflict("Khóa review tự động được dành riêng.", code="idempotency_conflict")
    return await execute(
        db,
        blob,
        request.app.state.container.chat_model,
        actor,
        workspace_id,
        collection_id,
        run_id,
        body,
        idempotency_key,
    )


@router.get("", response_model=list[ReviewResponse])
async def listing(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[CompilationReview]:
    return await service.list_reviews(db, actor, workspace_id, collection_id, run_id, limit, offset)


@router.get("/{review_id}", response_model=ReviewResponse)
async def detail(
    workspace_id: str, collection_id: str, run_id: str, review_id: str, db: DB, actor: Actor
) -> CompilationReview:
    return await service.get_review(db, actor, workspace_id, collection_id, run_id, review_id)


@router.get("/{review_id}/progress", response_model=ReviewProgress)
async def progress(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    db: DB,
    actor: Actor,
) -> ReviewProgress:
    return await service.progress(
        db, actor, workspace_id, collection_id, run_id, review_id
    )


@router.get("/{review_id}/segments/{segment_index}/raw")
async def segment_raw(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    segment_index: int,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> Response:
    content_type, sha256, payload = await service.read_segment_raw(
        db,
        blob,
        actor,
        workspace_id,
        collection_id,
        run_id,
        review_id,
        segment_index,
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


async def output(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    db: AsyncSession,
    actor: AuthActor,
    blob: BlobStore,
    kind: str,
) -> Response:
    artifact, payload = await service.read_output(
        db, blob, actor, workspace_id, collection_id, run_id, review_id, kind
    )
    return Response(
        payload,
        media_type=artifact.content_type,
        headers={
            "ETag": '"' + artifact.sha256 + '"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{review_id}/report")
async def report(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> Response:
    return await output(
        workspace_id, collection_id, run_id, review_id, db, actor, blob, "report_json"
    )


@router.get("/{review_id}/markdown")
async def markdown(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> Response:
    return await output(workspace_id, collection_id, run_id, review_id, db, actor, blob, "markdown")


@router.get("/{review_id}/raw")
async def raw(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    review_id: str,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> Response:
    return await output(
        workspace_id, collection_id, run_id, review_id, db, actor, blob, "raw_response"
    )
