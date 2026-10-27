"""All lookups walk workspace → collection → compiled document → version."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES, load_collection
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.lifecycle.guards import require_available
from qnu.domains.workspaces.access import resolve_workspace_access
from qnu.platform.errors import Conflict, EntityNotFound

ACTION_ROLES = {"approve": ("admin", "reviewer"), "publish": ("admin",), "withdraw": ("admin",)}
TRANSITIONS = {
    "approve": ({"draft", "superseded", "withdrawn"}, "approved"),
    "publish": ({"approved"}, "published"),
    "withdraw": ({"approved", "published"}, "withdrawn"),
}


async def authorize(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    *,
    write: bool = False,
    action: str | None = None,
) -> None:
    await resolve_workspace_access(
        db,
        actor,
        workspace_id,
        required_roles=ACTION_ROLES[action] if action else WRITE_ROLES if write else READ_ROLES,
        for_update=write or action is not None,
    )
    await load_collection(db, workspace_id, collection_id)


async def document(
    db: AsyncSession, workspace_id: str, collection_id: str, document_id: str, *, lock: bool = False
) -> CompiledDocument:
    statement = (
        select(CompiledDocument)
        .where(
            CompiledDocument.id == document_id,
            CompiledDocument.workspace_id == workspace_id,
            CompiledDocument.collection_id == collection_id,
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        statement = statement.with_for_update()
    row = await db.scalar(statement)
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy tài liệu biên soạn.", code="compiled_document_not_found"
        )
    await require_available(db, workspace_id, "document", document_id)
    return row


async def version(db: AsyncSession, doc: CompiledDocument, version_id: str) -> CompiledVersion:
    row = await db.scalar(
        select(CompiledVersion)
        .where(
            CompiledVersion.id == version_id,
            CompiledVersion.document_id == doc.id,
            CompiledVersion.workspace_id == doc.workspace_id,
            CompiledVersion.collection_id == doc.collection_id,
        )
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy phiên bản biên soạn.", code="compiled_version_not_found"
        )
    return row


async def active_version(db: AsyncSession, doc: CompiledDocument) -> CompiledVersion | None:
    return await db.scalar(
        select(CompiledVersion)
        .where(
            CompiledVersion.document_id == doc.id,
            CompiledVersion.status == "published",
        )
        .execution_options(populate_existing=True)
    )


def transition(version: CompiledVersion, action: str) -> str:
    allowed, target = TRANSITIONS[action]
    if version.status not in allowed:
        raise Conflict(
            "Trạng thái phiên bản không cho phép quyết định này.",
            code="publication_transition_invalid",
        )
    return target
