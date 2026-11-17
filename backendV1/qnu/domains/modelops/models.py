"""ModelOps persistence: providers, keys, system defaults, quotas and usage.

Table names are intentionally distinct from the legacy schema
(``model_provider_configs``/``provider_api_keys``/``provider_key_events``) so two
owners never migrate the same table.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.platform.database import Base

PROVIDER_TYPES = ("openai_compatible", "gemini", "local", "ollama", "llamacpp", "mineru")
CAPABILITIES = ("chat", "embedding", "rerank", "ocr")
KEY_STATUSES = ("active", "revoked")
DEFAULT_ROW_ID = "system"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Provider(Base):
    """Provider endpoint + the single model it serves for a capability set."""

    __tablename__ = "providers"
    __table_args__ = (
        CheckConstraint(
            "provider_type IN ('openai_compatible','gemini','local','ollama','llamacpp','mineru')",
            name="ck_provider_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    is_connection: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ProviderKey(Base):
    """Encrypted credential for one provider; plaintext never leaves the service."""

    __tablename__ = "provider_keys"
    __table_args__ = (
        CheckConstraint("status IN ('active','revoked')", name="ck_provider_key_status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    masked_hint: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # NULL means all child models. Migrated model-specific keys keep their old scope.
    model_ids: Mapped[list[str] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ProviderKeyAudit(Base):
    """Audit of credential lifecycle actions (never stores the secret)."""

    __tablename__ = "provider_key_audits"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ModelDefaults(Base):
    """Single row holding the system provider/model per capability."""

    __tablename__ = "model_defaults"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=DEFAULT_ROW_ID)
    chat_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chat_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    embedding_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rerank_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rerank_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ocr_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    document_provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_concurrency: Mapped[dict[str, int] | None] = mapped_column(JSONB(none_as_null=True))
    document_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    document_models: Mapped[list[dict] | None] = mapped_column(JSONB(none_as_null=True))
    updated_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class WorkspaceQuota(Base):
    """UTC calendar-month budget; NULL limit explicitly means unlimited."""

    __tablename__ = "workspace_quotas"
    __table_args__ = (
        CheckConstraint(
            "monthly_token_limit IS NULL OR monthly_token_limit >= 0", name="ck_quota_limit"
        ),
        CheckConstraint("tokens_used >= 0 AND tokens_reserved >= 0", name="ck_quota_counters"),
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), primary_key=True
    )
    month_period: Mapped[date] = mapped_column(Date, primary_key=True)
    monthly_token_limit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tokens_used: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_reserved: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_blocked: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class ModelUsageRecord(Base):
    """Idempotent inference ledger. Unknown usage/cost is not represented as zero."""

    __tablename__ = "model_usage_records"
    __table_args__ = (
        UniqueConstraint("workspace_id", "request_id", name="uq_model_usage_request"),
        CheckConstraint(
            "status IN ('reserved','completed','failed','unknown')", name="ck_model_usage_status"
        ),
        CheckConstraint(
            "reserved_tokens >= 0 AND (total_tokens IS NULL OR total_tokens >= 0)",
            name="ck_model_usage_tokens",
        ),
        CheckConstraint("cost_usd IS NULL OR cost_usd >= 0", name="ck_model_usage_cost"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    capability: Mapped[str] = mapped_column(String(16), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    month_period: Mapped[date] = mapped_column(Date, nullable=False)
    reserved_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="reserved")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ModelOpsEvent(Base):
    """Configuration audit contains identifiers and field names, never credentials."""

    __tablename__ = "modelops_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
