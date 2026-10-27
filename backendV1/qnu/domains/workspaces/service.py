"""Workspace service: CRUD, membership lifecycle and audit."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.workspaces.access import (
    actor_ref,
    is_platform_admin,
    require_platform_admin,
    resolve_workspace_access,
)
from qnu.domains.workspaces.models import Workspace, WorkspaceEvent, WorkspaceMember
from qnu.domains.workspaces.schemas import (
    MemberCreateRequest,
    MemberUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
)
from qnu.platform.errors import Conflict, EntityNotFound


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class WorkspaceService:
    """One method per use case; callers authorize, this service enforces data rules."""

    # ---------------------------------------------------------------- workspace
    async def create_workspace(
        self, db: AsyncSession, req: WorkspaceCreateRequest, actor: AuthActor
    ) -> Workspace:
        require_platform_admin(actor)
        code = req.code.strip().lower()
        existing = (
            (await db.execute(select(Workspace.id).where(Workspace.code == code))).scalars().first()
        )
        if existing is not None:
            raise Conflict(f"Mã workspace '{code}' đã tồn tại.", code="workspace_code_exists")
        workspace = Workspace(
            id=_new_id("ws"),
            code=code,
            name=req.name,
            description=req.description,
            status="active",
            created_by=actor_ref(actor) or None,
        )
        db.add(workspace)
        await self._record_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="workspace.created",
            detail={"code": code, "name": req.name},
        )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise Conflict("Mã workspace đã tồn tại.", code="workspace_code_exists") from exc
        await db.refresh(workspace)
        return workspace

    async def update_workspace(
        self, db: AsyncSession, workspace: Workspace, req: WorkspaceUpdateRequest, actor: AuthActor
    ) -> Workspace:
        require_platform_admin(actor)
        workspace = await resolve_workspace_access(
            db,
            actor,
            workspace.id,
            for_update=True,
            allow_suspended=True,
        )
        changes: dict[str, Any] = {}
        if req.name is not None and req.name != workspace.name:
            workspace.name = req.name
            changes["name"] = req.name
        if req.description is not None and req.description != workspace.description:
            workspace.description = req.description
            changes["description"] = req.description
        if req.status is not None and req.status != workspace.status:
            workspace.status = req.status
            changes["status"] = req.status

        if changes:
            action = "workspace.updated"
            if "status" in changes:
                action = (
                    "workspace.suspended"
                    if changes["status"] == "suspended"
                    else "workspace.reactivated"
                )
            await self._record_event(
                db, workspace_id=workspace.id, actor=actor, action=action, detail=changes
            )
        await db.commit()
        await db.refresh(workspace)
        return workspace

    async def list_workspaces(
        self, db: AsyncSession, actor: AuthActor, page: int, page_size: int
    ) -> tuple[list[Workspace], int, dict[str, int]]:
        actor_ref(actor)
        condition = None
        if not is_platform_admin(actor):
            membership = select(WorkspaceMember.workspace_id).where(
                WorkspaceMember.actor_ref == actor_ref(actor),
                WorkspaceMember.status == "active",
            )
            condition = and_(Workspace.id.in_(membership), Workspace.status == "active")

        count_stmt = select(func.count(Workspace.id))
        page_stmt = select(Workspace).order_by(Workspace.created_at.asc())
        if condition is not None:
            count_stmt = count_stmt.where(condition)
            page_stmt = page_stmt.where(condition)

        total = int((await db.execute(count_stmt)).scalar_one())
        page_stmt = page_stmt.limit(page_size).offset((page - 1) * page_size)
        items = list((await db.execute(page_stmt)).scalars().all())
        for item in items:
            await resolve_workspace_access(db, actor, item.id, allow_suspended=True)
        counts = await self.member_counts(db, [item.id for item in items])
        return items, total, counts

    async def member_counts(self, db: AsyncSession, workspace_ids: list[str]) -> dict[str, int]:
        if not workspace_ids:
            return {}
        stmt = (
            select(WorkspaceMember.workspace_id, func.count(WorkspaceMember.id))
            .where(WorkspaceMember.workspace_id.in_(workspace_ids))
            .group_by(WorkspaceMember.workspace_id)
        )
        return {row[0]: int(row[1]) for row in (await db.execute(stmt)).all()}

    # --------------------------------------------------------------- membership
    async def list_members(
        self, db: AsyncSession, workspace_id: str, page: int, page_size: int
    ) -> tuple[list[WorkspaceMember], int]:
        total = int(
            (
                await db.execute(
                    select(func.count(WorkspaceMember.id)).where(
                        WorkspaceMember.workspace_id == workspace_id
                    )
                )
            ).scalar_one()
        )
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list((await db.execute(stmt)).scalars().all()), total

    async def add_member(
        self, db: AsyncSession, workspace_id: str, req: MemberCreateRequest, actor: AuthActor
    ) -> WorkspaceMember:
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), for_update=True
        )
        ref = req.actor_ref.strip()
        existing = (
            (
                await db.execute(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.actor_ref == ref,
                    )
                )
            )
            .scalars()
            .first()
        )

        if existing is not None and existing.status == "active":
            raise Conflict(f"'{ref}' đã là thành viên đang hoạt động.", code="membership_exists")

        if existing is not None:
            existing.status = "active"
            existing.role = req.role
            if req.display_name:
                existing.display_name = req.display_name
            existing.invited_by = actor_ref(actor) or None
            member = existing
            action = "member.restored"
        else:
            member = WorkspaceMember(
                id=_new_id("wm"),
                workspace_id=workspace_id,
                actor_ref=ref,
                display_name=req.display_name,
                role=req.role,
                status="active",
                invited_by=actor_ref(actor) or None,
            )
            db.add(member)
            action = "member.added"

        await self._record_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action=action,
            target_type="workspace_member",
            target_id=member.id,
            detail={"actor_ref": ref, "role": req.role},
        )
        await db.commit()
        await db.refresh(member)
        return member

    async def update_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        member_id: str,
        req: MemberUpdateRequest,
        actor: AuthActor,
    ) -> WorkspaceMember:
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), for_update=True
        )
        member = await self._get_member(db, workspace_id, member_id)
        changes: dict[str, Any] = {}
        action = "member.updated"

        if req.role is not None and req.role != member.role:
            if (
                member.role == "admin"
                and member.status == "active"
                and req.role != "admin"
                and not is_platform_admin(actor)
            ):
                await self._guard_last_admin(db, workspace_id, member)
            member.role = req.role
            changes["role"] = req.role
            action = "member.role_changed"

        if req.status is not None and req.status != member.status:
            if (
                member.role == "admin"
                and member.status == "active"
                and req.status != "active"
                and not is_platform_admin(actor)
            ):
                await self._guard_last_admin(db, workspace_id, member)
            member.status = req.status
            changes["status"] = req.status
            action = "member.revoked" if req.status == "revoked" else "member.status_changed"

        if changes:
            await self._record_event(
                db,
                workspace_id=workspace_id,
                actor=actor,
                action=action,
                target_type="workspace_member",
                target_id=member.id,
                detail=changes,
            )
        await db.commit()
        await db.refresh(member)
        return member

    async def revoke_member(
        self, db: AsyncSession, workspace_id: str, member_id: str, actor: AuthActor
    ) -> WorkspaceMember:
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), for_update=True
        )
        member = await self._get_member(db, workspace_id, member_id)
        if member.status == "revoked":
            return member
        if member.role == "admin" and not is_platform_admin(actor):
            await self._guard_last_admin(db, workspace_id, member)
        member.status = "revoked"
        await self._record_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="member.revoked",
            target_type="workspace_member",
            target_id=member.id,
            detail={"actor_ref": member.actor_ref},
        )
        await db.commit()
        await db.refresh(member)
        return member

    async def _get_member(
        self, db: AsyncSession, workspace_id: str, member_id: str
    ) -> WorkspaceMember:
        member = await db.get(WorkspaceMember, member_id)
        if member is None or member.workspace_id != workspace_id:
            raise EntityNotFound(
                "Không tìm thấy thành viên trong workspace.", code="membership_not_found"
            )
        return member

    async def _guard_last_admin(
        self, db: AsyncSession, workspace_id: str, member: WorkspaceMember
    ) -> None:
        active_admins = int(
            (
                await db.execute(
                    select(func.count(WorkspaceMember.id)).where(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.role == "admin",
                        WorkspaceMember.status == "active",
                        WorkspaceMember.id != member.id,
                    )
                )
            ).scalar_one()
        )
        if active_admins == 0:
            raise Conflict(
                "Không thể huỷ quyền admin cuối cùng của workspace.",
                code="last_admin_required",
            )

    # -------------------------------------------------------------------- audit
    async def list_events(
        self, db: AsyncSession, workspace_id: str, page: int, page_size: int
    ) -> tuple[list[WorkspaceEvent], int]:
        total = int(
            (
                await db.execute(
                    select(func.count(WorkspaceEvent.id)).where(
                        WorkspaceEvent.workspace_id == workspace_id
                    )
                )
            ).scalar_one()
        )
        stmt = (
            select(WorkspaceEvent)
            .where(WorkspaceEvent.workspace_id == workspace_id)
            .order_by(WorkspaceEvent.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return list((await db.execute(stmt)).scalars().all()), total

    async def _record_event(
        self,
        db: AsyncSession,
        *,
        workspace_id: str,
        actor: AuthActor,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        db.add(
            WorkspaceEvent(
                id=_new_id("we"),
                workspace_id=workspace_id,
                actor_ref=actor_ref(actor) or None,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail or {},
            )
        )


workspace_service = WorkspaceService()
