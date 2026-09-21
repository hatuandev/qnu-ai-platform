"""Database models for QNU Real Conversations & Staff Handoff."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ConversationThreadModel(Base):
    """Represents a conversation session between a student/user and an assistant."""

    __tablename__ = "conversation_threads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"conv_{uuid.uuid4().hex[:12]}"
    )
    assistant_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    assistant_name: Mapped[str] = mapped_column(String(150), nullable=False)
    user_name: Mapped[str] = mapped_column(
        String(150), nullable=False, default="Thí sinh / Sinh viên"
    )
    user_email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    last_message: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(50), default="ai_active", index=True
    )  # ai_active, handoff_requested, staff_claimed, resolved
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="tenant_qnu", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    messages: Mapped[list[ConversationMessageModel]] = relationship(
        "ConversationMessageModel",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ConversationMessageModel.created_at",
    )


class ConversationFeedbackModel(Base):
    """Online eval signal: user thumbs up/down on an assistant answer (phiên #186)."""

    __tablename__ = "conversation_feedbacks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"fb_{uuid.uuid4().hex[:12]}"
    )
    thread_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("conversation_threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assistant_code: Mapped[str] = mapped_column(String(50), nullable=False, default="", index=True)
    vote: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # "up" | "down"
    question_excerpt: Mapped[str] = mapped_column(Text, default="")
    answer_excerpt: Mapped[str] = mapped_column(Text, default="")
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="tenant_qnu", nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ConversationMessageModel(Base):
    """Represents a single message in a conversation thread."""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"msg_{uuid.uuid4().hex[:12]}"
    )
    thread_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversation_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(String(20), nullable=False)  # "user", "assistant", "agent"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    thread: Mapped[ConversationThreadModel] = relationship(
        "ConversationThreadModel", back_populates="messages"
    )
