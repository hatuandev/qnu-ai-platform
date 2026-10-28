"""ModelOps HTTP API: providers, credentials, defaults and workspace allowlists."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.diagnostics.summary import provider_summaries
from qnu.domains.modelops.keys.service import key_service
from qnu.domains.modelops.models import ModelDefaults, Provider, ProviderKey
from qnu.domains.modelops.providers.service import provider_payload, provider_service
from qnu.domains.modelops.schemas import (
    AllowedProviderItem,
    AllowlistResponse,
    AllowlistUpdateRequest,
    CatalogItem,
    DefaultsResponse,
    DefaultsUpdateRequest,
    KeyAuditResponse,
    KeyCreateRequest,
    KeyResponse,
    KeyRevokeRequest,
    KeyRotateRequest,
    ModelOpsEventResponse,
    ProviderCreateRequest,
    ProviderResponse,
    ProviderSummaryItem,
    ProviderUpdateRequest,
    WorkspaceDefaultsRequest,
)
from qnu.domains.modelops.usage.service import usage_service
from qnu.domains.workspaces.access import resolve_workspace_access

router = APIRouter(prefix="/modelops", tags=["ModelOps"])
workspace_router = APIRouter(prefix="/workspaces", tags=["Workspaces · Model allowlist"])


@router.get("/events", response_model=list[ModelOpsEventResponse])
async def configuration_events(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> list[ModelOpsEventResponse]:
    return [
        ModelOpsEventResponse.model_validate(row)
        for row in await usage_service.configuration_events(db, actor, limit)
    ]


def _provider_out(provider: Provider) -> ProviderResponse:
    return ProviderResponse(**provider_payload(provider))


def _key_out(key: ProviderKey) -> KeyResponse:
    return KeyResponse(
        model_ids=key.model_ids,
        id=key.id,
        provider_id=key.provider_id,
        name=key.name,
        masked_hint=key.masked_hint,
        lease_until=key.lease_until,
        cooldown_until=key.cooldown_until,
        consecutive_failures=key.consecutive_failures,
        status=key.status,
        priority=key.priority,
        created_at=key.created_at,
        updated_at=key.updated_at,
    )


async def _allowlist_out(db: AsyncSession, workspace_id: str) -> AllowlistResponse:
    defaults = await catalog_service.workspace_defaults(db, workspace_id)
    return AllowlistResponse(
        workspace_id=workspace_id,
        providers=[
            AllowedProviderItem(
                provider_id=p.id,
                name=p.name,
                capabilities=p.capabilities,
                is_active=p.is_active,
                is_default=default,
                default_capabilities=[cap for cap, pid in defaults.items() if pid == p.id],
            )
            for p, default in await catalog_service.get_allowlist(db, workspace_id)
        ],
    )


def _defaults_out(row: ModelDefaults | None) -> DefaultsResponse:
    if row is None:
        return DefaultsResponse()
    return DefaultsResponse(
        chat_provider_id=row.chat_provider_id,
        chat_model=row.chat_model,
        embedding_provider_id=row.embedding_provider_id,
        embedding_model=row.embedding_model,
        rerank_provider_id=row.rerank_provider_id,
        rerank_model=row.rerank_model,
        ocr_provider_id=row.ocr_provider_id,
        ocr_model=row.ocr_model,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
    )


@router.post("/providers/{provider_id}/keys/{key_id}/rotate", response_model=KeyResponse)
async def rotate_key(
    provider_id: str,
    key_id: str,
    body: KeyRotateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> KeyResponse:
    return _key_out(await key_service.rotate_key(db, provider_id, key_id, body, actor))


@router.get("/providers/{provider_id}/key-events", response_model=list[KeyAuditResponse])
async def key_events(
    provider_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> list[KeyAuditResponse]:
    await provider_service.get(db, provider_id)
    return [
        KeyAuditResponse.model_validate(row)
        for row in await key_service.audit(db, provider_id, limit)
    ]


@router.post(
    "/providers",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký provider + model",
)
async def create_provider(
    body: ProviderCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> ProviderResponse:
    provider = await provider_service.create(db, body, actor)
    return _provider_out(provider)


@router.get("/providers", response_model=list[ProviderResponse], summary="Provider người gọi thấy")
async def list_providers(
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> list[ProviderResponse]:
    providers = await provider_service.list(db)
    return [_provider_out(item) for item in providers]


@router.get("/providers-summary", response_model=list[ProviderSummaryItem], summary="Tổng hợp providers kèm số lượng keys và diagnostics")
async def list_providers_summary(
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> list[ProviderSummaryItem]:
    return await provider_summaries(db)


@router.get(
    "/providers/{provider_id}", response_model=ProviderResponse, summary="Chi tiết provider"
)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> ProviderResponse:
    provider = await provider_service.get(db, provider_id)
    return _provider_out(provider)


@router.patch(
    "/providers/{provider_id}", response_model=ProviderResponse, summary="Cập nhật provider"
)
async def update_provider(
    provider_id: str,
    body: ProviderUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> ProviderResponse:
    provider = await provider_service.get(db, provider_id)
    updated = await provider_service.update(db, provider, body, actor)
    return _provider_out(updated)


@router.post(
    "/providers/{provider_id}/keys",
    response_model=KeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm credential (mã hoá, chỉ trả về dạng che)",
)
async def create_key(
    provider_id: str,
    body: KeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> KeyResponse:
    provider = await provider_service.get(db, provider_id)
    key = await key_service.add_key(db, provider, body, actor)
    return _key_out(key)


@router.get(
    "/providers/{provider_id}/keys",
    response_model=list[KeyResponse],
    summary="Danh sách credential (đã che)",
)
async def list_keys(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> list[KeyResponse]:
    await provider_service.get(db, provider_id)
    keys = await key_service.list_keys(db, provider_id)
    return [_key_out(item) for item in keys]


@router.post(
    "/providers/{provider_id}/keys/{key_id}/revoke",
    response_model=KeyResponse,
    summary="Thu hồi credential kèm audit",
)
async def revoke_key(
    provider_id: str,
    key_id: str,
    body: KeyRevokeRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> KeyResponse:
    key = await key_service.revoke_key(db, provider_id, key_id, actor, body.reason)
    return _key_out(key)


@router.get("/defaults", response_model=DefaultsResponse, summary="Model mặc định hệ thống")
async def get_defaults(
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> DefaultsResponse:
    return _defaults_out(await catalog_service.get_defaults(db))


@router.put("/defaults", response_model=DefaultsResponse, summary="Cập nhật model mặc định")
async def update_defaults(
    body: DefaultsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> DefaultsResponse:
    row = await catalog_service.update_defaults(db, body, actor)
    return _defaults_out(row)


@router.get("/catalog", response_model=list[CatalogItem], summary="Danh mục model được phép dùng")
async def catalog(
    workspace_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> list[CatalogItem]:
    providers = await catalog_service.visible_providers(db, actor, workspace_id)
    defaults = await catalog_service.workspace_defaults(db, workspace_id) if workspace_id else {}
    return [
        CatalogItem(
            id=item.id,
            name=item.name,
            model_name=item.model_name,
            capabilities=item.capabilities,
            default_capabilities=[cap for cap, pid in defaults.items() if pid == item.id],
        )
        for item in providers
    ]


@workspace_router.get(
    "/{workspace_id}/allowed-providers",
    response_model=AllowlistResponse,
    summary="Provider workspace được cấp",
)
async def get_workspace_allowlist(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> AllowlistResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id)
    return await _allowlist_out(db, workspace.id)


@workspace_router.put(
    "/{workspace_id}/allowed-providers",
    response_model=AllowlistResponse,
    summary="Cấp danh sách model cho workspace",
)
async def set_workspace_allowlist(
    workspace_id: str,
    body: AllowlistUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
) -> AllowlistResponse:
    workspace = await resolve_workspace_access(db, actor, workspace_id)
    await catalog_service.set_allowlist(db, workspace.id, body, actor)
    return await _allowlist_out(db, workspace.id)


@workspace_router.put(
    "/{workspace_id}/model-defaults",
    response_model=dict[str, str],
    summary="Chọn model mặc định trong danh sách đã cấp",
)
async def set_workspace_defaults(
    workspace_id: str,
    body: WorkspaceDefaultsRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> dict[str, str]:
    await catalog_service.set_workspace_defaults(db, actor, workspace_id, body.defaults)
    return await catalog_service.workspace_defaults(db, workspace_id)
