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
from app.modules.documents.models import DocumentGroup


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
    index_epoch: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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
    group_sources: Mapped[list[KnowledgeGroupSource]] = relationship(
        "KnowledgeGroupSource", back_populates="collection", cascade="all, delete-orphan"
    )
    import_batches: Mapped[list[KnowledgeImportBatch]] = relationship(
        "KnowledgeImportBatch", back_populates="collection", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"col_{uuid.uuid4().hex[:12]}"
        if getattr(self, "index_epoch", None) is None:
            self.index_epoch = 1
        if getattr(self, "is_active", None) is None:
            self.is_active = True
        if getattr(self, "tenant_id", None) is None:
            self.tenant_id = "tenant_qnu"
        if getattr(self, "workspace_id", None) is None:
            self.workspace_id = "workspace_qnu"
        if getattr(self, "collection_metadata", None) is None:
            self.collection_metadata = {}
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()



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
    repository_document_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("repository_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type_code: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("platform_document_types.code", ondelete="SET NULL"),
        nullable=True,
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
    index_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, indexing, indexed, index_failed
    index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    facts: Mapped[list[KnowledgeFact]] = relationship(
        "KnowledgeFact", back_populates="document", cascade="all, delete-orphan"
    )


    @property
    def ocr_method(self) -> str | None:
        """OCR/parser engine recorded in metadata (read-only convenience)."""
        metadata = self.doc_metadata or {}
        return metadata.get("ocr_method")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"doc_{uuid.uuid4().hex[:12]}"
        if getattr(self, "version", None) is None:
            self.version = 1
        if getattr(self, "status", None) is None:
            self.status = "pending"
        if getattr(self, "index_status", None) is None:
            self.index_status = "pending"
        if getattr(self, "is_active", None) is None:
            self.is_active = True
        if getattr(self, "doc_metadata", None) is None:
            self.doc_metadata = {}
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()


class KnowledgeChunk(Base):

    """Individual chunk extracted from document, stored for retrieval and citation."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"chk_{uuid.uuid4().hex[:12]}"
    )
    document_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Optional scoping fields for Knowledge Publishing V2
    binding_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    index_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

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
    document: Mapped[KnowledgeDocument | None] = relationship("KnowledgeDocument", back_populates="chunks")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"chk_{uuid.uuid4().hex[:12]}"
        if getattr(self, "token_count", None) is None:
            self.token_count = 0
        if getattr(self, "chunk_metadata", None) is None:
            self.chunk_metadata = {}
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()

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
    document_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Optional scoping fields for Knowledge Publishing V2
    binding_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    index_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    entity_name: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )  # e.g., "Công nghệ thông tin"
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # e.g., "major", "rule", "fee"
    attribute_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # e.g., "benchmark_score_2024", "quota"
    attribute_value: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "24.5", "180", full deliverables text

    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    collection: Mapped[KnowledgeCollection] = relationship(
        "KnowledgeCollection", back_populates="facts"
    )
    document: Mapped[KnowledgeDocument | None] = relationship(
        "KnowledgeDocument", back_populates="facts"
    )


# =========================================================================
# V2 Knowledge Publishing & Safe Index Build Models (ADR-011)
# =========================================================================


class KnowledgeVectorGeneration(Base):
    """Vector space configuration isolated per embedding model and dimension."""

    __tablename__ = "knowledge_vector_generations"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"vg_{uuid.uuid4().hex[:12]}"
    )
    collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    qdrant_collection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_schema_version: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_metric: Mapped[str] = mapped_column(String(32), default="cosine", nullable=False)
    generation_epoch: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, deprecated, draining
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_qnu", nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="workspace_qnu", nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"vg_{uuid.uuid4().hex[:12]}"
        if getattr(self, "generation_epoch", None) is None:
            self.generation_epoch = 1
        if getattr(self, "payload_schema_version", None) is None:
            self.payload_schema_version = 2
        if getattr(self, "status", None) is None:
            self.status = "active"
        if getattr(self, "distance_metric", None) is None:
            self.distance_metric = "cosine"
        if getattr(self, "tenant_id", None) is None:
            self.tenant_id = "tenant_qnu"
        if getattr(self, "workspace_id", None) is None:
            self.workspace_id = "workspace_qnu"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()



class KnowledgeGroupSource(Base):
    """Long-lived source binding a DocumentGroup to a KnowledgeCollection."""

    __tablename__ = "knowledge_group_sources"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"src_{uuid.uuid4().hex[:12]}"
    )
    collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_group_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sync_policy: Mapped[str] = mapped_column(
        String(32), default="manual", nullable=False
    )  # manual, auto_on_ready
    chunk_strategy: Mapped[str] = mapped_column(
        String(64), default="ClauseBasedChunker", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="empty", nullable=False, index=True
    )  # empty, up_to_date, updates_available, syncing, review_required, ready, failed, detached
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_membership_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), default="tenant_qnu", nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="workspace_qnu", nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    collection: Mapped[KnowledgeCollection] = relationship(
        "KnowledgeCollection", back_populates="group_sources"
    )
    document_group: Mapped[DocumentGroup] = relationship(
        "DocumentGroup", foreign_keys=[document_group_id], lazy="selectin"
    )
    bindings: Mapped[list[KnowledgeBinding]] = relationship(
        "KnowledgeBinding", back_populates="group_source"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"src_{uuid.uuid4().hex[:12]}"
        if getattr(self, "sync_policy", None) is None:
            self.sync_policy = "manual"
        if getattr(self, "chunk_strategy", None) is None:
            self.chunk_strategy = "ClauseBasedChunker"
        if getattr(self, "status", None) is None:
            self.status = "empty"
        if getattr(self, "tenant_id", None) is None:
            self.tenant_id = "tenant_qnu"
        if getattr(self, "workspace_id", None) is None:
            self.workspace_id = "workspace_qnu"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("ix_knowledge_group_sources_col_group", "collection_id", "document_group_id", unique=True),
        Index("ix_knowledge_group_sources_tenant_ws", "tenant_id", "workspace_id"),
        Index("ix_knowledge_group_sources_status", "status"),
    )


class KnowledgeBinding(Base):
    """Binding associating a RepositoryDocument and target revision to a KnowledgeCollection."""

    __tablename__ = "knowledge_bindings"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"bnd_{uuid.uuid4().hex[:12]}"
    )
    collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_document_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("repository_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_revision_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    group_source_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_group_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    active_index_revision_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_index_revisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    active_source_revision_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_source_revisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    active_epoch: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_strategy: Mapped[str] = mapped_column(String(64), default="ClauseBasedChunker", nullable=False)
    sync_policy: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)  # manual, auto_on_ready
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )  # pending: chưa staging/promote, không tham gia retrieval; active: đã promote, sẵn sàng RAG; archived; detached
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_qnu", nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="workspace_qnu", nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    collection: Mapped[KnowledgeCollection] = relationship("KnowledgeCollection")
    group_source: Mapped[KnowledgeGroupSource | None] = relationship(
        "KnowledgeGroupSource", back_populates="bindings"
    )
    active_index_revision: Mapped[KnowledgeIndexRevision | None] = relationship(
        "KnowledgeIndexRevision",
        foreign_keys=[active_index_revision_id],
        post_update=True,
    )
    active_source_revision: Mapped[KnowledgeSourceRevision | None] = relationship(
        "KnowledgeSourceRevision",
        foreign_keys=[active_source_revision_id],
        post_update=True,
    )
    source_revisions: Mapped[list[KnowledgeSourceRevision]] = relationship(
        "KnowledgeSourceRevision",
        back_populates="binding",
        cascade="all, delete-orphan",
        foreign_keys="KnowledgeSourceRevision.binding_id",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"bnd_{uuid.uuid4().hex[:12]}"
        if getattr(self, "active_epoch", None) is None:
            self.active_epoch = 0
        if getattr(self, "chunk_strategy", None) is None:
            self.chunk_strategy = "ClauseBasedChunker"
        if getattr(self, "sync_policy", None) is None:
            self.sync_policy = "manual"
        if getattr(self, "status", None) is None:
            self.status = "pending"
        if getattr(self, "tenant_id", None) is None:
            self.tenant_id = "tenant_qnu"
        if getattr(self, "workspace_id", None) is None:
            self.workspace_id = "workspace_qnu"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()


    __table_args__ = (
        Index("ix_knowledge_bindings_col_doc", "collection_id", "repository_document_id", unique=True),
        Index("ix_knowledge_bindings_tenant_ws", "tenant_id", "workspace_id"),
        Index("ix_knowledge_bindings_group_source", "group_source_id"),
    )


class KnowledgeIndexRevision(Base):
    """Immutable indexing artifact built in staging before atomic promotion."""

    __tablename__ = "knowledge_index_revisions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"idx_rev_{uuid.uuid4().hex[:12]}"
    )
    binding_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bindings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_revision_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
    )
    source_revision_v2_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_source_revisions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_chunk_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vector_generation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_vector_generations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fact_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    point_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    parity_report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="building", nullable=False, index=True)  # building, validating, ready, active, archived, failed
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    binding: Mapped[KnowledgeBinding] = relationship("KnowledgeBinding", foreign_keys=[binding_id])
    source_revision_v2: Mapped[KnowledgeSourceRevision | None] = relationship(
        "KnowledgeSourceRevision", foreign_keys=[source_revision_v2_id]
    )
    chunk_set: Mapped[KnowledgeChunkSet | None] = relationship(
        "KnowledgeChunkSet", foreign_keys=[chunk_set_id]
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"idx_rev_{uuid.uuid4().hex[:12]}"
        if getattr(self, "chunk_count", None) is None:
            self.chunk_count = 0
        if getattr(self, "fact_count", None) is None:
            self.fact_count = 0
        if getattr(self, "point_ids", None) is None:
            self.point_ids = []
        if getattr(self, "parity_report", None) is None:
            self.parity_report = {}
        if getattr(self, "status", None) is None:
            self.status = "building"
        if getattr(self, "lock_version", None) is None:
            self.lock_version = 1
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()

    __table_args__ = (
        Index("ix_idx_rev_binding_rev_no", "binding_id", "revision_no", unique=True),
        Index("ix_idx_rev_status", "status"),
    )


class KnowledgeIndexActivation(Base):
    """Historical audit log of atomic pointer swaps (promotions, rollbacks, rebuilds)."""

    __tablename__ = "knowledge_index_activations"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"act_{uuid.uuid4().hex[:12]}"
    )
    binding_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bindings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_index_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_index_revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), default="promote", nullable=False)  # promote, rollback, rebuild
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"act_{uuid.uuid4().hex[:12]}"
        if getattr(self, "action", None) is None:
            self.action = "promote"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()


class KnowledgeSourceRevision(Base):
    """Immutable parsed markdown content revision owned by Knowledge domain."""

    __tablename__ = "knowledge_source_revisions"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"ks_rev_{uuid.uuid4().hex[:12]}"
    )
    binding_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_bindings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)

    # Provenance snapshot (No FK cascade to Documents)
    origin_document_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    origin_file_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    snapshot_storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    snapshot_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Normalized content & hashes
    canonical_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Page manifest, citations & quality report
    page_manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    citation_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    parse_provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    quality_report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    parser_profile_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalizer_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    artifact_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # State: queued | extracting | normalizing | validating | review_required | ready | failed | cancelled
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    lock_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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
    binding: Mapped[KnowledgeBinding] = relationship(
        "KnowledgeBinding", back_populates="source_revisions", foreign_keys=[binding_id]
    )
    chunk_sets: Mapped[list[KnowledgeChunkSet]] = relationship(
        "KnowledgeChunkSet",
        back_populates="source_revision",
        cascade="all, delete-orphan",
        foreign_keys="KnowledgeChunkSet.source_revision_id",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"ks_rev_{uuid.uuid4().hex[:12]}"
        if getattr(self, "page_manifest", None) is None:
            self.page_manifest = []
        if getattr(self, "citation_metadata", None) is None:
            self.citation_metadata = {}
        if getattr(self, "parse_provenance", None) is None:
            self.parse_provenance = {}
        if getattr(self, "quality_report", None) is None:
            self.quality_report = {}
        if getattr(self, "snapshot_metadata", None) is None:
            self.snapshot_metadata = {}
        if getattr(self, "lock_version", None) is None:
            self.lock_version = 1
        if getattr(self, "status", None) is None:
            self.status = "queued"
        if getattr(self, "normalizer_version", None) is None:
            self.normalizer_version = "v1"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("uq_knowledge_source_rev_binding_rev_no", "binding_id", "revision_no", unique=True),
        Index("ix_knowledge_source_rev_status", "status"),
        Index("ix_knowledge_source_rev_origin_doc", "origin_document_id"),
        Index("ix_knowledge_source_rev_artifact_key", "artifact_key"),
    )


class KnowledgeChunkSet(Base):
    """Materialized chunks and facts set reusable across multiple vector generations."""

    __tablename__ = "knowledge_chunk_sets"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"chk_set_{uuid.uuid4().hex[:12]}"
    )
    source_revision_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_source_revisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_strategy: Mapped[str] = mapped_column(
        String(64), default="ClauseBasedChunker", nullable=False
    )
    chunk_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_set_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fact_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manifest_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="building", nullable=False)  # building, ready, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    source_revision: Mapped[KnowledgeSourceRevision] = relationship(
        "KnowledgeSourceRevision", back_populates="chunk_sets", foreign_keys=[source_revision_id]
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"chk_set_{uuid.uuid4().hex[:12]}"
        if getattr(self, "chunk_strategy", None) is None:
            self.chunk_strategy = "ClauseBasedChunker"
        if getattr(self, "chunk_config", None) is None:
            self.chunk_config = {}
        if getattr(self, "chunk_count", None) is None:
            self.chunk_count = 0
        if getattr(self, "fact_count", None) is None:
            self.fact_count = 0
        if getattr(self, "status", None) is None:
            self.status = "building"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("uq_knowledge_chunk_set_rev_config", "source_revision_id", "config_hash", unique=True),
        Index("ix_knowledge_chunk_set_key", "chunk_set_key"),
        Index("ix_knowledge_chunk_set_status", "status"),
    )


class KnowledgeImportBatch(Base):
    """Batch orchestration for snapshot imports from Document Repository into KnowledgeCollection."""

    __tablename__ = "knowledge_import_batches"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"imp_batch_{uuid.uuid4().hex[:12]}"
    )
    collection_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_qnu", nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="workspace_qnu", nullable=False, index=True)
    vector_generation_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("knowledge_vector_generations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    parser_profile: Mapped[str] = mapped_column(String(64), default="standard", nullable=False)
    chunk_strategy: Mapped[str] = mapped_column(String(64), default="ClauseBasedChunker", nullable=False)
    chunk_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Aggregate item counts
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queued_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_required_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    succeeded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status: queued | processing | review_required | ready_to_publish | completed | partial_failed | failed | cancelled
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    collection: Mapped[KnowledgeCollection] = relationship(
        "KnowledgeCollection", back_populates="import_batches"
    )
    vector_generation: Mapped[KnowledgeVectorGeneration | None] = relationship(
        "KnowledgeVectorGeneration"
    )
    items: Mapped[list[KnowledgeImportItem]] = relationship(
        "KnowledgeImportItem",
        back_populates="batch",
        cascade="all, delete-orphan",
        foreign_keys="KnowledgeImportItem.batch_id",
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"imp_batch_{uuid.uuid4().hex[:12]}"
        if getattr(self, "tenant_id", None) is None:
            self.tenant_id = "tenant_qnu"
        if getattr(self, "workspace_id", None) is None:
            self.workspace_id = "workspace_qnu"
        if getattr(self, "parser_profile", None) is None:
            self.parser_profile = "standard"
        if getattr(self, "chunk_strategy", None) is None:
            self.chunk_strategy = "ClauseBasedChunker"
        if getattr(self, "chunk_config", None) is None:
            self.chunk_config = {}
        if getattr(self, "total_count", None) is None:
            self.total_count = 0
        if getattr(self, "queued_count", None) is None:
            self.queued_count = 0
        if getattr(self, "processing_count", None) is None:
            self.processing_count = 0
        if getattr(self, "review_required_count", None) is None:
            self.review_required_count = 0
        if getattr(self, "succeeded_count", None) is None:
            self.succeeded_count = 0
        if getattr(self, "failed_count", None) is None:
            self.failed_count = 0
        if getattr(self, "skipped_count", None) is None:
            self.skipped_count = 0
        if getattr(self, "status", None) is None:
            self.status = "queued"
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("ix_knowledge_import_batches_tenant_ws", "tenant_id", "workspace_id"),
        Index("ix_knowledge_import_batches_status", "status"),
        Index("ix_knowledge_import_batches_idem", "collection_id", "idempotency_key"),
    )


class KnowledgeImportItem(Base):
    """Individual document item tracking within a KnowledgeImportBatch."""

    __tablename__ = "knowledge_import_items"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"imp_item_{uuid.uuid4().hex[:12]}"
    )
    batch_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot provenance
    origin_document_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    origin_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    origin_file_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    origin_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    origin_title: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    origin_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Knowledge entity linkages
    knowledge_binding_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    knowledge_source_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Lifecycle Phase & Status
    phase: Mapped[str] = mapped_column(
        String(32), default="snapshot", nullable=False
    )  # snapshot, parse, normalize, validate, chunk, facts, embed, parity, publish
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )  # queued, processing, review_required, succeeded, failed, skipped
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    batch: Mapped[KnowledgeImportBatch] = relationship(
        "KnowledgeImportBatch", back_populates="items", foreign_keys=[batch_id]
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not getattr(self, "id", None):
            self.id = f"imp_item_{uuid.uuid4().hex[:12]}"
        if getattr(self, "origin_metadata", None) is None:
            self.origin_metadata = {}
        if getattr(self, "phase", None) is None:
            self.phase = "snapshot"
        if getattr(self, "status", None) is None:
            self.status = "queued"
        if getattr(self, "retry_count", None) is None:
            self.retry_count = 0
        if getattr(self, "created_at", None) is None:
            self.created_at = utcnow()
        if getattr(self, "updated_at", None) is None:
            self.updated_at = utcnow()

    __table_args__ = (
        Index("uq_knowledge_import_item_batch_doc", "batch_id", "origin_document_id", unique=True),
        Index("ix_knowledge_import_item_status", "status"),
        Index("ix_knowledge_import_item_origin_doc", "origin_document_id"),
    )
