"""Public surface other domains may use instead of reaching into ModelOps internals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.capacity.automatic import operational_budget
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits, OperationalBudget
from qnu.domains.modelops.capacity.service import (
    plan_model_request,
    read_capacity,
    resolve_model_capacity,
)
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.keys.scope import key_scope
from qnu.domains.modelops.models import Provider, ProviderKey
from qnu.domains.modelops.reasoning import (
    EXTRA_CONFIG_KEY,
    ReasoningPolicy,
    parse_policy,
    resolve_directive,
    trace_for,
)
from qnu.domains.modelops.registry import transport_for
from qnu.platform.crypto import decrypt
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.ports.provider_execution import ProviderExecution


def _wait_for_completion(provider: Provider) -> bool:
    from qnu.domains.modelops.resilience.service import effective_policy

    return effective_policy(provider).wait_for_completion


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
    workspace_id: str | None = None
    routing_trace: tuple[dict, ...] = ()
    reasoning_policy: ReasoningPolicy | None = field(default=None, repr=False)
    session_factory: Any = field(default=None, repr=False, compare=False)
    wait_for_completion: bool = False
    operational_budget: OperationalBudget | None = None

    @property
    def execution_scope(self) -> ProviderExecution | None:
        return (
            ProviderExecution(self.workspace_id, self.provider_id, sessions=self.session_factory)
            if self.workspace_id
            else None
        )

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
        if self.wait_for_completion:
            material["wait_for_completion"] = True
        if self.operational_budget and self.operational_budget.status == "provisional":
            material["operational_budget"] = self.operational_budget.model_dump()
        return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()

    def public_dict(self) -> dict[str, Any]:
        """Safe description for artifacts and audit: no credential, no full URL query."""
        return {
            **({"routing": list(self.routing_trace)} if self.routing_trace else {}),
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "model_name": self.model_name,
            "timeout_seconds": self.timeout_seconds,
            "configuration_hash": self.configuration_hash,
            **({"wait_for_completion": True} if self.wait_for_completion else {}),
            **(
                {"operational_budget": self.operational_budget.model_dump()}
                if self.operational_budget and self.operational_budget.status == "provisional"
                else {}
            ),
        }

    def reasoning_directive(self, task: str):
        """Declared parameter for one task, or None to keep the server default."""
        return resolve_directive(self.reasoning_policy, task)

    def reasoning_trace(self, task: str) -> dict[str, Any]:
        """Explain what was sent: applied parameter or the reason it was not."""
        return trace_for(self.reasoning_policy, task)


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
    provider = await db.get(Provider, provider_id)
    stmt = (
        select(ProviderKey)
        .where(key_scope(provider), ProviderKey.status == "active")
        .order_by(ProviderKey.priority.asc(), ProviderKey.created_at.asc())
        .limit(1)
    )
    from qnu.domains.modelops.resilience.service import effective_policy

    provider = await db.get(Provider, provider_id)
    if provider is not None and effective_policy(provider).key_pool_enabled:
        stmt = stmt.where(
            or_(
                ProviderKey.cooldown_until.is_(None),
                ProviderKey.cooldown_until <= datetime.now(UTC),
            )
        )
    key = (await db.execute(stmt)).scalars().first()
    if key is None and provider is not None and effective_policy(provider).key_pool_enabled:
        existing = await db.scalar(
            select(ProviderKey.id)
            .where(
                key_scope(provider),
                ProviderKey.status == "active",
            )
            .limit(1)
        )
        if existing:
            raise DependencyUnavailable(
                "Các khóa đang tạm nghỉ; chưa gửi request.", code="provider_keys_unavailable"
            )
    return key


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
    if "ocr" not in transport_for(provider.provider_type).protocols:
        raise AppException(
            "Loại provider OCR chưa có adapter.",
            code="ocr_provider_type_unsupported",
            status_code=422,
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
        workspace_id=workspace_id,
        session_factory=async_sessionmaker(db.bind, expire_on_commit=False),
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
        wait_for_completion=_wait_for_completion(provider)
        if provider.provider_type == "mineru"
        else False,
    )


@dataclass(frozen=True, slots=True)
class ChatRuntime(OcrRuntime):
    """Protected chat target with the same pinned identity contract as OCR."""

    def inference_configuration_hash(self, task: str) -> str:
        """Task-specific identity; legacy compiler/index hashes remain unchanged."""
        material = {
            "version": "qnu.chat.inference/v1",
            "configuration_hash": self.configuration_hash,
            "task": task,
            "reasoning": self.reasoning_trace(task),
        }
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


async def resolve_chat_runtime(
    db: AsyncSession, workspace_id: str, provider_id: str | None = None
) -> ChatRuntime:
    """Trusted caller must authorize workspace access before resolving a chat target."""
    provider = await catalog_service.resolve_workspace_provider(
        db, workspace_id, "chat", provider_id
    )
    if "chat" not in transport_for(provider.provider_type).protocols:
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
    effective = operational_budget(capacity, "chat")
    return ChatRuntime(
        workspace_id=workspace_id,
        session_factory=async_sessionmaker(db.bind, expire_on_commit=False),
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        model_name=provider.model_name,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
        api_key=secret,
        extra=dict(provider.extra_config or {}),
        token_limits=effective.token_limits,
        capacity_status="provisional" if effective.status == "provisional" else capacity.status,
        operational_budget=effective,
        reasoning_policy=parse_policy((provider.extra_config or {}).get(EXTRA_CONFIG_KEY)),
        wait_for_completion=_wait_for_completion(provider),
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
