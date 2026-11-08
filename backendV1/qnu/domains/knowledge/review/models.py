"""Review handoff receipts pinned to one immutable version and bundle hash.

The publication status enum stays untouched. A submission records who handed a
draft to review, who closed the handoff and why; it never edits the version.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base

SUBMISSION_STATUSES = ("pending", "changes_requested", "resolved", "cancelled")
OPEN_SUBMISSION_STATUSES = ("pending", "changes_requested")
SUBMISSION_ACTIONS = ("submit", "request_changes", "cancel", "approved", "superseded")


class ReviewSubmission(Base):
    __tablename__ = "kb_review_submissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["version_id", "document_id", "workspace_id", "collection_id"],
            [
                "kb_compiled_versions.id",
                "kb_compiled_versions.document_id",
                "kb_compiled_versions.workspace_id",
                "kb_compiled_versions.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_review_submission_version",
        ),
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="RESTRICT",
            name="fk_review_submission_collection",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_review_submission_scope"),
        CheckConstraint(
            "status IN ('pending','changes_requested','resolved','cancelled')",
            name="ck_review_submission_status",
        ),
        CheckConstraint("state_version >= 1 AND document_sequence >= 1", name="ck_review_sequence"),
        CheckConstraint("char_length(bundle_sha256) = 64", name="ck_review_bundle_sha256"),
        Index(
            "uq_review_submission_pending",
            "version_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "ix_review_submission_document",
            "document_id",
            "version_id",
            "submitted_at",
        ),
        Index(
            "ix_review_submission_worklist",
            "workspace_id",
            "collection_id",
            "status",
            "submitted_at",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    note: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    submitted_by: Mapped[str] = mapped_column(String(200), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    document_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_by: Mapped[str | None] = mapped_column(String(200))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ReviewSubmissionPreview(Base):
    __tablename__ = "kb_review_submission_previews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["submission_id", "workspace_id", "collection_id"],
            [
                "kb_review_submissions.id",
                "kb_review_submissions.workspace_id",
                "kb_review_submissions.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_review_preview_submission",
        ),
        ForeignKeyConstraint(
            ["version_id", "document_id", "workspace_id", "collection_id"],
            [
                "kb_compiled_versions.id",
                "kb_compiled_versions.document_id",
                "kb_compiled_versions.workspace_id",
                "kb_compiled_versions.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_review_preview_version",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_review_preview_scope"),
        CheckConstraint(
            "action IN ('submit','request_changes','cancel')", name="ck_review_preview_action"
        ),
        Index("ix_review_preview_created", "workspace_id", "collection_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    submission_id: Mapped[str | None] = mapped_column(String(64))
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    expected_document_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_version_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_submission_status: Mapped[str | None] = mapped_column(String(20))
    expected_submission_sequence: Mapped[int | None] = mapped_column(Integer)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ReviewSubmissionAction(Base):
    __tablename__ = "kb_review_submission_actions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["submission_id", "workspace_id", "collection_id"],
            [
                "kb_review_submissions.id",
                "kb_review_submissions.workspace_id",
                "kb_review_submissions.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_review_action_submission",
        ),
        ForeignKeyConstraint(
            ["preview_id", "workspace_id", "collection_id"],
            [
                "kb_review_submission_previews.id",
                "kb_review_submission_previews.workspace_id",
                "kb_review_submission_previews.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_review_action_preview",
        ),
        UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_review_action_idempotency"
        ),
        UniqueConstraint("preview_id", name="uq_review_action_preview"),
        UniqueConstraint("publication_decision_id", name="uq_review_action_decision"),
        CheckConstraint(
            "action IN ('submit','request_changes','cancel','approved','superseded')",
            name="ck_review_action_action",
        ),
        Index("ix_review_action_submission", "submission_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    submission_id: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_id: Mapped[str | None] = mapped_column(String(64))
    publication_decision_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kb_publication_decisions.id", ondelete="RESTRICT")
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    document_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    before: Mapped[dict] = mapped_column(JSONB, nullable=False)
    after: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
