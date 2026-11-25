from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.modelops.connections import service
from qnu.domains.modelops.connections.capacity import sync_capacity
from qnu.domains.modelops.connections.schemas import (
    CapacitySyncRequest,
    ConnectionCreate,
    ConnectionModelCreate,
    ConnectionResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    ConnectionUpdate,
)
from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
from qnu.domains.modelops.providers.service import provider_payload
from qnu.domains.modelops.schemas import ProviderResponse
from qnu.ports.provider_diagnostics import ProviderDiagnosticClient

router = APIRouter(prefix="/modelops/connections", tags=["ModelOps · Nhà cung cấp"])
admin = require_permission("ai.models.manage")


@router.post("/{connection_id}/sync-capacity", response_model=list[ProviderResponse])
async def synchronize_capacity(
    connection_id: str,
    req: CapacitySyncRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(admin),
):
    return [
        ProviderResponse(**provider_payload(row))
        for row in await sync_capacity(db, actor, connection_id, req)
    ]


@router.get("", response_model=list[ConnectionResponse])
async def listing(db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(admin)):
    return await service.list_connections(db)


@router.post("", response_model=ConnectionResponse, status_code=201)
async def create(
    req: ConnectionCreate, db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(admin)
):
    return await service.save_connection(db, actor, req)


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def detail(
    connection_id: str, db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(admin)
):
    return (await service.output(db, [await service.get_connection(db, connection_id)]))[0]


@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def update(
    connection_id: str,
    req: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(admin),
):
    return await service.save_connection(db, actor, req, connection_id)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    connection_id: str, db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(admin)
) -> Response:
    await service.delete_connection(db, actor, connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{connection_id}/test", response_model=ConnectionTestResponse)
async def test(
    connection_id: str,
    req: ConnectionTestRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(admin),
    client: ProviderDiagnosticClient = Depends(get_diagnostic_client),
):
    return await service.test_connection(db, actor, connection_id, req, client)


@router.get("/{connection_id}/models", response_model=list[ProviderResponse])
async def models(
    connection_id: str, db: AsyncSession = Depends(get_db), actor: AuthActor = Depends(admin)
):
    return [
        ProviderResponse(**provider_payload(row))
        for row in await service.list_models(db, connection_id)
    ]


@router.post("/{connection_id}/models", response_model=ProviderResponse, status_code=201)
async def register(
    connection_id: str,
    req: ConnectionModelCreate,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(admin),
    client: ProviderDiagnosticClient = Depends(get_diagnostic_client),
):
    return ProviderResponse(
        **provider_payload(await service.add_model(db, actor, connection_id, req, client=client))
    )


@router.delete("/{connection_id}/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    connection_id: str,
    model_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(admin),
) -> Response:
    await service.delete_model(db, actor, connection_id, model_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{connection_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    connection_id: str,
    key_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(admin),
) -> Response:
    await service.delete_key(db, actor, connection_id, key_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
