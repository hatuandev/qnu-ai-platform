"""Thin APIs for durable index generations and source-bearing dense search."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index import search as retrieval
from qnu.domains.knowledge.index.models import IndexRun
from qnu.domains.knowledge.index.readiness import document_readiness
from qnu.domains.knowledge.index.schemas import (
    IndexCreated,
    IndexReadiness,
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
)
from qnu.domains.knowledge.index.service import get_run, request_index
from qnu.domains.knowledge.publication.access import authorize
from qnu.ports.blob_store import BlobStore
from qnu.ports.job_queue import JobQueue

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}",
    tags=["Knowledge · Index and search"],
)
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]


@router.post("/indexing-runs", response_model=IndexCreated, status_code=201)
async def create_index(
    workspace_id: str,
    collection_id: str,
    body: IndexRequest,
    response: Response,
    request: Request,
    idempotency_key: Key,
    db: DB,
    actor: Actor,
    blob: Blob,
    queue: JobQueue | None = Depends(get_job_queue),
) -> IndexCreated:
    outcome = await request_index(
        db,
        blob,
        request.app.state.container.vector_store,
        actor,
        workspace_id,
        collection_id,
        body,
        idempotency_key,
        queue,
    )
    if not outcome.created:
        response.status_code = 200
    return IndexCreated(
        run=IndexResponse.model_validate(outcome.run),
        created=outcome.created,
        dispatched=outcome.dispatched,
    )


@router.get("/indexing-runs", response_model=list[IndexResponse])
async def list_indexes(
    workspace_id: str,
    collection_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[IndexRun]:
    await authorize(db, actor, workspace_id, collection_id)
    return list(
        (
            await db.scalars(
                select(IndexRun)
                .where(
                    IndexRun.workspace_id == workspace_id, IndexRun.collection_id == collection_id
                )
                .order_by(IndexRun.generation.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )


@router.get("/compiled-documents/{document_id}/index-readiness", response_model=IndexReadiness)
async def index_readiness(
    workspace_id: str,
    collection_id: str,
    document_id: str,
    response: Response,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> IndexReadiness:
    response.headers["Cache-Control"] = "private, no-store"
    return await document_readiness(db, blob, actor, workspace_id, collection_id, document_id)


@router.get("/indexing-runs/{run_id}", response_model=IndexResponse)
async def index_status(
    workspace_id: str, collection_id: str, run_id: str, db: DB, actor: Actor
) -> IndexRun:
    return await get_run(db, actor, workspace_id, collection_id, run_id)


@router.get("/indexing-runs/{run_id}/manifest")
async def index_manifest(
    workspace_id: str,
    collection_id: str,
    run_id: str,
    response: Response,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> dict:
    run = await get_run(db, actor, workspace_id, collection_id, run_id)
    value = await retrieval.manifest(db, blob, run)
    response.headers.update(
        {"ETag": f'"{run.manifest_sha256}"', "Cache-Control": "private, no-store"}
    )
    return value


@router.post("/search", response_model=SearchResponse)
async def search(
    workspace_id: str,
    collection_id: str,
    body: SearchRequest,
    request: Request,
    response: Response,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> SearchResponse:
    container = request.app.state.container
    response.headers["Cache-Control"] = "private, no-store"
    return await retrieval.search(
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
