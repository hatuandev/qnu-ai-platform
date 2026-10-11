"""Decouple storage repository and knowledge document intelligence (ADR-012).

Revision ID: 20261010_decouple_storage_and_knowledge_v3
Revises: 20261010_knowledge_group_sources
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20261010_decouple_storage_and_knowledge_v3"
down_revision: str | Sequence[str] | None = "20261010_knowledge_group_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1. Create repository_file_revisions table
    if not inspector.has_table("repository_file_revisions"):
        op.create_table(
            "repository_file_revisions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "document_id",
                sa.String(64),
                sa.ForeignKey("repository_documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("revision_no", sa.Integer(), nullable=False),
            sa.Column("source_file_name", sa.String(255), nullable=False),
            sa.Column("source_file_type", sa.String(32), nullable=False),
            sa.Column("source_size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_hash", sa.String(64), nullable=False),
            sa.Column("source_storage_path", sa.String(512), nullable=False),
            sa.Column("created_by", sa.String(64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "uq_repo_file_revs_doc_rev_no",
            "repository_file_revisions",
            ["document_id", "revision_no"],
            unique=True,
        )
        op.create_index(
            "ix_repo_file_revs_source_hash",
            "repository_file_revisions",
            ["source_hash"],
        )
        op.create_index(
            "ix_repo_file_revs_doc_id",
            "repository_file_revisions",
            ["document_id"],
        )

    # 2. Create knowledge_source_revisions table
    if not inspector.has_table("knowledge_source_revisions"):
        op.create_table(
            "knowledge_source_revisions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "binding_id",
                sa.String(64),
                sa.ForeignKey("knowledge_bindings.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("revision_no", sa.Integer(), nullable=False),
            sa.Column("origin_document_id", sa.String(64), nullable=False),
            sa.Column("origin_file_hash", sa.String(64), nullable=False),
            sa.Column("snapshot_storage_path", sa.String(512), nullable=False),
            sa.Column("snapshot_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("canonical_markdown", sa.Text(), nullable=True),
            sa.Column("canonical_hash", sa.String(64), nullable=True),
            sa.Column("page_manifest", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("citation_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("parse_provenance", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("quality_report", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("parser_profile_hash", sa.String(64), nullable=True),
            sa.Column("normalizer_version", sa.String(32), nullable=False, server_default="v1"),
            sa.Column("artifact_key", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
            sa.Column("failure_code", sa.String(64), nullable=True),
            sa.Column("failure_detail", sa.Text(), nullable=True),
            sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "uq_knowledge_source_rev_binding_rev_no",
            "knowledge_source_revisions",
            ["binding_id", "revision_no"],
            unique=True,
        )
        op.create_index(
            "ix_knowledge_source_rev_status",
            "knowledge_source_revisions",
            ["status"],
        )
        op.create_index(
            "ix_knowledge_source_rev_origin_doc",
            "knowledge_source_revisions",
            ["origin_document_id"],
        )
        op.create_index(
            "ix_knowledge_source_rev_artifact_key",
            "knowledge_source_revisions",
            ["artifact_key"],
        )
        op.create_index(
            "ix_knowledge_source_rev_canonical_hash",
            "knowledge_source_revisions",
            ["canonical_hash"],
        )

    # 3. Create knowledge_chunk_sets table
    if not inspector.has_table("knowledge_chunk_sets"):
        op.create_table(
            "knowledge_chunk_sets",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "source_revision_id",
                sa.String(64),
                sa.ForeignKey("knowledge_source_revisions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("chunk_strategy", sa.String(64), nullable=False, server_default="ClauseBasedChunker"),
            sa.Column("chunk_config", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("config_hash", sa.String(64), nullable=False),
            sa.Column("chunk_set_key", sa.String(64), nullable=True),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fact_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("manifest_hash", sa.String(64), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="building"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "uq_knowledge_chunk_set_rev_config",
            "knowledge_chunk_sets",
            ["source_revision_id", "config_hash"],
            unique=True,
        )
        op.create_index(
            "ix_knowledge_chunk_set_key",
            "knowledge_chunk_sets",
            ["chunk_set_key"],
        )
        op.create_index(
            "ix_knowledge_chunk_set_status",
            "knowledge_chunk_sets",
            ["status"],
        )
        op.create_index(
            "ix_knowledge_chunk_set_config_hash",
            "knowledge_chunk_sets",
            ["config_hash"],
        )

    # 4. Create knowledge_import_batches table
    if not inspector.has_table("knowledge_import_batches"):
        op.create_table(
            "knowledge_import_batches",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "collection_id",
                sa.String(64),
                sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("tenant_id", sa.String(64), nullable=False, server_default="tenant_qnu"),
            sa.Column("workspace_id", sa.String(64), nullable=False, server_default="workspace_qnu"),
            sa.Column(
                "vector_generation_id",
                sa.String(64),
                sa.ForeignKey("knowledge_vector_generations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("parser_profile", sa.String(64), nullable=False, server_default="standard"),
            sa.Column("chunk_strategy", sa.String(64), nullable=False, server_default="ClauseBasedChunker"),
            sa.Column("chunk_config", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("config_hash", sa.String(64), nullable=True),
            sa.Column("idempotency_key", sa.String(128), nullable=True),
            sa.Column("request_hash", sa.String(64), nullable=True),
            sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("queued_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("processing_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("review_required_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("succeeded_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_knowledge_import_batches_tenant_ws",
            "knowledge_import_batches",
            ["tenant_id", "workspace_id"],
        )
        op.create_index(
            "ix_knowledge_import_batches_status",
            "knowledge_import_batches",
            ["status"],
        )
        op.create_index(
            "ix_knowledge_import_batches_idem",
            "knowledge_import_batches",
            ["collection_id", "idempotency_key"],
        )
        op.create_index(
            "ix_knowledge_import_batches_col_id",
            "knowledge_import_batches",
            ["collection_id"],
        )

    # 5. Create knowledge_import_items table
    if not inspector.has_table("knowledge_import_items"):
        op.create_table(
            "knowledge_import_items",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "batch_id",
                sa.String(64),
                sa.ForeignKey("knowledge_import_batches.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("origin_document_id", sa.String(64), nullable=False),
            sa.Column("origin_group_id", sa.String(64), nullable=True),
            sa.Column("origin_file_revision_id", sa.String(64), nullable=True),
            sa.Column("origin_file_hash", sa.String(64), nullable=False),
            sa.Column("origin_title", sa.String(255), nullable=False),
            sa.Column("origin_file_name", sa.String(255), nullable=False),
            sa.Column("origin_file_type", sa.String(32), nullable=False),
            sa.Column("origin_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("knowledge_binding_id", sa.String(64), nullable=True),
            sa.Column("knowledge_source_revision_id", sa.String(64), nullable=True),
            sa.Column("index_revision_id", sa.String(64), nullable=True),
            sa.Column("phase", sa.String(32), nullable=False, server_default="snapshot"),
            sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
            sa.Column("failure_code", sa.String(64), nullable=True),
            sa.Column("failure_detail", sa.Text(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "uq_knowledge_import_item_batch_doc",
            "knowledge_import_items",
            ["batch_id", "origin_document_id"],
            unique=True,
        )
        op.create_index(
            "ix_knowledge_import_item_status",
            "knowledge_import_items",
            ["status"],
        )
        op.create_index(
            "ix_knowledge_import_item_origin_doc",
            "knowledge_import_items",
            ["origin_document_id"],
        )
        op.create_index(
            "ix_knowledge_import_item_batch_id",
            "knowledge_import_items",
            ["batch_id"],
        )

    # 6. Extend knowledge_bindings table
    if inspector.has_table("knowledge_bindings"):
        binding_cols = {c["name"] for c in inspector.get_columns("knowledge_bindings")}
        if "active_source_revision_id" not in binding_cols:
            op.add_column(
                "knowledge_bindings",
                sa.Column("active_source_revision_id", sa.String(64), nullable=True),
            )
            op.create_foreign_key(
                "fk_knowledge_bindings_active_src_rev",
                "knowledge_bindings",
                "knowledge_source_revisions",
                ["active_source_revision_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_index(
                "ix_knowledge_bindings_active_src_rev",
                "knowledge_bindings",
                ["active_source_revision_id"],
            )

    # 7. Extend knowledge_index_revisions table
    if inspector.has_table("knowledge_index_revisions"):
        idx_rev_cols = {c["name"] for c in inspector.get_columns("knowledge_index_revisions")}
        if "source_revision_v2_id" not in idx_rev_cols:
            op.add_column(
                "knowledge_index_revisions",
                sa.Column("source_revision_v2_id", sa.String(64), nullable=True),
            )
            op.create_foreign_key(
                "fk_knowledge_index_revisions_src_rev_v2",
                "knowledge_index_revisions",
                "knowledge_source_revisions",
                ["source_revision_v2_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_index(
                "ix_knowledge_index_revisions_src_rev_v2",
                "knowledge_index_revisions",
                ["source_revision_v2_id"],
            )

        if "chunk_set_id" not in idx_rev_cols:
            op.add_column(
                "knowledge_index_revisions",
                sa.Column("chunk_set_id", sa.String(64), nullable=True),
            )
            op.create_foreign_key(
                "fk_knowledge_index_revisions_chunk_set",
                "knowledge_index_revisions",
                "knowledge_chunk_sets",
                ["chunk_set_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_index(
                "ix_knowledge_index_revisions_chunk_set",
                "knowledge_index_revisions",
                ["chunk_set_id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1. Revert index revisions extensions
    if inspector.has_table("knowledge_index_revisions"):
        idx_rev_cols = {c["name"] for c in inspector.get_columns("knowledge_index_revisions")}
        if "chunk_set_id" in idx_rev_cols:
            op.drop_constraint("fk_knowledge_index_revisions_chunk_set", "knowledge_index_revisions", type_="foreignkey")
            op.drop_index("ix_knowledge_index_revisions_chunk_set", "knowledge_index_revisions")
            op.drop_column("knowledge_index_revisions", "chunk_set_id")
        if "source_revision_v2_id" in idx_rev_cols:
            op.drop_constraint("fk_knowledge_index_revisions_src_rev_v2", "knowledge_index_revisions", type_="foreignkey")
            op.drop_index("ix_knowledge_index_revisions_src_rev_v2", "knowledge_index_revisions")
            op.drop_column("knowledge_index_revisions", "source_revision_v2_id")

    # 2. Revert bindings extensions
    if inspector.has_table("knowledge_bindings"):
        binding_cols = {c["name"] for c in inspector.get_columns("knowledge_bindings")}
        if "active_source_revision_id" in binding_cols:
            op.drop_constraint("fk_knowledge_bindings_active_src_rev", "knowledge_bindings", type_="foreignkey")
            op.drop_index("ix_knowledge_bindings_active_src_rev", "knowledge_bindings")
            op.drop_column("knowledge_bindings", "active_source_revision_id")

    # 3. Drop import items and batches
    if inspector.has_table("knowledge_import_items"):
        op.drop_table("knowledge_import_items")
    if inspector.has_table("knowledge_import_batches"):
        op.drop_table("knowledge_import_batches")

    # 4. Drop chunk sets and source revisions
    if inspector.has_table("knowledge_chunk_sets"):
        op.drop_table("knowledge_chunk_sets")
    if inspector.has_table("knowledge_source_revisions"):
        op.drop_table("knowledge_source_revisions")

    # 5. Drop repository_file_revisions
    if inspector.has_table("repository_file_revisions"):
        op.drop_table("repository_file_revisions")
