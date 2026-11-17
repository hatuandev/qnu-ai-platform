"""System defaults for automatic spelling checks."""

import sqlalchemy as sa

from alembic import op

revision = "0031_spelling_defaults"
down_revision = "0030_publication_stats"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "ocr_spelling_defaults",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ocr", sa.Boolean(), nullable=False),
        sa.Column("pdf_text", sa.Boolean(), nullable=False),
        sa.Column("word_text", sa.Boolean(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_ocr_spelling_defaults_singleton"),
    )


def downgrade() -> None:
    op.drop_table("ocr_spelling_defaults")
