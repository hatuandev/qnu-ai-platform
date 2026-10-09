"""Relational Database Models for Central Document Repository and Document Revisions."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.document_types.models import DocumentType


def utcnow() -> datetime:
    return datetime.now(UTC)


class RepositoryDocument(Base):
    """Central logical document item stored in MinIO and managed across revisions."""

    __tablename__ = "repository_documents"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"rep_doc_{uuid.uuid4().hex[:12]}"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), default="tenant_qnu", nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="workspace_qnu", nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # pdf, docx, xlsx, txt...
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )  # SHA-256 for idempotency & deduplication
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO S3 object key

    # Administrative & Regulatory Metadata (Nghị định 30/2020/NĐ-CP)
    document_type_code: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("platform_document_types.code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )  # e.g., "2139/QĐ-ĐHQN"
    issuing_authority: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # e.g., "Trường Đại học Quy Nhơn"
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Ngày ban hành
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Ngày có hiệu lực

    # Status & Revision Pointers
    status: Mapped[str] = mapped_column(
        String(32), default="active", nullable=False, index=True
    )  # active, archived
    current_revision_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("document_revisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latest_revision_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Legacy Compatibility Fields (Will be deprecated after cutover)
    parse_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, parsing, parsed, failed
    ocr_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parsed_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extended Metadata (JSONB)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    catalog_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    document_type: Mapped[DocumentType | None] = relationship("DocumentType")
    revisions: Mapped[list[DocumentRevision]] = relationship(
        "DocumentRevision",
        back_populates="document",
        foreign_keys="DocumentRevision.document_id",
        cascade="all, delete-orphan",
    )
    current_revision: Mapped[DocumentRevision | None] = relationship(
        "DocumentRevision",
        foreign_keys=[current_revision_id],
        post_update=True,
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"rep_doc_{uuid.uuid4().hex[:12]}"
        if getattr(self, "tenant_id", None) is None:
            self.tenant_id = "tenant_qnu"
        if getattr(self, "workspace_id", None) is None:
            self.workspace_id = "workspace_qnu"
        if getattr(self, "latest_revision_no", None) is None:
            self.latest_revision_no = 0
        if getattr(self, "row_version", None) is None:
            self.row_version = 1
        if getattr(self, "status", None) is None:
            self.status = "active"
        if getattr(self, "parse_status", None) is None:
            self.parse_status = "pending"
        if getattr(self, "doc_metadata", None) is None:
            self.doc_metadata = {}
        if getattr(self, "catalog_metadata", None) is None:
            self.catalog_metadata = {}
        if getattr(self, "is_active", None) is None:
            self.is_active = True
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("ix_repository_documents_doc_number", "document_number"),
        Index("ix_repository_documents_parse_status", "parse_status"),
        Index("ix_repository_documents_tenant_ws", "tenant_id", "workspace_id"),
    )


class DocumentRevision(Base):
    """Immutable document content version with parse manifest and quality report."""

    __tablename__ = "document_revisions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"rev_{uuid.uuid4().hex[:12]}"
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("repository_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    based_on_revision_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("document_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Source File Attributes at time of revision
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Normalized Content (Immutable once ready)
    canonical_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Structured Manifests & Quality Gate
    page_manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    citation_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    parse_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    quality_report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # State Machine: queued | processing | validating | review_required | ready | failed | cancelled
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Idempotency & Concurrency Control
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Timestamps & Audit
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    document: Mapped[RepositoryDocument] = relationship(
        "RepositoryDocument", back_populates="revisions", foreign_keys=[document_id]
    )
    based_on: Mapped[DocumentRevision | None] = relationship(
        "DocumentRevision", remote_side=[id], foreign_keys=[based_on_revision_id]
    )

    def __init__(self, **kwargs):
        """Eager Python-side defaults so records are valid even before DB flush."""
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"rev_{uuid.uuid4().hex[:12]}"
        if getattr(self, "page_manifest", None) is None:
            self.page_manifest = []
        if getattr(self, "citation_metadata", None) is None:
            self.citation_metadata = {}
        if getattr(self, "parse_provenance", None) is None:
            self.parse_provenance = {}
        if getattr(self, "quality_report", None) is None:
            self.quality_report = {}
        if getattr(self, "lock_version", None) is None:
            self.lock_version = 1
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("ix_doc_revisions_doc_rev_no", "document_id", "revision_no", unique=True),
        Index("ix_doc_revisions_doc_status", "document_id", "status"),
        Index("ix_doc_revisions_source_hash", "source_hash"),
    )
