"""Read-only inbox endpoint; completion comes from the underlying resource."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.inbox import service
from qnu.domains.knowledge.inbox.schemas import InboxPage

router = APIRouter(prefix="/workspaces/{workspace_id}/inbox", tags=["Knowledge · Inbox"])
KindFilter = Literal[
    "review_pending",
    "changes_requested",
    "awaiting_publish",
    "sync_incomplete",
    "preparation_failed",
]
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]


@router.get("", response_model=InboxPage)
async def read_inbox(
    workspace_id: str,
    db: DB,
    actor: Actor,
    collection_id: str | None = Query(None, min_length=1, max_length=64),
    kind: KindFilter | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> InboxPage:
    return await service.read_inbox(
        db,
        actor,
        workspace_id,
        collection_id=collection_id,
        kind=kind,
        page=page,
        page_size=page_size,
    )
