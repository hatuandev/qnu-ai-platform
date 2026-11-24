from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_blob_store, get_db
from qnu.domains.conversations import history, service
from qnu.domains.conversations.access import owned
from qnu.domains.conversations.document_export import (
    ExportFormat,
    content_disposition_header,
    export_turn_document,
)
from qnu.domains.conversations.execution import send
from qnu.domains.conversations.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    PromoteToBenchmarkRequest,
    PromoteToBenchmarkResponse,
    TurnFeedbackRequest,
    TurnRequest,
    TurnResponse,
)
from qnu.domains.identity.actor import AuthActor
from qnu.ports.blob_store import BlobStore


def no_store(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/workspaces/{workspace_id}/conversations",
    tags=["Conversations"],
    dependencies=[Depends(no_store)],
)
DB = Annotated[AsyncSession, Depends(get_db)]
Actor = Annotated[AuthActor, Depends(get_actor)]
Blob = Annotated[BlobStore, Depends(get_blob_store)]
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


@router.post("", response_model=ConversationResponse, status_code=201)
async def create(workspace_id: str, body: ConversationCreate, db: DB, actor: Actor):
    return await service.create(db, actor, workspace_id, body)


@router.get("", response_model=list[ConversationResponse])
async def listing(
    workspace_id: str,
    db: DB,
    actor: Actor,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    assistant_id: str | None = Query(None, max_length=64),
):
    return await service.listing(db, actor, workspace_id, limit, offset, assistant_id)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def detail(workspace_id: str, conversation_id: str, db: DB, actor: Actor):
    return await owned(db, actor, workspace_id, conversation_id)


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update(
    workspace_id: str, conversation_id: str, body: ConversationUpdate, db: DB, actor: Actor
):
    return await service.update(db, actor, workspace_id, conversation_id, body)


@router.post("/{conversation_id}/turns", response_model=TurnResponse)
async def message(
    workspace_id: str,
    conversation_id: str,
    body: TurnRequest,
    idempotency_key: Key,
    request: Request,
    db: DB,
    actor: Actor,
    blob: Blob,
):
    c = request.app.state.container
    return await send(
        db,
        blob,
        c.embedding_model,
        c.vector_store,
        c.chat_model,
        actor,
        workspace_id,
        conversation_id,
        body,
        idempotency_key,
        reranker=c.reranker,
    )


@router.get("/{conversation_id}/turns", response_model=list[TurnResponse])
async def turns(
    workspace_id: str,
    conversation_id: str,
    request: Request,
    db: DB,
    actor: Actor,
    blob: Blob,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await history.list_turns(
        db,
        blob,
        request.app.state.container.vector_store,
        actor,
        workspace_id,
        conversation_id,
        limit,
        offset,
    )


@router.get("/{conversation_id}/turns/{turn_id}", response_model=TurnResponse)
async def turn(
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    request: Request,
    db: DB,
    actor: Actor,
    blob: Blob,
):
    return await history.get_turn(
        db,
        blob,
        request.app.state.container.vector_store,
        actor,
        workspace_id,
        conversation_id,
        turn_id,
    )


@router.post("/{conversation_id}/turns/{turn_id}/feedback", response_model=TurnResponse)
async def feedback(
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    body: TurnFeedbackRequest,
    request: Request,
    db: DB,
    actor: Actor,
    blob: Blob,
):
    return await history.set_feedback(
        db,
        blob,
        request.app.state.container.vector_store,
        actor,
        workspace_id,
        conversation_id,
        turn_id,
        body,
    )


@router.post(
    "/{conversation_id}/turns/{turn_id}/promote-to-benchmark",
    response_model=PromoteToBenchmarkResponse,
)
async def promote_to_benchmark(
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    db: DB,
    actor: Actor,
    body: PromoteToBenchmarkRequest | None = None,
):
    return await history.promote_turn_to_benchmark(
        db,
        actor,
        workspace_id,
        conversation_id,
        turn_id,
        body or PromoteToBenchmarkRequest(),
    )


@router.get("/{conversation_id}/turns/{turn_id}/export")
async def export_turn(
    workspace_id: str,
    conversation_id: str,
    turn_id: str,
    db: DB,
    actor: Actor,
    format: ExportFormat = Query(...),
) -> Response:
    payload, media_type, filename = await export_turn_document(
        db, actor, workspace_id, conversation_id, turn_id, format
    )
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": content_disposition_header(filename),
            "Cache-Control": "private, no-store",
        },
    )



