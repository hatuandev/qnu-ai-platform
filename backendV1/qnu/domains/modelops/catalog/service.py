"""Workspace catalog, centrally granted providers and capability defaults."""

from __future__ import annotations

from sqlalchemy import delete, select
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
    WorkspaceAllowedProvider,
    WorkspaceModelDefault,
)
from qnu.domains.modelops.providers.service import active_connection, provider_service
from qnu.domains.modelops.schemas import AllowlistUpdateRequest, DefaultsUpdateRequest
from qnu.domains.workspaces.access import actor_ref, is_platform_admin, resolve_workspace_access
from qnu.domains.workspaces.public_api import record_workspace_event
from qnu.platform.errors import AppException, Conflict, EntityNotFound

CAPABILITY_FIELDS = {name: (f"{name}_provider_id", f"{name}_model") for name in CAPABILITIES}


class CatalogService:
    async def get_defaults(self, db: AsyncSession) -> ModelDefaults | None:
        return await db.get(ModelDefaults, DEFAULT_ROW_ID)

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
        if workspace_id is None:
            if is_platform_admin(actor):
                return await provider_service.list(db, active_only=True)
            raise AppException("Cần chọn workspace.", code="workspace_required", status_code=400)
        await resolve_workspace_access(db, actor, workspace_id)
        stmt = (
            select(Provider)
            .join(WorkspaceAllowedProvider)
            .where(
                WorkspaceAllowedProvider.workspace_id == workspace_id,
                Provider.is_active.is_(True),
                Provider.is_connection.is_(False),
                active_connection(),
            )
            .order_by(Provider.priority, Provider.name)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_allowlist(
        self, db: AsyncSession, workspace_id: str
    ) -> list[tuple[Provider, bool]]:
        stmt = (
            select(Provider, WorkspaceAllowedProvider.is_default)
            .join(WorkspaceAllowedProvider)
            .where(WorkspaceAllowedProvider.workspace_id == workspace_id)
            .order_by(Provider.priority, Provider.name)
        )
        return [(row[0], bool(row[1])) for row in (await db.execute(stmt)).all()]

    async def workspace_defaults(self, db: AsyncSession, workspace_id: str) -> dict[str, str]:
        rows = (
            (
                await db.execute(
                    select(WorkspaceModelDefault).where(
                        WorkspaceModelDefault.workspace_id == workspace_id
                    )
                )
            )
            .scalars()
            .all()
        )
        return {row.capability: row.provider_id for row in rows}

    async def _replace_defaults(
        self, db: AsyncSession, workspace_id: str, defaults: dict[str, str]
    ) -> None:
        granted = {
            provider.id: provider for provider, _ in await self.get_allowlist(db, workspace_id)
        }
        for capability, provider_id in defaults.items():
            if provider_id not in granted:
                raise Conflict(
                    "Model phải nằm trong danh sách đã cấp.", code="allowlist_default_not_allowed"
                )
            await provider_service.require_capability(db, provider_id, capability)
        await db.execute(
            delete(WorkspaceModelDefault).where(WorkspaceModelDefault.workspace_id == workspace_id)
        )
        for capability, provider_id in defaults.items():
            db.add(
                WorkspaceModelDefault(
                    workspace_id=workspace_id, capability=capability, provider_id=provider_id
                )
            )
        for grant in (
            await db.execute(
                select(WorkspaceAllowedProvider).where(
                    WorkspaceAllowedProvider.workspace_id == workspace_id
                )
            )
        ).scalars():
            grant.is_default = grant.provider_id == defaults.get("chat")

    async def set_allowlist(
        self, db: AsyncSession, workspace_id: str, req: AllowlistUpdateRequest, actor: AuthActor
    ) -> list[tuple[Provider, bool]]:
        require_model_admin(actor)
        await resolve_workspace_access(db, actor, workspace_id, for_update=True)
        providers = [
            await provider_service.get(db, provider_id) for provider_id in req.provider_ids
        ]
        if any(provider.is_connection for provider in providers):
            raise Conflict("Cấp quyền theo model cụ thể của nhà cung cấp.", code="model_required")
        defaults = dict(req.defaults)
        if req.default_provider_id:
            if defaults.get("chat", req.default_provider_id) != req.default_provider_id:
                raise Conflict("Hai model chat mặc định khác nhau.", code="default_conflict")
            defaults["chat"] = req.default_provider_id
        if any(value not in req.provider_ids for value in defaults.values()):
            raise Conflict("Model mặc định chưa được cấp.", code="allowlist_default_not_allowed")
        await db.execute(
            delete(WorkspaceModelDefault).where(WorkspaceModelDefault.workspace_id == workspace_id)
        )
        await db.execute(
            delete(WorkspaceAllowedProvider).where(
                WorkspaceAllowedProvider.workspace_id == workspace_id
            )
        )
        for provider in providers:
            db.add(WorkspaceAllowedProvider(workspace_id=workspace_id, provider_id=provider.id))
        await db.flush()
        await self._replace_defaults(db, workspace_id, defaults)
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="models.granted",
            detail={"provider_ids": req.provider_ids, "defaults": defaults},
        )
        await db.commit()
        return await self.get_allowlist(db, workspace_id)

    async def set_workspace_defaults(
        self, db: AsyncSession, actor: AuthActor, workspace_id: str, defaults: dict[str, str]
    ) -> None:
        await resolve_workspace_access(
            db, actor, workspace_id, required_roles=("admin",), for_update=True
        )
        await self._replace_defaults(db, workspace_id, defaults)
        await record_workspace_event(
            db,
            workspace_id=workspace_id,
            actor=actor,
            action="models.defaults_updated",
            detail=defaults,
        )
        await db.commit()

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
        """Resolve a granted, active provider for a capability without an HTTP actor.

        Trusted background work calls this after it has already re-checked workspace
        access; the allowlist, default and capability rules stay identical to the
        interactive path.
        """
        if capability not in CAPABILITIES:
            raise AppException("Capability không hợp lệ.", code="capability_invalid")
        if provider_id is None:
            provider_id = (await self.workspace_defaults(db, workspace_id)).get(capability)
        if not provider_id:
            raise Conflict(
                "Chưa chọn model mặc định cho chức năng này.", code="model_not_configured"
            )
        granted = await db.get(WorkspaceAllowedProvider, (workspace_id, provider_id))
        if granted is None:
            raise EntityNotFound("Model chưa được cấp cho workspace.", code="provider_not_found")
        return await provider_service.require_capability(db, provider_id, capability)


catalog_service = CatalogService()
