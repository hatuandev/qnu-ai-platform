"""Resolve task-specific model credentials from persisted ModelOps configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig

ModelRole = Literal["embedding", "reranker"]


@dataclass(frozen=True, slots=True)
class ModelRuntimeConfig:
    """Resolved provider settings used for one model invocation."""

    provider_id: str
    provider_type: str
    model_name: str
    api_base_url: str | None
    api_key: str | None
    account_id: str | None
    timeout_seconds: int


class ModelRuntimeResolver:
    """Resolve model defaults and provider secrets without environment coupling."""

    @staticmethod
    def _select_active_key(extra: dict, fallback_key: str | None) -> tuple[str | None, str | None]:
        key_pool = list(extra.get("api_keys", []))
        keys = [
            item
            for item in key_pool
            if item.get("is_active", True) and item.get("status", "active") == "active"
        ]
        keys.sort(key=lambda item: (item.get("priority", 1), item.get("usage_tokens", 0)))
        selected = keys[0] if keys else {}
        encrypted_key = selected.get("api_key") if key_pool else fallback_key
        account_id = selected.get("account_id") or extra.get("account_id")
        return decrypt_secret(encrypted_key), account_id

    async def resolve(self, db: AsyncSession, role: ModelRole) -> ModelRuntimeConfig:
        """Resolve the active provider and model configured for a task role."""
        defaults_result = await db.execute(
            select(ModelProviderConfig).where(ModelProviderConfig.id == "system_model_defaults")
        )
        defaults_record = defaults_result.scalar_one_or_none()
        defaults = dict((defaults_record.extra_config or {}).get("defaults") or {}) if defaults_record else {}

        provider_id = str(defaults.get(f"default_{role}_provider_id") or "").strip()
        model_name = str(defaults.get(f"default_{role}_model") or "").strip()
        if not provider_id or not model_name:
            raise AppException(
                f"Chưa chọn provider và mô hình mặc định cho {role} trong ModelOps.",
                code="MODEL_DEFAULT_NOT_CONFIGURED",
                status_code=503,
                details={"role": role},
            )

        provider_result = await db.execute(
            select(ModelProviderConfig).where(
                ModelProviderConfig.id == provider_id,
                ModelProviderConfig.is_active.is_(True),
            )
        )
        provider = provider_result.scalar_one_or_none()
        if provider is None:
            raise AppException(
                f"Provider mặc định '{provider_id}' chưa tồn tại hoặc đang tắt.",
                code="MODEL_PROVIDER_NOT_AVAILABLE",
                status_code=503,
                details={"role": role, "provider_id": provider_id},
            )

        extra = dict(provider.extra_config or {})
        api_key, account_id = self._select_active_key(extra, provider.api_key_encrypted)
        provider_type = provider.provider_type.strip().lower()
        invalid_cloudflare_account = (
            not account_id
            or account_id.startswith("cf-acc-")
            or "{" in account_id
            or "}" in account_id
        )
        if provider_type == "cloudflare" and (not api_key or invalid_cloudflare_account):
            raise AppException(
                "Provider Cloudflare thiếu Account ID hoặc API token.",
                code="MODEL_PROVIDER_CREDENTIALS_MISSING",
                status_code=503,
                details={
                    "role": role,
                    "provider_id": provider_id,
                    "required_fields": ["account_id", "api_key"],
                },
            )

        return ModelRuntimeConfig(
            provider_id=provider.id,
            provider_type=provider_type,
            model_name=model_name,
            api_base_url=provider.api_base_url,
            api_key=api_key,
            account_id=account_id.strip() if account_id else None,
            timeout_seconds=provider.timeout_seconds,
        )


model_runtime_resolver = ModelRuntimeResolver()
