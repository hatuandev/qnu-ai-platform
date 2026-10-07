"""Add credential-free key rotation history."""

import sqlalchemy as sa

from alembic import op

revision = "20261002_provider_key_events"
down_revision = "20261002_provider_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_key_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "provider_id",
            sa.String(36),
            sa.ForeignKey("model_provider_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_id", sa.String(100), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_provider_key_events_history", "provider_key_events", ["provider_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_table("provider_key_events")
