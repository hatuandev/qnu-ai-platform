"""Add feedback column to chat_turns.

Adds feedback column (JSONB, nullable) to chat_turns table to persist user feedback
(like/dislike, reasons, timestamps).
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0039_chat_turn_feedback"
down_revision = "0038_ocr_spelling_defaults_total_passes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_turns",
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_turns", "feedback")
