"""Add DocumentGroup and DocumentGroupMembership tables.

Revision ID: 20261009_document_groups
Revises: 20261008_publishing_v2_hardening
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261009_document_groups"
down_revision: str | Sequence[str] | None = "20261008_publishing_v2_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_groups",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="tenant_qnu"),
        sa.Column("workspace_id", sa.String(length=64), nullable=False, server_default="workspace_qnu"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "uq_doc_groups_tenant_ws_lower_name",
        "document_groups",
        ["tenant_id", "workspace_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_doc_groups_tenant_ws",
        "document_groups",
        ["tenant_id", "workspace_id"],
    )

    op.create_table(
        "document_group_memberships",
        sa.Column(
            "group_id",
            sa.String(length=64),
            sa.ForeignKey("document_groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            sa.String(length=64),
            sa.ForeignKey("repository_documents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("added_by", sa.String(length=64), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_doc_group_memberships_doc_id",
        "document_group_memberships",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_table("document_group_memberships")
    op.drop_table("document_groups")
