"""Move provider API-key pool state into a relational table.

Revision ID: 20261002_provider_api_keys
Revises: 20260926_reconcile_core_schema
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261002_provider_api_keys"
down_revision: str | Sequence[str] | None = "20260926_reconcile_core_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_api_keys",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("api_key_encrypted", sa.String(length=1000), nullable=False),
        sa.Column("api_key_masked", sa.String(length=100), nullable=False),
        sa.Column("account_id", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("quota_limit", sa.BigInteger(), nullable=True),
        sa.Column("usage_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_token", sa.String(length=36), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["model_provider_configs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_api_keys_provider_id", "provider_api_keys", ["provider_id"])
    op.create_index(
        "ix_provider_api_keys_selection",
        "provider_api_keys",
        ["provider_id", "is_active", "status", "priority"],
    )
    op.create_index(
        "ix_provider_api_keys_lease", "provider_api_keys", ["provider_id", "lease_until"]
    )

    # Preserve every JSONB pool entry. IDs are deterministic when old data omitted one.
    op.execute(
        sa.text(
            """
            INSERT INTO provider_api_keys (
                id, provider_id, name, api_key_encrypted, api_key_masked,
                account_id, priority, is_active, status, quota_limit,
                usage_tokens, cooldown_until, last_used_at, last_error_at,
                last_error_code, created_at, updated_at
            )
            SELECT
                COALESCE(NULLIF(item.value->>'id', ''),
                    'legacy_' || md5(provider.id || ':' || item.ordinality::text)),
                provider.id,
                COALESCE(NULLIF(item.value->>'name', ''), 'Khóa API'),
                item.value->>'api_key',
                COALESCE(NULLIF(item.value->>'api_key_masked', ''), '••••••••'),
                NULLIF(item.value->>'account_id', ''),
                COALESCE((item.value->>'priority')::integer, 1),
                COALESCE((item.value->>'is_active')::boolean, true),
                COALESCE(NULLIF(item.value->>'status', ''), 'active'),
                NULLIF(item.value->>'quota_limit', '')::bigint,
                COALESCE((item.value->>'usage_tokens')::bigint, 0),
                NULLIF(item.value->>'cooldown_until', '')::timestamptz,
                NULLIF(item.value->>'last_used_at', '')::timestamptz,
                NULLIF(item.value->>'last_error_at', '')::timestamptz,
                NULLIF(item.value->>'last_error_code', ''),
                COALESCE(NULLIF(item.value->>'created_at', '')::timestamptz, now()),
                now()
            FROM model_provider_configs AS provider
            CROSS JOIN LATERAL jsonb_array_elements(
                COALESCE(provider.extra_config->'api_keys', '[]'::jsonb)
            ) WITH ORDINALITY AS item(value, ordinality)
            WHERE NULLIF(item.value->>'api_key', '') IS NOT NULL
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    # Providers created before key pools existed still have a primary credential column.
    op.execute(
        sa.text(
            """
            INSERT INTO provider_api_keys (
                id, provider_id, name, api_key_encrypted, api_key_masked,
                priority, is_active, status, usage_tokens, created_at, updated_at
            )
            SELECT
                'primary_' || md5(provider.id), provider.id,
                'Khóa chính', provider.api_key_encrypted, '••••••••',
                1, true, 'active', 0, now(), now()
            FROM model_provider_configs AS provider
            WHERE NULLIF(provider.api_key_encrypted, '') IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM provider_api_keys AS key
                  WHERE key.provider_id = provider.id
              )
            ON CONFLICT (id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_provider_api_keys_lease", table_name="provider_api_keys")
    op.drop_index("ix_provider_api_keys_selection", table_name="provider_api_keys")
    op.drop_index("ix_provider_api_keys_provider_id", table_name="provider_api_keys")
    op.drop_table("provider_api_keys")
