"""Compiler drafts and immutable bindings to completed OCR generations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.platform.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class CompilationRun(Base):
    __tablename__ = "kb_compilation_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="RESTRICT",
            name="fk_compilation_collection",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_compilation_scope"),
        UniqueConstraint("collection_id", "generation", name="uq_compilation_generation"),
        UniqueConstraint(
            "workspace_id", "requested_by", "idempotency_key", name="uq_compilation_request"
        ),
        CheckConstraint(
            "status IN ('queued','running','completed','failed','uncertain','cancelled')",
            name="ck_compilation_status",
        ),
        CheckConstraint("generation >= 1 AND attempt_count >= 0", name="ck_compilation_counters"),
        ForeignKeyConstraint(
            ["parent_run_id", "workspace_id", "collection_id"],
            [
                "kb_compilation_runs.id",
                "kb_compilation_runs.workspace_id",
                "kb_compilation_runs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_compilation_parent",
        ),
        CheckConstraint("origin IN ('model','user_edit')", name="ck_compilation_origin"),
        CheckConstraint(
            "(origin = 'model' AND parent_run_id IS NULL) OR (origin = 'user_edit' AND parent_run_id IS NOT NULL)",
            name="ck_compilation_ancestry",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_run_id: Mapped[str | None] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(
        String(16), nullable=False, default="model", server_default="model"
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("model_usage_records.id", ondelete="RESTRICT")
    )
    usage_tokens: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))


class CompilationInput(Base):
    __tablename__ = "kb_compilation_inputs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "workspace_id", "collection_id"],
            [
                "kb_compilation_runs.id",
                "kb_compilation_runs.workspace_id",
                "kb_compilation_runs.collection_id",
            ],
            ondelete="CASCADE",
            name="fk_compilation_input_run",
        ),
        ForeignKeyConstraint(
            ["ocr_run_id", "workspace_id", "collection_id"],
            [
                "ocr_processing_runs.id",
                "ocr_processing_runs.workspace_id",
                "ocr_processing_runs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_compilation_input_ocr",
        ),
        UniqueConstraint("run_id", "ocr_run_id", name="uq_compilation_input_ocr"),
        ForeignKeyConstraint(
            ["text_version_id", "ocr_run_id", "workspace_id", "collection_id"],
            [
                "ocr_text_versions.id",
                "ocr_text_versions.run_id",
                "ocr_text_versions.workspace_id",
                "ocr_text_versions.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_compilation_input_text",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ocr_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    text_version_id: Mapped[str | None] = mapped_column(String(64))
    original_canonical_sha256: Mapped[str | None] = mapped_column(String(64))


class CompilationArtifact(Base):
    __tablename__ = "kb_compilation_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "kind", name="uq_compilation_artifact_kind"),
        CheckConstraint(
            "kind IN ('input_snapshot','raw_response','draft_json','markdown')",
            name="ck_compilation_artifact_kind",
        ),
        CheckConstraint(
            "size_bytes >= 0 AND char_length(sha256) = 64", name="ck_compilation_artifact_integrity"
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    blob_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
