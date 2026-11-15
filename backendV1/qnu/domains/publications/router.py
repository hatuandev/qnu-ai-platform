"""Thin admin router for one assistant's public release."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.publications import service
from qnu.domains.publications.schemas import (
    PublicationResponse,
    PublicationStatsResponse,
    PublicationUpdate,
)
from qnu.ports.blob_store import BlobStore

router = APIRouter(
    prefix="/workspaces/{workspace_id}/assistants/{assistant_id}/publication",
    tags=["Assistant Publications"],
)
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]


@router.get("", response_model=PublicationResponse)
async def detail(
    workspace_id: str, assistant_id: str, db: DB, actor: Actor, blob: Blob
) -> PublicationResponse:
    return await service.publication_view(db, blob, actor, workspace_id, assistant_id)


@router.get("/stats", response_model=PublicationStatsResponse)
async def stats(
    workspace_id: str,
    assistant_id: str,
    db: DB,
    actor: Actor,
    days: Annotated[int, Query(ge=7, le=30)] = 7,
) -> PublicationStatsResponse:
    return await service.publication_stats(db, actor, workspace_id, assistant_id, days)


@router.put("", response_model=PublicationResponse)
async def save(
    workspace_id: str,
    assistant_id: str,
    body: PublicationUpdate,
    db: DB,
    actor: Actor,
    blob: Blob,
) -> PublicationResponse:
    return await service.save_publication(db, blob, actor, workspace_id, assistant_id, body)
