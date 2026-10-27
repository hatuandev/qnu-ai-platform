"""Scoped lookups for workspace → collection → source → revision.

Every read goes through one of these helpers so an identifier from the URL can
never address a row outside the workspace already authorized by
``resolve_workspace_access``. A mismatch is a 404, never a 403, so existence of
another unit's identifiers is not disclosed.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.knowledge.models import KBCollection, KBSource, KBSourceRevision
from qnu.domains.lifecycle.guards import require_available
from qnu.platform.errors import EntityNotFound

READ_ROLES = ("admin", "editor", "reviewer", "member")
WRITE_ROLES = ("admin", "editor")


async def load_collection(
    db: AsyncSession, workspace_id: str, collection_id: str, *, for_update: bool = False
) -> KBCollection:
    stmt = select(KBCollection).where(
        KBCollection.id == collection_id, KBCollection.workspace_id == workspace_id
    )
    if for_update:
        stmt = stmt.with_for_update()
    collection = (
        await db.execute(stmt.execution_options(populate_existing=True))
    ).scalar_one_or_none()
    if collection is None:
        raise EntityNotFound("Không tìm thấy kho tri thức.", code="collection_not_found")
    await require_available(db, workspace_id, "collection", collection_id)
    return collection


async def load_source(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    source_id: str,
    *,
    for_update: bool = False,
) -> KBSource:
    await load_collection(db, workspace_id, collection_id)
    stmt = select(KBSource).where(
        KBSource.id == source_id,
        KBSource.collection_id == collection_id,
        KBSource.workspace_id == workspace_id,
    )
    if for_update:
        stmt = stmt.with_for_update()
    source = (await db.execute(stmt.execution_options(populate_existing=True))).scalar_one_or_none()
    if source is None:
        raise EntityNotFound("Không tìm thấy nguồn tài liệu.", code="source_not_found")
    await require_available(db, workspace_id, "source", source_id)
    return source


async def load_revision(
    db: AsyncSession, workspace_id: str, source_id: str, revision_id: str
) -> KBSourceRevision:
    revision = (
        await db.execute(
            select(KBSourceRevision).where(
                KBSourceRevision.id == revision_id,
                KBSourceRevision.source_id == source_id,
                KBSourceRevision.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()
    if revision is None:
        raise EntityNotFound("Không tìm thấy phiên bản tài liệu.", code="revision_not_found")
    return revision
