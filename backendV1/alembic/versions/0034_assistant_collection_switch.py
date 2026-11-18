"""Let an assistant bind several collections, and move without touching pinned history.

Conversations and answer reviews keep the collection they were created with; the
assistant's current bindings are only its serving scope. ``chat_assistants.collection_id``
stays as the first binding for older readers and is backfilled into the join table.
"""

import sqlalchemy as sa

from alembic import op

revision = "0034_assistant_collection_switch"
down_revision = "0033_document_model_group"
branch_labels = depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_chat_conversation_assistant", "chat_conversations", type_="foreignkey")
    op.drop_constraint("fk_answer_review_assistant", "kb_answer_reviews", type_="foreignkey")
    op.create_unique_constraint(
        "uq_chat_assistant_identity", "chat_assistants", ["id", "workspace_id"]
    )
    op.create_foreign_key(
        "fk_chat_conversation_assistant",
        "chat_conversations",
        "chat_assistants",
        ["assistant_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answer_review_assistant",
        "kb_answer_reviews",
        "chat_assistants",
        ["assistant_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "chat_assistant_collections",
        sa.Column("assistant_id", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(64), nullable=False),
        sa.Column("workspace_id", sa.String(64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("assistant_id", "collection_id"),
        sa.ForeignKeyConstraint(
            ["assistant_id", "workspace_id"],
            ["chat_assistants.id", "chat_assistants.workspace_id"],
            ondelete="CASCADE",
            name="fk_assistant_collection_link",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="RESTRICT",
            name="fk_assistant_collection_target",
        ),
    )
    op.create_index(
        "ix_chat_assistant_collections_collection",
        "chat_assistant_collections",
        ["workspace_id", "collection_id"],
    )
    op.execute(
        sa.text(
            "INSERT INTO chat_assistant_collections (assistant_id, workspace_id, collection_id, position) "
            "SELECT id, workspace_id, collection_id, 0 FROM chat_assistants"
        )
    )


def downgrade() -> None:
    # Refuses to run while any assistant's collection differs from a pinned
    # conversation or review; restoring the old contract would be a lie.
    op.drop_index(
        "ix_chat_assistant_collections_collection", table_name="chat_assistant_collections"
    )
    op.drop_table("chat_assistant_collections")
    op.drop_constraint("fk_chat_conversation_assistant", "chat_conversations", type_="foreignkey")
    op.drop_constraint("fk_answer_review_assistant", "kb_answer_reviews", type_="foreignkey")
    op.create_foreign_key(
        "fk_chat_conversation_assistant",
        "chat_conversations",
        "chat_assistants",
        ["assistant_id", "workspace_id", "collection_id"],
        ["id", "workspace_id", "collection_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answer_review_assistant",
        "kb_answer_reviews",
        "chat_assistants",
        ["assistant_id", "workspace_id", "collection_id"],
        ["id", "workspace_id", "collection_id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_chat_assistant_identity", "chat_assistants", type_="unique")
