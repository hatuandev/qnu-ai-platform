"""Allow automatic output budgeting for assistants."""

import sqlalchemy as sa

from alembic import op

revision = "0012_assistant_auto_output"
down_revision = "0011_mineru_ocr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("chat_assistants", "max_output_tokens", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE chat_assistants SET max_output_tokens = 2048 WHERE max_output_tokens IS NULL")
    op.alter_column("chat_assistants", "max_output_tokens", existing_type=sa.Integer(), nullable=False)
