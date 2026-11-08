"""Assistant answer tests with human labels, separate from retrieval gold."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0017_answer_review"
down_revision = "0016_review_submission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kb_answer_reviews",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("assistant_id", sa.String(64), nullable=False),
        sa.Column("assistant_revision", sa.Integer(), nullable=False),
        sa.Column("assistant_snapshot", JSONB(), nullable=False),
        sa.Column("requested_by", sa.String(200), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["assistant_id", "workspace_id", "collection_id"],
            [
                "chat_assistants.id",
                "chat_assistants.workspace_id",
                "chat_assistants.collection_id",
            ],
            name="fk_answer_review_assistant",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id", "workspace_id", "collection_id", name="uq_answer_review_scope"
        ),
        sa.UniqueConstraint(
            "workspace_id", "requested_by", "idempotency_key", name="uq_answer_review_request"
        ),
        sa.CheckConstraint(
            "assistant_revision >= 1 AND question_count BETWEEN 1 AND 3",
            name="ck_answer_review_state",
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','failed','uncertain')",
            name="ck_answer_review_status",
        ),
    )
    op.create_index(
        "ix_answer_review_assistant",
        "kb_answer_reviews",
        ["workspace_id", "assistant_id", "created_at"],
    )

    op.create_table(
        "kb_answer_review_items",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("review_id", sa.String(64), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("result", JSONB()),
        sa.Column("index_run_id", sa.String(64)),
        sa.Column("generation", sa.Integer()),
        sa.Column("label", sa.String(16)),
        sa.Column("label_note", sa.Text()),
        sa.Column("labelled_by", sa.String(200)),
        sa.Column("labelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["review_id", "workspace_id", "collection_id"],
            [
                "kb_answer_reviews.id",
                "kb_answer_reviews.workspace_id",
                "kb_answer_reviews.collection_id",
            ],
            name="fk_answer_review_item_review",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("review_id", "ordinal", name="uq_answer_review_item_ordinal"),
        sa.CheckConstraint("ordinal >= 0 AND ordinal < 3", name="ck_answer_review_item_ordinal"),
        sa.CheckConstraint(
            "status IN ('answered','insufficient_evidence','failed','uncertain')",
            name="ck_answer_review_item_status",
        ),
        sa.CheckConstraint(
            "label IS NULL OR label IN ('correct','missing','wrong_source','wrong_year')",
            name="ck_answer_review_item_label",
        ),
    )


def downgrade() -> None:
    op.drop_table("kb_answer_review_items")
    op.drop_table("kb_answer_reviews")
