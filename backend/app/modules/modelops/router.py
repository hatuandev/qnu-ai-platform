"""FastAPI Router for ModelOps — Multi-LLM Generation, Provider Cascade & Quota Queries."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.modelops.schemas import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    TenantQuotaResponse,
)
from app.modules.modelops.service import modelops_service

router = APIRouter(prefix="/modelops", tags=["ModelOps & Multi-LLM Routing"])


@router.post(
    "/generate",
    response_model=LLMGenerateResponse,
    summary="Sinh phản hồi LLM với cơ chế Circuit Breaker & Dynamic Fallback đa nhà cung cấp",
)
async def generate_completion(
    body: LLMGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> LLMGenerateResponse:
    return await modelops_service.generate(db, body)


@router.get(
    "/providers",
    summary="Lấy danh sách các nhà cung cấp mô hình LLM đang kích hoạt theo thứ tự ưu tiên",
)
async def list_active_providers(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await modelops_service.get_active_providers(db)


@router.get(
    "/quotas/{tenant_id}",
    response_model=TenantQuotaResponse,
    summary="Tra cứu trạng thái hạn ngạch token và chi phí tháng của một đơn vị / khoa phòng",
)
async def get_tenant_quota(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> TenantQuotaResponse:
    quota = await modelops_service.get_or_create_quota(db, tenant_id)
    percent = (
        round((quota.tokens_used / quota.monthly_token_limit) * 100, 2)
        if quota.monthly_token_limit > 0
        else 0.0
    )
    return TenantQuotaResponse(
        tenant_id=quota.tenant_id,
        month_period=quota.month_period,
        monthly_token_limit=quota.monthly_token_limit,
        monthly_cost_limit_usd=quota.monthly_cost_limit_usd,
        tokens_used=quota.tokens_used,
        cost_used_usd=quota.cost_used_usd,
        is_blocked=quota.is_blocked,
        usage_percent=percent,
    )
