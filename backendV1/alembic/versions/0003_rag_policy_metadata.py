"""Additive RAG policy and immutable, publication-bound retrieval annotations."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_rag_policy_metadata"
down_revision = "0002_operational_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_assistants",
        sa.Column(
            "rag_policy", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.add_column(
        "kb_compiled_versions",
        sa.Column(
            "retrieval_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "chat_turns",
        sa.Column(
            "metadata_filter",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    raise RuntimeError("Stored evidence must be preserved; restore an approved backup instead.")
