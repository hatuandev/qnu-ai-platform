"""SQLAlchemy Models for OCR Engines & Document Recognition Auditing."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class OCREngineModel(Base):
    """Registered OCR engine available for scanning document images and PDFs."""

    __tablename__ = "ocr_engines"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    engine_type: Mapped[str] = mapped_column(String(50), nullable=False)  # paddleocr, docling, mock_ocr
    provider_category: Mapped[str] = mapped_column(String(30), default="local")  # local, cloud
    capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.95)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OCRJobLog(Base):
    """Audit record for document OCR extraction operations."""

    __tablename__ = "ocr_job_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(100), default="tenant_qnu", index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    engine_used: Mapped[str] = mapped_column(String(100), nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="success")  # success, failed
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_ocr_job_tenant_engine", "tenant_id", "engine_used"),
    )
