"""Allow an assistant to be saved before any collection is attached.

``chat_assistants.collection_id`` is only a mirror of the first binding in
``chat_assistant_collections``; the join table keeps enforcing collection
existence. The scalar column becomes nullable so an assistant can be saved with
an empty binding set and refuse to serve turns until one is attached.
"""

import sqlalchemy as sa

from alembic import op

revision = "0035_assistant_without_collections"
down_revision = "0034_assistant_collection_switch"
branch_labels = depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_chat_assistant_collection", "chat_assistants", type_="foreignkey")
    op.alter_column(
        "chat_assistants", "collection_id", existing_type=sa.String(64), nullable=True
    )


def downgrade() -> None:
    # Refuses to run while an unbound assistant exists: restoring NOT NULL would
    # otherwise invent a collection for it or delete the row.
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM chat_assistants WHERE collection_id IS NULL) THEN "
            "RAISE EXCEPTION 'cannot restore NOT NULL: unbound assistants exist'; "
            "END IF; "
            "END $$"
        )
    )
    op.alter_column(
        "chat_assistants", "collection_id", existing_type=sa.String(64), nullable=False
    )
    op.create_foreign_key(
        "fk_chat_assistant_collection",
        "chat_assistants",
        "kb_collections",
        ["collection_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="RESTRICT",
    )
