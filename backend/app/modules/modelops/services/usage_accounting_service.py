"""ModelOps Usage Accounting Service — Token Quota, Cost Tracking, and Usage Statistics."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.modelops.models import LLMUsageLog, TenantQuota
from app.modules.modelops.pricing import calculate_cost_usd
from app.modules.modelops.schemas import (
    DailyUsageItem,
    ModelUsageBreakdownItem,
    UsageStatsResponse,
)

logger = logging.getLogger(__name__)


class UsageAccountingService:
    """Manages tenant token quotas, logs LLM usage events, and computes usage statistics."""

    def __init__(self, facade: Any = None) -> None:
        self.facade = facade

    async def _call_get_or_create_quota(
        self, db: AsyncSession, tenant_id: str, month_period: str | None = None
    ) -> TenantQuota:
        if self.facade is not None and hasattr(self.facade, "get_or_create_quota"):
            return await self.facade.get_or_create_quota(db, tenant_id, month_period)
        return await self.get_or_create_quota(db, tenant_id, month_period)

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
        quota = await self._call_get_or_create_quota(db, tenant_id)
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
        """Record usage metrics for audit, cost estimation, and quota tracking."""
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_cost_usd(model_name, prompt_tokens, completion_tokens)

        # Update quota
        try:
            quota = await self._call_get_or_create_quota(db, tenant_id)
            quota.tokens_used += total_tokens
            quota.cost_used_usd += cost_usd
        except Exception as q_err:
            logger.warning("Could not update quota: %s", q_err)

        log = LLMUsageLog(
            id=f"log_{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            assistant_id=assistant_id,
            conversation_id=conversation_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            is_fallback=is_fallback,
            status=status,
            error_message=error_message,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(log)
        try:
            await db.commit()
        except Exception as db_err:
            logger.warning("Could not commit LLMUsageLog: %s", db_err)

        return log

    async def get_usage_statistics(
        self,
        db: AsyncSession,
        days: int = 30,
        tenant_id: str | None = None,
    ) -> UsageStatsResponse:
        """Aggregate real-time usage metrics and cost tracking for the platform."""
        since_date = datetime.now(UTC) - timedelta(days=days)

        # Query all logs within period
        stmt = select(LLMUsageLog).where(LLMUsageLog.created_at >= since_date.replace(tzinfo=None))
        if tenant_id:
            stmt = stmt.where(LLMUsageLog.tenant_id == tenant_id)
        stmt = stmt.order_by(LLMUsageLog.created_at.desc())

        res = await db.execute(stmt)
        logs = res.scalars().all()

        total_requests = len(logs)
        total_tokens = sum(log.total_tokens for log in logs)
        total_cost_usd = round(sum(log.cost_usd for log in logs), 4)
        avg_latency_ms = (
            round(sum(log.latency_ms for log in logs) / total_requests, 2)
            if total_requests > 0
            else 0.0
        )

        # Group by model
        models_map: dict[str, dict[str, Any]] = {}
        # Group by date
        daily_map: dict[str, dict[str, Any]] = {}

        for log in logs:
            # Model breakdown
            m_key = f"{log.provider}:{log.model_name}"
            if m_key not in models_map:
                models_map[m_key] = {
                    "model_name": log.model_name,
                    "provider": log.provider,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "latencies": [],
                }
            models_map[m_key]["total_requests"] += 1
            models_map[m_key]["total_tokens"] += log.total_tokens
            models_map[m_key]["total_cost_usd"] += log.cost_usd
            models_map[m_key]["latencies"].append(log.latency_ms)

            # Daily usage
            d_str = (
                log.created_at.strftime("%Y-%m-%d")
                if log.created_at
                else datetime.now(UTC).strftime("%Y-%m-%d")
            )
            if d_str not in daily_map:
                daily_map[d_str] = {
                    "date": d_str,
                    "requests": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }
            daily_map[d_str]["requests"] += 1
            daily_map[d_str]["total_tokens"] += log.total_tokens
            daily_map[d_str]["cost_usd"] += log.cost_usd

        models_breakdown = [
            ModelUsageBreakdownItem(
                model_name=item["model_name"],
                provider=item["provider"],
                total_requests=item["total_requests"],
                total_tokens=item["total_tokens"],
                total_cost_usd=round(item["total_cost_usd"], 4),
                avg_latency_ms=(
                    round(sum(item["latencies"]) / len(item["latencies"]), 2)
                    if item["latencies"]
                    else 0.0
                ),
            )
            for item in models_map.values()
        ]
        models_breakdown.sort(key=lambda x: x.total_tokens, reverse=True)

        daily_usage = [
            DailyUsageItem(
                date=item["date"],
                requests=item["requests"],
                total_tokens=item["total_tokens"],
                cost_usd=round(item["cost_usd"], 4),
            )
            for item in sorted(daily_map.values(), key=lambda x: x["date"])
        ]

        return UsageStatsResponse(
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
            avg_latency_ms=avg_latency_ms,
            models_breakdown=models_breakdown,
            daily_usage=daily_usage,
        )


usage_accounting_service = UsageAccountingService()
