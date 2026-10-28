from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient
from qnu.api.dependencies import get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.modelops.diagnostics.schemas import (
    DiagnosticCheck,
    ProbeRequest,
    ProviderDiagnostics,
)
from qnu.domains.modelops.diagnostics.service import read_diagnostics, run_diagnostic

router = APIRouter(prefix="/modelops/providers", tags=["ModelOps · Diagnostics"])


def get_diagnostic_client() -> HttpProviderDiagnosticClient:
    return HttpProviderDiagnosticClient()


@router.get("/{provider_id}/diagnostics", response_model=ProviderDiagnostics)
async def diagnostics(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
):
    return await read_diagnostics(db, provider_id, actor)


@router.post("/{provider_id}/discover", response_model=DiagnosticCheck)
async def discover(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
    client: HttpProviderDiagnosticClient = Depends(get_diagnostic_client),
):
    return await run_diagnostic(db, provider_id, "discovery", actor, client)


@router.post("/{provider_id}/probe", response_model=DiagnosticCheck)
async def probe(
    provider_id: str,
    body: ProbeRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.models.manage")),
    client: HttpProviderDiagnosticClient = Depends(get_diagnostic_client),
):
    return await run_diagnostic(db, provider_id, body.capability, actor, client)
