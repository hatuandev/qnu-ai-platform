"""Thin preparation API: accept an intent, read its phase, cancel the next step."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from qnu.api.dependencies import get_actor, get_db, get_job_queue
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.preparation import service
from qnu.domains.knowledge.preparation.schemas import (
    PreparationCreated,
    PreparationRequest,
    PreparationResponse,
    preparation_response,
)
from qnu.ports.job_queue import JobQueue

router = APIRouter(
    prefix="/workspaces/{workspace_id}/collections/{collection_id}",
    tags=["Knowledge · Preparation"],
)


@router.post(
    "/sources/{source_id}/preparation-intents",
    response_model=PreparationCreated,
    status_code=201,
)
async def create_preparation(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    body: PreparationRequest,
    response: Response,
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    ],
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
    queue: JobQueue | None = Depends(get_job_queue),
) -> PreparationCreated:
    outcome = await service.create_intent(
        db, actor, workspace_id, collection_id, source_id, body, idempotency_key, queue
    )
    if not outcome.created:
        response.status_code = 200
    return PreparationCreated(
        intent=preparation_response(outcome.intent),
        created=outcome.created,
        dispatched=outcome.dispatched,
    )


@router.get(
    "/sources/{source_id}/preparation-intents",
    response_model=list[PreparationResponse],
)
async def list_preparations(
    workspace_id: str,
    collection_id: str,
    source_id: str,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> list[PreparationResponse]:
    rows = await service.list_intents(
        db, actor, workspace_id, collection_id, source_id, limit
    )
    return [preparation_response(row) for row in rows]


@router.get("/preparation-intents/{intent_id}", response_model=PreparationResponse)
async def preparation_status(
    workspace_id: str,
    collection_id: str,
    intent_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> PreparationResponse:
    row = await service.get_intent(db, actor, workspace_id, collection_id, intent_id)
    return preparation_response(row)


@router.post("/preparation-intents/{intent_id}/cancel", response_model=PreparationResponse)
async def cancel_preparation(
    workspace_id: str,
    collection_id: str,
    intent_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(get_actor),
) -> PreparationResponse:
    row = await service.cancel(db, actor, workspace_id, collection_id, intent_id)
    return preparation_response(row)
