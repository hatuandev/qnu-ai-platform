"""Small, separate store for assistant answer tests with human labels.

These rows are review evidence about answers, not retrieval gold chunks. The
benchmark domain remains the only source of ``gold_chunk_ids``.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class AnswerReview(Base):
    __tablename__ = "kb_answer_reviews"
    __table_args__ = (
        # A review keeps the collection it was run against; the assistant may later
        # be pointed at another collection without rewriting this history.
        ForeignKeyConstraint(
            ["assistant_id", "workspace_id"],
            ["chat_assistants.id", "chat_assistants.workspace_id"],
            ondelete="RESTRICT",
            name="fk_answer_review_assistant",
        ),
        UniqueConstraint(
            "id", "workspace_id", "collection_id", name="uq_answer_review_scope"
        ),
        UniqueConstraint(
            "workspace_id", "requested_by", "idempotency_key", name="uq_answer_review_request"
        ),
        CheckConstraint(
            "assistant_revision >= 1 AND question_count BETWEEN 1 AND 3",
            name="ck_answer_review_state",
        ),
        CheckConstraint(
            "status IN ('running','completed','failed','uncertain')",
            name="ck_answer_review_status",
        ),
        Index("ix_answer_review_assistant", "workspace_id", "assistant_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assistant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    assistant_revision: Mapped[int] = mapped_column(nullable=False)
    assistant_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    question_count: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_code: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnswerReviewItem(Base):
    __tablename__ = "kb_answer_review_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["review_id", "workspace_id", "collection_id"],
            [
                "kb_answer_reviews.id",
                "kb_answer_reviews.workspace_id",
                "kb_answer_reviews.collection_id",
            ],
            ondelete="CASCADE",
            name="fk_answer_review_item_review",
        ),
        UniqueConstraint("review_id", "ordinal", name="uq_answer_review_item_ordinal"),
        CheckConstraint("ordinal >= 0 AND ordinal < 3", name="ck_answer_review_item_ordinal"),
        CheckConstraint(
            "status IN ('answered','insufficient_evidence','failed','uncertain')",
            name="ck_answer_review_item_status",
        ),
        CheckConstraint(
            "label IS NULL OR label IN ('correct','missing','wrong_source','wrong_year')",
            name="ck_answer_review_item_label",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    collection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="failed")
    error_code: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[dict | None] = mapped_column(JSONB)
    index_run_id: Mapped[str | None] = mapped_column(String(64))
    generation: Mapped[int | None] = mapped_column()
    label: Mapped[str | None] = mapped_column(String(16))
    label_note: Mapped[str | None] = mapped_column(Text)
    labelled_by: Mapped[str | None] = mapped_column(String(200))
    labelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
