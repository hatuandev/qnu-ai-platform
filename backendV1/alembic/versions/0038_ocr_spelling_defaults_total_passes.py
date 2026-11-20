"""Add total_passes to ocr_spelling_defaults.

Adds total_passes column to ocr_spelling_defaults table with default 2
and check constraint 1 <= total_passes <= 4.
"""

import sqlalchemy as sa
from alembic import op

revision = "0038_ocr_spelling_defaults_total_passes"
down_revision = "0037_ocr_spelling_multi_pass"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ocr_spelling_defaults",
        sa.Column("total_passes", sa.Integer(), nullable=False, server_default=sa.text("2")),
    )
    op.create_check_constraint(
        "ck_ocr_spelling_defaults_passes",
        "ocr_spelling_defaults",
        "total_passes >= 1 AND total_passes <= 4",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ocr_spelling_defaults_passes", "ocr_spelling_defaults", type_="check")
    op.drop_column("ocr_spelling_defaults", "total_passes")
