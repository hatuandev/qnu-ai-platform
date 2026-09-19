"""HTTP administration and chat endpoints for QNU AI Assistants."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.assistants.schemas import (
    AssistantBundle,
    AssistantChatRequest,
    AssistantCloneRequest,
    AssistantCreateRequest,
    AssistantGenerateRequest,
    AssistantGenerateResponse,
    AssistantPublishResponse,
    AssistantReadinessResponse,
    AssistantResponse,
    AssistantRollbackResponse,
    AssistantSeedResponse,
    AssistantTemplateResponse,
    AssistantUpdateRequest,
    AssistantVersionResponse,
)
from app.modules.assistants.service import assistant_service

router = APIRouter(prefix="/assistants", tags=["05 Trợ lý Chuyên trách Chuẩn QNU"])
chat_router = APIRouter(prefix="/assistants", tags=["05 Trợ lý Chuyên trách Chuẩn QNU - Chat Runtime"])


@router.get("/templates", response_model=list[AssistantTemplateResponse])
async def list_assistant_templates() -> list[AssistantTemplateResponse]:
    """Return the five official Core-derived templates for the creation wizard."""
    return assistant_service.list_templates()


@router.post("/generate", response_model=AssistantGenerateResponse)
async def generate_assistant_spec(
    body: AssistantGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> AssistantGenerateResponse:
    """Generate assistant metadata, system prompt, and sample questions from an idea."""
    return await assistant_service.generate_spec(db, body)


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


@chat_router.post("/{reference}/chat")
async def chat_with_assistant(
    reference: str,
    body: AssistantChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    correlation_id = getattr(request.state, "correlation_id", None)
    if body.stream:
        return StreamingResponse(
            assistant_service.chat_stream(
                db,
                reference,
                body,
                correlation_id=correlation_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await assistant_service.chat(
        db,
        reference,
        body,
        correlation_id=correlation_id,
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


@router.get("/{reference}/readiness", response_model=AssistantReadinessResponse)
async def get_assistant_readiness(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantReadinessResponse:
    """Kiểm tra 5 tiêu chí sẵn sàng xuất bản (Publish Gate) cho Trợ lý AI."""
    return await assistant_service.get_readiness(db, reference)


@router.post("/{reference}/publish", response_model=AssistantPublishResponse)
async def publish_assistant(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantPublishResponse:
    """Cổng xuất bản chính thức (Publish Gate) - Chặn kích hoạt nếu có lỗi nghiêm trọng."""
    return await assistant_service.publish_assistant(db, reference)


@router.post("/{reference}/clone", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def clone_assistant(
    reference: str,
    body: AssistantCloneRequest,
    db: AsyncSession = Depends(get_db),
) -> AssistantResponse:
    """Nhân bản 1-click Trợ lý AI để tùy biến cho khoa/phòng ban chuyên trách."""
    return await assistant_service.clone_assistant(db, reference, body)


@router.get("/{reference}/versions", response_model=list[AssistantVersionResponse])
async def get_assistant_versions(
    reference: str,
    db: AsyncSession = Depends(get_db),
) -> list[AssistantVersionResponse]:
    """Lấy danh sách lịch sử các phiên bản cấu hình của Trợ lý AI."""
    return await assistant_service.get_versions(db, reference)


@router.post("/{reference}/rollback/{version_id}", response_model=AssistantRollbackResponse)
async def rollback_assistant_version(
    reference: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
) -> AssistantRollbackResponse:
    """Khôi phục cấu hình Trợ lý AI về một phiên bản snapshot trước đó."""
    return await assistant_service.rollback_version(db, reference, version_id)

