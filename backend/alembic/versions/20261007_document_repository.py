"""Add repository_documents table and knowledge_documents link.

Revision ID: 20261007_document_repository
Revises: 20261002_remove_local_models
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261007_document_repository"
down_revision: str | Sequence[str] | None = "20261002_remove_local_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create repository_documents table
    op.create_table(
        "repository_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("document_type_code", sa.String(length=64), nullable=True),
        sa.Column("document_number", sa.String(length=128), nullable=True),
        sa.Column("issuing_authority", sa.String(length=255), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("parse_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("ocr_engine", sa.String(length=64), nullable=True),
        sa.Column("parsed_markdown", sa.Text(), nullable=True),
        sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["document_type_code"],
            ["platform_document_types.code"],
            name="fk_repository_docs_doc_type",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_repository_documents"),
    )
    op.create_index("ix_repository_documents_file_hash", "repository_documents", ["file_hash"], unique=True)
    op.create_index("ix_repository_documents_doc_type", "repository_documents", ["document_type_code"])
    op.create_index("ix_repository_documents_doc_number", "repository_documents", ["document_number"])
    op.create_index("ix_repository_documents_parse_status", "repository_documents", ["parse_status"])
    op.create_index("ix_repository_documents_is_active", "repository_documents", ["is_active"])

    # 2. Add repository_document_id to knowledge_documents
    op.add_column(
        "knowledge_documents",
        sa.Column("repository_document_id", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_knowledge_docs_repo_doc",
        "knowledge_documents",
        "repository_documents",
        ["repository_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_knowledge_documents_repo_doc_id",
        "knowledge_documents",
        ["repository_document_id"],
    )


def downgrade() -> None:
    # 1. Remove link from knowledge_documents
    op.drop_index("ix_knowledge_documents_repo_doc_id", table_name="knowledge_documents")
    op.drop_constraint("fk_knowledge_docs_repo_doc", "knowledge_documents", type_="foreignkey")
    op.drop_column("knowledge_documents", "repository_document_id")

    # 2. Drop repository_documents table
    op.drop_index("ix_repository_documents_is_active", table_name="repository_documents")
    op.drop_index("ix_repository_documents_parse_status", table_name="repository_documents")
    op.drop_index("ix_repository_documents_doc_number", table_name="repository_documents")
    op.drop_index("ix_repository_documents_doc_type", table_name="repository_documents")
    op.drop_index("ix_repository_documents_file_hash", table_name="repository_documents")
    op.drop_table("repository_documents")
