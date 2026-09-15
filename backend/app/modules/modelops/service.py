"""ModelOps Service — Multi-Provider Orchestration, Dynamic Fallback, Quota & Cost Tracking."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cost_tracker import cost_tracker
from app.core.exceptions import AppException
from app.modules.modelops.circuit_breaker import circuit_breaker_registry
from app.modules.modelops.models import LLMUsageLog, ModelProviderConfig, TenantQuota
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.schemas import LLMGenerateRequest, LLMGenerateResponse

logger = logging.getLogger(__name__)


class ModelOpsService:
    """Orchestrates LLM calls across multiple providers with Circuit Breaker and Fallbacks."""

    async def get_or_create_quota(
        self, db: AsyncSession, tenant_id: str, month_period: str | None = None
    ) -> TenantQuota:
        """Get or initialize monthly quota record for a tenant."""
        period = month_period or datetime.now(UTC).strftime("%Y-%m")
        stmt = select(TenantQuota).where(
            TenantQuota.tenant_id == tenant_id, TenantQuota.month_period == period
        )
        res = await db.execute(stmt)
        quota = res.scalar_one_or_none()

        if not quota:
            quota = TenantQuota(
                tenant_id=tenant_id,
                month_period=period,
                monthly_token_limit=settings.DEFAULT_MONTHLY_TOKEN_QUOTA,
                tokens_used=0,
                cost_used_usd=0.0,
                is_blocked=False,
            )
            db.add(quota)
            await db.commit()
            await db.refresh(quota)

        return quota

    async def check_quota_available(
        self, db: AsyncSession, tenant_id: str, estimated_tokens: int = 500
    ) -> TenantQuota:
        """Verify tenant has remaining tokens before making expensive LLM calls."""
        quota = await self.get_or_create_quota(db, tenant_id)
        if quota.is_blocked:
            raise AppException(
                status_code=403,
                title="Tài khoản bị tạm khóa",
                detail=f"Đơn vị '{tenant_id}' đã bị tạm khóa do vi phạm chính sách.",
                code="TENANT_BLOCKED",
            )

        if quota.tokens_used + estimated_tokens > quota.monthly_token_limit:
            raise AppException(
                status_code=429,
                title="Hạn ngạch Token đã cạn",
                detail=(
                    f"Đơn vị '{tenant_id}' đã sử dụng {quota.tokens_used:,} / "
                    f"{quota.monthly_token_limit:,} tokens trong tháng {quota.month_period}."
                ),
                code="QUOTA_EXCEEDED",
            )
        return quota

    async def get_active_providers(self, db: AsyncSession) -> list[dict]:
        """Fetch active providers ordered by priority from DB or return robust defaults."""
        try:
            stmt = (
                select(ModelProviderConfig)
                .where(ModelProviderConfig.is_active.is_(True))
                .order_by(ModelProviderConfig.priority.asc())
            )
            res = await db.execute(stmt)
            configs = res.scalars().all()
            if configs:
                return [
                    {
                        "name": c.name,
                        "provider_type": c.provider_type,
                        "model_name": c.model_name,
                        "api_base_url": c.api_base_url,
                        "api_key": c.api_key_encrypted,
                        "timeout_seconds": c.timeout_seconds,
                    }
                    for c in configs
                ]
        except Exception as e:
            logger.debug("Database query for provider configs skipped or failed: %s", e)

        # Production Default Providers Fallback Hierarchy:
        # 1. Primary: OpenAI (gpt-4o-mini)
        # 2. Secondary: Gemini (gemini-1.5-flash)
        # 3. Local: Campus vLLM / Ollama (qwen2.5-7b-instruct)
        return [
            {
                "name": "OpenAI Primary",
                "provider_type": "openai",
                "model_name": settings.OPENAI_MODEL_NAME,
                "api_base_url": settings.OPENAI_BASE_URL,
                "api_key": settings.OPENAI_API_KEY,
                "timeout_seconds": 15,
            },
            {
                "name": "Gemini Secondary",
                "provider_type": "gemini",
                "model_name": settings.GEMINI_MODEL_NAME,
                "api_base_url": None,
                "api_key": settings.GEMINI_API_KEY,
                "timeout_seconds": 15,
            },
            {
                "name": "Local Campus AI",
                "provider_type": "local_vllm",
                "model_name": "qwen2.5-7b-instruct",
                "api_base_url": "http://localhost:8000/v1",
                "api_key": None,
                "timeout_seconds": 20,
            },
        ]

    async def generate(self, db: AsyncSession, req: LLMGenerateRequest) -> LLMGenerateResponse:
        """Execute chat completion with Circuit Breaker, Dynamic Fallback and Quota logging."""
        # 1. Quota Pre-check
        quota = await self.check_quota_available(db, req.tenant_id, estimated_tokens=300)

        # 2. Retrieve Provider Cascade
        providers = await self.get_active_providers(db)
        last_error: Exception | None = None

        # 3. Traverse Providers with Circuit Breaker
        for idx, p in enumerate(providers):
            p_name = p["name"]
            cb = circuit_breaker_registry.get(p_name)

            if not cb.can_execute():
                logger.warning("Circuit Breaker OPEN for [%s] — skipping to next fallback", p_name)
                continue

            try:
                adapter = get_llm_adapter(
                    provider_type=p["provider_type"],
                    model_name=p["model_name"],
                    api_key=p["api_key"],
                    base_url=p["api_base_url"],
                    timeout_seconds=p["timeout_seconds"],
                )

                resp = await adapter.generate(
                    messages=req.messages,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                )

                # Record success for circuit breaker
                cb.record_success()

                # Calculate monetary cost
                cost_usd = cost_tracker.calculate_cost(
                    provider=resp.provider,
                    model_name=resp.model,
                    prompt_tokens=resp.prompt_tokens,
                    completion_tokens=resp.completion_tokens,
                )

                # Update Quota & Usage
                try:
                    quota.tokens_used += resp.total_tokens
                    quota.cost_used_usd += cost_usd

                    usage_log = LLMUsageLog(
                        tenant_id=req.tenant_id,
                        assistant_id=req.assistant_code,
                        conversation_id=req.conversation_id,
                        provider=resp.provider,
                        model_name=resp.model,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                        total_tokens=resp.total_tokens,
                        cost_usd=cost_usd,
                        latency_ms=resp.latency_ms,
                        is_fallback=bool(idx > 0),
                        status="success",
                    )
                    db.add(usage_log)
                    await db.commit()
                except Exception as db_err:
                    logger.warning("Failed to record usage in database: %s", db_err)

                return LLMGenerateResponse(
                    content=resp.content,
                    provider=resp.provider,
                    model=resp.model,
                    prompt_tokens=resp.prompt_tokens,
                    completion_tokens=resp.completion_tokens,
                    total_tokens=resp.total_tokens,
                    cost_usd=cost_usd,
                    latency_ms=resp.latency_ms,
                    is_fallback=bool(idx > 0),
                )

            except Exception as exc:
                cb.record_failure(exc)
                last_error = exc
                logger.warning(
                    "Provider [%s] failed with %s: %s. Initiating fallback...",
                    p_name,
                    type(exc).__name__,
                    exc,
                )

        # 4. If all providers exhausted
        raise AppException(
            status_code=503,
            title="Dịch vụ AI đang gián đoạn",
            detail=(
                f"Tất cả các nhà cung cấp mô hình (OpenAI, Gemini, Local vLLM) đều không phản hồi: {last_error}"
            ),
            code="ALL_PROVIDERS_UNAVAILABLE",
        )


modelops_service = ModelOpsService()
