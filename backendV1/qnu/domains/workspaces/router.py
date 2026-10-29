"""HTTP routers for workspace administration and membership."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.domains.workspaces.models import Workspace, WorkspaceEvent, WorkspaceMember
from qnu.domains.workspaces.navigation import resolve_navigation
from qnu.domains.workspaces.schemas import (
    EventResponse,
    MemberCreateRequest,
    MemberResponse,
    MemberUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from qnu.domains.workspaces.service import workspace_service

router = APIRouter(prefix="/workspaces", tags=["Workspaces (Đơn vị)"])

ADMIN_ONLY = ("admin",)


def _workspace_out(workspace: Workspace, member_count: int = 0) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        code=workspace.code,
        name=workspace.name,
        description=workspace.description,
        status=workspace.status,
        member_count=member_count,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def _member_out(member: WorkspaceMember) -> MemberResponse:
    return MemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        actor_ref=member.actor_ref,
        display_name=member.display_name,
        role=member.role,
        status=member.status,
        invited_by=member.invited_by,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


def _event_out(event: WorkspaceEvent) -> EventResponse:
    return EventResponse(
        id=event.id,
        workspace_id=event.workspace_id,
        actor_ref=event.actor_ref,
        action=event.action,
        target_type=event.target_type,
        target_id=event.target_id,
        detail=event.detail or {},
        created_at=event.created_at,
    )


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo workspace (quản trị nền tảng)",
)
async def create_workspace(
    body: WorkspaceCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.workspaces.manage")),
) -> WorkspaceResponse:
    workspace = await workspace_service.create_workspace(db, body, actor)
    return _workspace_out(workspace, member_count=0)


@router.get("", response_model=Page[WorkspaceResponse], summary="Workspace người gọi được xem")
async def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[WorkspaceResponse]:
    items, total, counts = await workspace_service.list_workspaces(db, actor, page, page_size)
    return Page[WorkspaceResponse](
        items=[_workspace_out(item, counts.get(item.id, 0)) for item in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/resolve-route", summary="Tra cứu liên kết workspace có kiểm tra quyền")
async def resolve_workspace_route(
    code: str = Query(..., min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$"),
    source_id: str | None = Query(None, min_length=1, max_length=64),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> dict[str, str | None]:
    return await resolve_navigation(db, actor, code, source_id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse, summary="Chi tiết workspace")
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> WorkspaceResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, allow_suspended=True)
    counts = await workspace_service.member_counts(db, [workspace.id])
    return _workspace_out(workspace, counts.get(workspace.id, 0))


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Cập nhật hoặc tạm dừng workspace (quản trị nền tảng)",
)
async def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.workspaces.manage")),
) -> WorkspaceResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, allow_suspended=True)
    updated = await workspace_service.update_workspace(db, workspace, body, actor)
    counts = await workspace_service.member_counts(db, [updated.id])
    return _workspace_out(updated, counts.get(updated.id, 0))


@router.get(
    "/{workspace_id}/members",
    response_model=Page[MemberResponse],
    summary="Thành viên workspace",
)
async def list_members(
    workspace_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[MemberResponse]:
    workspace = await resolve_workspace_access(db, actor, workspace_id)
    items, total = await workspace_service.list_members(db, workspace.id, page, page_size)
    return Page[MemberResponse](
        items=[_member_out(item) for item in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.post(
    "/{workspace_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm hoặc khôi phục thành viên (quản trị workspace)",
)
async def add_member(
    workspace_id: str,
    body: MemberCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> MemberResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=ADMIN_ONLY)
    member = await workspace_service.add_member(db, workspace.id, body, actor)
    return _member_out(member)


@router.patch(
    "/{workspace_id}/members/{member_id}",
    response_model=MemberResponse,
    summary="Đổi vai trò hoặc trạng thái thành viên",
)
async def update_member(
    workspace_id: str,
    member_id: str,
    body: MemberUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> MemberResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=ADMIN_ONLY)
    member = await workspace_service.update_member(db, workspace.id, member_id, body, actor)
    return _member_out(member)


@router.delete(
    "/{workspace_id}/members/{member_id}",
    response_model=MemberResponse,
    summary="Thu hồi thành viên (giữ lịch sử)",
)
async def revoke_member(
    workspace_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> MemberResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=ADMIN_ONLY)
    member = await workspace_service.revoke_member(db, workspace.id, member_id, actor)
    return _member_out(member)


@router.get(
    "/{workspace_id}/events",
    response_model=Page[EventResponse],
    summary="Audit của workspace",
)
async def list_events(
    workspace_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[EventResponse]:
    workspace = await resolve_workspace_access(db, actor, workspace_id, required_roles=ADMIN_ONLY)
    items, total = await workspace_service.list_events(db, workspace.id, page, page_size)
    return Page[EventResponse](
        items=[_event_out(item) for item in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )
