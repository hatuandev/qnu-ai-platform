"""Thin synchronous answer endpoint, scoped to an authorized collection."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.rag.answer.schemas import AnswerRequest, AnswerResponse
from qnu.domains.rag.answer.service import answer
from qnu.ports.blob_store import BlobStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}", tags=["RAG · Answers"]
)


@router.post("/answers", response_model=AnswerResponse)
async def create_answer(
    workspace_id: str,
    collection_id: str,
    body: AnswerRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[AuthActor, Depends(get_actor)],
    blob: Annotated[BlobStore, Depends(get_blob_store)],
) -> AnswerResponse:
    container = request.app.state.container
    response.headers["Cache-Control"] = "private, no-store"
    return await answer(
        db,
        blob,
        container.embedding_model,
        container.vector_store,
        container.chat_model,
        actor,
        workspace_id,
        collection_id,
        body,
        reranker=container.reranker,
    )
