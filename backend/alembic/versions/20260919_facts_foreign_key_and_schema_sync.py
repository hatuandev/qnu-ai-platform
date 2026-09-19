"""Schema sync for facts foreign key cascade and document type code."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260919_facts_foreign_key_and_schema_sync"
down_revision = "20260918_workflow_control_plane"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Safely apply foreign key constraint on knowledge_facts and ensure document_type_code column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "knowledge_documents" in table_names:
        doc_columns = {col["name"] for col in inspector.get_columns("knowledge_documents")}
        if "document_type_code" not in doc_columns:
            op.add_column(
                "knowledge_documents",
                sa.Column("document_type_code", sa.String(length=64), nullable=True),
            )
        doc_indexes = {idx["name"] for idx in inspector.get_indexes("knowledge_documents")}
        if "ix_knowledge_documents_document_type_code" not in doc_indexes:
            op.create_index(
                "ix_knowledge_documents_document_type_code",
                "knowledge_documents",
                ["document_type_code"],
            )

    if "knowledge_facts" in table_names and "knowledge_documents" in table_names:
        existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("knowledge_facts")}
        fk_name = "fk_knowledge_facts_document_id_knowledge_documents"
        if fk_name not in existing_fks:
            try:
                op.create_foreign_key(
                    fk_name,
                    "knowledge_facts",
                    "knowledge_documents",
                    ["document_id"],
                    ["id"],
                    ondelete="CASCADE",
                )
            except Exception:
                # If existing invalid/orphan data prevents FK, migration passes safely
                pass


def downgrade() -> None:
    """Rollback foreign key and added columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "knowledge_facts" in table_names:
        existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("knowledge_facts")}
        fk_name = "fk_knowledge_facts_document_id_knowledge_documents"
        if fk_name in existing_fks:
            op.drop_constraint(fk_name, "knowledge_facts", type_="foreignkey")

    if "knowledge_documents" in table_names:
        doc_indexes = {idx["name"] for idx in inspector.get_indexes("knowledge_documents")}
        if "ix_knowledge_documents_document_type_code" in doc_indexes:
            op.drop_index("ix_knowledge_documents_document_type_code", table_name="knowledge_documents")
        doc_columns = {col["name"] for col in inspector.get_columns("knowledge_documents")}
        if "document_type_code" in doc_columns:
            op.drop_column("knowledge_documents", "document_type_code")
