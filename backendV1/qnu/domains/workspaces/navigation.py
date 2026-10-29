"""Resolve public workspace links without exposing another unit's resources."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.models import KBSource
from qnu.domains.knowledge.policies.access import load_collection, load_source
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.domains.workspaces.models import Workspace
from qnu.platform.errors import EntityNotFound


async def resolve_navigation(
    db: AsyncSession, actor: AuthActor, code: str, source_id: str | None = None
) -> dict[str, str | None]:
    workspace = (
        await db.execute(select(Workspace).where(Workspace.code == code))
    ).scalar_one_or_none()
    if workspace is None:
        raise EntityNotFound("Không tìm thấy workspace.", code="workspace_not_found")
    workspace = await resolve_workspace_access(db, actor, workspace.id)
    collection_id = None
    if source_id is not None:
        source = (
            await db.execute(
                select(KBSource).where(
                    KBSource.id == source_id, KBSource.workspace_id == workspace.id
                )
            )
        ).scalar_one_or_none()
        if source is None:
            raise EntityNotFound("Không tìm thấy tài liệu.", code="source_not_found")
        await load_collection(db, workspace.id, source.collection_id)
        await load_source(db, workspace.id, source.collection_id, source.id)
        collection_id = source.collection_id
    return {"workspace_id": workspace.id, "code": workspace.code, "collection_id": collection_id}
