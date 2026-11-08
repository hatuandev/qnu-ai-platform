"""Preview-first handoff between editors and reviewers.

A submission pins one immutable version and its bundle hash. Approval decisions
close the handoff in the same transaction, so the inbox never keeps a ghost row
after the version has moved on. Nothing here edits version content or the
publication status enum.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.policies.access import READ_ROLES, WRITE_ROLES, load_collection
from qnu.domains.knowledge.publication.access import document, version
from qnu.domains.knowledge.publication.evidence import digest
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.knowledge.review.models import (
    ReviewSubmission,
    ReviewSubmissionAction,
    ReviewSubmissionPreview,
)
from qnu.domains.knowledge.review.schemas import (
    SubmissionCommitRequest,
    SubmissionDetail,
    SubmissionOutcome,
    SubmissionPreviewRequest,
    SubmissionResponse,
)
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import (
    actor_ref,
    caller_workspace_role,
    resolve_workspace_access,
)
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.config import get_settings
from qnu.platform.errors import Conflict, EntityNotFound, Forbidden

SUBMITTABLE_STATUSES = ("draft", "superseded", "withdrawn")
APPROVE_ROLES = ("admin", "reviewer")
ALLOWED_ACTIONS = ("submit", "request_changes", "cancel")


def preview_material(row: ReviewSubmissionPreview) -> dict:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "collection_id": row.collection_id,
        "document_id": row.document_id,
        "version_id": row.version_id,
        "submission_id": row.submission_id,
        "actor_ref": row.actor_ref,
        "action": row.action,
        "reason": row.reason,
        "document_sequence": row.expected_document_sequence,
        "version_sequence": row.expected_version_sequence,
        "submission_status": row.expected_submission_status,
        "submission_sequence": row.expected_submission_sequence,
        "bundle_sha256": row.bundle_sha256,
        "expires_at": row.expires_at.isoformat(),
    }


def _response(row: ReviewSubmission, document_title: str, version_no: int) -> SubmissionResponse:
    return SubmissionResponse(
        id=row.id,
        workspace_id=row.workspace_id,
        collection_id=row.collection_id,
        document_id=row.document_id,
        document_title=document_title,
        version_id=row.version_id,
        version_no=version_no,
        bundle_sha256=row.bundle_sha256,
        status=row.status,
        state_version=row.state_version,
        note=row.note,
        submitted_by=row.submitted_by,
        submitted_at=row.submitted_at,
        document_sequence=row.document_sequence,
        closed_by=row.closed_by,
        closed_at=row.closed_at,
        close_reason=row.close_reason,
    )


async def _authorize(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    action: str,
) -> None:
    roles = (
        WRITE_ROLES
        if action == "submit"
        else APPROVE_ROLES
        if action == "request_changes"
        else READ_ROLES
    )
    await resolve_workspace_access(db, actor, workspace_id, required_roles=roles)
    await load_collection(db, workspace_id, collection_id)


async def _ensure_cancel_actor(
    db: AsyncSession, actor: AuthActor, workspace_id: str, submission: ReviewSubmission
) -> None:
    role = await caller_workspace_role(db, actor, workspace_id)
    if role != "admin" and submission.submitted_by != actor_ref(actor):
        raise Forbidden(
            "Chỉ người gửi hoặc quản trị đơn vị được rút yêu cầu duyệt.",
            code="review_submission_forbidden",
        )


async def _submission(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    document_id: str,
    version_id: str,
    submission_id: str,
    *,
    lock: bool = False,
) -> ReviewSubmission:
    statement = (
        select(ReviewSubmission)
        .where(
            ReviewSubmission.id == submission_id,
            ReviewSubmission.workspace_id == workspace_id,
            ReviewSubmission.collection_id == collection_id,
            ReviewSubmission.document_id == document_id,
            ReviewSubmission.version_id == version_id,
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        statement = statement.with_for_update()
    row = await db.scalar(statement)
    if row is None:
        raise EntityNotFound("Không tìm thấy yêu cầu duyệt.", code="review_submission_not_found")
    return row


async def _assert_can_submit(
    db: AsyncSession, doc: CompiledDocument, target: CompiledVersion
) -> None:
    if target.status not in SUBMITTABLE_STATUSES:
        raise Conflict(
            "Chỉ gửi duyệt phiên bản chưa được duyệt.", code="review_submission_version_invalid"
        )
    if await db.scalar(
        select(ReviewSubmission.id).where(
            ReviewSubmission.document_id == doc.id,
            ReviewSubmission.version_id == target.id,
            ReviewSubmission.status == "pending",
        )
    ):
        raise Conflict("Phiên bản này đã được gửi duyệt.", code="review_submission_duplicate")
    latest = await db.scalar(
        select(ReviewSubmission)
        .where(
            ReviewSubmission.document_id == doc.id,
            ReviewSubmission.version_id == target.id,
        )
        .order_by(ReviewSubmission.submitted_at.desc(), ReviewSubmission.id.desc())
        .limit(1)
    )
    if latest is not None and latest.status == "changes_requested":
        raise Conflict(
            "Phiên bản đã bị yêu cầu sửa; hãy chuẩn bị phiên bản mới.",
            code="review_submission_changes_required",
        )


def _ensure_pending(submission: ReviewSubmission) -> None:
    if submission.status != "pending":
        raise Conflict(
            "Yêu cầu duyệt đã được xử lý hoặc rút.", code="review_submission_not_pending"
        )


def _ensure_pinned(submission: ReviewSubmission, target: CompiledVersion) -> None:
    if (
        submission.bundle_sha256 != target.bundle_sha256
        or target.status not in SUBMITTABLE_STATUSES
    ):
        raise Conflict(
            "Phiên bản đã thay đổi so với yêu cầu duyệt.", code="review_submission_stale"
        )


async def create_preview(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: SubmissionPreviewRequest,
) -> ReviewSubmissionPreview:
    await _authorize(db, actor, workspace_id, collection_id, req.action)
    doc = await document(db, workspace_id, collection_id, req.document_id, lock=True)
    target = await version(db, doc, req.version_id)
    submission: ReviewSubmission | None = None
    if req.action == "submit":
        await _assert_can_submit(db, doc, target)
    else:
        submission = await _submission(
            db,
            workspace_id,
            collection_id,
            doc.id,
            target.id,
            req.submission_id or "",
        )
        _ensure_pending(submission)
        _ensure_pinned(submission, target)
        if req.action == "cancel":
            await _ensure_cancel_actor(db, actor, workspace_id, submission)
    row = ReviewSubmissionPreview(
        id=new_id("rprev"),
        workspace_id=workspace_id,
        collection_id=collection_id,
        document_id=doc.id,
        version_id=target.id,
        submission_id=submission.id if submission else None,
        actor_ref=actor_ref(actor),
        action=req.action,
        reason=req.reason,
        expected_document_sequence=doc.change_sequence,
        expected_version_sequence=target.state_version,
        expected_submission_status=submission.status if submission else None,
        expected_submission_sequence=submission.state_version if submission else None,
        bundle_sha256=target.bundle_sha256,
        expires_at=utcnow() + timedelta(seconds=get_settings().PUBLICATION_PREVIEW_TTL_SECONDS),
    )
    row.preview_sha256 = digest(preview_material(row))
    db.add(row)
    await db.commit()
    return row


async def _preview_for_actor(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    preview_id: str,
) -> ReviewSubmissionPreview:
    row = await db.scalar(
        select(ReviewSubmissionPreview).where(
            ReviewSubmissionPreview.id == preview_id,
            ReviewSubmissionPreview.workspace_id == workspace_id,
            ReviewSubmissionPreview.collection_id == collection_id,
            ReviewSubmissionPreview.actor_ref == actor_ref(actor),
        )
    )
    if row is None:
        raise EntityNotFound(
            "Không tìm thấy bản xem trước cho thao tác này.",
            code="review_preview_not_found",
        )
    return row


def _check_preview(
    db: AsyncSession,
    doc: CompiledDocument,
    target: CompiledVersion,
    preview: ReviewSubmissionPreview,
    preview_sha256: str,
    submission: ReviewSubmission | None,
) -> None:
    if preview.expires_at <= utcnow():
        raise Conflict(
            "Bản xem trước đã hết hạn; cần xem lại thao tác.", code="review_preview_expired"
        )
    if (
        preview_sha256 != preview.preview_sha256
        or digest(preview_material(preview)) != preview.preview_sha256
    ):
        raise Conflict("Bản xem trước không khớp nội dung đã xem.", code="review_preview_mismatch")
    if (
        doc.change_sequence != preview.expected_document_sequence
        or target.state_version != preview.expected_version_sequence
        or target.bundle_sha256 != preview.bundle_sha256
    ):
        raise Conflict("Phiên bản đã đổi; cần xem lại thao tác.", code="review_preview_stale")
    if preview.submission_id is not None and (
        submission is None
        or submission.id != preview.submission_id
        or submission.status != preview.expected_submission_status
        or submission.state_version != preview.expected_submission_sequence
    ):
        raise Conflict("Yêu cầu duyệt đã đổi; cần xem lại thao tác.", code="review_preview_stale")


async def _previous_action(
    db: AsyncSession, workspace_id: str, actor: AuthActor, key: str
) -> ReviewSubmissionAction | None:
    return await db.scalar(
        select(ReviewSubmissionAction).where(
            ReviewSubmissionAction.workspace_id == workspace_id,
            ReviewSubmissionAction.actor_ref == actor_ref(actor),
            ReviewSubmissionAction.idempotency_key == key,
        )
    )


async def _outcome(db: AsyncSession, action: ReviewSubmissionAction) -> SubmissionOutcome:
    submission = await db.get(ReviewSubmission, action.submission_id)
    doc = await db.get(CompiledDocument, submission.document_id)
    target = await db.get(CompiledVersion, submission.version_id)
    return SubmissionOutcome(
        submission=_response(submission, doc.title, target.version_no),
        action=action.action,
        created=False,
    )


async def _close_superseded_changes(
    db: AsyncSession,
    actor: AuthActor,
    doc: CompiledDocument,
    target: CompiledVersion,
) -> None:
    rows = (
        await db.execute(
            select(ReviewSubmission)
            .where(
                ReviewSubmission.document_id == doc.id,
                ReviewSubmission.status == "changes_requested",
                ReviewSubmission.version_id != target.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalars()
    for row in rows:
        before = {"status": row.status, "state_version": row.state_version}
        row.status, row.state_version = "resolved", row.state_version + 1
        row.closed_by, row.closed_at = actor_ref(actor), utcnow()
        row.close_reason = "Đã có phiên bản mới gửi duyệt."
        db.add(
            ReviewSubmissionAction(
                id=new_id("ract"),
                workspace_id=row.workspace_id,
                collection_id=row.collection_id,
                document_id=row.document_id,
                version_id=row.version_id,
                submission_id=row.id,
                preview_id=None,
                publication_decision_id=None,
                action="superseded",
                actor_ref=actor_ref(actor),
                reason=row.close_reason,
                idempotency_key=None,
                request_hash=None,
                document_sequence=doc.change_sequence,
                bundle_sha256=row.bundle_sha256,
                before=before,
                after={"status": row.status, "state_version": row.state_version},
            )
        )


async def commit_submission(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    req: SubmissionCommitRequest,
    key: str,
    *,
    commit: bool = True,
) -> SubmissionOutcome:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    await load_collection(db, workspace_id, collection_id)
    preview = await _preview_for_actor(db, actor, workspace_id, collection_id, req.preview_id)
    await _authorize(db, actor, workspace_id, collection_id, preview.action)
    doc = await document(db, workspace_id, collection_id, preview.document_id, lock=True)
    target = await version(db, doc, preview.version_id)
    submission = (
        await _submission(
            db,
            workspace_id,
            collection_id,
            doc.id,
            target.id,
            preview.submission_id,
            lock=True,
        )
        if preview.submission_id
        else None
    )
    if preview.action == "cancel" and submission is not None:
        await _ensure_cancel_actor(db, actor, workspace_id, submission)
    request_hash = digest(
        {
            "preview_id": req.preview_id,
            "preview_sha256": req.preview_sha256,
            "action": preview.action,
            "document_id": doc.id,
            "version_id": target.id,
            "submission_id": preview.submission_id,
        }
    )
    old = await _previous_action(db, workspace_id, actor, key)
    if old is not None:
        if old.request_hash != request_hash:
            raise Conflict(
                "Idempotency-Key đã dùng cho thao tác khác.", code="idempotency_conflict"
            )
        return await _outcome(db, old)
    if await db.scalar(
        select(ReviewSubmissionAction.id).where(ReviewSubmissionAction.preview_id == preview.id)
    ):
        raise Conflict(
            "Bản xem trước đã được sử dụng.", code="review_preview_consumed"
        )
    _check_preview(db, doc, target, preview, req.preview_sha256, submission)
    before: dict[str, object]
    after: dict[str, object]
    if preview.action == "submit":
        await _assert_can_submit(db, doc, target)
        submission = ReviewSubmission(
            id=new_id("rsub"),
            workspace_id=workspace_id,
            collection_id=collection_id,
            document_id=doc.id,
            version_id=target.id,
            bundle_sha256=target.bundle_sha256,
            status="pending",
            state_version=1,
            note=preview.reason,
            submitted_by=actor_ref(actor),
            submitted_at=utcnow(),
            document_sequence=doc.change_sequence,
        )
        db.add(submission)
        await db.flush()
        await _close_superseded_changes(db, actor, doc, target)
        before = {"status": None, "state_version": 0}
        after = {"status": "pending", "state_version": 1}
    else:
        _ensure_pending(submission)
        _ensure_pinned(submission, target)
        before = {"status": submission.status, "state_version": submission.state_version}
        submission.status = (
            "changes_requested" if preview.action == "request_changes" else "cancelled"
        )
        submission.state_version += 1
        submission.closed_by, submission.closed_at = actor_ref(actor), utcnow()
        submission.close_reason = preview.reason
        after = {"status": submission.status, "state_version": submission.state_version}
    action = ReviewSubmissionAction(
        id=new_id("ract"),
        workspace_id=workspace_id,
        collection_id=collection_id,
        document_id=doc.id,
        version_id=target.id,
        submission_id=submission.id,
        preview_id=preview.id,
        publication_decision_id=None,
        action=preview.action,
        actor_ref=actor_ref(actor),
        reason=preview.reason,
        idempotency_key=key,
        request_hash=request_hash,
        document_sequence=doc.change_sequence,
        bundle_sha256=target.bundle_sha256,
        before=before,
        after=after,
    )
    db.add(action)
    await record_workspace_event(
        db,
        workspace_id=workspace_id,
        actor=actor,
        action="review_submission." + preview.action,
        detail={
            "submission_id": submission.id,
            "document_id": doc.id,
            "version_id": target.id,
            "bundle_sha256": target.bundle_sha256,
            "status": submission.status,
            "state_version": submission.state_version,
        },
    )
    if commit:
        await db.commit()
    else:
        await db.flush()
    return SubmissionOutcome(
        submission=_response(submission, doc.title, target.version_no),
        action=preview.action,
        created=True,
    )


async def resolve_on_approval(
    db: AsyncSession,
    actor: AuthActor,
    doc: CompiledDocument,
    target: CompiledVersion,
    decision_id: str,
    reason: str,
) -> str | None:
    """Close a pending or changes-requested handoff in the decision transaction."""
    row = await db.scalar(
        select(ReviewSubmission)
        .where(
            ReviewSubmission.document_id == doc.id,
            ReviewSubmission.version_id == target.id,
            ReviewSubmission.status.in_(("pending", "changes_requested")),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        return None
    before = {"status": row.status, "state_version": row.state_version}
    row.status, row.state_version = "resolved", row.state_version + 1
    row.closed_by, row.closed_at = actor_ref(actor), utcnow()
    row.close_reason = reason[:1000] or "Phiên bản đã được duyệt."
    db.add(
        ReviewSubmissionAction(
            id=new_id("ract"),
            workspace_id=row.workspace_id,
            collection_id=row.collection_id,
            document_id=row.document_id,
            version_id=row.version_id,
            submission_id=row.id,
            preview_id=None,
            publication_decision_id=decision_id,
            action="approved",
            actor_ref=actor_ref(actor),
            reason=row.close_reason,
            idempotency_key=None,
            request_hash=None,
            document_sequence=doc.change_sequence,
            bundle_sha256=row.bundle_sha256,
            before=before,
            after={"status": row.status, "state_version": row.state_version},
        )
    )
    return row.id


async def _read_rows(
    db: AsyncSession,
    workspace_id: str,
    collection_id: str,
    *,
    document_id: str | None,
    version_id: str | None,
    status: str | None,
) -> list[tuple[ReviewSubmission, str, int]]:
    statement = (
        select(ReviewSubmission, CompiledDocument.title, CompiledVersion.version_no)
        .join(CompiledDocument, CompiledDocument.id == ReviewSubmission.document_id)
        .join(CompiledVersion, CompiledVersion.id == ReviewSubmission.version_id)
        .where(
            ReviewSubmission.workspace_id == workspace_id,
            ReviewSubmission.collection_id == collection_id,
        )
    )
    if document_id:
        statement = statement.where(ReviewSubmission.document_id == document_id)
    if version_id:
        statement = statement.where(ReviewSubmission.version_id == version_id)
    if status:
        statement = statement.where(ReviewSubmission.status == status)
    statement = statement.order_by(ReviewSubmission.submitted_at.desc(), ReviewSubmission.id.desc())
    return list((await db.execute(statement)).all())


async def list_submissions(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    *,
    status: str | None = None,
    document_id: str | None = None,
    version_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> Page[SubmissionResponse]:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    await load_collection(db, workspace_id, collection_id)
    if document_id:
        await document(db, workspace_id, collection_id, document_id)
    rows = await _read_rows(
        db,
        workspace_id,
        collection_id,
        document_id=document_id,
        version_id=version_id,
        status=status,
    )
    offset = (page - 1) * page_size
    return Page[SubmissionResponse](
        items=[
            _response(row, title, version_no)
            for row, title, version_no in rows[offset : offset + page_size]
        ],
        meta=PageMeta(page=page, page_size=page_size, total=len(rows)),
    )


async def submission_detail(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    collection_id: str,
    submission_id: str,
) -> SubmissionDetail:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    await load_collection(db, workspace_id, collection_id)
    row = await db.scalar(
        select(ReviewSubmission).where(
            ReviewSubmission.id == submission_id,
            ReviewSubmission.workspace_id == workspace_id,
            ReviewSubmission.collection_id == collection_id,
        )
    )
    if row is None:
        raise EntityNotFound("Không tìm thấy yêu cầu duyệt.", code="review_submission_not_found")
    doc = await document(db, workspace_id, collection_id, row.document_id)
    target = await version(db, doc, row.version_id)
    actions = list(
        (
            await db.execute(
                select(ReviewSubmissionAction)
                .where(ReviewSubmissionAction.submission_id == row.id)
                .order_by(ReviewSubmissionAction.created_at.asc(), ReviewSubmissionAction.id.asc())
            )
        )
        .scalars()
        .all()
    )
    base = _response(row, doc.title, target.version_no)
    return SubmissionDetail(**base.model_dump(), actions=actions)


__all__ = [
    "ALLOWED_ACTIONS",
    "commit_submission",
    "create_preview",
    "list_submissions",
    "preview_material",
    "resolve_on_approval",
    "submission_detail",
]
