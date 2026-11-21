from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.assistants import service
from qnu.domains.assistants.schemas import (
    AssistantCreate,
    AssistantReadiness,
    AssistantResponse,
    AssistantUpdate,
    PersonaCraftRequest,
    PersonaCraftResponse,
)
from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import DependencyUnavailable
from qnu.ports.blob_store import BlobStore

router = APIRouter(prefix="/workspaces/{workspace_id}/assistants", tags=["Assistants"])
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]


@router.post("/craft-persona", response_model=PersonaCraftResponse)
async def craft_persona(
    workspace_id: str,
    body: PersonaCraftRequest,
    db: DB,
    actor: Actor,
    request: Request,
):
    container = getattr(request.app.state, "container", None)
    chat_model = getattr(container, "chat_model", None)
    if chat_model is None:
        raise DependencyUnavailable("Mô hình chat chưa được khởi tạo.", code="chat_unavailable")
    return await service.craft_persona(db, actor, workspace_id, body, chat_model)


@router.post("", response_model=AssistantResponse, status_code=201)
async def create(workspace_id: str, body: AssistantCreate, db: DB, actor: Actor):
    return await service.save_assistant(db, actor, workspace_id, body)


@router.get("", response_model=list[AssistantResponse])
async def listing(
    workspace_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await service.list_assistants(db, actor, workspace_id, limit, offset)


@router.get("/{assistant_id}", response_model=AssistantResponse)
async def detail(workspace_id: str, assistant_id: str, db: DB, actor: Actor):
    return await service.get_assistant(db, actor, workspace_id, assistant_id)


@router.get("/{assistant_id}/readiness", response_model=AssistantReadiness)
async def readiness(workspace_id: str, assistant_id: str, db: DB, actor: Actor, blob: Blob):
    return await service.assistant_readiness(db, blob, actor, workspace_id, assistant_id)


@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update(workspace_id: str, assistant_id: str, body: AssistantUpdate, db: DB, actor: Actor):
    return await service.save_assistant(db, actor, workspace_id, body, assistant_id)


@router.delete("/{assistant_id}", status_code=204)
async def purge(workspace_id: str, assistant_id: str, db: DB, actor: Actor) -> Response:
    await service.delete_assistant(db, actor, workspace_id, assistant_id)
    return Response(status_code=204)
