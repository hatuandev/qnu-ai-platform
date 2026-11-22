"""Add allowed_embed_origins column to assistant_publications.

Adds allowed_embed_origins column (JSONB, server_default='[]', not null) to
assistant_publications table to control domain whitelist for iframe embedding.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0040_assistant_publication_allowed_embed_origins"
down_revision = "0039_chat_turn_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_publications",
        sa.Column(
            "allowed_embed_origins",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_publications", "allowed_embed_origins")
