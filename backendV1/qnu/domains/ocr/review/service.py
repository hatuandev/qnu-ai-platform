"""Atomic text versions: both stored derivatives must verify before becoming visible."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES
from qnu.domains.knowledge.public_api import resolve_revision_scope
from qnu.domains.ocr.artifacts.canonical import render_markdown
from qnu.domains.ocr.config import LEGACY_MARKDOWN_VERSION
from qnu.domains.ocr.ids import new_id
from qnu.domains.ocr.models import OcrProcessingRun, utcnow
from qnu.domains.ocr.review.models import (
    SpellingDisposition,
    SpellingReview,
    SpellingRun,
    TextVersion,
)
from qnu.domains.ocr.review.schemas import (
    ReviewDocument,
    SaveReview,
    SpellingEdit,
    Suggestion,
    TextChange,
    TextVersionSummary,
)
from qnu.domains.ocr.review.text import apply_changes, leaf_units
from qnu.domains.ocr.service import processing_service
from qnu.domains.ocr.warnings import acknowledged
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


async def versions(db: AsyncSession, run: OcrProcessingRun) -> list[TextVersionSummary]:
    rows = (
        await db.scalars(
            select(TextVersion)
            .where(TextVersion.run_id == run.id)
            .order_by(TextVersion.version.desc())
        )
    ).all()
    newest = rows[0].version if rows else 0
    return [
        TextVersionSummary(
            version=row.version,
            version_id=row.id,
            saved_at=row.created_at,
            change_count=len(row.changes),
            is_current=row.version == newest,
        )
        for row in rows
    ] + [
        TextVersionSummary(
            version=0,
            version_id=None,
            saved_at=None,
            change_count=0,
            is_current=not rows,
        )
    ]


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


async def load_review(
    db: AsyncSession, blob: BlobStore, run: OcrProcessingRun, version: int | None = None
) -> tuple[ReviewDocument, dict]:
    """Load the review and its canonical document once for a batch sequence."""
    doc, original_sha, row = await document(db, blob, run, version)
    if row is None:
        original = doc
    else:
        _, raw = await processing_service.read_document(db, blob, run)
        original = json.loads(raw)
    originals = {u.evidence_id: u.text for u, _ in leaf_units(original)}
    units = [
        u.model_copy(update={"original_text": originals[u.evidence_id]}) for u, _ in leaf_units(doc)
    ]
    if row is None:
        markdown = await processing_service.read_markdown(db, blob, run)
    else:
        markdown = await checked_bytes(blob, row.markdown_key, row.markdown_sha256)
        is_legacy = markdown.startswith(f"<!-- {LEGACY_MARKDOWN_VERSION} -->\n".encode())
        if render_markdown(doc, legacy=is_legacy).encode("utf-8") != markdown:
            raise AppException(
                "Markdown và JSON không đồng bộ.",
                code="ocr_text_derivative_mismatch",
                status_code=502,
            )
    review = ReviewDocument(
        run_id=run.id,
        version=row.version if row else 0,
        version_id=row.id if row else None,
        original_sha256=original_sha,
        canonical_sha256=row.canonical_sha256 if row else original_sha,
        markdown_sha256=sha(markdown),
        units=units,
        saved_at=row.created_at if row else None,
        image_ocr_failures=list(doc.get("image_ocr_failures") or []),
        image_ocr_acknowledged=acknowledged(run.config, doc.get("image_ocr_failures") or [])
        is not None,
    )
    return review, doc


async def read_review(
    db: AsyncSession, blob: BlobStore, run: OcrProcessingRun, version: int | None = None
) -> ReviewDocument:
    review, _ = await load_review(db, blob, run, version)
    return review


def require_version(current: ReviewDocument, version: int, expected_sha: str) -> None:
    if (current.version, current.canonical_sha256) != (version, expected_sha):
        raise Conflict(
            "Nội dung đã có bản mới. Tải lại trước khi sửa hoặc kiểm tra.",
            code="ocr_text_version_conflict",
        )


async def review_target(
    db: AsyncSession, run: OcrProcessingRun, current: ReviewDocument, req: SaveReview
) -> SpellingRun | None:
    if req.review_check_id is None:
        return None
    check = await db.scalar(
        select(SpellingRun).where(
            SpellingRun.id == req.review_check_id,
            SpellingRun.run_id == run.id,
            SpellingRun.workspace_id == run.workspace_id,
            SpellingRun.collection_id == run.collection_id,
        )
    )
    if check is None:
        raise EntityNotFound("Không tìm thấy lượt kiểm tra.", code="ocr_spelling_not_found")
    if "automatic_parent" in check.trace:
        raise Conflict(
            "Lượt kiểm tra này không phải bản rà soát độc lập.",
            code="ocr_spelling_check_not_reviewable",
        )
    if check.status != "completed":
        raise Conflict(
            "Chỉ duyệt được lượt kiểm tra đã hoàn tất.",
            code="ocr_spelling_check_not_ready",
        )
    approved = await db.scalar(select(SpellingReview.id).where(SpellingReview.check_id == check.id))
    if approved is not None:
        raise Conflict("Lượt kiểm tra này đã được duyệt.", code="ocr_spelling_review_exists")
    if (check.version, check.canonical_sha256) != (current.version, current.canonical_sha256):
        raise Conflict(
            "Kết quả soát không thuộc nội dung hiện tại; hãy soát lại trước khi duyệt.",
            code="ocr_spelling_check_stale",
        )
    return check


async def require_all_handled(
    db: AsyncSession, check: SpellingRun, changes: list[TextChange]
) -> None:
    ignored = {
        (row.evidence_id, row.span_start, row.span_end)
        for row in (
            await db.scalars(
                select(SpellingDisposition).where(SpellingDisposition.check_id == check.id)
            )
        ).all()
    }
    pending: dict[str, dict[tuple[int, int], Suggestion]] = defaultdict(dict)
    for item in check.suggestions + check.trace.get("withheld_suggestions", []):
        evidence_id, start, end = item["evidence_id"], item["start"], item["end"]
        if (evidence_id, start, end) not in ignored:
            pending[evidence_id][start, end] = Suggestion.model_validate(item)
    for change in changes:
        spans = pending.get(change.evidence_id, {})
        for position in _handled_spelling_spans(change, spans):
            spans.pop(position)
    remaining = sum(map(len, pending.values()))
    if remaining:
        raise Conflict(
            f"Còn {remaining} gợi ý chưa được áp dụng hoặc bỏ qua.",
            code="ocr_spelling_suggestions_pending",
        )


def _handled_spelling_spans(
    change: TextChange, pending: dict[tuple[int, int], Suggestion]
) -> set[tuple[int, int]]:
    edits = change.spelling_edits
    if edits is None:
        # Older callers can still submit the exact suggested text for the unit.
        edits = [
            SpellingEdit(start=start, end=end, replacement=item.replacement)
            for (start, end), item in pending.items()
        ]
    if not edits:
        return set()
    resolved = _replay_spelling_edits(change, edits, pending)
    if resolved is None and change.spelling_edits is not None:
        raise Conflict(
            "Các vị trí sửa không khớp với gợi ý hoặc văn bản đã gửi.",
            code="ocr_spelling_edit_invalid",
        )
    return resolved or set()


def _replay_spelling_edits(
    change: TextChange,
    edits: list[SpellingEdit],
    pending: dict[tuple[int, int], Suggestion],
) -> set[tuple[int, int]] | None:
    cursor, parts, resolved = 0, [], set()
    for edit in sorted(edits, key=lambda item: item.start):
        position = (edit.start, edit.end)
        suggestion = pending.get(position)
        if (
            suggestion is None
            or edit.start < cursor
            or change.before[edit.start : edit.end] != suggestion.original
            or not edit.replacement.strip()
            or edit.replacement == suggestion.original
        ):
            return None
        parts.extend((change.before[cursor : edit.start], edit.replacement))
        resolved.add(position)
        cursor = edit.end
    parts.append(change.before[cursor:])
    return resolved if "".join(parts) == change.after else None


def review_row(
    run: OcrProcessingRun,
    check: SpellingRun,
    *,
    version: int,
    canonical_sha256: str,
    version_id: str | None,
    change_count: int,
    ref: str,
    key: str,
    request_hash: str,
    now: datetime,
) -> SpellingReview:
    return SpellingReview(
        id=new_id("splrev"),
        run_id=run.id,
        workspace_id=run.workspace_id,
        collection_id=run.collection_id,
        check_id=check.id,
        reviewed_version=version,
        reviewed_sha256=canonical_sha256,
        reviewed_version_id=version_id,
        change_count=change_count,
        reviewed_by=ref,
        idempotency_key=key,
        request_hash=request_hash,
        reviewed_at=now,
    )


async def record_review(
    db: AsyncSession,
    actor: AuthActor,
    run: OcrProcessingRun,
    row: SpellingReview,
) -> None:
    await record_workspace_event(
        db,
        workspace_id=run.workspace_id,
        actor=actor,
        action="ocr.spelling_reviewed",
        detail={
            "run_id": run.id,
            "check_id": row.check_id,
            "version": row.reviewed_version,
            "change_count": row.change_count,
        },
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
    fields = req.model_dump(exclude_none=True)
    request_hash = sha(json_bytes({"run_id": run.id, **fields}))
    previous = await db.scalar(
        select(TextVersion).where(
            TextVersion.workspace_id == run.workspace_id,
            TextVersion.created_by == ref,
            TextVersion.idempotency_key == key,
        )
    )
    reviewed = await db.scalar(
        select(SpellingReview).where(
            SpellingReview.workspace_id == run.workspace_id,
            SpellingReview.reviewed_by == ref,
            SpellingReview.idempotency_key == key,
        )
    )
    replay = previous if previous is not None else reviewed
    if replay is not None:
        if replay.request_hash != request_hash:
            raise Conflict(
                "Yêu cầu lưu này đã dùng cho nội dung khác.", code="idempotency_conflict"
            )
        return await read_review(
            db, blob, run, previous.version if previous is not None else reviewed.reviewed_version
        )
    current = await read_review(db, blob, run)
    require_version(current, req.expected_version, req.expected_sha256)
    check = await review_target(db, run, current, req)
    if check is not None:
        await require_all_handled(db, check, req.changes)
    if not req.changes:
        if check is None:
            raise Conflict("Chưa có thay đổi để lưu.", code="ocr_text_unchanged")
        now = utcnow()
        review = review_row(
            run,
            check,
            version=current.version,
            canonical_sha256=current.canonical_sha256,
            version_id=current.version_id,
            change_count=0,
            ref=ref,
            key=key,
            request_hash=request_hash,
            now=now,
        )
        db.add(review)
        await record_review(db, actor, run, review)
        await db.commit()
        return await read_review(db, blob, run, current.version)
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
        "changes": fields["changes"],
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
        changes=fields["changes"],
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
    if check is not None:
        # The review references this version; flush first so its row exists.
        await db.flush()
        review = review_row(
            run,
            check,
            version=row.version,
            canonical_sha256=row.canonical_sha256,
            version_id=row.id,
            change_count=len(req.changes),
            ref=ref,
            key=key,
            request_hash=request_hash,
            now=now,
        )
        db.add(review)
        await record_review(db, actor, run, review)
    await db.commit()
    return await read_review(db, blob, run, row.version)
