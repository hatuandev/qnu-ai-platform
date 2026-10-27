"""Publication-aware snapshots; changes never silently replace a pinned version."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexInput, IndexRun
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.knowledge.publication.reading import read_published
from qnu.domains.knowledge.publication.schemas import PublishedResponse
from qnu.domains.lifecycle.guards import visible
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


async def published_versions(
    db: AsyncSession, workspace_id: str, collection_id: str, document_ids: list[str] | None = None
) -> list[CompiledVersion]:
    if document_ids is not None:
        scoped_ids = set(
            (
                await db.scalars(
                    select(CompiledDocument.id).where(
                        CompiledDocument.workspace_id == workspace_id,
                        CompiledDocument.collection_id == collection_id,
                        CompiledDocument.id.in_(document_ids),
                    )
                )
            ).all()
        )
        if scoped_ids != set(document_ids):
            raise EntityNotFound(
                "Document không thuộc scope đã chọn.", code="compiled_document_not_found"
            )
    statement = select(CompiledVersion).where(
        CompiledVersion.workspace_id == workspace_id,
        CompiledVersion.collection_id == collection_id,
        CompiledVersion.status == "published",
        visible("document", CompiledVersion.document_id),
    )
    if document_ids is not None:
        statement = statement.where(CompiledVersion.document_id.in_(document_ids))
    rows = list(
        (
            await db.scalars(
                statement.order_by(CompiledVersion.document_id).limit(
                    get_settings().INDEX_MAX_DOCUMENTS + 1
                )
            )
        ).all()
    )
    if len(rows) > get_settings().INDEX_MAX_DOCUMENTS:
        raise Conflict("Scope vượt số tài liệu của một generation.", code="index_scope_too_large")
    return rows


def publication_identity(published: PublishedResponse) -> dict:
    return {
        "document_id": published.document.id,
        "version_id": published.version.id,
        "publication_decision_id": published.decision.id,
        "bundle_sha256": published.version.bundle_sha256,
        "version_state": published.version.state_version,
    }


async def current_snapshot(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, workspace_id: str, collection_id: str
) -> list[PublishedResponse]:
    versions = await published_versions(db, workspace_id, collection_id)
    if not versions:
        raise Conflict("Chưa có bản xuất bản để indexing.", code="index_no_published_documents")
    from qnu.platform.errors import AppException

    result = []
    for version in versions:
        try:
            result.append(
                await read_published(
                    db, blob, actor, workspace_id, collection_id, version.document_id
                )
            )
        except AppException as exc:
            if exc.code != "resource_unavailable":
                raise
    if not result:
        raise Conflict(
            "Không còn bản xuất bản khả dụng để indexing.", code="index_no_published_documents"
        )
    return result


async def assert_snapshot(
    db: AsyncSession, blob: BlobStore, actor: AuthActor, run: IndexRun
) -> list[PublishedResponse]:
    bindings = list(
        (
            await db.scalars(
                select(IndexInput)
                .where(IndexInput.run_id == run.id)
                .order_by(IndexInput.document_id)
            )
        ).all()
    )
    if run.config.get("replacement_action_id"):
        from qnu.domains.lifecycle.replacement import prepared_snapshot

        current = await prepared_snapshot(db, blob, actor, run)
    else:
        current = await current_snapshot(db, blob, actor, run.workspace_id, run.collection_id)
    expected = [
        {
            k: getattr(b, k)
            for k in (
                "document_id",
                "version_id",
                "publication_decision_id",
                "bundle_sha256",
                "version_state",
            )
        }
        for b in bindings
    ]
    if expected != [publication_identity(p) for p in current]:
        raise Conflict("Publication đã đổi trong khi indexing.", code="index_publication_changed")
    return current
