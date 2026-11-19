"""Isolated vector generations, their publication bindings and source-bound chunks."""

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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class IndexRun(Base):
    __tablename__ = "kb_index_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="RESTRICT",
            name="fk_index_run_collection",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_index_run_scope"),
        UniqueConstraint("collection_id", "generation", name="uq_index_generation"),
        UniqueConstraint(
            "workspace_id", "requested_by", "idempotency_key", name="uq_index_request"
        ),
        Index(
            "uq_index_active",
            "collection_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "uq_index_working",
            "collection_id",
            unique=True,
            postgresql_where=text("status IN ('queued','running')"),
        ),
        CheckConstraint(
            "status IN ('queued','running','completed','failed','uncertain','cancelled')",
            name="ck_index_status",
        ),
        CheckConstraint(
            "generation >= 1 AND dimension > 0 AND attempt_count >= 0", name="ck_index_counters"
        ),
        CheckConstraint("NOT is_active OR status = 'completed'", name="ck_index_active_completed"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_collection: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(120))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(64))
    chunks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_batch: Mapped[dict | None] = mapped_column(JSONB)
    batch_receipts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    manifest_key: Mapped[str | None] = mapped_column(String(512))
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    vectors_retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexSync(Base):
    """Transactional publication outbox, coalesced by collection."""

    __tablename__ = "kb_index_sync"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("revision >= 1 AND run_revision >= 0", name="ck_index_sync_revision"),
        CheckConstraint(
            "status IN ('pending','building','ready','empty','failed','uncertain')",
            name="ck_index_sync_status",
        ),
    )
    collection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision: Mapped[int] = mapped_column(nullable=False, default=1)
    run_revision: Mapped[int] = mapped_column(nullable=False, default=0)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("kb_index_runs.id", ondelete="SET NULL")
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    retry_receipts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class IndexInput(Base):
    __tablename__ = "kb_index_inputs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "workspace_id", "collection_id"],
            ["kb_index_runs.id", "kb_index_runs.workspace_id", "kb_index_runs.collection_id"],
            ondelete="RESTRICT",
            name="fk_index_input_run",
        ),
        ForeignKeyConstraint(
            [
                "publication_decision_id",
                "version_id",
                "document_id",
                "workspace_id",
                "collection_id",
            ],
            [
                "kb_publication_decisions.id",
                "kb_publication_decisions.version_id",
                "kb_publication_decisions.document_id",
                "kb_publication_decisions.workspace_id",
                "kb_publication_decisions.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_index_input_publication",
        ),
        UniqueConstraint(
            "id", "run_id", "workspace_id", "collection_id", name="uq_index_input_scope"
        ),
        UniqueConstraint("run_id", "document_id", name="uq_index_input_document"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version_state: Mapped[int] = mapped_column(Integer, nullable=False)


class IndexChunk(Base):
    __tablename__ = "kb_index_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["input_id", "run_id", "workspace_id", "collection_id"],
            [
                "kb_index_inputs.id",
                "kb_index_inputs.run_id",
                "kb_index_inputs.workspace_id",
                "kb_index_inputs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_index_chunk_input",
        ),
        UniqueConstraint("run_id", "ordinal", name="uq_index_chunk_ordinal"),
        UniqueConstraint("point_id", name="uq_index_chunk_point"),
        CheckConstraint("ordinal >= 0", name="ck_index_chunk_ordinal"),
        Index(
            "ix_kb_index_chunks_fts",
            text("to_tsvector('simple'::regconfig, text)"),
            postgresql_using="gin",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    input_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    point_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    citations: Mapped[dict] = mapped_column(JSONB, nullable=False)
    structure: Mapped[dict | None] = mapped_column(JSONB)
    vector: Mapped[list | None] = mapped_column(JSONB)


class IndexTableFact(Base):
    """Structured Universal Facts scoped to one active IndexRun for deterministic query_facts."""

    __tablename__ = "kb_index_table_facts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["input_id", "index_run_id", "workspace_id", "collection_id"],
            [
                "kb_index_inputs.id",
                "kb_index_inputs.run_id",
                "kb_index_inputs.workspace_id",
                "kb_index_inputs.collection_id",
            ],
            ondelete="CASCADE",
            name="fk_index_table_fact_input",
        ),
        ForeignKeyConstraint(
            ["index_run_id", "workspace_id", "collection_id"],
            ["kb_index_runs.id", "kb_index_runs.workspace_id", "kb_index_runs.collection_id"],
            ondelete="CASCADE",
            name="fk_index_table_fact_run",
        ),
        UniqueConstraint("index_run_id", "fact_id", name="uq_index_table_fact_id"),
        CheckConstraint(
            "row_kind IN ('data','summary','group_header','inline_note')",
            name="ck_index_table_fact_row_kind",
        ),
        CheckConstraint(
            "data_status IN ('locked','interim','planned','unknown')",
            name="ck_index_table_fact_data_status",
        ),
        CheckConstraint("row_index >= 0", name="ck_index_table_fact_row_index"),
        Index(
            "ix_kb_index_table_facts_scope",
            "workspace_id",
            "index_run_id",
            "table_id",
            "data_year",
            "row_kind",
        ),
        Index(
            "ix_kb_index_table_facts_attributes_gin",
            "attributes",
            postgresql_using="gin",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    input_id: Mapped[str] = mapped_column(String(64), nullable=False)
    index_run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    publication_decision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    table_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_table_citation: Mapped[str] = mapped_column(String(256), nullable=False)
    table_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    has_header: Mapped[bool] = mapped_column(nullable=False, default=True)
    keep_whole_in_chunk: Mapped[bool] = mapped_column(nullable=False, default=False)
    column_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    scoped_notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    fact_id: Mapped[str] = mapped_column(String(192), nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row_kind: Mapped[str] = mapped_column(String(24), nullable=False, default="data")
    row_pointer: Mapped[str] = mapped_column(String(256), nullable=False)
    group_name: Mapped[str | None] = mapped_column(Text)
    subject_code: Mapped[str | None] = mapped_column(String(128))
    subject_name: Mapped[str | None] = mapped_column(Text)
    data_year: Mapped[int | None] = mapped_column(Integer)
    data_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    detail_md_pointers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    applicable_note_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    source_cell_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cross_references: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
