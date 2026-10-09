"""Helper functions for strict Tenant & Workspace Scoping in Knowledge Publishing V2."""

from __future__ import annotations

import inspect
from typing import Any, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.modules.auth.dependencies import AuthActor
from app.modules.knowledge.models import (
    KnowledgeBinding,
    KnowledgeCollection,
    KnowledgeIndexRevision,
)

T = TypeVar("T")


def apply_actor_scope(
    stmt: Select[Any],
    model: Any,
    actor: AuthActor | None,
) -> Select[Any]:
    """Apply strict tenant_id and optional workspace_id filtering to a query."""
    if not actor:
        return stmt

    tenant_id = getattr(actor, "tenant_id", None)
    if tenant_id and hasattr(model, "tenant_id"):
        stmt = stmt.where(model.tenant_id == tenant_id)

    workspace_id = getattr(actor, "workspace_id", None)
    if workspace_id and hasattr(model, "workspace_id"):
        stmt = stmt.where(model.workspace_id == workspace_id)

    return stmt


async def get_scoped_collection(
    db: AsyncSession,
    collection_id: str,
    actor: AuthActor | None = None,
    for_update: bool = False,
) -> KnowledgeCollection:
    """Retrieve a KnowledgeCollection ensuring it belongs to actor's tenant/workspace."""
    if actor is None and not for_update:
        col = await db.get(KnowledgeCollection, collection_id)
        if col is None:
            raise EntityNotFoundError(
                f"Không tìm thấy bộ sưu tập '{collection_id}' trong phạm vi quản lý."
            )
        return col

    stmt = select(KnowledgeCollection).where(KnowledgeCollection.id == collection_id)
    stmt = apply_actor_scope(stmt, KnowledgeCollection, actor)
    if for_update:
        stmt = stmt.with_for_update()

    res = await db.execute(stmt)
    if inspect.isawaitable(res):
        res = await res
    col = res.scalar_one_or_none()
    if inspect.isawaitable(col):
        col = await col
    if col is None:
        raise EntityNotFoundError(
            f"Không tìm thấy bộ sưu tập '{collection_id}' trong phạm vi quản lý."
        )

    return col


async def get_scoped_binding(
    db: AsyncSession,
    binding_id: str,
    actor: AuthActor | None = None,
    for_update: bool = False,
) -> KnowledgeBinding:
    """Retrieve a KnowledgeBinding ensuring it belongs to actor's tenant/workspace."""
    if actor is None and not for_update:
        binding = await db.get(KnowledgeBinding, binding_id)
        if binding is None:
            raise EntityNotFoundError(
                f"Không tìm thấy liên kết tài liệu '{binding_id}' trong phạm vi quản lý."
            )
        return binding

    stmt = select(KnowledgeBinding).where(KnowledgeBinding.id == binding_id)
    stmt = apply_actor_scope(stmt, KnowledgeBinding, actor)
    if for_update:
        stmt = stmt.with_for_update()

    res = await db.execute(stmt)
    if inspect.isawaitable(res):
        res = await res
    binding = res.scalar_one_or_none()
    if inspect.isawaitable(binding):
        binding = await binding
    if binding is None:
        raise EntityNotFoundError(
            f"Không tìm thấy liên kết tài liệu '{binding_id}' trong phạm vi quản lý."
        )

    return binding


async def get_scoped_index_revision(
    db: AsyncSession,
    index_revision_id: str,
    binding_id: str | None = None,
    actor: AuthActor | None = None,
    for_update: bool = False,
) -> KnowledgeIndexRevision:
    """Retrieve a KnowledgeIndexRevision ensuring it belongs to the binding and actor's scope."""
    if actor is None and not for_update:
        rev = await db.get(KnowledgeIndexRevision, index_revision_id)
        if rev is None or (binding_id is not None and rev.binding_id != binding_id):
            raise EntityNotFoundError(
                f"Không tìm thấy phiên bản chỉ mục '{index_revision_id}' trong phạm vi quản lý."
            )
        return rev

    stmt = (
        select(KnowledgeIndexRevision)
        .join(KnowledgeBinding, KnowledgeIndexRevision.binding_id == KnowledgeBinding.id)
        .where(KnowledgeIndexRevision.id == index_revision_id)
    )
    if binding_id:
        stmt = stmt.where(KnowledgeIndexRevision.binding_id == binding_id)
    stmt = apply_actor_scope(stmt, KnowledgeBinding, actor)
    if for_update:
        stmt = stmt.with_for_update()

    res = await db.execute(stmt)
    if inspect.isawaitable(res):
        res = await res
    rev = res.scalar_one_or_none()
    if inspect.isawaitable(rev):
        rev = await rev
    if rev is None:
        raise EntityNotFoundError(
            f"Không tìm thấy phiên bản chỉ mục '{index_revision_id}' trong phạm vi quản lý."
        )

    return rev


async def bump_collection_index_epoch(
    db: AsyncSession,
    collection_id: str,
) -> int:
    """Atomically increment collection's index_epoch using SQL UPDATE ... RETURNING index_epoch.

    Prevents race conditions / lost updates when multiple bindings are promoted/rolled back concurrently.
    """
    from sqlalchemy import update

    from app.core.exceptions import AppException

    stmt = (
        update(KnowledgeCollection)
        .where(KnowledgeCollection.id == collection_id)
        .values(index_epoch=KnowledgeCollection.index_epoch + 1)
        .returning(KnowledgeCollection.index_epoch)
    )
    res = await db.execute(stmt)
    if inspect.isawaitable(res):
        res = await res
    val = res.scalar_one_or_none()
    if inspect.isawaitable(val):
        val = await val
    if val is None:
        raise EntityNotFoundError(
            f"Không tìm thấy bộ sưu tập '{collection_id}' để cập nhật index epoch."
        )

    if isinstance(val, int) and not isinstance(val, bool):
        return val

    raise AppException(
        f"Giá trị index_epoch trả về không hợp lệ: {val}",
        code="INVALID_INDEX_EPOCH",
        status_code=500,
    )
