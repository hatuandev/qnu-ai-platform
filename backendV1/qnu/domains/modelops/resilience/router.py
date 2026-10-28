from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.registry import TRANSPORTS, ProviderTransport
from qnu.domains.modelops.resilience.schemas import (
    ExecutionObservation,
    PolicyResponse,
    ResiliencePolicy,
)
from qnu.domains.modelops.resilience.service import execution_history, read_policy, save_policy

router = APIRouter(prefix="/modelops", tags=["ModelOps · Resilience"])


@router.get("/providers/{provider_id}/executions", response_model=list[ExecutionObservation])
async def executions(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
):
    return await execution_history(db, actor, provider_id)


@router.get("/registry", response_model=list[ProviderTransport])
async def registry(actor: AuthActor = Depends(require_permission("ai.models.manage"))):
    return TRANSPORTS


@router.get("/providers/{provider_id}/resilience", response_model=PolicyResponse)
async def get_policy(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
):
    return read_policy(await provider_service.get(db, provider_id))


@router.put("/providers/{provider_id}/resilience", response_model=PolicyResponse)
async def put_policy(
    provider_id: str,
    body: ResiliencePolicy,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
):
    return await save_policy(db, actor, provider_id, body)
