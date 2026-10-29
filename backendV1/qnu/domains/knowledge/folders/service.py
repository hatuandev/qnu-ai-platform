"""Directory / folder business rules and use cases.

Folders belong to exactly one collection and workspace.
Hierarchy is strictly bounded within the same collection.
Loop / cycle detection and sibling collision are prevented in every write operation.
"""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.folders.schemas import (
    FolderBreadcrumbItem,
    FolderCreateRequest,
    FolderDetailResponse,
    FolderImpactResponse,
    FolderResponse,
    FolderUpdateRequest,
)
from qnu.domains.knowledge.ids import new_id
from qnu.domains.knowledge.models import KBFolder, KBSource
from qnu.domains.knowledge.policies.access import load_collection
from qnu.domains.lifecycle.guards import visible
from qnu.domains.lifecycle.models import ResourceState
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.models import Workspace
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound

INVALID_NAME_CHARS = re.compile(r"[/\\:\*\?\"<>\|]")


def _validate_folder_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise AppException(
            "Tên thư mục không được để trống.", code="invalid_folder_name", status_code=422
        )
    if len(cleaned) > 255:
        raise AppException(
            "Tên thư mục không được vượt quá 255 ký tự.",
            code="folder_name_too_long",
            status_code=422,
        )
    if cleaned in {".", ".."}:
        raise AppException(
            "Tên thư mục không hợp lệ.", code="invalid_folder_name", status_code=422
        )
    if INVALID_NAME_CHARS.search(cleaned):
        raise AppException(
            "Tên thư mục không được chứa ký tự đặc biệt (/, \\, :, *, ?, \", <, >, |).",
            code="invalid_folder_characters",
            status_code=422,
        )
    return cleaned


class FolderService:
    async def create(
        self,
        db: AsyncSession,
        workspace: Workspace,
        collection_id: str,
        req: FolderCreateRequest,
        actor: AuthActor,
    ) -> FolderResponse:
        clean_name = _validate_folder_name(req.name)
        collection = await load_collection(db, workspace.id, collection_id)

        # Check parent folder if specified
        parent_id = req.parent_id
        if parent_id is not None:
            parent = await self._load_folder(db, workspace.id, collection.id, parent_id)
            if parent is None:
                raise EntityNotFound(
                    "Không tìm thấy thư mục cha.", code="parent_folder_not_found"
                )

        # Check sibling uniqueness
        await self._check_sibling_name(
            db, workspace.id, collection.id, parent_id, clean_name, exclude_id=None
        )

        folder = KBFolder(
            id=new_id("fld"),
            workspace_id=workspace.id,
            collection_id=collection.id,
            parent_id=parent_id,
            name=clean_name,
            created_by=actor_ref(actor),
        )
        db.add(folder)
        await record_workspace_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="folder.created",
            detail={"folder_id": folder.id, "name": folder.name, "parent_id": folder.parent_id},
        )
        await db.commit()
        await db.refresh(folder)
        return self._to_response(folder, source_count=0, subfolder_count=0)

    async def list_folders(
        self, db: AsyncSession, workspace: Workspace, collection_id: str
    ) -> list[FolderResponse]:
        collection = await load_collection(db, workspace.id, collection_id)
        stmt = (
            select(KBFolder)
            .where(
                KBFolder.workspace_id == workspace.id,
                KBFolder.collection_id == collection.id,
                visible("folder", KBFolder.id),
            )
            .order_by(KBFolder.name.asc())
        )
        folders = (await db.scalars(stmt)).all()
        if not folders:
            return []

        folder_ids = [f.id for f in folders]

        # Count sources in each folder
        source_counts_stmt = (
            select(KBSource.folder_id, func.count(KBSource.id))
            .where(
                KBSource.folder_id.in_(folder_ids),
                visible("source", KBSource.id),
            )
            .group_by(KBSource.folder_id)
        )
        source_counts = dict((await db.execute(source_counts_stmt)).all())

        # Count direct subfolders in each folder
        subfolder_counts_stmt = (
            select(KBFolder.parent_id, func.count(KBFolder.id))
            .where(
                KBFolder.parent_id.in_(folder_ids),
                visible("folder", KBFolder.id),
            )
            .group_by(KBFolder.parent_id)
        )
        subfolder_counts = dict((await db.execute(subfolder_counts_stmt)).all())

        return [
            self._to_response(
                f,
                source_count=source_counts.get(f.id, 0),
                subfolder_count=subfolder_counts.get(f.id, 0),
            )
            for f in folders
        ]

    async def get_folder(
        self, db: AsyncSession, workspace: Workspace, collection_id: str, folder_id: str
    ) -> FolderDetailResponse:
        folder = await self._load_folder(db, workspace.id, collection_id, folder_id)
        if folder is None:
            raise EntityNotFound("Không tìm thấy thư mục.", code="folder_not_found")

        # Compute counts
        source_count = (
            await db.scalar(
                select(func.count(KBSource.id)).where(
                    KBSource.folder_id == folder.id, visible("source", KBSource.id)
                )
            )
            or 0
        )
        subfolder_count = (
            await db.scalar(
                select(func.count(KBFolder.id)).where(
                    KBFolder.parent_id == folder.id, visible("folder", KBFolder.id)
                )
            )
            or 0
        )

        # Build breadcrumbs upwards
        breadcrumbs: list[FolderBreadcrumbItem] = []
        current: KBFolder | None = folder
        while current is not None:
            breadcrumbs.insert(0, FolderBreadcrumbItem(id=current.id, name=current.name))
            if current.parent_id is None:
                break
            current = await self._load_folder(
                db, workspace.id, collection_id, current.parent_id
            )

        resp = self._to_response(folder, source_count=source_count, subfolder_count=subfolder_count)
        return FolderDetailResponse(
            **resp.model_dump(),
            breadcrumbs=breadcrumbs,
        )

    async def update(
        self,
        db: AsyncSession,
        workspace: Workspace,
        collection_id: str,
        folder_id: str,
        req: FolderUpdateRequest,
        actor: AuthActor,
    ) -> FolderResponse:
        folder = await self._load_folder(
            db, workspace.id, collection_id, folder_id, for_update=True
        )
        if folder is None:
            raise EntityNotFound("Không tìm thấy thư mục.", code="folder_not_found")

        clean_name = _validate_folder_name(req.name)
        if clean_name != folder.name:
            await self._check_sibling_name(
                db,
                workspace.id,
                collection_id,
                folder.parent_id,
                clean_name,
                exclude_id=folder.id,
            )
            folder.name = clean_name
            await record_workspace_event(
                db,
                workspace_id=workspace.id,
                actor=actor,
                action="folder.renamed",
                detail={"folder_id": folder.id, "name": folder.name},
            )
            await db.commit()
            await db.refresh(folder)

        return self._to_response(folder, source_count=0, subfolder_count=0)

    async def move(
        self,
        db: AsyncSession,
        workspace: Workspace,
        collection_id: str,
        folder_id: str,
        target_parent_id: str | None,
        actor: AuthActor,
    ) -> FolderResponse:
        folder = await self._load_folder(
            db, workspace.id, collection_id, folder_id, for_update=True
        )
        if folder is None:
            raise EntityNotFound("Không tìm thấy thư mục.", code="folder_not_found")

        if target_parent_id == folder.id:
            raise Conflict(
                "Không thể di chuyển thư mục vào chính nó.", code="folder_move_to_self"
            )

        if target_parent_id is not None:
            target_parent = await self._load_folder(
                db, workspace.id, collection_id, target_parent_id
            )
            if target_parent is None:
                raise EntityNotFound(
                    "Không tìm thấy thư mục đích.", code="target_folder_not_found"
                )

            # Prevent cycles: verify folder is not an ancestor of target_parent
            curr: KBFolder | None = target_parent
            while curr is not None:
                if curr.id == folder.id:
                    raise Conflict(
                        "Không thể di chuyển thư mục vào thư mục con của chính nó.",
                        code="folder_cycle_detected",
                    )
                if curr.parent_id is None:
                    break
                curr = await self._load_folder(db, workspace.id, collection_id, curr.parent_id)

        # Check sibling uniqueness in new parent
        await self._check_sibling_name(
            db,
            workspace.id,
            collection_id,
            target_parent_id,
            folder.name,
            exclude_id=folder.id,
        )

        folder.parent_id = target_parent_id
        await record_workspace_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="folder.moved",
            detail={"folder_id": folder.id, "new_parent_id": target_parent_id},
        )
        await db.commit()
        await db.refresh(folder)
        return self._to_response(folder, source_count=0, subfolder_count=0)

    async def get_impact(
        self, db: AsyncSession, workspace: Workspace, collection_id: str, folder_id: str
    ) -> FolderImpactResponse:
        folder = await self._load_folder(db, workspace.id, collection_id, folder_id)
        if folder is None:
            raise EntityNotFound("Không tìm thấy thư mục.", code="folder_not_found")

        descendants = await self._collect_descendant_ids(db, workspace.id, collection_id, folder.id)
        all_folder_ids = [folder.id, *descendants]

        source_count = (
            await db.scalar(
                select(func.count(KBSource.id)).where(
                    KBSource.folder_id.in_(all_folder_ids),
                    visible("source", KBSource.id),
                )
            )
            or 0
        )

        return FolderImpactResponse(
            folder_id=folder.id,
            folder_name=folder.name,
            subfolder_count=len(descendants),
            source_count=source_count,
            descendant_folder_ids=descendants,
        )

    async def delete(
        self, db: AsyncSession, workspace: Workspace, collection_id: str, folder_id: str, actor: AuthActor
    ) -> FolderImpactResponse:
        folder = await self._load_folder(
            db, workspace.id, collection_id, folder_id, for_update=True
        )
        if folder is None:
            raise EntityNotFound("Không tìm thấy thư mục.", code="folder_not_found")

        impact = await self.get_impact(db, workspace, collection_id, folder_id)
        if impact.source_count or impact.subfolder_count:
            raise AppException(
                "Thư mục còn tài liệu hoặc thư mục con. Hãy di chuyển nội dung ra ngoài trước khi xóa.",
                code="folder_not_empty",
                status_code=409,
            )
        all_folder_ids = [folder.id]

        # Soft delete in ResourceState
        for f_id in all_folder_ids:
            key = (workspace.id, "folder", f_id)
            state = await db.get(ResourceState, key)
            if state is None:
                db.add(ResourceState(workspace_id=workspace.id, kind="folder", resource_id=f_id, status="deleted"))
            else:
                state.status = "deleted"

        await record_workspace_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="folder.deleted",
            detail={"folder_id": folder.id, "subfolders": impact.subfolder_count, "sources": impact.source_count},
        )
        await db.commit()
        return impact

    async def restore(
        self, db: AsyncSession, workspace: Workspace, collection_id: str, folder_id: str, actor: AuthActor
    ) -> FolderResponse:
        folder = await db.scalar(
            select(KBFolder).where(
                KBFolder.id == folder_id,
                KBFolder.workspace_id == workspace.id,
                KBFolder.collection_id == collection_id,
            )
        )
        if folder is None:
            raise EntityNotFound("Không tìm thấy thư mục.", code="folder_not_found")

        key = (workspace.id, "folder", folder.id)
        state = await db.get(ResourceState, key)
        if state is not None:
            state.status = "active"

        await record_workspace_event(
            db,
            workspace_id=workspace.id,
            actor=actor,
            action="folder.restored",
            detail={"folder_id": folder.id},
        )
        await db.commit()
        await db.refresh(folder)
        return self._to_response(folder, source_count=0, subfolder_count=0)

    async def _load_folder(
        self, db: AsyncSession, workspace_id: str, collection_id: str, folder_id: str, for_update: bool = False
    ) -> KBFolder | None:
        stmt = select(KBFolder).where(
            KBFolder.id == folder_id,
            KBFolder.workspace_id == workspace_id,
            KBFolder.collection_id == collection_id,
            visible("folder", KBFolder.id),
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await db.scalar(stmt)

    async def _collect_descendant_ids(
        self, db: AsyncSession, workspace_id: str, collection_id: str, parent_id: str
    ) -> list[str]:
        descendants: list[str] = []
        queue = [parent_id]
        while queue:
            current_id = queue.pop(0)
            children = (
                await db.scalars(
                    select(KBFolder.id).where(
                        KBFolder.parent_id == current_id,
                        KBFolder.workspace_id == workspace_id,
                        KBFolder.collection_id == collection_id,
                        visible("folder", KBFolder.id),
                    )
                )
            ).all()
            for child_id in children:
                descendants.append(child_id)
                queue.append(child_id)
        return descendants

    async def _check_sibling_name(
        self,
        db: AsyncSession,
        workspace_id: str,
        collection_id: str,
        parent_id: str | None,
        name: str,
        exclude_id: str | None = None,
    ) -> None:
        conditions = [
            KBFolder.workspace_id == workspace_id,
            KBFolder.collection_id == collection_id,
            func.lower(KBFolder.name) == name.lower(),
            visible("folder", KBFolder.id),
        ]
        if parent_id is None:
            conditions.append(KBFolder.parent_id.is_(None))
        else:
            conditions.append(KBFolder.parent_id == parent_id)
        if exclude_id is not None:
            conditions.append(KBFolder.id != exclude_id)

        exists_count = await db.scalar(select(func.count(KBFolder.id)).where(*conditions))
        if exists_count and exists_count > 0:
            raise Conflict(
                f"Thư mục '{name}' đã tồn tại trong cùng vị trí.",
                code="folder_name_exists",
            )

    def _to_response(
        self, folder: KBFolder, source_count: int = 0, subfolder_count: int = 0
    ) -> FolderResponse:
        return FolderResponse(
            id=folder.id,
            workspace_id=folder.workspace_id,
            collection_id=folder.collection_id,
            parent_id=folder.parent_id,
            name=folder.name,
            source_count=source_count,
            subfolder_count=subfolder_count,
            created_by=folder.created_by,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )


folder_service = FolderService()
