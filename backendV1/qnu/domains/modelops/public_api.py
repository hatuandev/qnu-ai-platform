"""Public surface other domains may use instead of reaching into ModelOps internals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.domains.modelops.capacity.service import (
    plan_model_request,
    read_capacity,
    resolve_model_capacity,
)
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.platform.crypto import decrypt
from qnu.platform.errors import AppException, DependencyUnavailable


@dataclass(frozen=True, slots=True)
class OcrRuntime:
    """Resolved OCR target; the credential never leaves the process or reaches a log."""

    provider_id: str
    provider_name: str
    provider_type: str
    model_name: str
    base_url: str
    timeout_seconds: int
    api_key: str | None = field(default=None, repr=False)
    auth_optional: bool = False
    extra: dict[str, Any] = field(default_factory=dict, repr=False)
    token_limits: ModelTokenLimits | None = None
    capacity_status: str = "unknown"

    @property
    def configuration_hash(self) -> str:
        material = {
            "endpoint": self.base_url.rstrip("/"),
            "model": self.model_name,
            "provider_type": self.provider_type,
            "timeout_seconds": self.timeout_seconds,
            "auth_optional": self.auth_optional,
            "capacity_status": self.capacity_status,
            "token_limits": self.token_limits.model_dump() if self.token_limits else None,
        }
        return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()

    def public_dict(self) -> dict[str, Any]:
        """Safe description for artifacts and audit: no credential, no full URL query."""
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "model_name": self.model_name,
            "timeout_seconds": self.timeout_seconds,
            "configuration_hash": self.configuration_hash,
        }


async def visible_providers(
    db: AsyncSession, actor: AuthActor, workspace_id: str
) -> list[Provider]:
    """Providers the actor may select for a workspace they belong to."""
    return await catalog_service.visible_providers(db, actor, workspace_id)


async def assert_provider_allowed(
    db: AsyncSession,
    actor: AuthActor,
    workspace_id: str,
    capability: str,
    provider_id: str | None = None,
) -> Provider:
    """Fail with 404 when the provider is unknown or outside the actor's allowlist."""
    return await catalog_service.resolve_provider(db, actor, workspace_id, capability, provider_id)


async def _active_key(db: AsyncSession, provider_id: str) -> ProviderKey | None:
    stmt = (
        select(ProviderKey)
        .where(ProviderKey.provider_id == provider_id, ProviderKey.status == "active")
        .order_by(ProviderKey.priority.asc(), ProviderKey.created_at.asc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def resolve_ocr_runtime(
    db: AsyncSession, workspace_id: str, provider_id: str | None = None
) -> OcrRuntime:
    """Resolve the granted OCR provider plus its decrypted credential.

    Callers must have authorized the actor for ``workspace_id`` already; this function
    only enforces the ModelOps rules (grant, capability, active state, credential).
    """
    provider = await catalog_service.resolve_workspace_provider(
        db, workspace_id, "ocr", provider_id
    )
    extra = dict(provider.extra_config or {})
    capacity = read_capacity(provider)
    key = await _active_key(db, provider.id)
    if key is None and not extra.get("ocr_auth_optional", False):
        raise AppException(
            "Provider OCR chưa có credential đang hoạt động.",
            code="ocr_credentials_missing",
            status_code=503,
            title="Thiếu credential OCR",
        )
    try:
        secret = decrypt(key.secret_encrypted) if key is not None else None
    except AppException as exc:
        raise DependencyUnavailable(
            "Không giải mã được credential OCR.", code="ocr_credentials_unreadable"
        ) from exc
    return OcrRuntime(
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        model_name=provider.model_name,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        api_key=secret,
        auth_optional=bool(extra.get("ocr_auth_optional", False)),
        extra=extra,
        token_limits=capacity.token_limits,
        capacity_status=capacity.status,
    )


@dataclass(frozen=True, slots=True)
class ChatRuntime(OcrRuntime):
    """Protected chat target with the same pinned identity contract as OCR."""


async def resolve_chat_runtime(
    db: AsyncSession, workspace_id: str, provider_id: str | None = None
) -> ChatRuntime:
    """Trusted caller must authorize workspace access before resolving a chat target."""
    provider = await catalog_service.resolve_workspace_provider(
        db, workspace_id, "chat", provider_id
    )
    if provider.provider_type not in {"openai_compatible", "local"}:
        raise AppException(
            "Adapter chat chưa hỗ trợ loại provider đã chọn.",
            code="chat_provider_type_unsupported",
            status_code=422,
        )
    key = await _active_key(db, provider.id)
    if key is None:
        raise DependencyUnavailable("Chưa có credential chat.", code="chat_credentials_missing")
    try:
        secret = decrypt(key.secret_encrypted)
    except AppException as exc:
        raise DependencyUnavailable(
            "Không giải mã được credential chat.", code="chat_credentials_unreadable"
        ) from exc
    capacity = read_capacity(provider)
    return ChatRuntime(
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        model_name=provider.model_name,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        api_key=secret,
        token_limits=capacity.token_limits,
        capacity_status=capacity.status,
    )


__all__ = [
    "ChatRuntime",
    "OcrRuntime",
    "assert_provider_allowed",
    "plan_model_request",
    "resolve_chat_runtime",
    "resolve_model_capacity",
    "resolve_ocr_runtime",
    "visible_providers",
]
