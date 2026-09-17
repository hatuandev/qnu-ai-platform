"""HTTP administration and chat endpoints for QNU AI Assistants."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.assistants.schemas import (
    AssistantBundle,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantCreateRequest,
    AssistantResponse,
    AssistantSeedResponse,
    AssistantTemplateResponse,
    AssistantUpdateRequest,
)
from app.modules.assistants.service import assistant_service

router = APIRouter(prefix="/assistants", tags=["05 Trợ lý Chuyên trách Chuẩn QNU"])


@router.get("/templates", response_model=list[AssistantTemplateResponse])
async def list_assistant_templates() -> list[AssistantTemplateResponse]:
    """Return the five official Core-derived templates for the creation wizard."""
    return assistant_service.list_templates()


@router.post("/seed-defaults", response_model=AssistantSeedResponse)
async def seed_default_assistants(
    db: AsyncSession = Depends(get_db),
) -> AssistantSeedResponse:
    """Persist missing official assistants and workflows without overwriting existing rows."""
    return await assistant_service.seed_defaults(db)


@router.post(
    "/import",
    response_model=AssistantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_assistant_bundle(
    body: AssistantBundle,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    return await assistant_service.import_bundle(db, body)


@router.get("", response_model=list[AssistantResponse])
async def list_assistants(
    search: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=50),
    include_inactive: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[AssistantResponse]:
    return await assistant_service.list_assistants(
        db,
        search=search,
        category=category,
        include_inactive=include_inactive,
    )


@router.post(
    "",
    response_model=AssistantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assistant(
    body: AssistantCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    return await assistant_service.create_assistant(db, body)


@router.get("/{reference}/export", response_model=AssistantBundle)
async def export_assistant_bundle(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantBundle:
    return await assistant_service.export_bundle(db, reference)


@router.post("/{reference}/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(
    reference: str,
    body: AssistantChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AssistantChatResponse:
    return await assistant_service.chat(
        db,
        reference,
        body,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/{reference}", response_model=AssistantResponse)
async def get_assistant(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    return await assistant_service.get_assistant(db, reference)


@router.patch("/{reference}", response_model=AssistantResponse)
async def update_assistant(
    reference: str,
    body: AssistantUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    return await assistant_service.update_assistant(db, reference, body)


@router.delete("/{reference}", response_model=AssistantResponse)
async def deactivate_assistant(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    """Soft-delete an assistant so workflow history and audits remain intact."""
    return await assistant_service.deactivate_assistant(db, reference)
