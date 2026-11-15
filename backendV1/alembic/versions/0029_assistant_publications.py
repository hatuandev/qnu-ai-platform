"""Public chatbot release per assistant: share slug, presentation and limits."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0029_assistant_publications"
down_revision = "0028_drop_index_system_default_authorized"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_publications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("assistant_id", sa.String(64), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("welcome_message", sa.Text(), nullable=False),
        sa.Column("starter_prompts", JSONB(), nullable=False, server_default="[]"),
        sa.Column("max_turns_per_session", sa.Integer(), nullable=False),
        sa.Column("daily_token_budget", sa.Integer()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assistant_id"],
            ["chat_assistants.id"],
            name="fk_assistant_publication_assistant",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("assistant_id", name="uq_assistant_publication_assistant"),
        sa.UniqueConstraint("slug", name="uq_assistant_publication_slug"),
        sa.CheckConstraint(
            "revision >= 1 AND max_turns_per_session BETWEEN 1 AND 100"
            " AND (daily_token_budget IS NULL OR daily_token_budget >= 1000)",
            name="ck_assistant_publication_config",
        ),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$'",
            name="ck_assistant_publication_slug",
        ),
    )


def downgrade() -> None:
    op.drop_table("assistant_publications")
