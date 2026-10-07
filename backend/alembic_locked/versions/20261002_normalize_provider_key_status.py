"""Normalize legacy provider-key statuses and enforce canonical values.

Revision ID: 20261002_normalize_provider_key_status
Revises: 20261002_provider_key_events
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261002_normalize_provider_key_status"
down_revision: str | Sequence[str] | None = "20261002_provider_key_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CANONICAL_STATUSES = "'active', 'rate_limited', 'exhausted', 'invalid', 'inactive'"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE provider_api_keys
            SET status = CASE
                WHEN lower(trim(status)) = 'disabled' THEN 'inactive'
                WHEN lower(trim(status)) IN ({_CANONICAL_STATUSES}) THEN lower(trim(status))
                ELSE 'inactive'
            END
            WHERE status IS NULL
               OR status <> lower(trim(status))
               OR lower(trim(status)) NOT IN ({_CANONICAL_STATUSES})
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE model_provider_configs AS provider
            SET extra_config = jsonb_set(
                provider.extra_config,
                '{api_keys}',
                COALESCE(
                    (
                        SELECT jsonb_agg(
                            CASE
                                WHEN lower(trim(COALESCE(item->>'status', 'active'))) = 'disabled'
                                    THEN jsonb_set(item, '{status}', '"inactive"'::jsonb)
                                WHEN lower(trim(COALESCE(item->>'status', 'active'))) IN
                                    ('active', 'rate_limited', 'exhausted', 'invalid', 'inactive')
                                    THEN jsonb_set(
                                        item,
                                        '{status}',
                                        to_jsonb(lower(trim(COALESCE(item->>'status', 'active'))))
                                    )
                                ELSE jsonb_set(item, '{status}', '"inactive"'::jsonb)
                            END
                            ORDER BY ordinality
                        )
                        FROM jsonb_array_elements(provider.extra_config->'api_keys')
                            WITH ORDINALITY AS entries(item, ordinality)
                    ),
                    '[]'::jsonb
                )
            )
            WHERE jsonb_typeof(provider.extra_config->'api_keys') = 'array'
            """
        )
    )
    op.create_check_constraint(
        "ck_provider_api_keys_status",
        "provider_api_keys",
        f"status IN ({_CANONICAL_STATUSES})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_provider_api_keys_status",
        "provider_api_keys",
        type_="check",
    )
