"""Workspace authorization and audit interface for other domains."""

from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.service import workspace_service

__all__ = ["actor_ref", "record_workspace_event", "resolve_workspace_access"]


async def record_workspace_event(
    db: AsyncSession, *, workspace_id: str, actor: AuthActor, action: str, detail: dict
) -> None:
    await workspace_service._record_event(
        db, workspace_id=workspace_id, actor=actor, action=action, detail=detail
    )
