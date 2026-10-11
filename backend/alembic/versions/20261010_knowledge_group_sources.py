"""Add knowledge_group_sources table and link to knowledge_bindings.

Revision ID: 20261010_knowledge_group_sources
Revises: 20261010_composite_file_hash_deduplication
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "20261010_knowledge_group_sources"
down_revision: str | Sequence[str] | None = "20261010_composite_file_hash_deduplication"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1. Create knowledge_group_sources table if not exists
    if not inspector.has_table("knowledge_group_sources"):
        op.create_table(
            "knowledge_group_sources",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "collection_id",
                sa.String(64),
                sa.ForeignKey("knowledge_collections.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "document_group_id",
                sa.String(64),
                sa.ForeignKey("document_groups.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("sync_policy", sa.String(32), server_default="manual", nullable=False),
            sa.Column("chunk_strategy", sa.String(64), server_default="ClauseBasedChunker", nullable=False),
            sa.Column("status", sa.String(32), server_default="empty", nullable=False),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_membership_hash", sa.String(64), nullable=True),
            sa.Column("tenant_id", sa.String(64), server_default="tenant_qnu", nullable=False),
            sa.Column("workspace_id", sa.String(64), server_default="workspace_qnu", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

        op.create_index(
            "ix_knowledge_group_sources_col_group",
            "knowledge_group_sources",
            ["collection_id", "document_group_id"],
            unique=True,
        )
        op.create_index(
            "ix_knowledge_group_sources_status",
            "knowledge_group_sources",
            ["status"],
            unique=False,
        )
        op.create_index(
            "ix_knowledge_group_sources_tenant_ws",
            "knowledge_group_sources",
            ["tenant_id", "workspace_id"],
            unique=False,
        )

    # 2. Add group_source_id column to knowledge_bindings if not exists
    if inspector.has_table("knowledge_bindings"):
        binding_cols = {col["name"] for col in inspector.get_columns("knowledge_bindings")}
        if "group_source_id" not in binding_cols:
            op.add_column(
                "knowledge_bindings",
                sa.Column(
                    "group_source_id",
                    sa.String(64),
                    sa.ForeignKey("knowledge_group_sources.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
            op.create_index(
                "ix_knowledge_bindings_group_source",
                "knowledge_bindings",
                ["group_source_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("knowledge_bindings"):
        binding_cols = {col["name"] for col in inspector.get_columns("knowledge_bindings")}
        if "group_source_id" in binding_cols:
            op.drop_index("ix_knowledge_bindings_group_source", table_name="knowledge_bindings")
            op.drop_column("knowledge_bindings", "group_source_id")

    if inspector.has_table("knowledge_group_sources"):
        op.drop_index("ix_knowledge_group_sources_tenant_ws", table_name="knowledge_group_sources")
        op.drop_index("ix_knowledge_group_sources_status", table_name="knowledge_group_sources")
        op.drop_index("ix_knowledge_group_sources_col_group", table_name="knowledge_group_sources")
        op.drop_table("knowledge_group_sources")
