"""Persist reviewer-dismissed spelling suggestions for an existing check."""

import sqlalchemy as sa

from alembic import op

revision = "0023_spelling_dispositions"
down_revision = "0022_ocr_warning_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ocr_spelling_dispositions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("check_id", sa.String(64), nullable=False),
        sa.Column("evidence_id", sa.String(128), nullable=False),
        sa.Column("span_start", sa.Integer(), nullable=False),
        sa.Column("span_end", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "workspace_id", "collection_id"],
            [
                "ocr_processing_runs.id",
                "ocr_processing_runs.workspace_id",
                "ocr_processing_runs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_disposition_run",
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["ocr_spelling_runs.id"],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_disposition_check",
        ),
        sa.UniqueConstraint(
            "check_id",
            "evidence_id",
            "span_start",
            "span_end",
            name="uq_ocr_spelling_disposition",
        ),
        sa.CheckConstraint(
            "span_start >= 0 AND span_end > span_start",
            name="ck_ocr_spelling_disposition_span",
        ),
    )
    op.create_index(
        "ix_ocr_spelling_dispositions_check_id",
        "ocr_spelling_dispositions",
        ["check_id"],
    )


def downgrade() -> None:
    op.drop_table("ocr_spelling_dispositions")
