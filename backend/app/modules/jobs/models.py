"""Relational Models for Async Background Job Tracking (ARQ Workers)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobRecord(Base):
    """Persistent record of a background job (ingestion, reindex, export)."""

    __tablename__ = "job_records"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"job_{uuid.uuid4().hex[:12]}"
    )
    # ingestion | reindex | export
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # queued | running | completed | failed | cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    collection_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    arq_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="tenant_qnu")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __init__(self, **kwargs):
        """Eager Python-side defaults so records are valid even before flush."""
        super().__init__(**kwargs)
        if not self.id:
            self.id = f"job_{uuid.uuid4().hex[:12]}"
        if self.payload is None:
            self.payload = {}
        if self.result is None:
            self.result = {}
        if self.progress is None:
            self.progress = 0.0
        now = utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
