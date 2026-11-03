"""Workspace usage reporting with a compatibility endpoint for old callers."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db
from qnu.contracts.pagination import Page, PageMeta
from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.schemas import QuotaResponse, QuotaUpdateRequest, UsageResponse
from qnu.domains.modelops.usage.service import month_start, usage_service

router = APIRouter(prefix="/workspaces", tags=["Workspaces · Quota & usage"])


@router.get("/{workspace_id}/quota", response_model=QuotaResponse)
async def get_quota(
    workspace_id: str,
    period: date | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> QuotaResponse:
    month = month_start(period)
    row = await usage_service.read_quota(db, actor, workspace_id, month)
    if row is not None:
        return QuotaResponse.model_validate(row).model_copy(
            update={"monthly_token_limit": None, "is_blocked": False}
        )
    return QuotaResponse(
        workspace_id=workspace_id,
        month_period=month,
        monthly_token_limit=None,
        tokens_used=0,
        tokens_reserved=0,
        is_blocked=False,
        configured=False,
    )


@router.put("/{workspace_id}/quota", response_model=QuotaResponse, deprecated=True)
async def set_quota(
    workspace_id: str,
    _body: QuotaUpdateRequest,
    period: date | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> QuotaResponse:
    return QuotaResponse.model_validate(
        await usage_service.initialize_legacy_period(db, actor, workspace_id, month_start(period))
    )


@router.get("/{workspace_id}/usage", response_model=Page[UsageResponse])
async def list_usage(
    workspace_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> Page[UsageResponse]:
    rows, total = await usage_service.list_usage(db, actor, workspace_id, page, page_size)
    return Page[UsageResponse](
        items=[UsageResponse.model_validate(row) for row in rows],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )
