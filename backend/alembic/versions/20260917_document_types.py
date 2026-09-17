"""Add the canonical document taxonomy and document type foreign key."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260917_document_types"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create taxonomy storage and extend knowledge documents when present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "platform_document_types" not in table_names:
        op.create_table(
            "platform_document_types",
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("retention_period", sa.String(length=64), nullable=True),
            sa.Column("nd30", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "is_system_default", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "source_system",
                sa.String(length=64),
                nullable=False,
                server_default="qnu-ai-core",
            ),
            sa.Column("source_version", sa.String(length=128), nullable=True),
            sa.Column("source_hash", sa.String(length=64), nullable=True),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("code"),
        )
        op.create_index(
            "ix_platform_document_types_category",
            "platform_document_types",
            ["category"],
        )
        op.create_index("ix_platform_document_types_nd30", "platform_document_types", ["nd30"])
        op.create_index(
            "ix_platform_document_types_is_active", "platform_document_types", ["is_active"]
        )

    if "knowledge_documents" in table_names:
        knowledge_columns = {column["name"] for column in inspector.get_columns("knowledge_documents")}
        if "document_type_code" not in knowledge_columns:
            op.add_column(
                "knowledge_documents",
                sa.Column(
                    "document_type_code",
                    sa.String(length=64),
                    nullable=True,
                ),
            )
        knowledge_indexes = {index["name"] for index in inspector.get_indexes("knowledge_documents")}
        if "ix_knowledge_documents_document_type_code" not in knowledge_indexes:
            op.create_index(
                "ix_knowledge_documents_document_type_code",
                "knowledge_documents",
                ["document_type_code"],
            )
        knowledge_foreign_keys = {
            foreign_key["name"] for foreign_key in inspector.get_foreign_keys("knowledge_documents")
        }
        if "knowledge_documents_document_type_code_fkey" not in knowledge_foreign_keys:
            op.create_foreign_key(
                "knowledge_documents_document_type_code_fkey",
                "knowledge_documents",
                "platform_document_types",
                ["document_type_code"],
                ["code"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    """Remove the taxonomy extension while preserving knowledge documents."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "knowledge_documents" in table_names:
        knowledge_columns = {column["name"] for column in inspector.get_columns("knowledge_documents")}
        if "document_type_code" in knowledge_columns:
            knowledge_foreign_keys = {
                foreign_key["name"]
                for foreign_key in inspector.get_foreign_keys("knowledge_documents")
            }
            if "knowledge_documents_document_type_code_fkey" in knowledge_foreign_keys:
                op.drop_constraint(
                    "knowledge_documents_document_type_code_fkey",
                    "knowledge_documents",
                    type_="foreignkey",
                )
            op.drop_index(
                "ix_knowledge_documents_document_type_code", table_name="knowledge_documents"
            )
            op.drop_column("knowledge_documents", "document_type_code")
    if "platform_document_types" in table_names:
        op.drop_index("ix_platform_document_types_is_active", table_name="platform_document_types")
        op.drop_index("ix_platform_document_types_nd30", table_name="platform_document_types")
        op.drop_index("ix_platform_document_types_category", table_name="platform_document_types")
        op.drop_table("platform_document_types")
