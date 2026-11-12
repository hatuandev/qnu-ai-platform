"""Allow a completed OCR run that keeps explicit, reviewable image warnings."""

import sqlalchemy as sa

from alembic import op

revision = "0022_ocr_warning_status"
down_revision = "0021_index_system_embedding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_ocr_run_status", "ocr_processing_runs", type_="check")
    op.alter_column(
        "ocr_processing_runs",
        "status",
        existing_type=sa.String(16),
        type_=sa.String(32),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_ocr_run_status",
        "ocr_processing_runs",
        "status IN "
        "('queued','running','completed','completed_with_warnings',"
        "'failed','uncertain','cancelled')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE ocr_processing_runs SET status = 'completed' "
        "WHERE status = 'completed_with_warnings'"
    )
    op.drop_constraint("ck_ocr_run_status", "ocr_processing_runs", type_="check")
    op.alter_column(
        "ocr_processing_runs",
        "status",
        existing_type=sa.String(32),
        type_=sa.String(16),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_ocr_run_status",
        "ocr_processing_runs",
        "status IN ('queued','running','completed','failed','uncertain','cancelled')",
    )
