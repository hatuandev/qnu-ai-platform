from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.answer_review import service
from qnu.domains.answer_review.schemas import (
    AnswerReviewCreate,
    AnswerReviewLabelUpdate,
    AnswerReviewResponse,
)
from qnu.domains.identity.actor import AuthActor
from qnu.ports.blob_store import BlobStore


def no_store(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/workspaces/{workspace_id}/assistants/{assistant_id}/answer-reviews",
    tags=["Assistant answer reviews"],
    dependencies=[Depends(no_store)],
)
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


@router.post("", response_model=AnswerReviewResponse, status_code=201)
async def create(
    workspace_id: str,
    assistant_id: str,
    body: AnswerReviewCreate,
    idempotency_key: Key,
    response: Response,
    request: Request,
    db: DB,
    actor: Actor,
    blob: Blob,
):
    c = request.app.state.container
    review, created = await service.create_review(
        db,
        blob,
        c.embedding_model,
        c.vector_store,
        c.chat_model,
        actor,
        workspace_id,
        assistant_id,
        body,
        idempotency_key,
        reranker=c.reranker,
    )
    if not created:
        response.status_code = 200
    return review


@router.get("", response_model=list[AnswerReviewResponse])
async def listing(
    workspace_id: str,
    assistant_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await service.list_reviews(db, actor, workspace_id, assistant_id, limit, offset)


@router.get("/{review_id}", response_model=AnswerReviewResponse)
async def detail(
    workspace_id: str, assistant_id: str, review_id: str, db: DB, actor: Actor
):
    return await service.read_review(db, actor, workspace_id, assistant_id, review_id)


@router.put("/{review_id}/items/{item_id}", response_model=AnswerReviewResponse)
async def label(
    workspace_id: str,
    assistant_id: str,
    review_id: str,
    item_id: str,
    body: AnswerReviewLabelUpdate,
    db: DB,
    actor: Actor,
):
    return await service.label_item(
        db, actor, workspace_id, assistant_id, review_id, item_id, body
    )
