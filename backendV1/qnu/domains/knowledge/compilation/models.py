"""Compiler drafts and immutable bindings to completed OCR generations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
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
    @property
    def source_first(self) -> bool:
        return self.config.get("source_first") is True

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
    # Pointer to the verified final JSON/Markdown pair; intentionally not an FK so
    # old runs without outputs keep loading and a partial row can never be published.
    output_id: Mapped[str | None] = mapped_column(String(64))
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
            "kind IN ('input_snapshot','raw_response','draft_json','markdown','segment_manifest')",
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


class CompilationOutput(Base):
    """One verified JSON/Markdown generation; partial generations are never publishable."""

    __tablename__ = "kb_compilation_outputs"
    __table_args__ = (
        UniqueConstraint("run_id", "generation", name="uq_compilation_output_generation"),
        CheckConstraint("generation >= 1", name="ck_compilation_output_generation"),
        CheckConstraint(
            "char_length(draft_sha256) = 64 AND char_length(markdown_sha256) = 64",
            name="ck_compilation_output_hash",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft_blob_key: Mapped[str] = mapped_column(String(512), nullable=False)
    draft_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    markdown_blob_key: Mapped[str] = mapped_column(String(512), nullable=False)
    markdown_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    coverage: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class CompilationSegment(Base):
    """Durable checkpoint for one owned source scope of a compilation run."""

    __tablename__ = "kb_compilation_segments"
    __table_args__ = (
        UniqueConstraint("run_id", "segment_index", name="uq_compilation_segment_index"),
        CheckConstraint(
            "status IN ('pending','running','received','completed','failed','uncertain')",
            name="ck_compilation_segment_status",
        ),
        CheckConstraint(
            "segment_index >= 1 AND attempt_count >= 0",
            name="ck_compilation_segment_counters",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_segment_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kb_compilation_segments.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(120), nullable=False)
    schema_sha256: Mapped[str | None] = mapped_column(String(64))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("model_usage_records.id", ondelete="RESTRICT")
    )
    usage_tokens: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))


class CompilationSegmentArtifact(Base):
    __tablename__ = "kb_compilation_segment_artifacts"
    __table_args__ = (
        UniqueConstraint("segment_id", "kind", name="uq_compilation_segment_artifact"),
        CheckConstraint(
            "kind IN ('raw_response','draft_json','markdown')",
            name="ck_compilation_segment_artifact_kind",
        ),
        CheckConstraint(
            "size_bytes >= 0 AND char_length(sha256) = 64",
            name="ck_compilation_segment_artifact_integrity",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    segment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_segments.id", ondelete="CASCADE"),
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
