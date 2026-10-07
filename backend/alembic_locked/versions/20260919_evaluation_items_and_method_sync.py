"""Schema sync for evaluation run method and result item details.

Revision ID: 20260919_evaluation_items_and_method_sync
Revises: 20260919_facts_foreign_key_and_schema_sync
Create Date: 2026-09-19 22:10:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260919_evaluation_items_and_method_sync"
down_revision = "20260919_facts_foreign_key_and_schema_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Safely add evaluation_method to evaluation_runs and detail columns to evaluation_result_items."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "evaluation_runs" in table_names:
        run_cols = {col["name"] for col in inspector.get_columns("evaluation_runs")}
        if "evaluation_method" not in run_cols:
            op.add_column(
                "evaluation_runs",
                sa.Column("evaluation_method", sa.String(length=30), nullable=True, server_default="heuristic"),
            )

    if "evaluation_result_items" in table_names:
        item_cols = {col["name"] for col in inspector.get_columns("evaluation_result_items")}
        if "execution_path" not in item_cols:
            op.add_column(
                "evaluation_result_items",
                sa.Column("execution_path", sa.String(length=50), nullable=True, server_default="assistant_workflow"),
            )
        if "is_refusal" not in item_cols:
            op.add_column(
                "evaluation_result_items",
                sa.Column("is_refusal", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            )
        if "reasoning" not in item_cols:
            op.add_column(
                "evaluation_result_items",
                sa.Column("reasoning", sa.Text(), nullable=True),
            )


def downgrade() -> None:
    """Rollback evaluation detail columns."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "evaluation_result_items" in table_names:
        item_cols = {col["name"] for col in inspector.get_columns("evaluation_result_items")}
        if "reasoning" in item_cols:
            op.drop_column("evaluation_result_items", "reasoning")
        if "is_refusal" in item_cols:
            op.drop_column("evaluation_result_items", "is_refusal")
        if "execution_path" in item_cols:
            op.drop_column("evaluation_result_items", "execution_path")

    if "evaluation_runs" in table_names:
        run_cols = {col["name"] for col in inspector.get_columns("evaluation_runs")}
        if "evaluation_method" in run_cols:
            op.drop_column("evaluation_runs", "evaluation_method")
