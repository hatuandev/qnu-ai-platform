"""Allow source-only compilation runs without a chat provider.

Automatic preparation may legitimately continue without an AI supplement when no
chat target is configured. Such a run never calls a model, so recording a provider
would be misleading; historical rows keep their pinned provider.

Revision ID: 0019_source_only_compilation
Revises: 0018_preparation_auto
"""

import sqlalchemy as sa

from alembic import op

revision = "0019_source_only_compilation"
down_revision = "0018_preparation_auto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "kb_compilation_runs",
        "provider_id",
        existing_type=sa.String(length=64),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    # Deliberately no data fabrication: if source-only rows exist, setting NOT NULL
    # fails and an operator must decide how to represent them.
    op.alter_column(
        "kb_compilation_runs",
        "provider_id",
        existing_type=sa.String(length=64),
        existing_nullable=True,
        nullable=False,
    )
