"""FastAPI Router for ModelOps — Multi-LLM Generation, Provider Cascade, Key Pool & Quota Queries."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.modelops.schemas import (
    PROVIDER_PRESETS,
    LLMGenerateRequest,
    LLMGenerateResponse,
    ProviderConfigCreate,
    ProviderConfigUpdate,
    ProviderKeyCreate,
    ProviderKeyItem,
    ProviderKeyTestResponse,
    ProviderKeyUpdate,
    ProviderPresetItem,
    ProviderTestResponse,
    SetDefaultModelRequest,
    SimulateKeyRotationRequest,
    SimulateKeyRotationResponse,
    SystemModelDefaultsResponse,
    SystemModelDefaultsUpdate,
    TenantQuotaResponse,
)
from app.modules.modelops.service import modelops_service

router = APIRouter(prefix="/modelops", tags=["ModelOps & Multi-LLM Routing"])


@router.get(
    "/defaults",
    response_model=SystemModelDefaultsResponse,
    summary="Lấy cấu hình mô hình mặc định hệ thống cho Embedding, Reranker, OCR kèm danh sách model khả dụng",
)
async def get_system_model_defaults(
    db: AsyncSession = Depends(get_db),
) -> SystemModelDefaultsResponse:
    return await modelops_service.get_system_model_defaults(db)


@router.put(
    "/defaults",
    response_model=SystemModelDefaultsResponse,
    summary="Cập nhật cấu hình mô hình mặc định hệ thống cho Embedding, Reranker, OCR",
)
async def update_system_model_defaults(
    body: SystemModelDefaultsUpdate,
    db: AsyncSession = Depends(get_db),
) -> SystemModelDefaultsResponse:
    return await modelops_service.update_system_model_defaults(db, body)


@router.post(
    "/providers/{provider_id}/set-default",
    response_model=SystemModelDefaultsResponse,
    summary="Đặt nhanh một mô hình của Provider làm mặc định cho Embedding, Reranker hoặc OCR",
)
async def set_provider_model_as_default(
    provider_id: str,
    body: SetDefaultModelRequest,
    db: AsyncSession = Depends(get_db),
) -> SystemModelDefaultsResponse:
    return await modelops_service.set_provider_model_as_default(
        db, provider_id=provider_id, role=body.role, model_name=body.model_name
    )



@router.post(
    "/generate",
    response_model=LLMGenerateResponse,
    summary="Sinh phản hồi LLM với cơ chế Circuit Breaker, Key Pool Failover & Dynamic Fallback đa nhà cung cấp",
)
async def generate_completion(
    body: LLMGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> LLMGenerateResponse:
    return await modelops_service.generate(db, body)


@router.get(
    "/presets",
    response_model=list[ProviderPresetItem],
    summary="Lấy danh mục các cấu hình mẫu sẵn của các nhà cung cấp đặc thù (OpenAI, Gemini, Groq, DeepSeek, Cloudflare, NVIDIA, Ollama...)",
)
async def list_provider_presets() -> list[ProviderPresetItem]:
    return PROVIDER_PRESETS


@router.get(
    "/providers",
    summary="Lấy danh sách các nhà cung cấp mô hình LLM theo thứ tự ưu tiên kèm số lượng API Keys",
)
async def list_active_providers(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await modelops_service.get_active_providers(db)


@router.post(
    "/providers/seed-defaults",
    summary="Khôi phục hoặc nạp lại danh sách cấu hình Provider chuẩn từ QNU AI Core (OpenAI, Gemini, Mistral, Cloudflare, DeepSeek, Groq, Claude, Local vLLM)",
)
async def seed_default_providers(
    overwrite: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await modelops_service.seed_default_providers(db, overwrite=overwrite)


@router.post(
    "/providers",
    summary="Thêm mới một nhà cung cấp LLM (Provider) và cấu hình mô hình",
)
async def create_provider(
    body: ProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await modelops_service.create_provider(db, body)


@router.put(
    "/providers/{provider_id}",
    summary="Cập nhật thông tin, API key và danh sách mô hình của Provider",
)
async def update_provider(
    provider_id: str,
    body: ProviderConfigUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await modelops_service.update_provider(db, provider_id, body)


@router.delete(
    "/providers/{provider_id}",
    summary="Xóa bỏ một nhà cung cấp LLM",
)
async def delete_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await modelops_service.delete_provider(db, provider_id)


@router.post(
    "/providers/{provider_id}/toggle",
    summary="Bật hoặc tạm dừng hoạt động của một nhà cung cấp LLM",
)
async def toggle_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await modelops_service.toggle_provider(db, provider_id)


@router.post(
    "/providers/{provider_id}/test",
    response_model=ProviderTestResponse,
    summary="Kiểm tra kết nối và độ trễ tới nhà cung cấp LLM",
)
async def test_provider_connection(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProviderTestResponse:
    res = await modelops_service.test_provider(db, provider_id)
    return ProviderTestResponse(**res)


# ---------------- Key Pool Endpoints ----------------


@router.get(
    "/providers/{provider_id}/keys",
    response_model=list[ProviderKeyItem],
    summary="Lấy danh sách tất cả các API Key trong nhóm (Key Pool) của một nhà cung cấp",
)
async def list_provider_keys(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await modelops_service.get_provider_keys(db, provider_id)


@router.post(
    "/providers/{provider_id}/keys",
    response_model=ProviderKeyItem,
    status_code=201,
    summary="Thêm một khóa API mới vào nhóm (Key Pool) của nhà cung cấp",
)
async def add_provider_key(
    provider_id: str,
    body: ProviderKeyCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await modelops_service.add_provider_key(db, provider_id, body)


@router.put(
    "/providers/{provider_id}/keys/{key_id}",
    response_model=ProviderKeyItem,
    summary="Cập nhật nhãn, độ ưu tiên hoặc trạng thái của một khóa API",
)
async def update_provider_key(
    provider_id: str,
    key_id: str,
    body: ProviderKeyUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await modelops_service.update_provider_key(db, provider_id, key_id, body)


@router.delete(
    "/providers/{provider_id}/keys/{key_id}",
    summary="Xóa một khóa API khỏi nhóm (Key Pool)",
)
async def delete_provider_key(
    provider_id: str,
    key_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await modelops_service.delete_provider_key(db, provider_id, key_id)


@router.post(
    "/providers/{provider_id}/keys/{key_id}/test",
    response_model=ProviderKeyTestResponse,
    summary="Kiểm tra tính hợp lệ và độ trễ của một khóa API cụ thể",
)
async def test_provider_single_key(
    provider_id: str,
    key_id: str,
    db: AsyncSession = Depends(get_db),
) -> ProviderKeyTestResponse:
    res = await modelops_service.test_provider_key(db, provider_id, key_id)
    return ProviderKeyTestResponse(**res)


@router.post(
    "/providers/{provider_id}/keys/simulate-rotation",
    response_model=SimulateKeyRotationResponse,
    summary="Mô phỏng tiêu thụ token và cơ chế tự động xoay vòng sang khóa kế tiếp khi chạm Rate Limit 429",
)
async def simulate_provider_key_rotation(
    provider_id: str,
    body: SimulateKeyRotationRequest,
    db: AsyncSession = Depends(get_db),
) -> SimulateKeyRotationResponse:
    res = await modelops_service.simulate_key_rotation(
        db,
        provider_id,
        tokens_consumed=body.tokens_consumed,
        trigger_rate_limit=body.trigger_rate_limit,
        cooldown_seconds=body.cooldown_seconds,
    )
    return SimulateKeyRotationResponse(**res)


# ---------------- Quotas ----------------


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
