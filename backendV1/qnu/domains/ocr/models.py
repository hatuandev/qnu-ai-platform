"""OCR processing persistence: runs pinned to one immutable revision, pages and artifacts.

Table names use the ``ocr_`` prefix but avoid the legacy ``ocr_engines`` /
``ocr_job_logs`` names owned by ``backend/``. A run references the revision with a
composite foreign key, so a run can never be attached to a revision of another
collection or workspace even if a service filter is bypassed.

Processing state lives here, never on ``kb_sources``: the original file stays
``stored`` no matter how the OCR run ends.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.platform.database import Base

RUN_STATUSES = (
    "queued",
    "running",
    "completed",
    "completed_with_warnings",
    "failed",
    "uncertain",
    "cancelled",
)
ACTIVE_RUN_STATUSES = ("queued", "running")
PAGE_STATUSES = ("pending", "in_flight", "completed", "blank", "failed", "uncertain")
ARTIFACT_KINDS = (
    "provider_document",
    "native_page",
    "embedded_image",
    "render_pdf",
    "page_image",
    "raw_response",
    "canonical_json",
    "markdown",
    "manifest",
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class OcrProcessingRun(Base):
    """One processing attempt (generation) of one revision under one pinned config."""

    __tablename__ = "ocr_processing_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["revision_id", "source_id", "collection_id", "workspace_id"],
            [
                "kb_source_revisions.id",
                "kb_source_revisions.source_id",
                "kb_source_revisions.collection_id",
                "kb_source_revisions.workspace_id",
            ],
            ondelete="CASCADE",
            name="fk_ocr_run_revision",
        ),
        UniqueConstraint("revision_id", "generation", name="uq_ocr_run_generation"),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_ocr_run_scope"),
        Index(
            "uq_ocr_run_active",
            "revision_id",
            unique=True,
            postgresql_where=text("status IN ('queued','running')"),
        ),
        Index("ix_ocr_runs_workspace_status", "workspace_id", "status"),
        CheckConstraint(
            "status IN "
            "('queued','running','completed','completed_with_warnings',"
            "'failed','uncertain','cancelled')",
            name="ck_ocr_run_status",
        ),
        CheckConstraint("generation >= 1", name="ck_ocr_run_generation"),
        CheckConstraint(
            "pages_done >= 0 AND pages_failed >= 0 AND attempt_count >= 0",
            name="ck_ocr_run_counters",
        ),
        CheckConstraint("char_length(source_sha256) = 64", name="ck_ocr_run_sha256"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    config_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pages_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    worker_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    usage_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OcrRunPage(Base):
    """Per-page state so a resumed run never calls the provider twice for a done page.

    ``in_flight`` is written and committed *before* the HTTP request: a worker that
    dies mid-request leaves a marker that turns into ``uncertain`` instead of being
    silently retried and billed twice.
    """

    __tablename__ = "ocr_run_pages"
    __table_args__ = (
        UniqueConstraint("run_id", "page_number", name="uq_ocr_page_number"),
        CheckConstraint("page_number >= 1", name="ck_ocr_page_number"),
        CheckConstraint(
            "status IN ('pending','in_flight','completed','blank','failed','uncertain')",
            name="ck_ocr_page_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_ocr_page_attempts"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ocr_processing_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_tables: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class OcrRunArtifact(Base):
    """Immutable, content-addressed artifact of one run; bytes are never rewritten."""

    __tablename__ = "ocr_run_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "kind", "page_no", name="uq_ocr_artifact_kind_page"),
        CheckConstraint(
            "kind IN ('render_pdf','page_image','raw_response','canonical_json','markdown','manifest','native_page','embedded_image','provider_document')",
            name="ck_ocr_artifact_kind",
        ),
        CheckConstraint("page_no >= 0", name="ck_ocr_artifact_page"),
        CheckConstraint("size_bytes > 0", name="ck_ocr_artifact_size"),
        CheckConstraint("char_length(sha256) = 64", name="ck_ocr_artifact_sha256"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ocr_processing_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blob_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
