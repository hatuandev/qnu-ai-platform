"""FastAPI routers for Integration management and OpenAI-compatible endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.service import resolve_actor
from qnu.domains.integration.gateway import (
    authenticate_api_key,
    openai_gateway_service,
)
from qnu.domains.integration.models import AppApiKey, AppClient
from qnu.domains.integration.schemas import (
    AppApiKeyCreate,
    AppApiKeyResponse,
    AppApiKeyRevokeRequest,
    AppApiKeyRotateRequest,
    AppApiKeySecretResponse,
    AppApiKeyStatusUpdate,
    AppClientCreate,
    AppClientResponse,
    AppRequestLogResponse,
    IntegrationConfigResponse,
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIModelsResponse,
)
from qnu.domains.integration.service import integration_service
from qnu.platform.config import Settings, get_settings
from qnu.platform.errors import DependencyUnavailable

# Admin Management Router (Workspace-scoped)
admin_router = APIRouter(tags=["Integration & API Keys"])

# OpenAI Gateway Router (Bearer API Key authenticated)
gateway_router = APIRouter(tags=["Integration OpenAI Gateway"])


# --- Workspace Admin Endpoints ---


@admin_router.get("/integrations/config", response_model=IntegrationConfigResponse)
async def get_integration_config(
    request: Request,
    actor: AuthActor = Depends(resolve_actor),
    settings: Settings = Depends(get_settings),
) -> IntegrationConfigResponse:
    """Return trusted base URLs and capabilities for external API clients."""
    if settings.PUBLIC_BASE_URL is None:
        raise DependencyUnavailable(
            "Chưa cấu hình PUBLIC_BASE_URL của server.", code="public_endpoint_unconfigured"
        )
    base = f"{str(settings.PUBLIC_BASE_URL).rstrip('/')}{settings.API_PREFIX}/integrations"
    openai_endpoint = f"{base}/openai/v1"

    return IntegrationConfigResponse(
        base_url=base,
        openai_endpoint=openai_endpoint,
        supported_protocols=[
            "POST /chat/completions (single user message, stream=false)",
            "GET /models",
        ],
        capabilities=["single_turn_chat", "evidence_first_citations", "rag_retrieval"],
        version="v1alpha1",
    )


@admin_router.post(
    "/workspaces/{workspace_id}/integrations/apps",
    response_model=AppClientResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_app_client(
    workspace_id: str,
    req: AppClientCreate,
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> AppClientResponse:
    app = await integration_service.create_app(db, actor, workspace_id, req)
    return AppClientResponse.model_validate(app)


@admin_router.get(
    "/workspaces/{workspace_id}/integrations/apps",
    response_model=list[AppClientResponse],
)
async def list_app_clients(
    workspace_id: str,
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> list[AppClientResponse]:
    apps = await integration_service.list_apps(db, actor, workspace_id)
    return [AppClientResponse.model_validate(a) for a in apps]


@admin_router.post(
    "/workspaces/{workspace_id}/integrations/keys",
    response_model=AppApiKeySecretResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    workspace_id: str,
    req: AppApiKeyCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> AppApiKeySecretResponse:
    response.headers["Cache-Control"] = "no-store"
    key, raw_secret, app_name = await integration_service.create_key(
        db, actor, workspace_id, req, idempotency_key=idempotency_key
    )
    return AppApiKeySecretResponse(
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
        secret_key=raw_secret,
    )


@admin_router.get(
    "/workspaces/{workspace_id}/integrations/keys",
    response_model=list[AppApiKeyResponse],
)
async def list_api_keys(
    workspace_id: str,
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> list[AppApiKeyResponse]:
    return await integration_service.list_keys(db, actor, workspace_id)


@admin_router.put(
    "/workspaces/{workspace_id}/integrations/keys/{key_id}/status",
    response_model=AppApiKeyResponse,
)
async def update_api_key_status(
    workspace_id: str,
    key_id: str,
    req: AppApiKeyStatusUpdate,
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> AppApiKeyResponse:
    return await integration_service.update_key_status(db, actor, workspace_id, key_id, req)


@admin_router.post(
    "/workspaces/{workspace_id}/integrations/keys/{key_id}/rotate",
    response_model=AppApiKeySecretResponse,
)
async def rotate_api_key(
    workspace_id: str,
    key_id: str,
    req: AppApiKeyRotateRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> AppApiKeySecretResponse:
    response.headers["Cache-Control"] = "no-store"
    if idempotency_key:
        req.idempotency_key = idempotency_key

    new_key, raw_secret, app_name = await integration_service.rotate_key(
        db, actor, workspace_id, key_id, req
    )
    return AppApiKeySecretResponse(
        id=new_key.id,
        app_id=new_key.app_id,
        app_name=app_name,
        workspace_id=new_key.workspace_id,
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        status=new_key.status,
        allowed_assistant_ids=new_key.allowed_assistant_ids,
        rate_limit_rpm=new_key.rate_limit_rpm,
        rate_limit_rpd=new_key.rate_limit_rpd,
        expires_at=new_key.expires_at,
        last_used_at=new_key.last_used_at,
        rotated_from_key_id=new_key.rotated_from_key_id,
        revoked_at=new_key.revoked_at,
        revoked_reason=new_key.revoked_reason,
        created_by=new_key.created_by,
        created_at=new_key.created_at,
        secret_key=raw_secret,
    )


@admin_router.delete(
    "/workspaces/{workspace_id}/integrations/keys/{key_id}",
    response_model=AppApiKeyResponse,
)
async def revoke_api_key(
    workspace_id: str,
    key_id: str,
    req: AppApiKeyRevokeRequest | None = None,
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> AppApiKeyResponse:
    reason = req.reason if req else "Thu hồi bởi quản trị viên"
    return await integration_service.revoke_key(db, actor, workspace_id, key_id, reason)


@admin_router.get(
    "/workspaces/{workspace_id}/integrations/logs",
    response_model=list[AppRequestLogResponse],
)
async def list_integration_logs(
    workspace_id: str,
    limit: int = Query(50, ge=1, le=200),
    actor: AuthActor = Depends(resolve_actor),
    db: AsyncSession = Depends(get_db),
) -> list[AppRequestLogResponse]:
    logs = await integration_service.list_logs(db, actor, workspace_id, limit=limit)
    return [AppRequestLogResponse.model_validate(item) for item in logs]


# --- OpenAI Compatible Gateway Endpoints ---


@gateway_router.get(
    "/integrations/openai/v1/models",
    response_model=OpenAIModelsResponse,
)
async def list_openai_models(
    auth: tuple[AppApiKey, AppClient, AuthActor] = Depends(authenticate_api_key),
    db: AsyncSession = Depends(get_db),
) -> OpenAIModelsResponse:
    key, app, machine_actor = auth
    return await openai_gateway_service.list_models(db, key, app, machine_actor)


@gateway_router.post(
    "/integrations/openai/v1/chat/completions",
    response_model=OpenAIChatCompletionResponse,
)
async def create_openai_chat_completion(
    req: OpenAIChatCompletionRequest,
    request: Request,
    auth: tuple[AppApiKey, AppClient, AuthActor] = Depends(authenticate_api_key),
    db: AsyncSession = Depends(get_db),
) -> OpenAIChatCompletionResponse:
    key, app, machine_actor = auth
    container = getattr(request.app.state, "container", None)
    blob = getattr(container, "blob_store", None) if container else None
    embedding = getattr(container, "embedding_model", None) if container else None
    vectors = getattr(container, "vector_store", None) if container else None
    chat = getattr(container, "chat_model", None) if container else None
    reranker = getattr(container, "reranker", None) if container else None

    return await openai_gateway_service.create_chat_completion(
        db=db,
        blob=blob,
        embedding=embedding,
        vectors=vectors,
        chat=chat,
        key=key,
        app=app,
        actor=machine_actor,
        req=req,
        reranker=reranker,
    )
