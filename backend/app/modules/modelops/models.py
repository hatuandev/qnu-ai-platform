"""SQLAlchemy Models for ModelOps — LLM Providers, Tenant Quotas, and Usage Tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ModelProviderConfig(Base):
    """Configuration for LLM Providers (OpenAI, Gemini, Local vLLM/Ollama)."""

    __tablename__ = "model_provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # openai, gemini, local_vllm
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, index=True)  # 1 = primary, 2 = secondary
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=15)
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProviderApiKey(Base):
    """A provider credential with durable quota, health, and lease state."""

    __tablename__ = "provider_api_keys"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=generate_uuid)
    provider_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("model_provider_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(1000), nullable=False)
    api_key_masked: Mapped[str] = mapped_column(String(100), nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    quota_limit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    usage_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    cooldown_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index(
            "ix_provider_api_keys_selection",
            "provider_id",
            "is_active",
            "status",
            "priority",
        ),
        Index("ix_provider_api_keys_lease", "provider_id", "lease_until"),
    )


class TenantQuota(Base):
    """Monthly Token & Cost Quotas per Tenant / Department."""

    __tablename__ = "tenant_quotas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    month_period: Mapped[str] = mapped_column(
        String(7), nullable=False, index=True
    )  # Format: "2026-09"
    monthly_token_limit: Mapped[int] = mapped_column(Integer, default=5_000_000)
    monthly_cost_limit_usd: Mapped[float] = mapped_column(Float, default=100.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_used_usd: Mapped[float] = mapped_column(Float, default=0.0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_tenant_month_period", "tenant_id", "month_period", unique=True),
    )


class LLMUsageLog(Base):
    """Auditable Usage Record for every LLM interaction."""

    __tablename__ = "llm_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    assistant_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, error
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
