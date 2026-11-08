"""Durable preparation intents.

One row records exactly what the user accepted: the pinned revision and hash, the
chosen mode, the saved text version and the runs created to reach the result. The
row survives a closed tab, a worker restart and a queue outage; it is the only
address a client needs to read the phase of the work.
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.models import utcnow
from qnu.platform.database import Base

PREPARATION_STATUSES = (
    "queued",
    "waiting_ocr",
    "compiling",
    "ready",
    "failed",
    "uncertain",
    "cancelled",
)
ACTIVE_PREPARATION_STATUSES = ("queued", "waiting_ocr", "compiling")
TERMINAL_PREPARATION_STATUSES = ("ready", "failed", "uncertain", "cancelled")
PREPARATION_MODES = ("source", "ai")


class PreparationIntent(Base):
    """Server-persisted request; every step re-reads authority and lifecycle."""

    __tablename__ = "kb_preparation_intents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "collection_id", "workspace_id"],
            ["kb_sources.id", "kb_sources.collection_id", "kb_sources.workspace_id"],
            ondelete="CASCADE",
            name="fk_preparation_source",
        ),
        ForeignKeyConstraint(
            ["revision_id", "source_id", "collection_id", "workspace_id"],
            [
                "kb_source_revisions.id",
                "kb_source_revisions.source_id",
                "kb_source_revisions.collection_id",
                "kb_source_revisions.workspace_id",
            ],
            ondelete="CASCADE",
            name="fk_preparation_revision",
        ),
        UniqueConstraint(
            "workspace_id", "requested_by", "idempotency_key", name="uq_preparation_idempotency"
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_preparation_scope"),
        CheckConstraint(
            "status IN ('queued','waiting_ocr','compiling','ready','failed','uncertain','cancelled')",
            name="ck_preparation_status",
        ),
        CheckConstraint("mode IN ('source','ai')", name="ck_preparation_mode"),
        CheckConstraint("revision_no >= 1", name="ck_preparation_revision"),
        CheckConstraint("text_version >= 0", name="ck_preparation_text_version"),
        CheckConstraint("char_length(revision_sha256) = 64", name="ck_preparation_sha256"),
        Index("ix_preparation_source_created", "source_id", "created_at"),
        Index("ix_preparation_status_lease", "status", "lease_expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    topic: Mapped[str] = mapped_column(String(2000), nullable=False)
    text_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_version_id: Mapped[str | None] = mapped_column(String(64))
    text_canonical_sha256: Mapped[str | None] = mapped_column(String(64))
    provider_id: Mapped[str | None] = mapped_column(String(64))
    max_output_tokens: Mapped[int | None] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ocr_run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("ocr_processing_runs.id", ondelete="RESTRICT"),
        index=True,
    )
    compilation_run_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_runs.id", ondelete="RESTRICT"),
        index=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_detail: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(120))
