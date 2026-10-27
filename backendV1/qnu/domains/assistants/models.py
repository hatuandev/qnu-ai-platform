"""Workspace-authorized assistant configuration; no credential copies."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class Assistant(Base):
    __tablename__ = "chat_assistants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["collection_id", "workspace_id"],
            ["kb_collections.id", "kb_collections.workspace_id"],
            ondelete="RESTRICT",
            name="fk_chat_assistant_collection",
        ),
        UniqueConstraint("id", "workspace_id", "collection_id", name="uq_chat_assistant_scope"),
        CheckConstraint(
            "revision >= 1 AND top_k BETWEEN 1 AND 20 AND history_turns BETWEEN 0 AND 10 AND max_output_tokens > 0",
            name="ck_chat_assistant_config",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    persona: Mapped[str] = mapped_column(Text, nullable=False, default="")
    chat_provider_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="RESTRICT")
    )
    revision: Mapped[int] = mapped_column(nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    top_k: Mapped[int] = mapped_column(nullable=False, default=5)
    history_turns: Mapped[int] = mapped_column(nullable=False, default=3)
    max_output_tokens: Mapped[int] = mapped_column(nullable=False, default=2048)
    rag_policy: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
