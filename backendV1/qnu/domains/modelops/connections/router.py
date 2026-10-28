from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_db
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.permissions import require_permission
from qnu.domains.modelops.connections import service
from qnu.domains.modelops.connections.schemas import (
    ConnectionCreate,
    ConnectionModelCreate,
    ConnectionResponse,
    ConnectionUpdate,
)
from qnu.domains.modelops.providers.service import provider_payload
from qnu.domains.modelops.schemas import ProviderResponse

router = APIRouter(prefix="/modelops/connections", tags=["ModelOps · Nhà cung cấp"])
admin = require_permission("ai.models.manage")


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
):
    return ProviderResponse(
        **provider_payload(await service.add_model(db, actor, connection_id, req))
    )
