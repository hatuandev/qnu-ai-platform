"""Anonymous daily usage stats and unanswered questions per public release."""

import sqlalchemy as sa

from alembic import op

revision = "0030_publication_stats"
down_revision = "0029_assistant_publications"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_publication_stats",
        sa.Column("publication_id", sa.String(64), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("insufficient_turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_turns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["assistant_publications.id"],
            name="fk_publication_stats_publication",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("publication_id", "day", name="pk_assistant_publication_stats"),
    )
    op.create_table(
        "assistant_publication_questions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("publication_id", sa.String(64), nullable=False),
        sa.Column("question_hash", sa.String(64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("times_asked", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_asked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["assistant_publications.id"],
            name="fk_publication_questions_publication",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("publication_id", "question_hash", name="uq_publication_question_hash"),
    )


def downgrade() -> None:
    op.drop_table("assistant_publication_questions")
    op.drop_table("assistant_publication_stats")
