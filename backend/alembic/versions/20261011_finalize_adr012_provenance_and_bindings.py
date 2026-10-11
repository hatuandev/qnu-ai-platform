"""Finalize ADR-012 provenance and decouple bindings from cascade delete.

Revision ID: 20261011_finalize_adr012_provenance_and_bindings
Revises: 20261010_decouple_storage_and_knowledge_v3
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "20261011_finalize_adr012_provenance_and_bindings"
down_revision: str | Sequence[str] | None = "20261010_decouple_storage_and_knowledge_v3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1. Update knowledge_bindings
    if inspector.has_table("knowledge_bindings"):
        # Drop legacy FK constraint on source_revision_id if present
        fks = inspector.get_foreign_keys("knowledge_bindings")
        for fk in fks:
            fk_name = fk.get("name")
            constrained_cols = fk.get("constrained_columns", [])
            referred_table = fk.get("referred_table")

            # Drop FK pointing to document_revisions
            if fk_name and ("source_revision_id" in constrained_cols or referred_table == "document_revisions"):
                op.drop_constraint(fk_name, "knowledge_bindings", type_="foreignkey")

            # Drop old CASCADE FK pointing to repository_documents to replace with SET NULL
            if fk_name and "repository_document_id" in constrained_cols and referred_table == "repository_documents":
                op.drop_constraint(fk_name, "knowledge_bindings", type_="foreignkey")

        # Make source_revision_id and repository_document_id nullable
        op.alter_column(
            "knowledge_bindings",
            "source_revision_id",
            existing_type=sa.String(64),
            nullable=True,
        )
        op.alter_column(
            "knowledge_bindings",
            "repository_document_id",
            existing_type=sa.String(64),
            nullable=True,
        )

        # Re-add foreign key for repository_document_id with ON DELETE SET NULL
        op.create_foreign_key(
            "fk_knowledge_bindings_repo_doc_set_null",
            "knowledge_bindings",
            "repository_documents",
            ["repository_document_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 2. Update knowledge_chunks: make document_id nullable for V3 independent chunks
    if inspector.has_table("knowledge_chunks"):
        chunk_cols = {c["name"]: c for c in inspector.get_columns("knowledge_chunks")}
        if "document_id" in chunk_cols and not chunk_cols["document_id"]["nullable"]:
            op.alter_column(
                "knowledge_chunks",
                "document_id",
                existing_type=sa.String(64),
                nullable=True,
            )

    # 3. Update knowledge_facts: make document_id nullable for V3 independent facts
    if inspector.has_table("knowledge_facts"):
        fact_cols = {c["name"]: c for c in inspector.get_columns("knowledge_facts")}
        if "document_id" in fact_cols and not fact_cols["document_id"]["nullable"]:
            op.alter_column(
                "knowledge_facts",
                "document_id",
                existing_type=sa.String(64),
                nullable=True,
            )


def downgrade() -> None:
    pass
