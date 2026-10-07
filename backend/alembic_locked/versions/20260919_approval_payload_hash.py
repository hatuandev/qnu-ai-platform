"""Add tool_name, payload_hash, requested_by, and expires_at to workflow_approval_requests.

Revision ID: 20260919_approval_payload_hash
Revises: 20260919_sync_missing_schema
Create Date: 2026-09-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260919_approval_payload_hash"
down_revision = "20260919_sync_missing_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "workflow_approval_requests" in table_names:
        cols = {c["name"] for c in inspector.get_columns("workflow_approval_requests")}
        indexes = {i["name"] for i in inspector.get_indexes("workflow_approval_requests")}

        if "tool_name" not in cols:
            op.add_column(
                "workflow_approval_requests",
                sa.Column("tool_name", sa.String(100), nullable=True),
            )
        if "payload_hash" not in cols:
            op.add_column(
                "workflow_approval_requests",
                sa.Column("payload_hash", sa.String(64), nullable=True),
            )
        if "requested_by" not in cols:
            op.add_column(
                "workflow_approval_requests",
                sa.Column("requested_by", sa.String(128), nullable=True),
            )
        if "expires_at" not in cols:
            op.add_column(
                "workflow_approval_requests",
                sa.Column("expires_at", sa.DateTime(), nullable=True),
            )

        if "ix_workflow_approval_requests_tool_name" not in indexes:
            op.create_index(
                "ix_workflow_approval_requests_tool_name",
                "workflow_approval_requests",
                ["tool_name"],
            )
        if "ix_workflow_approval_requests_payload_hash" not in indexes:
            op.create_index(
                "ix_workflow_approval_requests_payload_hash",
                "workflow_approval_requests",
                ["payload_hash"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "workflow_approval_requests" in table_names:
        cols = {c["name"] for c in inspector.get_columns("workflow_approval_requests")}
        indexes = {i["name"] for i in inspector.get_indexes("workflow_approval_requests")}

        if "ix_workflow_approval_requests_payload_hash" in indexes:
            op.drop_index("ix_workflow_approval_requests_payload_hash", table_name="workflow_approval_requests")
        if "ix_workflow_approval_requests_tool_name" in indexes:
            op.drop_index("ix_workflow_approval_requests_tool_name", table_name="workflow_approval_requests")

        if "expires_at" in cols:
            op.drop_column("workflow_approval_requests", "expires_at")
        if "requested_by" in cols:
            op.drop_column("workflow_approval_requests", "requested_by")
        if "payload_hash" in cols:
            op.drop_column("workflow_approval_requests", "payload_hash")
        if "tool_name" in cols:
            op.drop_column("workflow_approval_requests", "tool_name")
