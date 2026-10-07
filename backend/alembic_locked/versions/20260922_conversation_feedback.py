"""Add conversation_feedbacks table for online RAG evaluation votes.

Revision ID: 20260922_conversation_feedback
Revises: 20260920_expand_facts_text
Create Date: 2026-09-22
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260922_conversation_feedback"
down_revision = "20260920_expand_facts_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "conversation_threads" not in table_names:
        op.create_table(
            "conversation_threads",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("assistant_code", sa.String(length=50), nullable=False),
            sa.Column("assistant_name", sa.String(length=150), nullable=False),
            sa.Column("user_name", sa.String(length=150), nullable=False, server_default="Thí sinh / Sinh viên"),
            sa.Column("user_email", sa.String(length=150), nullable=True),
            sa.Column("last_message", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="ai_active"),
            sa.Column("assigned_to", sa.String(length=100), nullable=True),
            sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="tenant_qnu"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_conversation_threads_assistant_code", "conversation_threads", ["assistant_code"])
        op.create_index("ix_conversation_threads_status", "conversation_threads", ["status"])
        op.create_index("ix_conversation_threads_tenant_id", "conversation_threads", ["tenant_id"])

    if "conversation_messages" not in table_names:
        op.create_table(
            "conversation_messages",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("thread_id", sa.String(length=36), nullable=False),
            sa.Column("sender", sa.String(length=20), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_conversation_messages_thread_id", "conversation_messages", ["thread_id"])

    if "conversation_feedbacks" not in table_names:
        op.create_table(
            "conversation_feedbacks",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("thread_id", sa.String(length=36), nullable=True),
            sa.Column("assistant_code", sa.String(length=50), nullable=False, server_default=""),
            sa.Column("vote", sa.String(length=10), nullable=False),
            sa.Column("question_excerpt", sa.Text(), nullable=False, server_default=""),
            sa.Column("answer_excerpt", sa.Text(), nullable=False, server_default=""),
            sa.Column("tenant_id", sa.String(length=100), nullable=False, server_default="tenant_qnu"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_conversation_feedbacks_thread_id", "conversation_feedbacks", ["thread_id"])
        op.create_index(
            "ix_conversation_feedbacks_assistant_code", "conversation_feedbacks", ["assistant_code"]
        )
        op.create_index("ix_conversation_feedbacks_vote", "conversation_feedbacks", ["vote"])
        op.create_index("ix_conversation_feedbacks_tenant_id", "conversation_feedbacks", ["tenant_id"])
        op.create_index("ix_conversation_feedbacks_created_at", "conversation_feedbacks", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "conversation_feedbacks" in table_names:
        op.drop_index("ix_conversation_feedbacks_created_at", table_name="conversation_feedbacks")
        op.drop_index("ix_conversation_feedbacks_tenant_id", table_name="conversation_feedbacks")
        op.drop_index("ix_conversation_feedbacks_vote", table_name="conversation_feedbacks")
        op.drop_index("ix_conversation_feedbacks_assistant_code", table_name="conversation_feedbacks")
        op.drop_index("ix_conversation_feedbacks_thread_id", table_name="conversation_feedbacks")
        op.drop_table("conversation_feedbacks")
