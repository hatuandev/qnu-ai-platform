"""Actor-bound operation approvals and immutable evidence backup receipts."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.platform.database import Base


class OperationAction(Base):
    __tablename__ = "ops_actions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_ops_action_request"
        ),
        CheckConstraint(
            "status IN ('preview','pending','dispatched','superseded')", name="ck_ops_action_status"
        ),
        CheckConstraint("action IN ('dispatch','delete_backup')", name="ck_ops_action_type"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="preview")
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    state_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    preview_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StorageCleanupAction(Base):
    __tablename__ = "ops_storage_cleanup_actions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "actor_ref", "idempotency_key", name="uq_storage_cleanup_request"
        ),
        CheckConstraint(
            "status IN ('preview','pending','completed')", name="ck_storage_cleanup_status"
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="preview")
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    target_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    candidates: Mapped[list] = mapped_column(JSONB, nullable=False)
    preview_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128))
    request_hash: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceBackup(Base):
    __tablename__ = "ops_evidence_backups"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "created_by", "idempotency_key", name="uq_ops_backup_request"
        ),
        CheckConstraint(
            "status IN ('queued','running','completed','failed','uncertain','deleting','deleted')",
            name="ck_ops_backup_status",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(120))
    blob_key: Mapped[str | None] = mapped_column(String(512))
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    manifest: Mapped[dict | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(64))
    delete_action_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("ops_actions.id", ondelete="RESTRICT")
    )
