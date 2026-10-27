"""Knowledge persistence: collections, logical sources and immutable file revisions.

Table names use the ``kb_`` prefix so the legacy ``knowledge_*`` tables created by
``backend/`` stay owned by the other migration chain. See
``docs/migration-ownership.yaml``.

Isolation is enforced by composite foreign keys, not only by service filters: a
source cannot point at a collection of another workspace, and a revision cannot
point at a source of another collection or workspace.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from qnu.platform.database import Base

SOURCE_STATUSES = ("stored",)


def utcnow() -> datetime:
    return datetime.now(UTC)


class KBCollection(Base):
    """A knowledge collection; the only owner of sources inside one workspace."""

    __tablename__ = "kb_collections"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_kb_collection_name"),
        UniqueConstraint("id", "workspace_id", name="uq_kb_collection_scope"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class KBSource(Base):
    """Logical document. Bytes and evidence metadata live only on its revisions."""

    __tablename__ = "kb_sources"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="CASCADE",
            name="fk_kb_source_collection",
        ),
        UniqueConstraint("id", "collection_id", "workspace_id", name="uq_kb_source_scope"),
        CheckConstraint("status IN ('stored')", name="ck_kb_source_status"),
        CheckConstraint("latest_revision_no >= 1", name="ck_kb_source_latest_revision"),
        CheckConstraint(
            "serving_revision_no >= 1 AND serving_revision_no <= latest_revision_no",
            name="ck_source_serving_revision",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="stored")
    latest_revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    serving_revision_no: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class KBSourceRevision(Base):
    """Immutable snapshot of one uploaded file; never updated after insert.

    ``(collection_id, sha256)`` is unique, so identical content cannot enter the
    same collection twice — not even through two concurrent requests. A revision
    therefore owns exactly one stored object.
    """

    __tablename__ = "kb_source_revisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "collection_id", "workspace_id"],
            ["kb_sources.id", "kb_sources.collection_id", "kb_sources.workspace_id"],
            ondelete="CASCADE",
            name="fk_kb_revision_source",
        ),
        UniqueConstraint("source_id", "revision_no", name="uq_kb_revision_no"),
        UniqueConstraint("collection_id", "sha256", name="uq_kb_revision_content"),
        UniqueConstraint("storage_key", name="uq_kb_revision_storage_key"),
        # Referenced by ocr_processing_runs: a run cannot point at a revision of
        # another source, collection or workspace (Context640).
        UniqueConstraint(
            "id", "source_id", "collection_id", "workspace_id", name="uq_kb_revision_scope"
        ),
        CheckConstraint("revision_no >= 1", name="ck_kb_revision_no"),
        CheckConstraint("size_bytes > 0", name="ck_kb_revision_size"),
        CheckConstraint("char_length(sha256) = 64", name="ck_kb_revision_sha256"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class KBUploadRequest(Base):
    """Idempotency ledger for uploads; one row per (workspace, actor, key)."""

    __tablename__ = "kb_upload_requests"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_kb_upload_idempotency"
        ),
        CheckConstraint("char_length(request_hash) = 64", name="ck_kb_upload_request_hash"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revision_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
