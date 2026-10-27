"""HTTP API for knowledge collections inside one workspace."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.collections.schemas import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
)
from qnu.domains.knowledge.collections.service import collection_service
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES
from qnu.domains.workspaces.access import resolve_workspace_access

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections", tags=["Knowledge · Collections"]
)


def _collection_out(collection: KBCollection, source_count: int = 0) -> CollectionResponse:
    return CollectionResponse(
        id=collection.id,
        workspace_id=collection.workspace_id,
        name=collection.name,
        description=collection.description,
        source_count=source_count,
        created_by=collection.created_by,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo kho tri thức trong workspace (admin/editor)",
)
async def create_collection(
    workspace_id: str,
    body: CollectionCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> CollectionResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=WRITE_ROLES)
    collection = await collection_service.create(db, workspace, body, actor)
    return _collection_out(collection, source_count=0)


@router.get(
    "",
    response_model=Page[CollectionResponse],
    summary="Kho tri thức của workspace (thành viên đang hoạt động)",
)
async def list_collections(
    workspace_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[CollectionResponse]:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    items, total, counts = await collection_service.list_page(db, workspace, page, page_size)
    return Page[CollectionResponse](
        items=[_collection_out(item, counts.get(item.id, 0)) for item in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Chi tiết kho tri thức",
)
async def get_collection(
    workspace_id: str,
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> CollectionResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    collection, source_count = await collection_service.get(db, workspace, collection_id)
    return _collection_out(collection, source_count)


@router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Cập nhật metadata kho tri thức (admin/editor)",
)
async def update_collection(
    workspace_id: str,
    collection_id: str,
    body: CollectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> CollectionResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=WRITE_ROLES)
    collection, source_count = await collection_service.update(
        db, workspace, collection_id, body, actor
    )
    return _collection_out(collection, source_count)
