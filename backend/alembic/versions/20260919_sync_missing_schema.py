"""Sync missing schema columns and indexes for knowledge, assistants, workflows, and evaluation.

Revision ID: 20260919_sync_missing_schema
Revises: 20260919_evaluation_items_and_method_sync
Create Date: 2026-09-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260919_sync_missing_schema"
down_revision = "20260919_evaluation_items_and_method_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    # 1. Knowledge Documents: index_status & index_error
    if "knowledge_documents" in table_names:
        cols = {c["name"] for c in inspector.get_columns("knowledge_documents")}
        indexes = {i["name"] for i in inspector.get_indexes("knowledge_documents")}

        if "index_status" not in cols:
            op.add_column(
                "knowledge_documents",
                sa.Column("index_status", sa.String(32), server_default="pending", nullable=False),
            )
        if "index_error" not in cols:
            op.add_column(
                "knowledge_documents",
                sa.Column("index_error", sa.Text(), nullable=True),
            )
        if "ix_knowledge_documents_index_status" not in indexes:
            op.create_index(
                "ix_knowledge_documents_index_status",
                "knowledge_documents",
                ["index_status"],
            )

    # 2. Assistants: published_workflow_version_id & workflow_ownership
    if "assistants" in table_names:
        cols = {c["name"] for c in inspector.get_columns("assistants")}
        indexes = {i["name"] for i in inspector.get_indexes("assistants")}

        if "published_workflow_version_id" not in cols:
            op.add_column(
                "assistants",
                sa.Column("published_workflow_version_id", sa.String(36), nullable=True),
            )
        if "workflow_ownership" not in cols:
            op.add_column(
                "assistants",
                sa.Column("workflow_ownership", sa.String(20), server_default="private", nullable=False),
            )
        if "ix_assistants_workflow_ownership" not in indexes:
            op.create_index(
                "ix_assistants_workflow_ownership",
                "assistants",
                ["workflow_ownership"],
            )

    # 3. Workflow Definitions: ownership & assistant_id
    if "workflow_definitions" in table_names:
        cols = {c["name"] for c in inspector.get_columns("workflow_definitions")}
        indexes = {i["name"] for i in inspector.get_indexes("workflow_definitions")}

        if "ownership" not in cols:
            op.add_column(
                "workflow_definitions",
                sa.Column("ownership", sa.String(20), server_default="shared", nullable=False),
            )
        if "assistant_id" not in cols:
            op.add_column(
                "workflow_definitions",
                sa.Column("assistant_id", sa.String(36), nullable=True),
            )
        if "ix_workflow_definitions_assistant_id" not in indexes:
            op.create_index(
                "ix_workflow_definitions_assistant_id",
                "workflow_definitions",
                ["assistant_id"],
            )
        if "ix_workflow_definitions_ownership" not in indexes:
            op.create_index(
                "ix_workflow_definitions_ownership",
                "workflow_definitions",
                ["ownership"],
            )

    # 4. Evaluation nullable alignment
    if "evaluation_result_items" in table_names:
        op.alter_column(
            "evaluation_result_items",
            "is_refusal",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        )
        op.alter_column(
            "evaluation_result_items",
            "execution_path",
            existing_type=sa.String(50),
            nullable=False,
            server_default="direct_llm",
        )

    if "evaluation_runs" in table_names:
        op.alter_column(
            "evaluation_runs",
            "evaluation_method",
            existing_type=sa.String(30),
            nullable=False,
            server_default="synthetic_ragas",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "workflow_definitions" in table_names:
        indexes = {i["name"] for i in inspector.get_indexes("workflow_definitions")}
        cols = {c["name"] for c in inspector.get_columns("workflow_definitions")}
        if "ix_workflow_definitions_ownership" in indexes:
            op.drop_index("ix_workflow_definitions_ownership", table_name="workflow_definitions")
        if "ix_workflow_definitions_assistant_id" in indexes:
            op.drop_index("ix_workflow_definitions_assistant_id", table_name="workflow_definitions")
        if "assistant_id" in cols:
            op.drop_column("workflow_definitions", "assistant_id")
        if "ownership" in cols:
            op.drop_column("workflow_definitions", "ownership")

    if "assistants" in table_names:
        indexes = {i["name"] for i in inspector.get_indexes("assistants")}
        cols = {c["name"] for c in inspector.get_columns("assistants")}
        if "ix_assistants_workflow_ownership" in indexes:
            op.drop_index("ix_assistants_workflow_ownership", table_name="assistants")
        if "workflow_ownership" in cols:
            op.drop_column("assistants", "workflow_ownership")
        if "published_workflow_version_id" in cols:
            op.drop_column("assistants", "published_workflow_version_id")

    if "knowledge_documents" in table_names:
        indexes = {i["name"] for i in inspector.get_indexes("knowledge_documents")}
        cols = {c["name"] for c in inspector.get_columns("knowledge_documents")}
        if "ix_knowledge_documents_index_status" in indexes:
            op.drop_index("ix_knowledge_documents_index_status", table_name="knowledge_documents")
        if "index_error" in cols:
            op.drop_column("knowledge_documents", "index_error")
        if "index_status" in cols:
            op.drop_column("knowledge_documents", "index_status")
