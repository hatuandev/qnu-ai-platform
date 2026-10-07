"""Relational Database Model for Central Document Repository."""

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
    """Central document item stored in MinIO and pre-parsed for reuse across Knowledge Collections."""

    __tablename__ = "repository_documents"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"rep_doc_{uuid.uuid4().hex[:12]}"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # pdf, docx, xlsx, txt...
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )  # SHA-256 for idempotency & deduplication
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO S3 object key

    # Administrative & Regulatory Metadata
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

    # Parsing & OCR Pipeline Status
    parse_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, parsing, parsed, failed
    ocr_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)  # qwen3-vl:8b, pymupdf...
    parsed_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # Cleaned Unicode NFC Markdown

    # Extended Metadata (JSONB)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    document_type: Mapped[DocumentType | None] = relationship("DocumentType")

    __table_args__ = (
        Index("ix_repository_documents_doc_number", "document_number"),
        Index("ix_repository_documents_parse_status", "parse_status"),
    )
