"""Explicit, bounded evaluation calls; JSON response is suitable for storing as an experiment artifact."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.evaluation.schemas import EvaluationRequest
from qnu.domains.evaluation.service import evaluate
from qnu.domains.identity.actor import AuthActor
from qnu.ports.blob_store import BlobStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/retrieval-evaluations",
    tags=["Evaluation"],
)


@router.post("")
async def compare(
    workspace_id: str,
    collection_id: str,
    body: EvaluationRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[AuthActor, Depends(get_actor)],
    blob: Annotated[BlobStore, Depends(get_blob_store)],
) -> dict:
    response.headers["Cache-Control"] = "private, no-store"
    container = request.app.state.container
    return await evaluate(
        db,
        blob,
        container.embedding_model,
        container.vector_store,
        actor,
        workspace_id,
        collection_id,
        body,
        reranker=container.reranker,
    )
