"""Owned conversations and durable question/answer pairs, scoped to v1 assistants."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class Conversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        # A conversation keeps the collection it was created with; the assistant may
        # later be pointed at another collection without rewriting this history.
        ForeignKeyConstraint(
            ["assistant_id", "workspace_id"],
            ["chat_assistants.id", "chat_assistants.workspace_id"],
            ondelete="RESTRICT",
            name="fk_chat_conversation_assistant",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_chat_conversation_scope"),
        CheckConstraint(
            "assistant_revision >= 1 AND last_turn_no >= 0 AND status IN ('active','archived')",
            name="ck_chat_conversation_state",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assistant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assistant_revision: Mapped[int] = mapped_column(nullable=False)
    owner_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    document_ids: Mapped[list | None] = mapped_column(JSONB)
    assistant_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    last_turn_no: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ConversationTurn(Base):
    __tablename__ = "chat_turns"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id", "workspace_id", "collection_id"],
            [
                "chat_conversations.id",
                "chat_conversations.workspace_id",
                "chat_conversations.collection_id",
            ],
            ondelete="RESTRICT",
            name="fk_chat_turn_conversation",
        ),
        UniqueConstraint("conversation_id", "turn_no", name="uq_chat_turn_sequence"),
        UniqueConstraint("conversation_id", "idempotency_key", name="uq_chat_turn_request"),
        CheckConstraint(
            "turn_no >= 1 AND status IN ('running','completed','failed','uncertain','cancelled')",
            name="ck_chat_turn_status",
        ),
        Index(
            "uq_chat_turn_running",
            "conversation_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    turn_no: Mapped[int] = mapped_column(nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_filter: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    resolved_question: Mapped[str | None] = mapped_column(Text)
    history_turn_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_code: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[dict | None] = mapped_column(JSONB)
    rewrite_trace: Mapped[dict | None] = mapped_column(JSONB)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
