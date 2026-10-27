"""Atomic text versions: both stored derivatives must verify before becoming visible."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES
from qnu.domains.knowledge.public_api import resolve_revision_scope
from qnu.domains.ocr.artifacts.canonical import render_markdown
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review.models import TextVersion
from qnu.domains.ocr.review.schemas import ReviewDocument, SaveReview
from qnu.domains.ocr.review.text import apply_changes, leaf_units
from qnu.domains.ocr.service import processing_service
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.ports.blob_store import BlobStore


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


async def authorize(
    db: AsyncSession,
    actor: AuthActor,
    run: OcrProcessingRun,
    *,
    write: bool = False,
    lock: bool = False,
) -> None:
    await resolve_workspace_access(
        db,
        actor,
        run.workspace_id,
        required_roles=WRITE_ROLES if write else READ_ROLES,
        for_update=lock,
    )
    await resolve_revision_scope(
        db, run.workspace_id, run.collection_id, run.source_id, run.revision_id
    )
    current = (
        await db.scalar(
            select(OcrProcessingRun)
            .where(OcrProcessingRun.id == run.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if lock
        else run
    )
    processing_service._require_completed(current)


async def version_row(
    db: AsyncSession, run_id: str, version: int | None = None
) -> TextVersion | None:
    statement = select(TextVersion).where(TextVersion.run_id == run_id)
    if version is not None:
        statement = statement.where(TextVersion.version == version)
    result = await db.scalar(statement.order_by(TextVersion.version.desc()).limit(1))
    if version and result is None:
        raise EntityNotFound("Không tìm thấy bản văn bản đã lưu.", code="ocr_text_not_found")
    return result


async def checked_bytes(blob: BlobStore, key: str, expected: str) -> bytes:
    try:
        payload = await blob.get_bytes(key)
    except Exception as exc:
        raise AppException(
            "Không đọc được bản văn bản đã lưu.", code="storage_unavailable", status_code=502
        ) from exc
    if sha(payload) != expected:
        raise AppException(
            "Tệp văn bản không khớp kiểm tra toàn vẹn.",
            code="artifact_integrity_failed",
            status_code=502,
        )
    return payload


async def document(
    db: AsyncSession, blob: BlobStore, run: OcrProcessingRun, version: int | None = None
) -> tuple[dict, str, TextVersion | None]:
    original_sha, raw = await processing_service.read_document(db, blob, run)
    row = await version_row(db, run.id, version) if version != 0 else None
    if row is None:
        return json.loads(raw), original_sha, None
    if row.original_sha256 != original_sha:
        raise Conflict("Bản sửa không khớp OCR gốc.", code="ocr_text_source_changed")
    return (
        json.loads(await checked_bytes(blob, row.document_key, row.canonical_sha256)),
        original_sha,
        row,
    )


async def read_review(
    db: AsyncSession, blob: BlobStore, run: OcrProcessingRun, version: int | None = None
) -> ReviewDocument:
    doc, original_sha, row = await document(db, blob, run, version)
    _, original = await processing_service.read_document(db, blob, run)
    originals = {u.evidence_id: u.text for u, _ in leaf_units(json.loads(original))}
    units = [
        u.model_copy(update={"original_text": originals[u.evidence_id]}) for u, _ in leaf_units(doc)
    ]
    markdown = render_markdown(doc).encode("utf-8")
    if row is not None:
        await checked_bytes(blob, row.markdown_key, row.markdown_sha256)
        if sha(markdown) != row.markdown_sha256:
            raise AppException(
                "Markdown và JSON không đồng bộ.",
                code="ocr_text_derivative_mismatch",
                status_code=502,
            )
    return ReviewDocument(
        run_id=run.id,
        version=row.version if row else 0,
        version_id=row.id if row else None,
        original_sha256=original_sha,
        canonical_sha256=row.canonical_sha256 if row else original_sha,
        markdown_sha256=sha(markdown),
        units=units,
        saved_at=row.created_at if row else None,
    )


def require_version(current: ReviewDocument, version: int, expected_sha: str) -> None:
    if (current.version, current.canonical_sha256) != (version, expected_sha):
        raise Conflict(
            "Nội dung đã có bản mới. Tải lại trước khi sửa hoặc kiểm tra.",
            code="ocr_text_version_conflict",
        )


async def save(
    db: AsyncSession,
    blob: BlobStore,
    actor: AuthActor,
    run: OcrProcessingRun,
    req: SaveReview,
    key: str,
) -> ReviewDocument:
    await authorize(db, actor, run, write=True, lock=True)
    ref = actor_ref(actor)
    request_hash = sha(json_bytes({"run_id": run.id, **req.model_dump()}))
    previous = await db.scalar(
        select(TextVersion).where(
            TextVersion.workspace_id == run.workspace_id,
            TextVersion.created_by == ref,
            TextVersion.idempotency_key == key,
        )
    )
    if previous is not None:
        if previous.request_hash != request_hash:
            raise Conflict(
                "Yêu cầu lưu này đã dùng cho nội dung khác.", code="idempotency_conflict"
            )
        return await read_review(db, blob, run, previous.version)
    current = await read_review(db, blob, run)
    require_version(current, req.expected_version, req.expected_sha256)
    doc, _, parent = await document(db, blob, run)
    edited = apply_changes(doc, req.changes)
    version_id, now = new_id("txt"), utcnow()
    edited["text_review"] = {
        "schema_version": "qnu.ocr.text-review/v1",
        "version_id": version_id,
        "version": current.version + 1,
        "parent_version_id": parent.id if parent else None,
        "original_canonical_sha256": current.original_sha256,
        "previous_canonical_sha256": current.canonical_sha256,
        "saved_at": now.isoformat(),
        "saved_by": ref,
        "changes": [c.model_dump() for c in req.changes],
        "source_image_verified": False,
    }
    payload, markdown = json_bytes(edited), render_markdown(edited).encode("utf-8")
    prefix = f"ocr-text/{run.workspace_id}/{run.id}/{version_id}"
    row = TextVersion(
        id=version_id,
        run_id=run.id,
        workspace_id=run.workspace_id,
        collection_id=run.collection_id,
        version=current.version + 1,
        original_sha256=current.original_sha256,
        canonical_sha256=sha(payload),
        markdown_sha256=sha(markdown),
        document_key=f"{prefix}/{sha(payload)}.json",
        markdown_key=f"{prefix}/{sha(markdown)}.md",
        changes=[c.model_dump() for c in req.changes],
        created_by=ref,
        created_at=now,
        idempotency_key=key,
        request_hash=request_hash,
    )
    try:
        await blob.put_bytes(row.document_key, payload, "application/json")
        await blob.put_bytes(row.markdown_key, markdown, "text/markdown; charset=utf-8")
        await checked_bytes(blob, row.document_key, row.canonical_sha256)
        await checked_bytes(blob, row.markdown_key, row.markdown_sha256)
    except Exception as exc:
        raise AppException(
            "Chưa lưu được đủ Markdown và JSON; hãy thử lưu lại.",
            code="ocr_text_save_failed",
            status_code=502,
        ) from exc
    db.add(row)
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="ocr.text_saved",
        detail={
            "run_id": run.id,
            "version_id": row.id,
            "version": row.version,
            "change_count": len(req.changes),
        },
    )
    await db.commit()
    return await read_review(db, blob, run, row.version)
