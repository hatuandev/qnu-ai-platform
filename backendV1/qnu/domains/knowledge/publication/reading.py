"""Published-content boundary for future indexers: active status, receipt, hashes and scope."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.publication.access import active_version, authorize, document, version
from qnu.domains.knowledge.publication.evidence import assert_pinned, load_bundle
from qnu.domains.knowledge.publication.models import PublicationDecision
from qnu.domains.knowledge.publication.schemas import (
    DecisionResponse,
    DocumentResponse,
    PublishedResponse,
    VersionResponse,
)
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


async def read_published(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
) -> PublishedResponse:
    await authorize(db, actor, workspace_id, collection_id)
    doc = await document(db, workspace_id, collection_id, document_id, lock=True)
    active = await active_version(db, doc)
    if active is None:
        raise EntityNotFound(
            "Tài liệu chưa có phiên bản đang xuất bản.", code="published_compilation_not_found"
        )
    bundle = await load_bundle(
        db,
        blob,
        workspace_id,
        collection_id,
        active.compilation_run_id,
        require_current=True,
        serving=True,
    )
    assert_pinned(active, bundle)
    receipt = await db.scalar(
        select(PublicationDecision)
        .where(
            PublicationDecision.version_id == active.id,
            PublicationDecision.action == "publish",
            PublicationDecision.document_id == doc.id,
        )
        .order_by(PublicationDecision.document_sequence.desc())
        .limit(1)
    )
    if (
        receipt is None
        or receipt.bundle_sha256 != active.bundle_sha256
        or receipt.after.get("state_version") != active.state_version
        or receipt.after.get("active_version_id") != active.id
    ):
        raise Conflict(
            "Thiếu quyết định xuất bản khớp nội dung.", code="publication_receipt_invalid"
        )
    return PublishedResponse(
        document=DocumentResponse.model_validate(doc),
        version=VersionResponse.model_validate(active),
        decision=DecisionResponse.model_validate(receipt),
        content=bundle.content,
    )


async def read_version_draft(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
) -> tuple[str, dict]:
    await authorize(db, actor, workspace_id, collection_id)
    doc = await document(db, workspace_id, collection_id, document_id)
    target = await version(db, doc, version_id)
    bundle = await load_bundle(db, blob, workspace_id, collection_id, target.compilation_run_id)
    assert_pinned(target, bundle)
    return target.draft_sha256, bundle.content
