"""SQLAlchemy Models for QNU Standard AI Assistants."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AssistantModel(Base):
    """Database record for an enterprise AI Assistant on QNU Platform."""

    __tablename__ = "assistants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="academic", index=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False)
    published_workflow_version_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, default=None
    )
    workflow_ownership: Mapped[str] = mapped_column(
        String(20), default="private", index=True
    )  # 'private' | 'shared'
    collection_id: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="tenant_qnu", index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AssistantVersionModel(Base):
    """Snapshot record for assistant configuration versioning and rollback."""

    __tablename__ = "assistant_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"asv_{uuid.uuid4().hex[:12]}"
    )
    assistant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    assistant_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version_number: Mapped[str] = mapped_column(String(20), nullable=False)
    change_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[str] = mapped_column(String(100), default="cán bộ quản trị")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

