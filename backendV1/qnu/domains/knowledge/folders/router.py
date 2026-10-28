"""HTTP API for knowledge collection directory folders."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.folders.schemas import (
    FolderCreateRequest,
    FolderDetailResponse,
    FolderImpactResponse,
    FolderMoveRequest,
    FolderResponse,
    FolderUpdateRequest,
)
from qnu.domains.knowledge.folders.service import folder_service
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES
from qnu.domains.workspaces.access import resolve_workspace_access

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}/folders",
    tags=["Knowledge · Folders"],
)


@router.get(
    "",
    response_model=list[FolderResponse],
    summary="Danh sách thư mục trong kho tri thức",
)
async def list_folders(
    workspace_id: str,
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> list[FolderResponse]:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    return await folder_service.list_folders(db, workspace, collection_id)


@router.post(
    "",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo thư mục mới trong kho tri thức",
)
async def create_folder(
    workspace_id: str,
    collection_id: str,
    req: FolderCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    return await folder_service.create(db, workspace, collection_id, req, actor)


@router.get(
    "/{folder_id}",
    response_model=FolderDetailResponse,
    summary="Chi tiết thư mục và đường dẫn breadcrumb",
)
async def get_folder(
    workspace_id: str,
    collection_id: str,
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderDetailResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    return await folder_service.get_folder(db, workspace, collection_id, folder_id)


@router.patch(
    "/{folder_id}",
    response_model=FolderResponse,
    summary="Đổi tên thư mục",
)
async def update_folder(
    workspace_id: str,
    collection_id: str,
    folder_id: str,
    req: FolderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    return await folder_service.update(db, workspace, collection_id, folder_id, req, actor)


@router.post(
    "/{folder_id}/move",
    response_model=FolderResponse,
    summary="Di chuyển thư mục",
)
async def move_folder(
    workspace_id: str,
    collection_id: str,
    folder_id: str,
    req: FolderMoveRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    return await folder_service.move(
        db, workspace, collection_id, folder_id, req.target_parent_id, actor
    )


@router.get(
    "/{folder_id}/impact",
    response_model=FolderImpactResponse,
    summary="Xem trước phạm vi ảnh hưởng khi xóa thư mục",
)
async def get_folder_impact(
    workspace_id: str,
    collection_id: str,
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderImpactResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    return await folder_service.get_impact(db, workspace, collection_id, folder_id)


@router.delete(
    "/{folder_id}",
    response_model=FolderImpactResponse,
    summary="Xóa thư mục và đưa vào thùng rác",
)
async def delete_folder(
    workspace_id: str,
    collection_id: str,
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderImpactResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    return await folder_service.delete(db, workspace, collection_id, folder_id, actor)


@router.post(
    "/{folder_id}/restore",
    response_model=FolderResponse,
    summary="Khôi phục thư mục từ thùng rác",
)
async def restore_folder(
    workspace_id: str,
    collection_id: str,
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> FolderResponse:
    workspace = await resolve_workspace_access(
        db, actor, workspace_id, required_roles=WRITE_ROLES, for_update=True
    )
    return await folder_service.restore(db, workspace, collection_id, folder_id, actor)

