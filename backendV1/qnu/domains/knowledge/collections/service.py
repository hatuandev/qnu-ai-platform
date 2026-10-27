"""Collection use cases. Authorization happens in the router; data rules live here."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.collections.schemas import (
    CollectionCreateRequest,
    CollectionUpdateRequest,
)
from qnu.domains.knowledge.ids import new_id
from qnu.domains.knowledge.models import KBCollection, KBSource
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.lifecycle.guards import visible
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.models import Workspace
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict

NAME_CONFLICT = "Trong workspace đã có kho tri thức cùng tên."


class CollectionService:
    """One method per use case; callers must already have resolved workspace access."""

    async def create(
        self, db: AsyncSession, workspace: Workspace, req: CollectionCreateRequest, actor: AuthActor
    ) -> KBCollection:
        collection = KBCollection(
            id=new_id("col"),
            workspace_id=workspace.id,
            name=req.name,
            description=req.description,
            created_by=actor_ref(actor),
        )
        db.add(collection)
        await record_workspace_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="collection.created",
            detail={"collection_id": collection.id, "name": collection.name},
        )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise Conflict(NAME_CONFLICT, code="collection_name_exists") from exc
        await db.refresh(collection)
        return collection

    async def list_page(
        self, db: AsyncSession, workspace: Workspace, page: int, page_size: int
    ) -> tuple[list[KBCollection], int, dict[str, int]]:
        condition = (KBCollection.workspace_id == workspace.id) & visible(
            "collection", KBCollection.id
        )
        total = int(
            (await db.execute(select(func.count(KBCollection.id)).where(condition))).scalar_one()
        )
        rows = (
            (
                await db.execute(
                    select(KBCollection)
                    .where(condition)
                    .order_by(KBCollection.created_at.desc(), KBCollection.id.desc())
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
            )
            .scalars()
            .all()
        )
        items = list(rows)
        return items, total, await self.source_counts(db, [item.id for item in items])

    async def get(
        self, db: AsyncSession, workspace: Workspace, collection_id: str
    ) -> tuple[KBCollection, int]:
        collection = await load_collection(db, workspace.id, collection_id)
        counts = await self.source_counts(db, [collection.id])
        return collection, counts.get(collection.id, 0)

    async def update(
        self,
        db: AsyncSession,
        workspace: Workspace,
        collection_id: str,
        req: CollectionUpdateRequest,
        actor: AuthActor,
    ) -> tuple[KBCollection, int]:
        collection = await load_collection(db, workspace.id, collection_id, for_update=True)
        changes: dict[str, str | None] = {}
        provided = req.model_fields_set
        if "name" in provided and req.name is not None and req.name != collection.name:
            collection.name = req.name
            changes["name"] = req.name
        if "description" in provided and req.description != collection.description:
            collection.description = req.description
            changes["description"] = req.description

        if changes:
            await record_workspace_event(
                db,
                workspace_id=workspace.id,
                actor=actor,
                action="collection.updated",
                detail={"collection_id": collection.id, **changes},
            )
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise Conflict(NAME_CONFLICT, code="collection_name_exists") from exc
        await db.refresh(collection)
        counts = await self.source_counts(db, [collection.id])
        return collection, counts.get(collection.id, 0)

    async def source_counts(self, db: AsyncSession, collection_ids: list[str]) -> dict[str, int]:
        if not collection_ids:
            return {}
        stmt = (
            select(KBSource.collection_id, func.count(KBSource.id))
            .where(KBSource.collection_id.in_(collection_ids))
            .where(visible("source", KBSource.id))
            .group_by(KBSource.collection_id)
        )
        return {row[0]: int(row[1]) for row in (await db.execute(stmt)).all()}


collection_service = CollectionService()
