"""Provider registry: endpoint + model + capabilities."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.access import require_model_admin
from qnu.domains.modelops.audit import record_event
from qnu.domains.modelops.capacity.automatic import operational_budget
from qnu.domains.modelops.capacity.schemas import CapacityBasis
from qnu.domains.modelops.capacity.service import invalidate_capacity, read_capacity, set_capacity
from qnu.domains.modelops.embedding.configuration import read_dimension, set_dimension
from qnu.domains.modelops.models import Provider
from qnu.domains.modelops.reasoning import (
    EXTRA_CONFIG_KEY,
    ReasoningPolicy,
    parse_policy,
    trace_for,
)
from qnu.domains.modelops.schemas import ProviderCreateRequest, ProviderUpdateRequest
from qnu.domains.workspaces.access import actor_ref
from qnu.platform.errors import AppException, Conflict, EntityNotFound
from qnu.platform.network_policy import assert_allowed_endpoint


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def active_connection():
    parent = aliased(Provider)
    return or_(
        Provider.parent_id.is_(None),
        exists(
            select(parent.id).where(
                parent.id == Provider.parent_id,
                parent.is_connection.is_(True),
                parent.is_active.is_(True),
            )
        ),
    )


class ProviderService:
    async def create(
        self,
        db: AsyncSession,
        req: ProviderCreateRequest,
        actor: AuthActor,
        *,
        parent_id: str | None = None,
        capacity_basis: CapacityBasis = "operator_configured",
        capacity_source: dict | None = None,
    ) -> Provider:
        require_model_admin(actor)
        if req.provider_type == "mineru" and (
            set(req.capabilities) != {"ocr"} or req.token_limits is not None
        ):
            raise AppException(
                "MinerU chỉ hỗ trợ OCR PDF, không khai báo token LLM.",
                code="provider_capability_mismatch",
                status_code=422,
            )
        assert_allowed_endpoint(req.base_url, allow_private=True)
        existing = (
            (await db.execute(select(Provider.id).where(Provider.name == req.name)))
            .scalars()
            .first()
        )
        if existing is not None:
            raise Conflict(f"Provider '{req.name}' đã tồn tại.", code="provider_name_exists")
        provider = Provider(
            parent_id=parent_id,
            id=_new_id("prv"),
            name=req.name,
            provider_type=req.provider_type,
            base_url=req.base_url,
            model_name=req.model_name,
            capabilities=list(req.capabilities),
            is_active=True,
            priority=req.priority,
            timeout_seconds=req.timeout_seconds,
            created_by=actor_ref(actor) or None,
        )
        if req.token_limits is not None:
            set_capacity(provider, req.token_limits, basis=capacity_basis)
        if req.embedding_dimension is not None:
            set_dimension(provider, req.embedding_dimension, basis=capacity_basis)
        if capacity_source:
            provider.extra_config = {
                **(provider.extra_config or {}),
                "capacity_discovery_v1": capacity_source,
            }
        db.add(provider)
        record_event(db, actor, "provider.created", provider.id, list(req.model_fields_set))
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise Conflict("Tên provider đã tồn tại.", code="provider_name_exists") from exc
        await db.refresh(provider)
        return provider

    async def get(self, db: AsyncSession, provider_id: str) -> Provider:
        provider = await db.get(Provider, provider_id)
        if provider is None:
            raise EntityNotFound("Không tìm thấy provider.", code="provider_not_found")
        return provider

    async def list(self, db: AsyncSession, *, active_only: bool = False) -> list[Provider]:
        stmt = (
            select(Provider)
            .where(Provider.is_connection.is_(False))
            .order_by(Provider.priority.asc(), Provider.created_at.asc())
        )
        if active_only:
            stmt = stmt.where(Provider.is_active.is_(True), active_connection())
        return list((await db.execute(stmt)).scalars().all())

    async def update(
        self, db: AsyncSession, provider: Provider, req: ProviderUpdateRequest, actor: AuthActor
    ) -> Provider:
        require_model_admin(actor)
        provider = (
            await db.execute(
                select(Provider)
                .where(Provider.id == provider.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        if provider.provider_type == "mineru" and (
            (req.capabilities is not None and set(req.capabilities) != {"ocr"})
            or req.token_limits is not None
        ):
            raise AppException(
                "MinerU chỉ hỗ trợ OCR PDF, không khai báo token LLM.",
                code="provider_capability_mismatch",
                status_code=422,
            )
        identity = (provider.base_url.rstrip("/"), provider.model_name)
        if provider.is_connection:
            raise Conflict(
                "Sửa nhà cung cấp qua API connections.", code="connection_update_required"
            )
        if provider.parent_id and req.base_url is not None:
            parent = await self.get(db, provider.parent_id)
            if req.base_url.rstrip("/") != parent.base_url.rstrip("/"):
                raise Conflict(
                    "Endpoint do nhà cung cấp quản lý; không đổi riêng trên model.",
                    code="model_connection_mismatch",
                )
        if req.base_url is not None:
            assert_allowed_endpoint(req.base_url, allow_private=True)
            provider.base_url = req.base_url
        if req.name is not None and req.name != provider.name:
            clash = (
                (await db.execute(select(Provider.id).where(Provider.name == req.name)))
                .scalars()
                .first()
            )
            if clash is not None:
                raise Conflict(f"Provider '{req.name}' đã tồn tại.", code="provider_name_exists")
            provider.name = req.name
        if req.model_name is not None:
            provider.model_name = req.model_name
        if req.capabilities is not None:
            provider.capabilities = list(req.capabilities)
        if req.is_active is not None:
            provider.is_active = req.is_active
        if req.priority is not None:
            provider.priority = req.priority
        if req.timeout_seconds is not None:
            provider.timeout_seconds = req.timeout_seconds
        if identity != (provider.base_url.rstrip("/"), provider.model_name):
            invalidate_capacity(provider)
        if "token_limits" in req.model_fields_set:
            set_capacity(provider, req.token_limits)
        if "embedding_dimension" in req.model_fields_set:
            set_dimension(provider, req.embedding_dimension)
        record_event(db, actor, "provider.updated", provider.id, list(req.model_fields_set))
        await db.commit()
        await db.refresh(provider)
        return provider

    async def read_reasoning(self, db: AsyncSession, provider_id: str) -> Provider:
        provider = await self.get(db, provider_id)
        return provider

    async def set_reasoning(
        self,
        db: AsyncSession,
        provider_id: str,
        policy: ReasoningPolicy,
        actor: AuthActor,
    ) -> Provider:
        """Persist a declared reasoning contract; never touches model/endpoint/keys."""
        require_model_admin(actor)
        provider = (
            await db.execute(
                select(Provider)
                .where(Provider.id == provider_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if provider is None:
            raise EntityNotFound("Không tìm thấy provider.", code="provider_not_found")
        if provider.is_connection:
            raise Conflict(
                "Khai báo reasoning trên model, không trên nhà cung cấp.",
                code="model_required",
            )
        extra = dict(provider.extra_config or {})
        if policy.mode == "server_default":
            extra.pop(EXTRA_CONFIG_KEY, None)
        else:
            extra[EXTRA_CONFIG_KEY] = policy.model_dump(mode="json")
        provider.extra_config = extra
        record_event(
            db,
            actor,
            "provider.reasoning_updated",
            provider.id,
            ["mode", "parameter", "level", "verified"],
        )
        await db.commit()
        await db.refresh(provider)
        return provider

    async def require_capability(
        self, db: AsyncSession, provider_id: str, capability: str
    ) -> Provider:
        provider = await self.get(db, provider_id)
        if provider.is_connection:
            raise Conflict(
                "Chọn model của nhà cung cấp, không chọn nhà cung cấp trực tiếp.",
                code="model_required",
            )
        if provider.parent_id:
            parent = await self.get(db, provider.parent_id)
            if not parent.is_connection or not parent.is_active:
                raise Conflict("Nhà cung cấp đang tắt.", code="provider_inactive")
        if not provider.is_active:
            raise Conflict(f"Provider '{provider.name}' đang tắt.", code="provider_inactive")
        if capability not in (provider.capabilities or []):
            raise Conflict(
                f"Provider '{provider.name}' không có capability '{capability}'.",
                code="provider_capability_mismatch",
            )
        return provider


def provider_payload(provider: Provider) -> dict[str, Any]:
    """Serialize a provider without leaking configuration secrets."""
    capacity = read_capacity(provider)
    dimension, dimension_status = read_dimension(provider)
    policy = parse_policy((provider.extra_config or {}).get(EXTRA_CONFIG_KEY))
    return {
        "is_connection": provider.is_connection,
        "parent_id": provider.parent_id,
        "id": provider.id,
        "name": provider.name,
        "provider_type": provider.provider_type,
        "base_url": provider.base_url,
        "model_name": provider.model_name,
        "capabilities": list(provider.capabilities or []),
        "is_active": provider.is_active,
        "priority": provider.priority,
        "timeout_seconds": provider.timeout_seconds,
        "token_limits": capacity.token_limits.model_dump() if capacity.token_limits else None,
        "capacity_status": capacity.status,
        "capacity_basis": capacity.basis,
        "operational_budgets": {
            capability: operational_budget(capacity, capability).model_dump(mode="json")
            for capability in (provider.capabilities or [])
        }
        if provider.provider_type != "mineru"
        else {},
        "field_sources": getattr(capacity, "field_sources", {}) or {},
        "embedding_dimension": dimension,
        "embedding_dimension_status": dimension_status,
        "reasoning": policy.public_dict() if policy is not None else None,
        "reasoning_status": policy.status if policy is not None else "not_configured",
        "created_at": provider.created_at,
        "updated_at": provider.updated_at,
    }


def reasoning_payload(provider: Provider) -> dict[str, Any]:
    """Current contract plus the effective decision for every task this model serves."""
    policy = parse_policy((provider.extra_config or {}).get(EXTRA_CONFIG_KEY))
    return {
        "provider_id": provider.id,
        "status": policy.status if policy is not None else "not_configured",
        "policy": policy.model_dump(mode="json") if policy is not None else None,
        "effective": trace_for(policy),
    }


provider_service = ProviderService()
