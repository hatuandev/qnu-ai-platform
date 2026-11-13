"""Drop the unused per-run system-default authorization marker from index runs."""

import sqlalchemy as sa

from alembic import op

revision = "0028_drop_index_system_default_authorized"
down_revision = "0027_drop_ws_model_policy"
branch_labels = depends_on = None


def upgrade() -> None:
    op.drop_column("kb_index_runs", "system_default_authorized")


def downgrade() -> None:
    op.add_column(
        "kb_index_runs",
        sa.Column(
            "system_default_authorized", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
