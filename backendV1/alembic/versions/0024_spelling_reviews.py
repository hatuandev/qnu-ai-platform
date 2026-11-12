"""Persist one durable approval per completed spelling check."""

import sqlalchemy as sa

from alembic import op

revision = "0024_spelling_reviews"
down_revision = "0023_spelling_dispositions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ocr_spelling_reviews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("check_id", sa.String(64), nullable=False),
        sa.Column("reviewed_version", sa.Integer(), nullable=False),
        sa.Column("reviewed_sha256", sa.String(64), nullable=False),
        sa.Column("reviewed_version_id", sa.String(64), nullable=True),
        sa.Column("change_count", sa.Integer(), nullable=False),
        sa.Column("reviewed_by", sa.String(200), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "workspace_id", "collection_id"],
            [
                "ocr_processing_runs.id",
                "ocr_processing_runs.workspace_id",
                "ocr_processing_runs.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_review_run",
        ),
        sa.ForeignKeyConstraint(
            ["check_id"],
            ["ocr_spelling_runs.id"],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_review_check",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_version_id"],
            ["ocr_text_versions.id"],
            ondelete="RESTRICT",
            name="fk_ocr_spelling_review_version",
        ),
        sa.UniqueConstraint("check_id", name="uq_ocr_spelling_review_check"),
        sa.UniqueConstraint(
            "workspace_id",
            "reviewed_by",
            "idempotency_key",
            name="uq_ocr_spelling_review_request",
        ),
        sa.CheckConstraint("reviewed_version >= 0", name="ck_ocr_spelling_review_version"),
    )
    op.create_index("ix_ocr_spelling_reviews_run_id", "ocr_spelling_reviews", ["run_id"])


def downgrade() -> None:
    op.drop_table("ocr_spelling_reviews")
