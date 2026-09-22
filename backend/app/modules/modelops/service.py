"""ModelOps Service Facade — Multi-Provider Orchestration, Key Pool Rotation, Dynamic Fallback, Quota & Cost Tracking.

This module acts as a thin Facade orchestrating four specialized sub-services:
- ProviderService: Provider configurations, multi-key pools, health/connectivity verification, and key rotation.
- ModelCatalogService: System-wide default models (Embedding, Reranker, OCR) and dynamic model discovery.
- InferenceService: Chat completion execution and token streaming with Dynamic Fallback and Circuit Breaker.
- UsageAccountingService: Token quota management, usage event logging, and cost statistics.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modelops.models import LLMUsageLog, TenantQuota
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.schemas import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    ProviderConfigCreate,
    ProviderConfigUpdate,
    ProviderImportRequest,
    ProviderKeyCreate,
    ProviderKeyUpdate,
    SystemModelDefaultsResponse,
    SystemModelDefaultsUpdate,
    UsageStatsResponse,
)
from app.modules.modelops.services.inference_service import (
    InferenceService,
)
from app.modules.modelops.services.inference_service import (
    inference_service as default_inference_service,
)
from app.modules.modelops.services.model_catalog_service import (
    ModelCatalogService,
)
from app.modules.modelops.services.model_catalog_service import (
    model_catalog_service as default_model_catalog_service,
)
from app.modules.modelops.services.provider_service import (
    STANDARD_QNU_PROVIDERS,
    ProviderService,
    mask_api_key,
)
from app.modules.modelops.services.provider_service import (
    provider_service as default_provider_service,
)
from app.modules.modelops.services.usage_accounting_service import (
    UsageAccountingService,
)
from app.modules.modelops.services.usage_accounting_service import (
    usage_accounting_service as default_usage_accounting_service,
)

logger = logging.getLogger(__name__)


class ModelOpsService:
    """Orchestrates LLM calls across multiple providers with Key Pool, Circuit Breaker and Fallbacks."""

    _has_checked_initial_seed: bool = False

    def __init__(
        self,
        provider_service: ProviderService | None = None,
        catalog_service: ModelCatalogService | None = None,
        usage_service: UsageAccountingService | None = None,
        inference_service: InferenceService | None = None,
    ) -> None:
        self._provider = provider_service or default_provider_service
        self._catalog = catalog_service or default_model_catalog_service
        self._usage = usage_service or default_usage_accounting_service
        self._inference = inference_service or default_inference_service

        # Link facade
        self._provider.facade = self
        self._catalog.facade = self
        self._usage.facade = self
        self._inference.facade = self

    # ---------------- Provider Management ----------------

    @staticmethod
    def _sync_runtime_credentials(
        provider_type: str,
        api_key: str | None,
        account_id: str | None = None,
    ) -> None:
        ProviderService._sync_runtime_credentials(provider_type, api_key, account_id)

    async def seed_default_providers(
        self, db: AsyncSession, overwrite: bool = False
    ) -> list[dict[str, Any]]:
        return await self._provider.seed_default_providers(db, overwrite=overwrite)

    async def sync_active_providers_to_runtime(self, db: AsyncSession) -> int:
        return await self._provider.sync_active_providers_to_runtime(db)

    async def get_active_providers(
        self, db: AsyncSession, only_active: bool = False
    ) -> list[dict]:
        return await self._provider.get_active_providers(db, only_active=only_active)

    async def create_provider(
        self, db: AsyncSession, data: ProviderConfigCreate
    ) -> dict[str, Any]:
        return await self._provider.create_provider(db, data)

    async def update_provider(
        self, db: AsyncSession, provider_id: str, data: ProviderConfigUpdate
    ) -> dict[str, Any]:
        return await self._provider.update_provider(db, provider_id, data)

    async def delete_provider(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        return await self._provider.delete_provider(db, provider_id)

    async def toggle_provider(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        return await self._provider.toggle_provider(db, provider_id)

    async def _ping_provider_api(
        self,
        provider_type: str,
        base_url: str | None,
        api_key: str | None,
        account_id: str | None = None,
    ) -> tuple[bool, float, str]:
        return await self._provider._ping_provider_api(
            provider_type, base_url, api_key, account_id=account_id
        )

    async def test_provider(self, db: AsyncSession, provider_id: str) -> dict[str, Any]:
        return await self._provider.test_provider(db, provider_id)

    async def _ping_single_model(
        self,
        provider_type: str,
        model_name: str,
        base_url: str | None,
        api_key: str | None,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._provider._ping_single_model(
            provider_type, model_name, base_url, api_key, account_id=account_id
        )

    async def test_provider_models(
        self,
        db: AsyncSession,
        provider_id: str,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        return await self._provider.test_provider_models(db, provider_id, model_name=model_name)

    async def get_provider_keys(self, db: AsyncSession, provider_id: str) -> list[dict[str, Any]]:
        return await self._provider.get_provider_keys(db, provider_id)

    async def add_provider_key(
        self, db: AsyncSession, provider_id: str, data: ProviderKeyCreate
    ) -> dict[str, Any]:
        return await self._provider.add_provider_key(db, provider_id, data)

    async def update_provider_key(
        self, db: AsyncSession, provider_id: str, key_id: str, data: ProviderKeyUpdate
    ) -> dict[str, Any]:
        return await self._provider.update_provider_key(db, provider_id, key_id, data)

    async def delete_provider_key(
        self, db: AsyncSession, provider_id: str, key_id: str
    ) -> dict[str, Any]:
        return await self._provider.delete_provider_key(db, provider_id, key_id)

    async def test_provider_key(
        self, db: AsyncSession, provider_id: str, key_id: str
    ) -> dict[str, Any]:
        return await self._provider.test_provider_key(db, provider_id, key_id)

    async def simulate_key_rotation(
        self,
        db: AsyncSession,
        provider_id: str,
        tokens_consumed: int,
        trigger_rate_limit: bool,
        cooldown_seconds: int,
    ) -> dict[str, Any]:
        return await self._provider.simulate_key_rotation(
            db, provider_id, tokens_consumed, trigger_rate_limit, cooldown_seconds
        )

    # ---------------- Import / Export Providers ----------------

    async def export_provider(
        self, db: AsyncSession, provider_id: str, include_secrets: bool = True
    ) -> dict[str, Any]:
        return await self._provider.export_provider(db, provider_id, include_secrets=include_secrets)

    async def export_all_providers(
        self, db: AsyncSession, include_secrets: bool = True
    ) -> dict[str, Any]:
        return await self._provider.export_all_providers(db, include_secrets=include_secrets)

    async def import_providers(
        self, db: AsyncSession, payload: ProviderImportRequest
    ) -> dict[str, Any]:
        return await self._provider.import_providers(db, payload)

    # ---------------- Model Catalog & System Defaults ----------------

    async def get_system_model_defaults(self, db: AsyncSession) -> SystemModelDefaultsResponse:
        return await self._catalog.get_system_model_defaults(db)

    async def update_system_model_defaults(
        self, db: AsyncSession, update_data: SystemModelDefaultsUpdate
    ) -> SystemModelDefaultsResponse:
        return await self._catalog.update_system_model_defaults(db, update_data)

    async def set_provider_model_as_default(
        self, db: AsyncSession, provider_id: str, role: str, model_name: str
    ) -> SystemModelDefaultsResponse:
        return await self._catalog.set_provider_model_as_default(db, provider_id, role, model_name)

    # ---------------- Usage Accounting & Quotas ----------------

    async def get_or_create_quota(
        self, db: AsyncSession, tenant_id: str, month_period: str | None = None
    ) -> TenantQuota:
        return await self._usage.get_or_create_quota(db, tenant_id, month_period=month_period)

    async def check_quota_available(
        self, db: AsyncSession, tenant_id: str, estimated_tokens: int = 500
    ) -> TenantQuota:
        return await self._usage.check_quota_available(db, tenant_id, estimated_tokens=estimated_tokens)

    async def record_usage_log(
        self,
        db: AsyncSession,
        tenant_id: str = "tenant_qnu",
        assistant_id: str | None = None,
        conversation_id: str | None = None,
        provider: str = "openai",
        model_name: str = "gpt-4o-mini",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        is_fallback: bool = False,
        status: str = "success",
        error_message: str | None = None,
    ) -> LLMUsageLog:
        return await self._usage.record_usage_log(
            db,
            tenant_id=tenant_id,
            assistant_id=assistant_id,
            conversation_id=conversation_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            is_fallback=is_fallback,
            status=status,
            error_message=error_message,
        )

    async def get_usage_statistics(
        self,
        db: AsyncSession,
        days: int = 30,
        tenant_id: str | None = None,
    ) -> UsageStatsResponse:
        return await self._usage.get_usage_statistics(db, days=days, tenant_id=tenant_id)

    # ---------------- Inference Operations ----------------

    async def generate(self, db: AsyncSession, req: LLMGenerateRequest) -> LLMGenerateResponse:
        return await self._inference.generate(db, req)

    async def generate_stream(
        self, db: AsyncSession, req: LLMGenerateRequest
    ) -> AsyncIterator[str]:
        async for chunk in self._inference.generate_stream(db, req):
            yield chunk


modelops_service = ModelOpsService()

__all__ = [
    "STANDARD_QNU_PROVIDERS",
    "ModelOpsService",
    "get_llm_adapter",
    "mask_api_key",
    "modelops_service",
]
