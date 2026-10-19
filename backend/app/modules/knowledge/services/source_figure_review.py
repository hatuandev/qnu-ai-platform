"""Authenticated, source-hash-bound transcription review; never publication approval."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from io import BytesIO
from zipfile import ZipFile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.models import KnowledgeBinding, KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument
from app.modules.knowledge.services.scope_helper import get_scoped_collection

KEY = "reviewed_source_figures"
VERSION = "source-figure-review/v1"


def _image_hashes(content: bytes) -> set[str]:
    with ZipFile(BytesIO(content)) as package:
        return {hashlib.sha256(package.read(name)).hexdigest() for name in package.namelist()
                if name.startswith("word/media/") and not name.endswith("/")}


async def record_figure_review(db: AsyncSession, collection_id: str, binding_id: str, revision_id: str,
                               image_sha256: str, transcription: str, approval_reference: str, actor: AuthActor) -> dict:
    """Record an explicit user confirmation on a queued draft, before extraction starts."""
    await require_permission("ai.knowledge.update")(actor)
    if not actor.authenticated or not transcription.strip() or not approval_reference.strip():
        raise AppException("Thiếu xác nhận hoặc tài khoản ghi nhận.", code="FIGURE_REVIEW_REQUIRED", status_code=403)
    await get_scoped_collection(db, collection_id, actor=actor, for_update=True)
    revision = await db.scalar(select(KnowledgeSourceRevision).join(
        KnowledgeBinding, KnowledgeSourceRevision.binding_id == KnowledgeBinding.id).where(
        KnowledgeSourceRevision.id == revision_id, KnowledgeSourceRevision.binding_id == binding_id,
        KnowledgeBinding.collection_id == collection_id).with_for_update())
    if not revision or revision.status != "queued":
        raise AppException("Chỉ ghi xác nhận trước khi bản nháp bắt đầu xử lý.", code="FIGURE_REVIEW_CONFLICT", status_code=409)
    raw = await storage_service.get(revision.snapshot_storage_path)
    if raw is None or hashlib.sha256(raw).hexdigest() != revision.origin_file_hash or image_sha256 not in _image_hashes(raw):
        raise AppException("Ảnh hoặc tệp nguồn không khớp.", code="FIGURE_SOURCE_MISMATCH", status_code=409)
    current = list((revision.snapshot_metadata or {}).get(KEY) or [])
    prior = next((r for r in current if r["image_sha256"] == image_sha256), None)
    if prior:
        if prior["transcription"] != transcription or prior["approval_reference"] != approval_reference:
            raise AppException("Xác nhận ảnh đã thay đổi.", code="FIGURE_REVIEW_CONFLICT", status_code=409)
        return prior
    receipt = {"version": VERSION, "origin_sha256": revision.origin_file_hash, "binding_id": binding_id,
        "image_sha256": image_sha256, "transcription": transcription,
        "transcription_sha256": hashlib.sha256(transcription.encode()).hexdigest(),
        "approval_kind": "explicit_user_confirmation", "approval_reference": approval_reference,
        "recorded_by": actor.actor_id, "at": datetime.now(UTC).isoformat(), "publication_granted": False}
    revision.snapshot_metadata = {**(revision.snapshot_metadata or {}), KEY: [*current, receipt]}
    await db.commit()
    return receipt


def apply_figure_reviews(document: QnuStructuredDocument, content: bytes, records: list[dict], binding_id: str) -> None:
    """Only receipts read from server-owned revision metadata may reach this function."""
    if not records:
        return
    source_hash = hashlib.sha256(content).hexdigest()
    hashes = _image_hashes(content)
    for review in records:
        text = review.get("transcription", "")
        if (review.get("version") != VERSION or review.get("origin_sha256") != source_hash
                or document.source.sha256 != source_hash or review.get("binding_id") != binding_id
                or review.get("image_sha256") not in hashes or not text.strip()
                or review.get("transcription_sha256") != hashlib.sha256(text.encode()).hexdigest()
                or review.get("approval_kind") != "explicit_user_confirmation" or not review.get("recorded_by")
                or not review.get("approval_reference") or review.get("publication_granted") is not False):
            raise AppException("Xác nhận nội dung hình không còn khớp nguồn.", code="FIGURE_REVIEW_STALE", status_code=409)
        matched = [b for b in document.blocks if b.type == "figure"
                   and (b.attributes.get("resource") or {}).get("sha256") == review["image_sha256"]]
        if len(matched) != 1:
            raise AppException("Không xác định duy nhất hình được duyệt.", code="FIGURE_REVIEW_STALE", status_code=409)
        block = matched[0]
        block.body = text
        block.attributes["source_figure_review"] = review
        block.quality_flags = [f for f in block.quality_flags if f.code != "figure_content_unverified"]


def verify_figure_reviews(document: QnuStructuredDocument, content: bytes, records: list[dict], binding_id: str) -> None:
    expected = document.model_copy(deep=True)
    apply_figure_reviews(expected, content, records, binding_id)
    trusted = {r["image_sha256"]: r for r in records}
    for actual, checked in zip(document.blocks, expected.blocks, strict=True):
        receipt = actual.attributes.get("source_figure_review")
        if receipt and trusted.get(receipt.get("image_sha256")) != receipt:
            raise AppException("Xác nhận hình không có trong bản ghi server.", code="FIGURE_REVIEW_STALE", status_code=409)
        if actual.model_dump() != checked.model_dump():
            raise AppException("Nội dung hình đã thay đổi sau xác nhận.", code="FIGURE_REVIEW_STALE", status_code=409)
