"""System capability defaults and provider catalog resolution."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.models import (
    CAPABILITIES,
    DEFAULT_ROW_ID,
    ModelDefaults,
    Provider,
)
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.schemas import DefaultsUpdateRequest
from qnu.domains.workspaces.access import actor_ref, is_platform_admin, resolve_workspace_access
from qnu.platform.errors import AppException, Conflict

CAPABILITY_FIELDS = {name: (f"{name}_provider_id", f"{name}_model") for name in CAPABILITIES}


class CatalogService:
    async def get_defaults(self, db: AsyncSession) -> ModelDefaults | None:
        return await db.get(ModelDefaults, DEFAULT_ROW_ID)

    async def system_default_for(self, db: AsyncSession, capability: str) -> str | None:
        row = await self.get_defaults(db)
        if row is None:
            return None
        field = f"{capability}_provider_id"
        return getattr(row, field, None)

    async def system_defaults(self, db: AsyncSession) -> dict[str, str]:
        row = await self.get_defaults(db)
        if row is None:
            return {}
        return {
            capability: getattr(row, f"{capability}_provider_id")
            for capability in CAPABILITIES
            if getattr(row, f"{capability}_provider_id")
        }

    async def update_defaults(
        self, db: AsyncSession, req: DefaultsUpdateRequest, actor: AuthActor
    ) -> ModelDefaults:
        require_model_admin(actor)
        await db.execute(insert(ModelDefaults).values(id=DEFAULT_ROW_ID).on_conflict_do_nothing())
        row = (
            await db.execute(
                select(ModelDefaults).where(ModelDefaults.id == DEFAULT_ROW_ID).with_for_update()
            )
        ).scalar_one()
        payload = req.model_dump(exclude_unset=True)
        for capability, (provider_field, model_field) in CAPABILITY_FIELDS.items():
            if provider_field not in payload and model_field not in payload:
                continue
            provider_id = payload.get(provider_field, getattr(row, provider_field))
            if not provider_id:
                if payload.get(model_field):
                    raise Conflict("Model phải có provider.", code="default_provider_required")
                setattr(row, provider_field, None)
                setattr(row, model_field, None)
                continue
            provider = await provider_service.require_capability(db, provider_id, capability)
            if payload.get(model_field) not in (None, provider.model_name):
                raise Conflict("Model không khớp provider đã đăng ký.", code="model_mismatch")
            setattr(row, provider_field, provider.id)
            setattr(row, model_field, provider.model_name)
        row.updated_by = actor_ref(actor)
        record_event(db, actor, "defaults.updated", fields=list(payload))
        await db.commit()
        await db.refresh(row)
        return row

    async def visible_providers(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str | None = None
    ) -> list[Provider]:
        """Active providers an actor may select through a workspace they belong to."""
        if workspace_id is not None:
            await resolve_workspace_access(db, actor, workspace_id)
        elif not is_platform_admin(actor):
            raise AppException("Cần chọn workspace.", code="workspace_required", status_code=400)
        return await provider_service.list(db, active_only=True)

    async def resolve_provider(
        self,
        db: AsyncSession,
        actor: AuthActor,
        workspace_id: str,
        capability: str,
        provider_id: str | None = None,
    ) -> Provider:
        await resolve_workspace_access(db, actor, workspace_id)
        return await self.resolve_workspace_provider(db, workspace_id, capability, provider_id)

    async def resolve_workspace_provider(
        self,
        db: AsyncSession,
        workspace_id: str,
        capability: str,
        provider_id: str | None = None,
    ) -> Provider:
        """Resolve an active provider for a capability without an HTTP actor.

        Trusted background work calls this after it has already re-checked workspace
        access; the system-default, explicit-target and capability rules stay
        identical to the interactive path.
        """
        return await self.resolve_workspace_target(db, workspace_id, capability, provider_id)

    async def resolve_workspace_target(
        self,
        db: AsyncSession,
        workspace_id: str,
        capability: str,
        provider_id: str | None = None,
    ) -> Provider:
        """Return the active provider, preferring an explicit target over the system default."""
        if capability not in CAPABILITIES:
            raise AppException("Capability không hợp lệ.", code="capability_invalid")
        if provider_id is None:
            provider_id = await self.system_default_for(db, capability)
        if not provider_id:
            raise Conflict(
                "Chưa chọn model mặc định cho chức năng này.", code="model_not_configured"
            )
        return await provider_service.require_capability(db, provider_id, capability)


catalog_service = CatalogService()
