"""Allow durable manual review intents before a worker claims them."""

from alembic import op

revision = "0013_queued_review"
down_revision = "0012_assistant_auto_output"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_compilation_review_status", "kb_compilation_reviews", type_="check")
    op.create_check_constraint(
        "ck_compilation_review_status",
        "kb_compilation_reviews",
        "status IN ('queued','running','completed','failed','uncertain','cancelled')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE kb_compilation_reviews SET status='cancelled', finished_at=now() "
        "WHERE status='queued'"
    )
    op.drop_constraint("ck_compilation_review_status", "kb_compilation_reviews", type_="check")
    op.create_check_constraint(
        "ck_compilation_review_status",
        "kb_compilation_reviews",
        "status IN ('running','completed','failed','uncertain','cancelled')",
    )
