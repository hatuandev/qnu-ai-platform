"""Durable review intents and actor-bound edit previews."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


def parent_scope(name):
    return ForeignKeyConstraint(
        ["compilation_run_id", "workspace_id", "collection_id"],
        [
            "kb_compilation_runs.id",
            "kb_compilation_runs.workspace_id",
            "kb_compilation_runs.collection_id",
        ],
        name=name,
        ondelete="RESTRICT",
    )


class AutoReviewJob(Base):
    __tablename__ = "kb_compilation_review_jobs"
    __table_args__ = (
        parent_scope("fk_compilation_review_job_scope"),
        CheckConstraint(
            "status IN ('queued','running','completed','failed','uncertain','cancelled')",
            name="ck_compilation_review_job_status",
        ),
    )
    compilation_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    review_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kb_compilation_reviews.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(120))
    error_code: Mapped[str | None] = mapped_column(String(64))


class EditPreview(Base):
    __tablename__ = "kb_compilation_edit_previews"
    __table_args__ = (parent_scope("fk_compilation_edit_scope"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    compilation_run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_edit_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    review_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kb_compilation_reviews.id", ondelete="RESTRICT")
    )
    report_sha256: Mapped[str | None] = mapped_column(String(64))
    preview_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    child_run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kb_compilation_runs.id", ondelete="RESTRICT"), unique=True
    )
