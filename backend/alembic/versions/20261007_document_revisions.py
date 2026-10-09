"""Add document_revisions table and expand repository_documents.

Revision ID: 20261007_document_revisions
Revises: 20261007_document_repository
Create Date: 2026-10-07
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261007_document_revisions"
down_revision: str | Sequence[str] | None = "20261007_document_repository"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Expand repository_documents with tenant, workspace, status, revision pointer, row_version
    op.add_column(
        "repository_documents",
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="tenant_qnu"),
    )
    op.add_column(
        "repository_documents",
        sa.Column("workspace_id", sa.String(length=64), nullable=False, server_default="workspace_qnu"),
    )
    op.add_column(
        "repository_documents",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.add_column(
        "repository_documents",
        sa.Column("current_revision_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "repository_documents",
        sa.Column("latest_revision_no", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "repository_documents",
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "repository_documents",
        sa.Column("catalog_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.create_index("ix_repository_documents_tenant_ws", "repository_documents", ["tenant_id", "workspace_id"])
    op.create_index("ix_repository_documents_status", "repository_documents", ["status"])
    op.create_index("ix_repository_documents_current_rev_id", "repository_documents", ["current_revision_id"])

    # 2. Create document_revisions table
    op.create_table(
        "document_revisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("based_on_revision_id", sa.String(length=64), nullable=True),
        sa.Column("source_file_name", sa.String(length=255), nullable=False),
        sa.Column("source_file_type", sa.String(length=32), nullable=False),
        sa.Column("source_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("source_storage_path", sa.String(length=512), nullable=False),
        sa.Column("canonical_markdown", sa.Text(), nullable=True),
        sa.Column("canonical_hash", sa.String(length=64), nullable=True),
        sa.Column("page_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("citation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("parse_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("quality_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=True),
        sa.Column("lock_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["repository_documents.id"],
            name="fk_doc_revisions_document_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["based_on_revision_id"],
            ["document_revisions.id"],
            name="fk_doc_revisions_based_on",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_revisions"),
    )
    op.create_index("ix_doc_revisions_doc_rev_no", "document_revisions", ["document_id", "revision_no"], unique=True)
    op.create_index("ix_doc_revisions_doc_status", "document_revisions", ["document_id", "status"])
    op.create_index("ix_doc_revisions_source_hash", "document_revisions", ["source_hash"])
    op.create_index("ix_doc_revisions_canonical_hash", "document_revisions", ["canonical_hash"])
    op.create_index("ix_doc_revisions_idempotency", "document_revisions", ["idempotency_key"])

    # 3. Add Foreign Key from repository_documents.current_revision_id to document_revisions.id
    op.create_foreign_key(
        "fk_repository_docs_current_rev",
        "repository_documents",
        "document_revisions",
        ["current_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Safe Backfill (Tạo revision v1 từ repository_documents hiện có)
    conn = op.get_bind()
    repo_docs = conn.execute(
        sa.text(
            "SELECT id, file_name, file_type, file_size_bytes, file_hash, storage_path, "
            "parsed_markdown, parse_status, ocr_engine, doc_metadata, created_at, updated_at "
            "FROM repository_documents"
        )
    ).fetchall()

    for row in repo_docs:
        rev_id = f"rev_{row.id.replace('rep_doc_', '')[:12]}"
        if row.parse_status == "parsed" and row.parsed_markdown:
            rev_status = "ready"
        elif row.parse_status in ("pending", "queued"):
            rev_status = "queued"
        elif row.parse_status in ("parsing", "processing"):
            rev_status = "processing"
        else:
            rev_status = "failed"
        meta = row.doc_metadata if isinstance(row.doc_metadata, dict) else {}
        provenance = {
            "ocr_engine": row.ocr_engine or "native",
            "legacy_backfilled": True,
        }
        quality_report = {
            "overall_status": "passed" if rev_status == "ready" else "failed",
            "page_count": meta.get("page_count", 1),
            "table_count": meta.get("table_count", 0),
        }
        conn.execute(
            sa.text(
                "INSERT INTO document_revisions ("
                "id, document_id, revision_no, source_file_name, source_file_type, source_size_bytes, "
                "source_hash, source_storage_path, canonical_markdown, parse_provenance, quality_report, "
                "status, lock_version, created_at, updated_at"
                ") VALUES ("
                ":id, :doc_id, 1, :file_name, :file_type, :size_bytes, "
                ":file_hash, :storage_path, :markdown, :provenance, :quality_report, "
                ":status, 1, :created_at, :updated_at"
                ")"
            ),
            {
                "id": rev_id,
                "doc_id": row.id,
                "file_name": row.file_name,
                "file_type": row.file_type,
                "size_bytes": row.file_size_bytes,
                "file_hash": row.file_hash,
                "storage_path": row.storage_path,
                "markdown": row.parsed_markdown,
                "provenance": json.dumps(provenance),
                "quality_report": json.dumps(quality_report),
                "status": rev_status,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )
        if rev_status == "ready":
            conn.execute(
                sa.text(
                    "UPDATE repository_documents SET current_revision_id = :rev_id, "
                    "latest_revision_no = 1 WHERE id = :doc_id"
                ),
                {"rev_id": rev_id, "doc_id": row.id},
            )
        else:
            conn.execute(
                sa.text(
                    "UPDATE repository_documents SET latest_revision_no = 1 WHERE id = :doc_id"
                ),
                {"doc_id": row.id},
            )


def downgrade() -> None:
    # 1. Drop foreign key from repository_documents to document_revisions
    op.drop_constraint("fk_repository_docs_current_rev", "repository_documents", type_="foreignkey")

    # 2. Drop document_revisions table
    op.drop_index("ix_doc_revisions_idempotency", table_name="document_revisions")
    op.drop_index("ix_doc_revisions_canonical_hash", table_name="document_revisions")
    op.drop_index("ix_doc_revisions_source_hash", table_name="document_revisions")
    op.drop_index("ix_doc_revisions_doc_status", table_name="document_revisions")
    op.drop_index("ix_doc_revisions_doc_rev_no", table_name="document_revisions")
    op.drop_table("document_revisions")

    # 3. Drop expanded columns on repository_documents
    op.drop_index("ix_repository_documents_current_rev_id", table_name="repository_documents")
    op.drop_index("ix_repository_documents_status", table_name="repository_documents")
    op.drop_index("ix_repository_documents_tenant_ws", table_name="repository_documents")
    op.drop_column("repository_documents", "catalog_metadata")
    op.drop_column("repository_documents", "row_version")
    op.drop_column("repository_documents", "latest_revision_no")
    op.drop_column("repository_documents", "current_revision_id")
    op.drop_column("repository_documents", "status")
    op.drop_column("repository_documents", "workspace_id")
    op.drop_column("repository_documents", "tenant_id")
