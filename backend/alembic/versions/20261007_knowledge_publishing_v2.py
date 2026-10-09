"""Add knowledge publishing v2 tables and index epoch fields.

Revision ID: 20261007_knowledge_publishing_v2
Revises: 20261007_document_revisions
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261007_knowledge_publishing_v2"
down_revision: str | Sequence[str] | None = "20261007_document_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Expand knowledge_collections
    op.add_column(
        "knowledge_collections",
        sa.Column("index_epoch", sa.Integer(), nullable=False, server_default="1"),
    )

    # 2. Expand knowledge_chunks
    op.add_column(
        "knowledge_chunks",
        sa.Column("binding_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column("index_revision_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_knowledge_chunks_binding_id", "knowledge_chunks", ["binding_id"])
    op.create_index("ix_knowledge_chunks_index_revision_id", "knowledge_chunks", ["index_revision_id"])

    # 3. Expand knowledge_facts
    op.add_column(
        "knowledge_facts",
        sa.Column("binding_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "knowledge_facts",
        sa.Column("index_revision_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_knowledge_facts_binding_id", "knowledge_facts", ["binding_id"])
    op.create_index("ix_knowledge_facts_index_revision_id", "knowledge_facts", ["index_revision_id"])

    # 4. Create knowledge_vector_generations
    op.create_table(
        "knowledge_vector_generations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("distance_metric", sa.String(length=32), server_default="cosine", nullable=False),
        sa.Column("generation_epoch", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="tenant_qnu", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="workspace_qnu", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["knowledge_collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_vector_generations_collection_id",
        "knowledge_vector_generations",
        ["collection_id"],
    )
    op.create_index(
        "ix_knowledge_vector_generations_tenant_id",
        "knowledge_vector_generations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_knowledge_vector_generations_workspace_id",
        "knowledge_vector_generations",
        ["workspace_id"],
    )

    # 5. Create knowledge_bindings
    op.create_table(
        "knowledge_bindings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collection_id", sa.String(length=64), nullable=False),
        sa.Column("repository_document_id", sa.String(length=64), nullable=False),
        sa.Column("source_revision_id", sa.String(length=64), nullable=False),
        sa.Column("active_index_revision_id", sa.String(length=64), nullable=True),
        sa.Column("active_epoch", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chunk_strategy", sa.String(length=64), server_default="ClauseBasedChunker", nullable=False),
        sa.Column("sync_policy", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="tenant_qnu", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="workspace_qnu", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["knowledge_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_document_id"], ["repository_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["document_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_bindings_collection_id", "knowledge_bindings", ["collection_id"])
    op.create_index("ix_knowledge_bindings_repository_document_id", "knowledge_bindings", ["repository_document_id"])
    op.create_index("ix_knowledge_bindings_source_revision_id", "knowledge_bindings", ["source_revision_id"])
    op.create_index("ix_knowledge_bindings_active_index_revision_id", "knowledge_bindings", ["active_index_revision_id"])
    op.create_index("ix_knowledge_bindings_status", "knowledge_bindings", ["status"])
    op.create_index("ix_knowledge_bindings_tenant_id", "knowledge_bindings", ["tenant_id"])
    op.create_index("ix_knowledge_bindings_workspace_id", "knowledge_bindings", ["workspace_id"])
    op.create_index(
        "ix_knowledge_bindings_col_doc",
        "knowledge_bindings",
        ["collection_id", "repository_document_id"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_bindings_tenant_ws",
        "knowledge_bindings",
        ["tenant_id", "workspace_id"],
    )

    # 6. Create knowledge_index_revisions
    op.create_table(
        "knowledge_index_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("binding_id", sa.String(length=64), nullable=False),
        sa.Column("source_revision_id", sa.String(length=64), nullable=False),
        sa.Column("vector_generation_id", sa.String(length=64), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fact_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("point_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("parity_report", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="building", nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("lock_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["binding_id"], ["knowledge_bindings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_revision_id"], ["document_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vector_generation_id"], ["knowledge_vector_generations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_index_revisions_binding_id", "knowledge_index_revisions", ["binding_id"])
    op.create_index("ix_knowledge_index_revisions_source_revision_id", "knowledge_index_revisions", ["source_revision_id"])
    op.create_index("ix_knowledge_index_revisions_vector_generation_id", "knowledge_index_revisions", ["vector_generation_id"])
    op.create_index("ix_knowledge_index_revisions_status", "knowledge_index_revisions", ["status"])
    op.create_index(
        "ix_idx_rev_binding_rev_no",
        "knowledge_index_revisions",
        ["binding_id", "revision_no"],
        unique=True,
    )
    op.create_index("ix_idx_rev_status", "knowledge_index_revisions", ["status"])

    # 7. Add foreign key for knowledge_bindings.active_index_revision_id
    op.create_foreign_key(
        "fk_knowledge_bindings_active_index_revision",
        "knowledge_bindings",
        "knowledge_index_revisions",
        ["active_index_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 8. Create knowledge_index_activations
    op.create_table(
        "knowledge_index_activations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("binding_id", sa.String(length=64), nullable=False),
        sa.Column("from_index_revision_id", sa.String(length=64), nullable=True),
        sa.Column("to_index_revision_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), server_default="promote", nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("activated_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["binding_id"], ["knowledge_bindings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_index_activations_binding_id", "knowledge_index_activations", ["binding_id"])


def downgrade() -> None:
    # 8. Drop knowledge_index_activations
    op.drop_table("knowledge_index_activations")

    # 7. Drop foreign key constraint on knowledge_bindings
    op.drop_constraint("fk_knowledge_bindings_active_index_revision", "knowledge_bindings", type_="foreignkey")

    # 6. Drop knowledge_index_revisions
    op.drop_table("knowledge_index_revisions")

    # 5. Drop knowledge_bindings
    op.drop_table("knowledge_bindings")

    # 4. Drop knowledge_vector_generations
    op.drop_table("knowledge_vector_generations")

    # 3. Drop columns on knowledge_facts
    op.drop_index("ix_knowledge_facts_index_revision_id", table_name="knowledge_facts")
    op.drop_index("ix_knowledge_facts_binding_id", table_name="knowledge_facts")
    op.drop_column("knowledge_facts", "index_revision_id")
    op.drop_column("knowledge_facts", "binding_id")

    # 2. Drop columns on knowledge_chunks
    op.drop_index("ix_knowledge_chunks_index_revision_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_binding_id", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "index_revision_id")
    op.drop_column("knowledge_chunks", "binding_id")

    # 1. Drop columns on knowledge_collections
    op.drop_column("knowledge_collections", "index_epoch")
