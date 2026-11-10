"""Tombstones preserve evidence; receipts bind destructive intent to one actor and snapshot."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class ResourceState(Base):
    __tablename__ = "resource_lifecycle_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','archived','deleted')", name="ck_resource_lifecycle_status"
        ),
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(24), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class LifecycleAction(Base):
    __tablename__ = "resource_lifecycle_actions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_lifecycle_request"
        ),
        CheckConstraint(
            "status IN ('preview','pending','completed','failed')",
            name="ck_lifecycle_action_status",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    impact: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="preview")
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(64))
    phase: Mapped[str | None] = mapped_column(String(32))
    progress: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    takeover_by: Mapped[str | None] = mapped_column(String(200))
    takeover_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
