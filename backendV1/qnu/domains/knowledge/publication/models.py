"""Compiled document identities, immutable version bindings and human decision receipts."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class CompiledDocument(Base):
    __tablename__ = "kb_compiled_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="RESTRICT",
            name="fk_compiled_document_collection",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_compiled_document_scope"),
        UniqueConstraint(
            "workspace_id", "collection_id", "document_key", name="uq_compiled_document_key"
        ),
        CheckConstraint("change_sequence >= 1", name="ck_compiled_document_sequence"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    change_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class CompiledVersion(Base):
    __tablename__ = "kb_compiled_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "workspace_id", "collection_id"],
            [
                "kb_compiled_documents.id",
                "kb_compiled_documents.workspace_id",
                "kb_compiled_documents.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_compiled_version_document",
        ),
        ForeignKeyConstraint(
            ["compilation_run_id", "workspace_id", "collection_id"],
            [
                "kb_compilation_runs.id",
                "kb_compilation_runs.workspace_id",
                "kb_compilation_runs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_compiled_version_run",
        ),
        UniqueConstraint(
            "id", "document_id", "workspace_id", "collection_id", name="uq_compiled_version_scope"
        ),
        UniqueConstraint("compilation_run_id", name="uq_compiled_version_run"),
        UniqueConstraint("document_id", "version_no", name="uq_compiled_version_no"),
        UniqueConstraint(
            "workspace_id", "created_by", "idempotency_key", name="uq_compiled_registration"
        ),
        CheckConstraint(
            "status IN ('draft','approved','published','superseded','withdrawn')",
            name="ck_compiled_version_status",
        ),
        CheckConstraint(
            "version_no >= 1 AND state_version >= 1", name="ck_compiled_version_sequence"
        ),
        Index(
            "uq_compiled_document_published",
            "document_id",
            unique=True,
            postgresql_where=text("status = 'published'"),
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    compilation_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    markdown_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    retrieval_metadata: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class PublicationPreview(Base):
    __tablename__ = "kb_publication_previews"
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
            name="fk_publication_preview_version",
        ),
        UniqueConstraint(
            "id",
            "version_id",
            "document_id",
            "workspace_id",
            "collection_id",
            name="uq_publication_preview_scope",
        ),
        CheckConstraint(
            "action IN ('approve','publish','withdraw')", name="ck_publication_preview_action"
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    review_ack: Mapped[dict | None] = mapped_column(JSONB)
    expected_document_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_version_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_active_version_id: Mapped[str | None] = mapped_column(String(64))
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class PublicationDecision(Base):
    __tablename__ = "kb_publication_decisions"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "version_id",
            "document_id",
            "workspace_id",
            "collection_id",
            name="uq_publication_decision_scope",
        ),
        ForeignKeyConstraint(
            ["preview_id", "version_id", "document_id", "workspace_id", "collection_id"],
            [
                "kb_publication_previews.id",
                "kb_publication_previews.version_id",
                "kb_publication_previews.document_id",
                "kb_publication_previews.workspace_id",
                "kb_publication_previews.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_publication_decision_preview",
        ),
        UniqueConstraint("preview_id", name="uq_publication_decision_preview"),
        UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_publication_decision_request"
        ),
        UniqueConstraint(
            "document_id", "document_sequence", name="uq_publication_decision_sequence"
        ),
        CheckConstraint(
            "action IN ('approve','publish','withdraw')", name="ck_publication_decision_action"
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preview_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    document_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    before: Mapped[dict] = mapped_column(JSONB, nullable=False)
    after: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
