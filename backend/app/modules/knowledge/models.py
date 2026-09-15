"""Relational Database Models for Knowledge Base Management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class KnowledgeCollection(Base):
    """Collection grouping related documents and knowledge chunks."""

    __tablename__ = "knowledge_collections"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"col_{uuid.uuid4().hex[:12]}"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_code: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # admissions, regulations, library...
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="tenant_qnu", index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="workspace_qnu", index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    collection_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    documents: Mapped[list[KnowledgeDocument]] = relationship(
        "KnowledgeDocument", back_populates="collection", cascade="all, delete-orphan"
    )
    facts: Mapped[list[KnowledgeFact]] = relationship(
        "KnowledgeFact", back_populates="collection", cascade="all, delete-orphan"
    )


class KnowledgeDocument(Base):
    """Uploaded or ingested document item."""

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"doc_{uuid.uuid4().hex[:12]}"
    )
    collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # pdf, docx, xlsx, txt...
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # SHA-256 for idempotency

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending, processed, approved, archived
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    doc_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    collection: Mapped[KnowledgeCollection] = relationship(
        "KnowledgeCollection", back_populates="documents"
    )
    chunks: Mapped[list[KnowledgeChunk]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    """Individual chunk extracted from document, stored for retrieval and citation."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"chk_{uuid.uuid4().hex[:12]}"
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of content
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    section: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # e.g., "Điều 5. Cảnh báo học vụ"
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    document: Mapped[KnowledgeDocument] = relationship("KnowledgeDocument", back_populates="chunks")

    __table_args__ = (Index("ix_chunks_col_doc", "collection_id", "document_id"),)


class KnowledgeFact(Base):
    """Structured Fact Record extracted from tables/forms (Tuition fees, Cutoff scores, Quotas)."""

    __tablename__ = "knowledge_facts"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"fct_{uuid.uuid4().hex[:12]}"
    )
    collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    entity_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # e.g., "Công nghệ thông tin"
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # e.g., "major", "rule", "fee"
    attribute_name: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # e.g., "benchmark_score_2024", "quota"
    attribute_value: Mapped[str] = mapped_column(String(512), nullable=False)  # e.g., "24.5", "180"

    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    collection: Mapped[KnowledgeCollection] = relationship(
        "KnowledgeCollection", back_populates="facts"
    )
