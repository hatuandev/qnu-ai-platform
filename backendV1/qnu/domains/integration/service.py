"""Service layer for external applications and API key lifecycle."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.assistants.models import Assistant
from qnu.domains.identity.actor import AuthActor
from qnu.domains.integration.models import AppApiKey, AppClient, AppRequestLog, utcnow
from qnu.domains.integration.schemas import (
    AppApiKeyCreate,
    AppApiKeyResponse,
    AppApiKeyRotateRequest,
    AppApiKeyStatusUpdate,
    AppClientCreate,
)
from qnu.domains.ocr.ids import new_id
from qnu.domains.workspaces.access import actor_ref, resolve_workspace_access
from qnu.domains.workspaces.models import WorkspaceMember
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import Conflict, EntityNotFound


def generate_key_secret() -> tuple[str, str, str]:
    """Generate cryptographically secure 32-byte secret with live prefix.
    Returns (raw_secret, key_hash, key_prefix).
    """
    token = secrets.token_urlsafe(32)
    raw_secret = f"qnu_live_{token}"
    key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
    key_prefix = f"qnu_live_{token[:8]}...{token[-4:]}"
    return raw_secret, key_hash, key_prefix


class IntegrationService:
    async def create_app(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        req: AppClientCreate,
        *,
        commit: bool = True,
    ) -> AppClient:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        app = AppClient(
            id=new_id("app"),
            workspace_id=workspace_id,
            name=req.name.strip(),
            description=req.description.strip(),
            status="active",
            created_by=actor_ref(actor),
        )
        db.add(app)

        # Register machine principal as a real workspace member with 'member' role
        # so resolve_workspace_access passes cleanly without AI.Admin bypass
        machine_ref = f"app:{app.id}"
        member = WorkspaceMember(
            id=new_id("mem"),
            workspace_id=workspace_id,
            actor_ref=machine_ref,
            role="member",
            status="active",
            invited_by=actor_ref(actor),
        )
        db.add(member)

        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="integration.app.created",
            detail={"app_id": app.id, "app_name": app.name},
        )
        if commit:
            await db.commit()
            await db.refresh(app)
        else:
            await db.flush()
        return app

    async def list_apps(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str
    ) -> list[AppClient]:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        stmt = (
            select(AppClient)
            .where(AppClient.workspace_id == workspace_id, AppClient.status != "revoked")
            .order_by(AppClient.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def create_key(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        req: AppApiKeyCreate,
        idempotency_key: str | None = None,
    ) -> tuple[AppApiKey, str, str]:
        """Create a new API key. Returns (key_record, raw_secret, app_name)."""
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))

        # Check idempotency
        effective_idem = idempotency_key or req.idempotency_key
        if effective_idem:
            stmt_idem = select(AppApiKey).where(
                AppApiKey.workspace_id == workspace_id,
                AppApiKey.idempotency_key == effective_idem,
            )
            existing = (await db.execute(stmt_idem)).scalars().first()
            if existing is not None:
                raise Conflict(
                    "Khóa đã được tạo theo Idempotency-Key này. Vì lý do an toàn bảo mật, "
                    "secret key chỉ được hiển thị duy nhất một lần khi tạo và không được lưu lại dưới dạng plaintext.",
                    code="idempotency_conflict",
                )

        # Resolve or create AppClient
        app: AppClient | None = None
        if req.app_id:
            app = await db.get(AppClient, req.app_id)
            if not app or app.workspace_id != workspace_id:
                raise EntityNotFound(
                    "Không tìm thấy ứng dụng trong workspace.", code="app_not_found"
                )
            if app.status != "active":
                raise Conflict("Ứng dụng không ở trạng thái hoạt động.", code="app_inactive")
        else:
            app_name = (req.app_name or req.name).strip()
            app = await self.create_app(
                db,
                actor,
                workspace_id,
                AppClientCreate(name=app_name, description="Tạo tự động cùng API key"),
                commit=False,
            )

        # Validate allowed assistants within workspace
        if req.allowed_assistant_ids:
            stmt_ast = select(Assistant.id).where(
                Assistant.workspace_id == workspace_id,
                Assistant.id.in_(req.allowed_assistant_ids),
                Assistant.is_active.is_(True),
            )
            valid_ids = set((await db.execute(stmt_ast)).scalars().all())
            invalid = set(req.allowed_assistant_ids) - valid_ids
            if invalid:
                raise Conflict(
                    f"Trợ lý không hợp lệ hoặc không thuộc workspace: {', '.join(invalid)}",
                    code="invalid_assistant_scope",
                )

        raw_secret, key_hash, key_prefix = generate_key_secret()
        expires_at = utcnow() + timedelta(days=req.expires_in_days) if req.expires_in_days else None

        key = AppApiKey(
            id=new_id("key"),
            app_id=app.id,
            workspace_id=workspace_id,
            name=req.name.strip(),
            key_prefix=key_prefix,
            key_hash=key_hash,
            status="active",
            allowed_assistant_ids=req.allowed_assistant_ids,
            rate_limit_rpm=req.rate_limit_rpm,
            rate_limit_rpd=req.rate_limit_rpd,
            expires_at=expires_at,
            idempotency_key=effective_idem,
            created_by=actor_ref(actor),
        )
        db.add(key)

        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="integration.key.created",
            detail={"key_id": key.id, "key_prefix": key_prefix, "app_id": app.id},
        )
        await db.commit()
        await db.refresh(key)
        return key, raw_secret, app.name

    async def list_keys(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str
    ) -> list[AppApiKeyResponse]:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        stmt = (
            select(AppApiKey, AppClient.name.label("app_name"))
            .join(AppClient, AppApiKey.app_id == AppClient.id)
            .where(AppApiKey.workspace_id == workspace_id)
            .order_by(AppApiKey.created_at.desc())
        )
        results = (await db.execute(stmt)).all()
        responses: list[AppApiKeyResponse] = []
        for key_row, app_name in results:
            responses.append(
                AppApiKeyResponse(
                    id=key_row.id,
                    app_id=key_row.app_id,
                    app_name=app_name,
                    workspace_id=key_row.workspace_id,
                    name=key_row.name,
                    key_prefix=key_row.key_prefix,
                    status=key_row.status,
                    allowed_assistant_ids=key_row.allowed_assistant_ids,
                    rate_limit_rpm=key_row.rate_limit_rpm,
                    rate_limit_rpd=key_row.rate_limit_rpd,
                    expires_at=key_row.expires_at,
                    last_used_at=key_row.last_used_at,
                    rotated_from_key_id=key_row.rotated_from_key_id,
                    revoked_at=key_row.revoked_at,
                    revoked_reason=key_row.revoked_reason,
                    created_by=key_row.created_by,
                    created_at=key_row.created_at,
                )
            )
        return responses

    async def update_key_status(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        key_id: str,
        req: AppApiKeyStatusUpdate,
    ) -> AppApiKeyResponse:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        key = await self.lock_key(db, workspace_id, key_id)
        if not key or key.workspace_id != workspace_id:
            raise EntityNotFound("Không tìm thấy API key.", code="key_not_found")
        if key.status == "revoked":
            raise Conflict("Không thể đổi trạng thái khóa đã bị thu hồi.", code="key_revoked")

        key.status = req.status
        if req.status == "suspended":
            key.revoked_reason = req.reason or "Tạm dừng bởi quản trị viên"

        app = await db.get(AppClient, key.app_id)
        app_name = app.name if app else "Unknown"

        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action=f"integration.key.{req.status}",
            detail={"key_id": key.id, "reason": req.reason},
        )
        await db.commit()
        await db.refresh(key)

        return AppApiKeyResponse(
            id=key.id,
            app_id=key.app_id,
            app_name=app_name,
            workspace_id=key.workspace_id,
            name=key.name,
            key_prefix=key.key_prefix,
            status=key.status,
            allowed_assistant_ids=key.allowed_assistant_ids,
            rate_limit_rpm=key.rate_limit_rpm,
            rate_limit_rpd=key.rate_limit_rpd,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            rotated_from_key_id=key.rotated_from_key_id,
            revoked_at=key.revoked_at,
            revoked_reason=key.revoked_reason,
            created_by=key.created_by,
            created_at=key.created_at,
        )

    async def rotate_key(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        key_id: str,
        req: AppApiKeyRotateRequest,
    ) -> tuple[AppApiKey, str, str]:
        """Rotate existing key by revoking it and generating a new active key. Returns (new_key, raw_secret, app_name)."""
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        old_key = await self.lock_key(db, workspace_id, key_id)
        if not old_key or old_key.workspace_id != workspace_id:
            raise EntityNotFound("Không tìm thấy API key cần xoay.", code="key_not_found")
        if old_key.status == "revoked":
            raise Conflict(
                "Khóa đã bị thu hồi trước đó, không thể xoay.", code="key_already_revoked"
            )

        # Check idempotency for rotation
        if req.idempotency_key:
            stmt_idem = select(AppApiKey).where(
                AppApiKey.workspace_id == workspace_id,
                AppApiKey.idempotency_key == req.idempotency_key,
            )
            existing = (await db.execute(stmt_idem)).scalars().first()
            if existing is not None:
                raise Conflict(
                    "Thao tác xoay khóa đã được xử lý theo Idempotency-Key này. "
                    "Vì lý do an toàn, secret mới chỉ hiển thị duy nhất một lần.",
                    code="idempotency_conflict",
                )

        app = await db.get(AppClient, old_key.app_id)
        if not app or app.status != "active":
            raise Conflict("Ứng dụng không ở trạng thái hoạt động.", code="app_inactive")

        # Revoke old key
        old_key.status = "revoked"
        old_key.revoked_at = utcnow()
        old_key.revoked_reason = "Đã xoay sang khóa mới"

        # Generate new key
        raw_secret, key_hash, key_prefix = generate_key_secret()
        expires_at = (
            utcnow() + timedelta(days=req.expires_in_days)
            if req.expires_in_days
            else old_key.expires_at
        )

        new_key = AppApiKey(
            id=new_id("key"),
            app_id=old_key.app_id,
            workspace_id=workspace_id,
            name=f"{old_key.name} (Rotated)",
            key_prefix=key_prefix,
            key_hash=key_hash,
            status="active",
            allowed_assistant_ids=old_key.allowed_assistant_ids,
            rate_limit_rpm=old_key.rate_limit_rpm,
            rate_limit_rpd=old_key.rate_limit_rpd,
            expires_at=expires_at,
            rotated_from_key_id=old_key.id,
            idempotency_key=req.idempotency_key,
            created_by=actor_ref(actor),
        )
        db.add(new_key)

        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="integration.key.rotated",
            detail={"old_key_id": old_key.id, "new_key_id": new_key.id},
        )
        await db.commit()
        await db.refresh(new_key)

        return new_key, raw_secret, app.name

    async def revoke_key(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        key_id: str,
        reason: str,
    ) -> AppApiKeyResponse:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        key = await self.lock_key(db, workspace_id, key_id)
        if not key or key.workspace_id != workspace_id:
            raise EntityNotFound("Không tìm thấy API key.", code="key_not_found")
        if key.status == "revoked":
            raise Conflict("Khóa đã bị thu hồi trước đó.", code="key_already_revoked")

        key.status = "revoked"
        key.revoked_at = utcnow()
        key.revoked_reason = reason.strip()

        app = await db.get(AppClient, key.app_id)
        app_name = app.name if app else "Unknown"

        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="integration.key.revoked",
            detail={"key_id": key.id, "reason": reason},
        )
        await db.commit()
        await db.refresh(key)

        return AppApiKeyResponse(
            id=key.id,
            app_id=key.app_id,
            app_name=app_name,
            workspace_id=key.workspace_id,
            name=key.name,
            key_prefix=key.key_prefix,
            status=key.status,
            allowed_assistant_ids=key.allowed_assistant_ids,
            rate_limit_rpm=key.rate_limit_rpm,
            rate_limit_rpd=key.rate_limit_rpd,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            rotated_from_key_id=key.rotated_from_key_id,
            revoked_at=key.revoked_at,
            revoked_reason=key.revoked_reason,
            created_by=key.created_by,
            created_at=key.created_at,
        )

    async def lock_key(self, db: AsyncSession, workspace_id: str, key_id: str) -> AppApiKey | None:
        return await db.scalar(
            select(AppApiKey)
            .where(
                AppApiKey.id == key_id,
                AppApiKey.workspace_id == workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def list_logs(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str, limit: int = 50
    ) -> list[AppRequestLog]:
        await resolve_workspace_access(db, actor, workspace_id, required_roles=("admin",))
        stmt = (
            select(AppRequestLog)
            .where(AppRequestLog.workspace_id == workspace_id)
            .order_by(AppRequestLog.created_at.desc())
            .limit(limit)
        )
        return list((await db.execute(stmt)).scalars().all())


integration_service = IntegrationService()
