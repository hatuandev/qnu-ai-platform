"""Allow the automatic preparation policy and index its reuse key."""

import sqlalchemy as sa

from alembic import op

revision = "0018_preparation_auto"
down_revision = "0017_answer_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_preparation_mode", "kb_preparation_intents", type_="check")
    op.create_check_constraint(
        "ck_preparation_mode",
        "kb_preparation_intents",
        "mode IN ('source','ai','auto')",
    )
    op.create_index(
        "ix_compilation_reuse_key",
        "kb_compilation_runs",
        [sa.text("(config->>'reuse_key')")],
        postgresql_where=sa.text("config ? 'reuse_key'"),
    )


def downgrade() -> None:
    op.drop_index("ix_compilation_reuse_key", table_name="kb_compilation_runs")
    op.drop_constraint("ck_preparation_mode", "kb_preparation_intents", type_="check")
    op.create_check_constraint(
        "ck_preparation_mode",
        "kb_preparation_intents",
        "mode IN ('source','ai')",
    )
