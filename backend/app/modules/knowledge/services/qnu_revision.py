"""Immutable standard content edits using the existing revision/review lifecycle."""

import asyncio
import copy
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.schemas import SourceContextEditRequest
from app.modules.knowledge.services.qnu_docx_artifacts import save_qnu_document
from app.modules.knowledge.services.qnu_serving import (
    document_from_edit,
    prepare_standard_revision,
    verify_revision_pair,
)


async def update_standard_revision(db: AsyncSession, binding: KnowledgeBinding, base: KnowledgeSourceRevision,
                                   markdown: str, *, actor_id: str, reason: str, expected_hash: str | None,
                                   context_edits: SourceContextEditRequest | None = None) -> KnowledgeSourceRevision:
    if not expected_hash or expected_hash != base.canonical_hash:
        raise AppException("Tải lại revision trước khi lưu bản chuẩn.", code="SOURCE_CONTENT_CHANGED", status_code=409)
    latest = (await db.execute(select(KnowledgeSourceRevision.revision_no).where(
        KnowledgeSourceRevision.binding_id == binding.id).order_by(KnowledgeSourceRevision.revision_no.desc()))).scalars().first() or base.revision_no
    if latest != base.revision_no:
        raise AppException("Đã có revision mới hơn; hãy tải lại.", code="SOURCE_CONTENT_CHANGED", status_code=409)
    document = await verify_revision_pair(base)
    if not (context_edits is not None and markdown == base.canonical_markdown):
        document = await asyncio.to_thread(document_from_edit, markdown, document, binding_id=binding.id, revision_id=base.id)
    values = {col.key: copy.deepcopy(getattr(base, col.key)) for col in KnowledgeSourceRevision.__table__.columns
              if col.key not in {"id", "revision_no", "created_at", "updated_at"}}
    revision = KnowledgeSourceRevision(**values, id=f"ks_rev_{uuid4().hex[:12]}", revision_no=latest + 1)
    reference = await save_qnu_document(document, document_id=binding.id, revision_id=revision.id,
                                        snapshot_path=base.snapshot_storage_path)
    if reference.get("status") != "ready":
        raise AppException("Không lưu được cặp MD/JSON hợp lệ; revision chưa được tạo.", code="QNU_STANDARD_INVALID", status_code=409)
    revision.snapshot_metadata = {**revision.snapshot_metadata, "qnu_markdown": reference}
    revision.parse_provenance = {**revision.parse_provenance, "qnu_markdown": reference,
        "edited_from_revision_id": base.id,
        "content_review": {"actor_id": actor_id, "reason": reason, "at": datetime.now(UTC).isoformat(),
                           "base_revision_id": base.id, "base_hash": base.canonical_hash}}
    # A content/context edit creates another revision. Prior approvals remain on
    # the old revision; they never transfer by equal text or a reused path.
    from app.modules.knowledge.services.semantic_store import STORE

    inherited = revision.parse_provenance.pop(STORE, None)
    previous_artifact = revision.parse_provenance.pop("structured_artifact", {})
    if inherited or previous_artifact.get("semantic_effective") or (previous_artifact.get("semantic_annotations") or {}).get("status") == "verified":
        revision.parse_provenance["semantic_review_required_from_revision"] = base.id
    revision.status = "review_required"
    await prepare_standard_revision(revision)
    if context_edits is not None:
        from app.modules.knowledge.services.source_artifact import get_source_artifact
        from app.modules.knowledge.services.source_context import apply_context_edits

        artifact = apply_context_edits(revision.parse_provenance["structured_artifact"], context_edits,
                                      actor_id, base_artifact=get_source_artifact(base))
        revision.parse_provenance = {**revision.parse_provenance, "structured_artifact": artifact}
    revision.status = "review_required"
    revision.normalizer_version = "qnu-rag-projection/v1"
    revision.failure_code = revision.failure_detail = None
    revision.artifact_key = hashlib.sha256(f"{revision.origin_file_hash}:qnu-edit:{revision.id}".encode()).hexdigest()
    revision.parse_provenance["content_review"]["content_hash"] = revision.canonical_hash
    db.add(revision)
    await db.flush()
    await db.commit()
    await db.refresh(revision)
    return revision
