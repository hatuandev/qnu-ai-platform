"""Read-only workspace inbox of work that needs a human decision."""

import sqlalchemy as sa
from sqlalchemy import and_, exists, func, literal, null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.contracts.pagination import PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.inbox.schemas import InboxItem, InboxPage
from qnu.domains.knowledge.index.models import IndexRun, IndexSync
from qnu.domains.knowledge.models import KBCollection, KBSource
from qnu.domains.knowledge.policies.access import READ_ROLES, load_collection
from qnu.domains.knowledge.preparation.models import PreparationIntent
from qnu.domains.knowledge.publication.models import (
    CompiledDocument,
    CompiledVersion,
    PublicationDecision,
)
from qnu.domains.knowledge.review.models import ReviewSubmission
from qnu.domains.lifecycle.models import ResourceState
from qnu.domains.workspaces.access import resolve_workspace_access


def _text(value):
    return sa.cast(value, sa.String())


def _item_row(
    kind: str,
    item_id,
    title,
    problem: str,
    detail,
    occurred_at,
    collection_id,
    collection_name,
    document_id=None,
    version_id=None,
    submission_id=None,
    source_id=None,
):
    return select(
        sa.literal(kind, sa.String()).label("kind"),
        item_id.label("item_id"),
        title.label("title"),
        sa.literal(problem, sa.String()).label("problem"),
        detail.label("detail"),
        occurred_at.label("occurred_at"),
        collection_id.label("collection_id"),
        collection_name.label("collection_name"),
        _text(document_id if document_id is not None else null()).label("document_id"),
        _text(version_id if version_id is not None else null()).label("version_id"),
        _text(submission_id if submission_id is not None else null()).label("submission_id"),
        _text(source_id if source_id is not None else null()).label("source_id"),
    )


def _document_lifecycle(document_id):
    return ~exists().where(
        ResourceState.workspace_id == CompiledDocument.workspace_id,
        ResourceState.kind == "document",
        ResourceState.resource_id == document_id,
        ResourceState.status != "active",
    )


def _submission_branch(workspace_id: str, collection_id: str | None, status: str):
    kind = "review_pending" if status == "pending" else "changes_requested"
    statement = (
        _item_row(
            kind,
            ReviewSubmission.id,
            CompiledDocument.title,
            "Chờ người duyệt" if status == "pending" else "Đã yêu cầu sửa",
            ReviewSubmission.note if status == "pending" else ReviewSubmission.close_reason,
            ReviewSubmission.submitted_at if status == "pending" else ReviewSubmission.closed_at,
            ReviewSubmission.collection_id,
            KBCollection.name,
            document_id=ReviewSubmission.document_id,
            version_id=ReviewSubmission.version_id,
            submission_id=ReviewSubmission.id,
        )
        .select_from(ReviewSubmission)
        .join(CompiledDocument, CompiledDocument.id == ReviewSubmission.document_id)
        .join(
            KBCollection,
            and_(
                KBCollection.id == ReviewSubmission.collection_id,
                KBCollection.workspace_id == ReviewSubmission.workspace_id,
            ),
        )
        .where(
            ReviewSubmission.workspace_id == workspace_id,
            ReviewSubmission.status == status,
            _document_lifecycle(ReviewSubmission.document_id),
        )
    )
    if collection_id:
        statement = statement.where(ReviewSubmission.collection_id == collection_id)
    return statement


def _awaiting_publish_branch(workspace_id: str, collection_id: str | None):
    approved_at = (
        select(PublicationDecision.created_at)
        .where(
            PublicationDecision.version_id == CompiledVersion.id,
            PublicationDecision.action == "approve",
            PublicationDecision.bundle_sha256 == CompiledVersion.bundle_sha256,
        )
        .order_by(PublicationDecision.created_at.desc())
        .limit(1)
        .correlate(CompiledVersion)
        .scalar_subquery()
    )
    statement = (
        _item_row(
            "awaiting_publish",
            CompiledVersion.id,
            CompiledDocument.title,
            "Chờ xuất bản",
            func.concat("Phiên bản v", CompiledVersion.version_no, " đã duyệt, chưa xuất bản"),
            approved_at,
            CompiledVersion.collection_id,
            KBCollection.name,
            document_id=CompiledVersion.document_id,
            version_id=CompiledVersion.id,
        )
        .select_from(CompiledVersion)
        .join(CompiledDocument, CompiledDocument.id == CompiledVersion.document_id)
        .join(
            KBCollection,
            and_(
                KBCollection.id == CompiledVersion.collection_id,
                KBCollection.workspace_id == CompiledVersion.workspace_id,
            ),
        )
        .where(
            CompiledVersion.workspace_id == workspace_id,
            CompiledVersion.status == "approved",
            approved_at.is_not(None),
            _document_lifecycle(CompiledVersion.document_id),
        )
    )
    if collection_id:
        statement = statement.where(CompiledVersion.collection_id == collection_id)
    return statement


def _sync_failed_branch(workspace_id: str, collection_id: str | None):
    statement = (
        _item_row(
            "sync_incomplete",
            KBCollection.id,
            KBCollection.name,
            "Đồng bộ chưa hoàn tất",
            func.coalesce(IndexSync.error_code, "Lần đồng bộ gần nhất thất bại"),
            IndexSync.updated_at,
            KBCollection.id,
            KBCollection.name,
        )
        .select_from(IndexSync)
        .join(
            KBCollection,
            and_(
                KBCollection.id == IndexSync.collection_id,
                KBCollection.workspace_id == IndexSync.workspace_id,
            ),
        )
        .where(
            IndexSync.workspace_id == workspace_id,
            IndexSync.status.in_(("failed", "uncertain")),
            _collection_lifecycle(),
        )
    )
    if collection_id:
        statement = statement.where(IndexSync.collection_id == collection_id)
    return statement


def _sync_missing_branch(workspace_id: str, collection_id: str | None):
    last_publish = (
        select(func.max(PublicationDecision.created_at))
        .where(
            PublicationDecision.collection_id == KBCollection.id,
            PublicationDecision.action == "publish",
        )
        .correlate(KBCollection)
        .scalar_subquery()
    )
    published = exists().where(
        CompiledVersion.collection_id == KBCollection.id,
        CompiledVersion.workspace_id == workspace_id,
        CompiledVersion.status == "published",
    )
    no_sync = ~exists().where(IndexSync.collection_id == KBCollection.id)
    no_run = ~exists().where(
        IndexRun.collection_id == KBCollection.id,
        IndexRun.workspace_id == workspace_id,
        or_(IndexRun.is_active.is_(True), IndexRun.status.in_(("queued", "running"))),
    )
    statement = _item_row(
        "sync_incomplete",
        KBCollection.id,
        KBCollection.name,
        "Đồng bộ chưa hoàn tất",
        literal("Chưa có chỉ mục hoạt động"),
        func.coalesce(last_publish, KBCollection.created_at),
        KBCollection.id,
        KBCollection.name,
    ).where(
        KBCollection.workspace_id == workspace_id,
        published,
        no_sync,
        no_run,
        _collection_lifecycle(),
    )
    if collection_id:
        statement = statement.where(KBCollection.id == collection_id)
    return statement


def _collection_lifecycle():
    return ~exists().where(
        ResourceState.workspace_id == KBCollection.workspace_id,
        ResourceState.kind == "collection",
        ResourceState.resource_id == KBCollection.id,
        ResourceState.status != "active",
    )


def _preparation_failed_branch(workspace_id: str, collection_id: str | None):
    latest_ids = (
        select(PreparationIntent.id)
        .where(PreparationIntent.workspace_id == workspace_id)
        .distinct(PreparationIntent.source_id)
        .order_by(
            PreparationIntent.source_id,
            PreparationIntent.created_at.desc(),
            PreparationIntent.id.desc(),
        )
    )
    if collection_id:
        latest_ids = latest_ids.where(PreparationIntent.collection_id == collection_id)
    statement = (
        _item_row(
            "preparation_failed",
            PreparationIntent.id,
            KBSource.title,
            "Chuẩn bị nội dung lỗi",
            func.coalesce(
                PreparationIntent.error_detail,
                PreparationIntent.error_code,
                "Lần chuẩn bị gần nhất không hoàn tất",
            ),
            func.coalesce(PreparationIntent.finished_at, PreparationIntent.updated_at),
            PreparationIntent.collection_id,
            KBCollection.name,
            source_id=PreparationIntent.source_id,
        )
        .select_from(PreparationIntent)
        .join(KBSource, KBSource.id == PreparationIntent.source_id)
        .join(
            KBCollection,
            and_(
                KBCollection.id == PreparationIntent.collection_id,
                KBCollection.workspace_id == PreparationIntent.workspace_id,
            ),
        )
        .where(
            PreparationIntent.workspace_id == workspace_id,
            PreparationIntent.status.in_(("failed", "uncertain")),
            PreparationIntent.id.in_(latest_ids),
            ~exists().where(
                ResourceState.workspace_id == PreparationIntent.workspace_id,
                ResourceState.kind == "source",
                ResourceState.resource_id == PreparationIntent.source_id,
                ResourceState.status != "active",
            ),
        )
    )
    return statement


ALLOWED_ROLES = {
    "review_pending": ("admin", "reviewer"),
    "changes_requested": ("admin", "editor"),
    "awaiting_publish": ("admin",),
    "sync_incomplete": ("admin",),
    "preparation_failed": ("admin", "editor"),
}


def _deep_path(row: dict, workspace_id: str) -> str:
    kind, collection_id = row["kind"], row["collection_id"]
    if kind in {"review_pending", "changes_requested", "awaiting_publish"}:
        return (
            f"/workspaces/{workspace_id}/collections/{collection_id}"
            f"/documents/{row['document_id']}/versions/{row['version_id']}"
        )
    if kind == "preparation_failed":
        return f"/workspaces/{workspace_id}/collections/{collection_id}/sources/{row['source_id']}"
    return f"/workspaces/{workspace_id}/collections/{collection_id}?tab=index"


async def read_inbox(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    *,
    collection_id: str | None = None,
    kind: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> InboxPage:
    await resolve_workspace_access(db, actor, workspace_id, required_roles=READ_ROLES)
    if collection_id:
        await load_collection(db, workspace_id, collection_id)
    branches = [
        _submission_branch(workspace_id, collection_id, "pending"),
        _submission_branch(workspace_id, collection_id, "changes_requested"),
        _awaiting_publish_branch(workspace_id, collection_id),
        _sync_failed_branch(workspace_id, collection_id),
        _sync_missing_branch(workspace_id, collection_id),
        _preparation_failed_branch(workspace_id, collection_id),
    ]
    combined = sa.union_all(*branches).subquery("inbox")
    counts_rows = (
        await db.execute(
            select(combined.c.kind, func.count()).select_from(combined).group_by(combined.c.kind)
        )
    ).all()
    counts = {row[0]: row[1] for row in counts_rows}
    statement = select(combined)
    if kind:
        statement = statement.where(combined.c.kind == kind)
    total = await db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = (
        await db.execute(
            statement.order_by(combined.c.occurred_at.desc(), combined.c.item_id.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).mappings()
    return InboxPage(
        items=[
            InboxItem(
                id=f"{row['kind']}:{row['item_id']}",
                kind=row["kind"],
                title=row["title"],
                problem=row["problem"],
                detail=row["detail"] or "",
                occurred_at=row["occurred_at"],
                collection_id=row["collection_id"],
                collection_name=row["collection_name"],
                document_id=row["document_id"],
                version_id=row["version_id"],
                submission_id=row["submission_id"],
                source_id=row["source_id"],
                allowed_roles=list(ALLOWED_ROLES[row["kind"]]),
                deep_path=_deep_path(row, workspace_id),
            )
            for row in rows
        ],
        meta=PageMeta(page=page, page_size=page_size, total=total or 0),
        counts=counts,
    )
