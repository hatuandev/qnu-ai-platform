"""Durable unique review requests and immutable report/raw artifacts."""

from datetime import datetime

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

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class CompilationReview(Base):
    __tablename__ = "kb_compilation_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["compilation_run_id", "workspace_id", "collection_id"],
            [
                "kb_compilation_runs.id",
                "kb_compilation_runs.workspace_id",
                "kb_compilation_runs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_compilation_review_scope",
        ),
        UniqueConstraint(
            "workspace_id", "created_by", "idempotency_key", name="uq_compilation_review_request"
        ),
        CheckConstraint(
            "status IN ('running','completed','failed','uncertain','cancelled')",
            name="ck_compilation_review_status",
        ),
        CheckConstraint(
            "verdict IS NULL OR verdict IN ('needs_attention','no_issues_detected')",
            name="ck_compilation_review_verdict",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    compilation_run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(32))
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    trace: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("model_usage_records.id", ondelete="RESTRICT")
    )
    usage_tokens: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))


class ReviewArtifact(Base):
    __tablename__ = "kb_compilation_review_artifacts"
    __table_args__ = (
        UniqueConstraint("review_id", "kind", name="uq_compilation_review_artifact"),
        CheckConstraint(
            "kind IN ('input_snapshot','raw_response','report_json','markdown','segment_manifest')",
            name="ck_compilation_review_artifact_kind",
        ),
        CheckConstraint(
            "size_bytes >= 0 AND char_length(sha256) = 64",
            name="ck_compilation_review_artifact_hash",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_reviews.id", ondelete="RESTRICT"),
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


class CompilationReviewSegment(Base):
    """One owned review scope; merged coverage is checked over every full unit."""

    __tablename__ = "kb_compilation_review_segments"
    __table_args__ = (
        UniqueConstraint("review_id", "segment_index", name="uq_compilation_review_segment_index"),
        CheckConstraint(
            "status IN ('pending','running','received','completed','failed','uncertain')",
            name="ck_compilation_review_segment_status",
        ),
        CheckConstraint(
            "segment_index >= 1 AND attempt_count >= 0",
            name="ck_compilation_review_segment_counters",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
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


class CompilationReviewSegmentArtifact(Base):
    __tablename__ = "kb_compilation_review_segment_artifacts"
    __table_args__ = (
        UniqueConstraint("segment_id", "kind", name="uq_compilation_review_segment_artifact"),
        CheckConstraint(
            "kind IN ('raw_response','assessment_json')",
            name="ck_compilation_review_segment_artifact_kind",
        ),
        CheckConstraint(
            "size_bytes >= 0 AND char_length(sha256) = 64",
            name="ck_compilation_review_segment_artifact_hash",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    segment_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kb_compilation_review_segments.id", ondelete="CASCADE"),
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
