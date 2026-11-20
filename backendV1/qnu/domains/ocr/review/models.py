"""Append-only saved edits, spelling inspections and reviewer dispositions."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.ocr.models import utcnow
from qnu.platform.database import Base


def scope_constraint(name: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["run_id", "workspace_id", "collection_id"],
        [
            "ocr_processing_runs.id",
            "ocr_processing_runs.workspace_id",
            "ocr_processing_runs.collection_id",
        ],
        ondelete="RESTRICT",
        name=name,
    )


class TextVersion(Base):
    __tablename__ = "ocr_text_versions"
    __table_args__ = (
        scope_constraint("fk_ocr_text_run"),
        UniqueConstraint("run_id", "version", name="uq_ocr_text_version"),
        UniqueConstraint("id", "run_id", "workspace_id", "collection_id", name="uq_ocr_text_scope"),
        UniqueConstraint(
            "workspace_id", "created_by", "idempotency_key", name="uq_ocr_text_request"
        ),
        CheckConstraint("version > 0", name="ck_ocr_text_version"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    original_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    markdown_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_key: Mapped[str] = mapped_column(String(512), nullable=False)
    markdown_key: Mapped[str] = mapped_column(String(512), nullable=False)
    changes: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class SpellingRun(Base):
    __tablename__ = "ocr_spelling_runs"
    __table_args__ = (
        scope_constraint("fk_ocr_spelling_run"),
        UniqueConstraint(
            "workspace_id", "created_by", "idempotency_key", name="uq_ocr_spelling_request"
        ),
        CheckConstraint(
            "status IN ('running','completed','failed','uncertain','cancelled')",
            name="ck_ocr_spelling_status",
        ),
        CheckConstraint(
            "pass_number >= 1 AND total_passes >= pass_number",
            name="ck_ocr_spelling_passes",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    canonical_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pass_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    total_passes: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    pass_name: Mapped[str] = mapped_column(String(64), nullable=False, default="char_ocr", server_default="char_ocr")
    parent_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    batch_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    checked_evidence_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    trace: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    usage_id: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SpellingReview(Base):
    """One durable approval of a completed check and the text it produced."""

    __tablename__ = "ocr_spelling_reviews"
    __table_args__ = (
        scope_constraint("fk_ocr_spelling_review_run"),
        ForeignKeyConstraint(
            ["check_id"],
            ["ocr_spelling_runs.id"],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_review_check",
        ),
        ForeignKeyConstraint(
            ["reviewed_version_id"],
            ["ocr_text_versions.id"],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_review_version",
        ),
        UniqueConstraint("check_id", name="uq_ocr_spelling_review_check"),
        UniqueConstraint(
            "workspace_id", "reviewed_by", "idempotency_key", name="uq_ocr_spelling_review_request"
        ),
        CheckConstraint("reviewed_version >= 0", name="ck_ocr_spelling_review_version"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    check_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewed_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewed_version_id: Mapped[str | None] = mapped_column(String(64))
    change_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class SpellingDisposition(Base):
    """A reviewer's persisted "ignore" for one exact suggestion of one check."""

    __tablename__ = "ocr_spelling_dispositions"
    __table_args__ = (
        scope_constraint("fk_ocr_spelling_disposition_run"),
        ForeignKeyConstraint(
            ["check_id"],
            ["ocr_spelling_runs.id"],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_disposition_check",
        ),
        UniqueConstraint(
            "check_id",
            "evidence_id",
            "span_start",
            "span_end",
            name="uq_ocr_spelling_disposition",
        ),
        CheckConstraint(
            "span_start >= 0 AND span_end > span_start",
            name="ck_ocr_spelling_disposition_span",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    check_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    span_start: Mapped[int] = mapped_column(Integer, nullable=False)
    span_end: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
