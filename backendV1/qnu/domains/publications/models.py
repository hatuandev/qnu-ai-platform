"""One public release per assistant: share link, greeting, limits and kill flag.

A row describes the admin's intent. Whether the link actually answers is
decided per request from the assistant's current readiness, so withdrawing a
source stops public answers without rewriting this configuration silently.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class AssistantPublication(Base):
    __tablename__ = "assistant_publications"
    __table_args__ = (
        UniqueConstraint("assistant_id", name="uq_assistant_publication_assistant"),
        UniqueConstraint("slug", name="uq_assistant_publication_slug"),
        CheckConstraint(
            "revision >= 1 AND max_turns_per_session BETWEEN 1 AND 100"
            " AND (daily_token_budget IS NULL OR daily_token_budget >= 1000)",
            name="ck_assistant_publication_config",
        ),
        CheckConstraint(
            "slug ~ '^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$'",
            name="ck_assistant_publication_slug",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assistant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_assistants.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    welcome_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    starter_prompts: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    max_turns_per_session: Mapped[int] = mapped_column(nullable=False, default=15)
    daily_token_budget: Mapped[int | None] = mapped_column(nullable=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    revision: Mapped[int] = mapped_column(nullable=False, default=1)
    updated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class AssistantPublicationStat(Base):
    """Anonymous daily counters per release; no visitor identity is kept."""

    __tablename__ = "assistant_publication_stats"
    publication_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("assistant_publications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    sessions: Mapped[int] = mapped_column(nullable=False, default=0)
    turns: Mapped[int] = mapped_column(nullable=False, default=0)
    insufficient_turns: Mapped[int] = mapped_column(nullable=False, default=0)
    error_turns: Mapped[int] = mapped_column(nullable=False, default=0)
    tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class AssistantPublicationQuestion(Base):
    """Questions the public surface could not ground, kept to improve content."""

    __tablename__ = "assistant_publication_questions"
    __table_args__ = (
        UniqueConstraint("publication_id", "question_hash", name="uq_publication_question_hash"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    publication_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("assistant_publications.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    times_asked: Mapped[int] = mapped_column(nullable=False, default=1)
    last_asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
