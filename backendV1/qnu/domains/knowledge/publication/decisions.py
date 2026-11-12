"""Explicit previews and serialized, idempotent human lifecycle decisions."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.publication import review_gate
from qnu.domains.knowledge.publication.access import (
    active_version,
    authorize,
    document,
    transition,
    version,
)
from qnu.domains.knowledge.publication.evidence import assert_pinned, digest, load_bundle
from qnu.domains.knowledge.publication.models import (
    CompiledDocument,
    CompiledVersion,
    PublicationDecision,
    PublicationPreview,
)
from qnu.domains.knowledge.publication.schemas import CommitRequest, PreviewRequest
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


def preview_material(row: PublicationPreview) -> dict:
    return {
        "id": row.id,
        "version_id": row.version_id,
        "document_id": row.document_id,
        "workspace_id": row.workspace_id,
        "collection_id": row.collection_id,
        "actor_ref": row.actor_ref,
        "action": row.action,
        "reason": row.reason,
        "document_sequence": row.expected_document_sequence,
        "version_sequence": row.expected_version_sequence,
        "active_version_id": row.expected_active_version_id,
        "bundle_sha256": row.bundle_sha256,
        "review_ack": row.review_ack,
        "expires_at": row.expires_at.isoformat(),
    }


async def create_preview(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    req: PreviewRequest,
) -> PublicationPreview:
    await authorize(db, actor, workspace_id, collection_id, action=req.action)
    doc = await document(db, workspace_id, collection_id, document_id, lock=True)
    target = await version(db, doc, version_id)
    transition(target, req.action)
    if req.action == "publish":
        await assert_approval_receipt(db, target, blob)
    acknowledgement = (
        (
            review_gate.acknowledge_skip(target, req.review_skip, req.reason)
            if req.review_skip is not None
            else await review_gate.acknowledge(db, blob, target, req.review_ack)
        )
        if req.action == "approve"
        else None
    )
    if req.action != "withdraw":
        bundle = await load_bundle(
            db,
            blob,
            workspace_id,
            collection_id,
            target.compilation_run_id,
            require_current=True,
            allow_staged=req.action == "approve",
            serving=True,
            require_warning_ack=True,
        )
        assert_pinned(target, bundle)
    active = await active_version(db, doc)
    row = PublicationPreview(
        id=new_id("pprev"),
        version_id=target.id,
        document_id=doc.id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        actor_ref=actor_ref(actor),
        action=req.action,
        reason=req.reason,
        review_ack=acknowledgement,
        expected_document_sequence=doc.change_sequence,
        expected_version_sequence=target.state_version,
        expected_active_version_id=active.id if active else None,
        bundle_sha256=target.bundle_sha256,
        expires_at=utcnow() + timedelta(seconds=get_settings().PUBLICATION_PREVIEW_TTL_SECONDS),
    )
    row.preview_sha256 = digest(preview_material(row))
    db.add(row)
    await db.commit()
    return row


async def _preview(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    preview_id: str,
) -> PublicationPreview:
    row = await db.scalar(
        select(PublicationPreview).where(
            PublicationPreview.id == preview_id,
            PublicationPreview.workspace_id == workspace_id,
            PublicationPreview.collection_id == collection_id,
            PublicationPreview.document_id == document_id,
            PublicationPreview.version_id == version_id,
            PublicationPreview.actor_ref == actor_ref(actor),
        )
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy preview cho quyết định này.", code="publication_preview_not_found"
        )
    return row


async def commit_decision(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    req: CommitRequest,
    key: str,
) -> PublicationDecision:
    await authorize(db, actor, workspace_id, collection_id)
    preview = await _preview(
        db, actor, workspace_id, collection_id, document_id, version_id, req.preview_id
    )
    await authorize(db, actor, workspace_id, collection_id, action=preview.action)
    doc = await document(db, workspace_id, collection_id, document_id, lock=True)
    target = await version(db, doc, version_id)
    request_hash = digest(
        {"document_id": document_id, "version_id": version_id, **req.model_dump()}
    )
    old = await db.scalar(
        select(PublicationDecision).where(
            PublicationDecision.workspace_id == workspace_id,
            PublicationDecision.actor_ref == actor_ref(actor),
            PublicationDecision.idempotency_key == key,
        )
    )
    if old is not None:
        if old.request_hash != request_hash:
            raise Conflict(
                "Idempotency-Key đã dùng cho quyết định khác.", code="idempotency_conflict"
            )
        return old
    await _check_preview(db, doc, target, preview, req)
    if preview.action == "publish":
        await assert_approval_receipt(db, target, blob)
    if preview.action == "approve":
        await review_gate.recheck(db, blob, target, preview.review_ack)
    if preview.action != "withdraw":
        bundle = await load_bundle(
            db,
            blob,
            workspace_id,
            collection_id,
            target.compilation_run_id,
            require_current=True,
            allow_staged=preview.action == "approve",
            serving=True,
            require_warning_ack=True,
        )
        assert_pinned(target, bundle)
    return await _apply(db, actor, doc, target, preview, key, request_hash)


async def _check_preview(
    db: AsyncSession,
    doc: CompiledDocument,
    target: CompiledVersion,
    preview: PublicationPreview,
    req: CommitRequest,
) -> None:
    if preview.expires_at <= utcnow():
        raise Conflict(
            "Preview hết hạn; cần xem lại quyết định.", code="publication_preview_expired"
        )
    if (
        req.preview_sha256 != preview.preview_sha256
        or digest(preview_material(preview)) != preview.preview_sha256
    ):
        raise Conflict("Preview không khớp nội dung đã xem.", code="publication_preview_mismatch")
    active = await active_version(db, doc)
    if (
        doc.change_sequence,
        target.state_version,
        active.id if active else None,
        target.bundle_sha256,
    ) != (
        preview.expected_document_sequence,
        preview.expected_version_sequence,
        preview.expected_active_version_id,
        preview.bundle_sha256,
    ):
        raise Conflict(
            "Phiên bản hoặc bản đang hiệu lực đã đổi; cần preview mới.",
            code="publication_preview_stale",
        )
    if await db.scalar(
        select(PublicationDecision.id).where(PublicationDecision.preview_id == preview.id)
    ):
        raise Conflict("Preview đã được sử dụng.", code="publication_preview_consumed")
    transition(target, preview.action)


async def assert_approval_receipt(
    db: AsyncSession, target: CompiledVersion, blob: BlobStore
) -> None:
    receipt = await db.scalar(
        select(PublicationDecision)
        .where(
            PublicationDecision.version_id == target.id,
            PublicationDecision.action == "approve",
            PublicationDecision.document_id == target.document_id,
        )
        .order_by(PublicationDecision.document_sequence.desc())
        .limit(1)
    )
    if (
        receipt is None
        or receipt.bundle_sha256 != target.bundle_sha256
        or receipt.after.get("state_version") != target.state_version
        or receipt.after.get("status") != "approved"
    ):
        raise Conflict(
            "Thiếu quyết định duyệt khớp phiên bản.", code="publication_approval_required"
        )
    await review_gate.recheck(db, blob, target, receipt.after.get("review_ack"))


async def _apply(
    db: AsyncSession,
    actor: AuthActor,
    doc: CompiledDocument,
    target: CompiledVersion,
    preview: PublicationPreview,
    key: str,
    request_hash: str,
    *,
    commit: bool = True,
) -> PublicationDecision:
    previous = await active_version(db, doc)
    before = {
        "status": target.status,
        "state_version": target.state_version,
        "active_version_id": previous.id if previous else None,
    }
    if preview.action == "publish" and previous is not None:
        previous.status = "superseded"
        previous.state_version += 1
        # Flush the old active row before setting the replacement; partial unique index.
        await db.flush()
    target.status = transition(target, preview.action)
    target.state_version += 1
    doc.change_sequence += 1
    active_id = (
        target.id
        if preview.action == "publish"
        else (
            None
            if preview.action == "withdraw" and previous and previous.id == target.id
            else previous.id
            if previous
            else None
        )
    )
    row = PublicationDecision(
        id=new_id("pdec"),
        preview_id=preview.id,
        version_id=target.id,
        document_id=doc.id,
        workspace_id=doc.workspace_id,
        collection_id=doc.collection_id,
        actor_ref=actor_ref(actor),
        action=preview.action,
        reason=preview.reason,
        idempotency_key=key,
        request_hash=request_hash,
        document_sequence=doc.change_sequence,
        bundle_sha256=target.bundle_sha256,
        before=before,
        after={
            "review_ack": preview.review_ack if preview.action == "approve" else None,
            "status": target.status,
            "state_version": target.state_version,
            "active_version_id": active_id,
            "superseded_version_id": previous.id
            if preview.action == "publish" and previous
            else None,
        },
    )
    db.add(row)
    closed_submission_id = None
    if preview.action == "approve":
        from qnu.domains.knowledge.review.service import resolve_on_approval

        closed_submission_id = await resolve_on_approval(
            db, actor, doc, target, row.id, preview.reason
        )
    if preview.action in {"publish", "withdraw"}:
        from qnu.domains.knowledge.index.sync import mark_pending

        await mark_pending(db, actor, doc.workspace_id, doc.collection_id)
    await record_workspace_event(
        db,
        workspace_id=doc.workspace_id,
        actor=actor,
        action="compiled_version." + preview.action,
        detail={
            "document_id": doc.id,
            "version_id": target.id,
            "decision_id": row.id,
            "bundle_sha256": target.bundle_sha256,
            "review_mode": (preview.review_ack or {}).get("mode", "reviewed")
            if preview.action == "approve"
            else None,
            "closed_submission_id": closed_submission_id,
        },
    )
    if commit:
        await db.commit()
    else:
        await db.flush()
    return row
