"""Add multi-pass columns to ocr_spelling_runs.

Adds pass_number, total_passes, pass_name, parent_run_id, and batch_group_id
to support asynchronous multi-pass OCR spelling review pipelines.
"""

import sqlalchemy as sa
from alembic import op

revision = "0037_ocr_spelling_multi_pass"
down_revision = "0036_kb_index_table_facts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ocr_spelling_runs",
        sa.Column("pass_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "ocr_spelling_runs",
        sa.Column("total_passes", sa.Integer(), nullable=False, server_default=sa.text("2")),
    )
    op.add_column(
        "ocr_spelling_runs",
        sa.Column("pass_name", sa.String(length=64), nullable=False, server_default=sa.text("'char_ocr'")),
    )
    op.add_column(
        "ocr_spelling_runs",
        sa.Column("parent_run_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "ocr_spelling_runs",
        sa.Column("batch_group_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_ocr_spelling_runs_batch_group_id",
        "ocr_spelling_runs",
        ["batch_group_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_ocr_spelling_passes",
        "ocr_spelling_runs",
        "pass_number >= 1 AND total_passes >= pass_number",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ocr_spelling_passes", "ocr_spelling_runs", type_="check")
    op.drop_index("ix_ocr_spelling_runs_batch_group_id", table_name="ocr_spelling_runs")
    op.drop_column("ocr_spelling_runs", "batch_group_id")
    op.drop_column("ocr_spelling_runs", "parent_run_id")
    op.drop_column("ocr_spelling_runs", "pass_name")
    op.drop_column("ocr_spelling_runs", "total_passes")
    op.drop_column("ocr_spelling_runs", "pass_number")
