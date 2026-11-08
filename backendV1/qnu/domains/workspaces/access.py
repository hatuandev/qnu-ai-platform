"""Reusable workspace authorization helpers.

``resolve_workspace_access`` is the single entry point promised in AGENTS.md:
every workspace-scoped resource lookup must go through it, and a workspace id
coming from a path/body/header is only the object to be checked.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.workspaces.models import Workspace, WorkspaceMember
from qnu.platform.errors import AppException, EntityNotFound, Forbidden

PLATFORM_PERMISSION = "ai.workspaces.manage"


def is_platform_admin(actor: AuthActor) -> bool:
    """Platform admins manage every workspace; workspace admins do not."""
    return actor.authenticated and actor.has_permission(PLATFORM_PERMISSION)


def require_platform_admin(actor: AuthActor) -> None:
    if not is_platform_admin(actor):
        raise Forbidden(
            "Chỉ quản trị nền tảng được thực hiện thao tác này.", code="permission_denied"
        )


def actor_ref(actor: AuthActor) -> str:
    """SSO subjects are opaque, case-sensitive identifiers, not display names."""
    ref = actor.actor_id.strip()
    if not actor.authenticated or not ref or ref == "unknown":
        raise AppException("Thiếu định danh đã xác thực.", code="invalid_identity", status_code=401)
    return ref


async def find_active_membership(
    db: AsyncSession, workspace_id: str, ref: str
) -> WorkspaceMember | None:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.actor_ref == ref,
        WorkspaceMember.status == "active",
    )
    return (await db.execute(stmt.execution_options(populate_existing=True))).scalars().first()


async def resolve_workspace_access(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    *,
    required_roles: Iterable[str] | None = None,
    for_update: bool = False,
    allow_suspended: bool = False,
) -> Workspace:
    """Return the workspace when the actor may use it, else fail closed.

    404 is returned for missing workspaces and for non-members (never leak
    existence); 403 is reserved for real members lacking a required role or for
    a suspended workspace they still belong to.
    """
    if not actor.authenticated:
        raise AppException("Chưa xác thực người gọi.", code="unauthorized", status_code=401)

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    workspace = (await db.execute(stmt)).scalar_one_or_none()
    if workspace is None:
        raise EntityNotFound("Không tìm thấy workspace.", code="workspace_not_found")

    if is_platform_admin(actor):
        if workspace.status != "active" and not allow_suspended:
            raise Forbidden("Workspace đang tạm dừng.", code="workspace_suspended")
        return workspace

    membership = await find_active_membership(db, workspace.id, actor_ref(actor))
    if membership is None:
        raise EntityNotFound("Không tìm thấy workspace.", code="workspace_not_found")

    if workspace.status != "active":
        raise AppException(
            "Workspace đang tạm dừng; không thể truy cập nội dung.",
            code="workspace_suspended",
            status_code=403,
            title="Workspace tạm dừng",
        )

    if required_roles is not None and membership.role not in set(required_roles):
        raise Forbidden(
            f"Vai trò '{membership.role}' không đủ quyền cho hành động này.",
            code="workspace_forbidden",
        )
    return workspace


async def caller_workspace_role(db: AsyncSession, actor: AuthActor, workspace_id: str) -> str:
    """Role for read-model capabilities only; call after ``resolve_workspace_access``."""
    if is_platform_admin(actor):
        return "admin"
    membership = await find_active_membership(db, workspace_id, actor_ref(actor))
    if membership is None:
        raise EntityNotFound("Không tìm thấy workspace.", code="workspace_not_found")
    return membership.role


async def list_visible_workspaces(db: AsyncSession, actor: AuthActor) -> list[Workspace]:
    """Workspaces the actor may see: all for platform admins, memberships otherwise."""
    if is_platform_admin(actor):
        stmt = select(Workspace).order_by(Workspace.created_at.asc())
        return list((await db.execute(stmt)).scalars().all())

    stmt = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.actor_ref == actor_ref(actor),
            WorkspaceMember.status == "active",
        )
        .order_by(Workspace.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().unique().all())


def require_workspace_role(*roles: str):
    """Dependency factory for later workspace-scoped domains (collections, assistants)."""
    from qnu.api.dependencies import get_actor, get_db

    async def _dependency(
        workspace_id: str,
        db: AsyncSession = Depends(get_db),
        actor: AuthActor = Depends(get_actor),
    ) -> Workspace:
        return await resolve_workspace_access(db, actor, workspace_id, required_roles=roles)

    return _dependency
