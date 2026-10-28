"""Application API keys and external integration logging.

Revision ID: 0004_application_api_keys
Revises: 0003_rag_policy_metadata
Create Date: 2026-10-28 16:45:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_application_api_keys"
down_revision = "0003_rag_policy_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. External application clients
    op.create_table(
        "app_clients",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_app_client_workspace"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_app_clients"),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')", name="ck_app_client_status"
        ),
    )
    op.create_index("ix_app_clients_workspace_id", "app_clients", ["workspace_id"])

    # 2. Application API keys with hashed secrets
    op.create_table(
        "app_api_keys",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column(
            "allowed_assistant_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=True, server_default="60"),
        sa.Column("rate_limit_rpd", sa.Integer(), nullable=True, server_default="10000"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_from_key_id", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["app_id"], ["app_clients.id"], ondelete="RESTRICT", name="fk_app_key_client"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_app_key_workspace"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_app_api_keys"),
        sa.UniqueConstraint("key_hash", name="uq_app_key_hash"),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')", name="ck_app_key_status"
        ),
    )
    op.create_index("ix_app_api_keys_workspace_id", "app_api_keys", ["workspace_id"])
    op.create_index("ix_app_api_keys_app_id", "app_api_keys", ["app_id"])
    op.create_index(
        "ix_app_api_keys_idempotency_key",
        "app_api_keys",
        ["workspace_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    # 3. Request logs for integrations
    op.create_table(
        "app_request_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("assistant_id", sa.String(length=64), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id", name="pk_app_request_logs"),
    )
    op.create_index(
        "ix_app_request_logs_workspace_id", "app_request_logs", ["workspace_id", "created_at"]
    )
    op.create_index("ix_app_request_logs_app_id", "app_request_logs", ["app_id", "created_at"])
    op.create_index("ix_app_request_logs_key_id", "app_request_logs", ["key_id", "created_at"])


def downgrade() -> None:
    raise RuntimeError(
        "Stored evidence must be preserved, including integration data; restore an approved backup instead."
    )
