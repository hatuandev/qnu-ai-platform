"""Add persisted workflow drafts, immutable versions, and approval checkpoints."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260918_workflow_control_plane"
down_revision = "20260917_document_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workflow control-plane tables and extend execution audit records safely."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "workflow_definitions" in table_names:
        definition_columns = {
            column["name"] for column in inspector.get_columns("workflow_definitions")
        }
        if "published_version_id" not in definition_columns:
            op.add_column(
                "workflow_definitions",
                sa.Column("published_version_id", sa.String(length=36), nullable=True),
            )

    if "workflow_executions" in table_names:
        execution_columns = {
            column["name"] for column in inspector.get_columns("workflow_executions")
        }
        for column_name, column in (
            ("workflow_version_id", sa.Column("workflow_version_id", sa.String(length=36))),
            ("assistant_id", sa.Column("assistant_id", sa.String(length=36))),
            ("assistant_revision", sa.Column("assistant_revision", sa.String(length=64))),
            ("correlation_id", sa.Column("correlation_id", sa.String(length=128))),
            ("runtime_profile", sa.Column("runtime_profile", postgresql.JSONB())),
        ):
            if column_name not in execution_columns:
                op.add_column("workflow_executions", column)
        execution_indexes = {
            index["name"] for index in inspector.get_indexes("workflow_executions")
        }
        for index_name, column_name in (
            ("ix_workflow_executions_workflow_version_id", "workflow_version_id"),
            ("ix_workflow_executions_assistant_id", "assistant_id"),
            ("ix_workflow_executions_correlation_id", "correlation_id"),
        ):
            if index_name not in execution_indexes:
                op.create_index(index_name, "workflow_executions", [column_name])

    if "workflow_drafts" not in table_names:
        op.create_table(
            "workflow_drafts",
            sa.Column("workflow_id", sa.String(length=64), nullable=False),
            sa.Column("dag_spec", postgresql.JSONB(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("updated_by", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("workflow_id"),
        )

    if "workflow_versions" not in table_names:
        op.create_table(
            "workflow_versions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workflow_id", sa.String(length=64), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("dag_spec", postgresql.JSONB(), nullable=False),
            sa.Column("validation_report", postgresql.JSONB(), nullable=False),
            sa.Column("published_by", sa.String(length=128), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workflow_id", "version_number", name="uq_workflow_version_number"),
        )
        op.create_index("ix_workflow_versions_workflow_id", "workflow_versions", ["workflow_id"])

    if "workflow_checkpoints" not in table_names:
        op.create_table(
            "workflow_checkpoints",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("execution_id", sa.String(length=36), nullable=False),
            sa.Column("resume_node_id", sa.String(length=100), nullable=False),
            sa.Column("completed_node_ids", postgresql.JSONB(), nullable=False),
            sa.Column("node_data", postgresql.JSONB(), nullable=False),
            sa.Column("outputs", postgresql.JSONB(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("resumed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_workflow_checkpoints_execution_id", "workflow_checkpoints", ["execution_id"])
        op.create_index("ix_workflow_checkpoints_status", "workflow_checkpoints", ["status"])

    if "workflow_approval_requests" not in table_names:
        op.create_table(
            "workflow_approval_requests",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("execution_id", sa.String(length=36), nullable=False),
            sa.Column("checkpoint_id", sa.String(length=36), nullable=False),
            sa.Column("node_id", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("decided_by", sa.String(length=128), nullable=True),
            sa.Column("decision_reason", sa.String(length=1000), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_workflow_approval_requests_execution_id",
            "workflow_approval_requests",
            ["execution_id"],
        )
        op.create_index(
            "ix_workflow_approval_requests_checkpoint_id",
            "workflow_approval_requests",
            ["checkpoint_id"],
        )
        op.create_index(
            "ix_workflow_approval_requests_status",
            "workflow_approval_requests",
            ["status"],
        )


def downgrade() -> None:
    """Remove workflow control-plane storage in reverse dependency order."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "workflow_approval_requests" in table_names:
        op.drop_table("workflow_approval_requests")
    if "workflow_checkpoints" in table_names:
        op.drop_table("workflow_checkpoints")
    if "workflow_versions" in table_names:
        op.drop_table("workflow_versions")
    if "workflow_drafts" in table_names:
        op.drop_table("workflow_drafts")

    if "workflow_executions" in table_names:
        execution_columns = {
            column["name"] for column in inspector.get_columns("workflow_executions")
        }
        execution_indexes = {
            index["name"] for index in inspector.get_indexes("workflow_executions")
        }
        for index_name in (
            "ix_workflow_executions_workflow_version_id",
            "ix_workflow_executions_assistant_id",
            "ix_workflow_executions_correlation_id",
        ):
            if index_name in execution_indexes:
                op.drop_index(index_name, table_name="workflow_executions")
        for column_name in (
            "runtime_profile",
            "correlation_id",
            "assistant_revision",
            "assistant_id",
            "workflow_version_id",
        ):
            if column_name in execution_columns:
                op.drop_column("workflow_executions", column_name)

    if "workflow_definitions" in table_names:
        definition_columns = {
            column["name"] for column in inspector.get_columns("workflow_definitions")
        }
        if "published_version_id" in definition_columns:
            op.drop_column("workflow_definitions", "published_version_id")
