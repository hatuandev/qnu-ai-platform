"""Change file_hash unique constraint to composite (tenant_id, workspace_id, file_hash).

Revision ID: 20261010_composite_file_hash_deduplication
Revises: 20261009_document_groups
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import inspect, text

from alembic import op

revision: str = "20261010_composite_file_hash_deduplication"
down_revision: str | Sequence[str] | None = "20261009_document_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("repository_documents")}

    # 1. Drop the legacy global unique index on file_hash if it exists
    if "ix_repository_documents_file_hash" in existing_indexes:
        op.drop_index("ix_repository_documents_file_hash", table_name="repository_documents")
    elif bind.dialect.name == "postgresql":
        op.execute(text("DROP INDEX IF EXISTS ix_repository_documents_file_hash;"))

    # 2. Re-create non-unique index on file_hash for fast single-column lookups
    updated_indexes = {idx["name"] for idx in inspect(bind).get_indexes("repository_documents")}
    if "ix_repository_documents_file_hash" not in updated_indexes:
        op.create_index(
            "ix_repository_documents_file_hash",
            "repository_documents",
            ["file_hash"],
            unique=False,
        )

    # 3. Create composite unique index scoped by tenant and workspace
    if "uq_repo_docs_tenant_ws_file_hash" not in updated_indexes:
        op.create_index(
            "uq_repo_docs_tenant_ws_file_hash",
            "repository_documents",
            ["tenant_id", "workspace_id", "file_hash"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    # Check if existing data violates global unique constraint on file_hash
    dup_rows = bind.execute(
        text("SELECT file_hash, count(*) FROM repository_documents GROUP BY file_hash HAVING count(*) > 1")
    ).fetchall()
    if dup_rows:
        dup_hashes = [str(row[0]) for row in dup_rows]
        raise RuntimeError(
            f"Không thể hạ cấp migration: Phát hiện {len(dup_rows)} file_hash trùng lặp giữa các tenant/workspace "
            f"({dup_hashes[:5]}). Việc tái tạo unique index toàn cục trên file_hash sẽ vi phạm tính duy nhất."
        )

    inspector = inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("repository_documents")}

    if "uq_repo_docs_tenant_ws_file_hash" in existing_indexes:
        op.drop_index("uq_repo_docs_tenant_ws_file_hash", table_name="repository_documents")

    if "ix_repository_documents_file_hash" in existing_indexes:
        op.drop_index("ix_repository_documents_file_hash", table_name="repository_documents")

    op.create_index(
        "ix_repository_documents_file_hash",
        "repository_documents",
        ["file_hash"],
        unique=True,
    )
