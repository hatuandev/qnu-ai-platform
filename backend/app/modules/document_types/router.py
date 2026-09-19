"""FastAPI router for document taxonomy administration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.document_types.schemas import (
    DocumentTypeCreateRequest,
    DocumentTypeResponse,
    DocumentTypeSyncResponse,
    DocumentTypeUpdateRequest,
)
from app.modules.document_types.service import document_types_service

router = APIRouter(prefix="/document-types", tags=["Document Types"])


@router.get("", response_model=list[DocumentTypeResponse], summary="Danh sách loại văn bản")
async def list_document_types(
    search: str | None = Query(None, max_length=255),
    category: str | None = Query(None, max_length=64),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentTypeResponse]:
    return await document_types_service.list_document_types(
        db, search=search, category=category, active_only=active_only
    )


@router.get("/{code}", response_model=DocumentTypeResponse, summary="Chi tiết loại văn bản")
async def get_document_type(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentTypeResponse:
    return await document_types_service.get_document_type(db, code)


@router.post(
    "",
    response_model=DocumentTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo loại văn bản tùy chỉnh",
)
async def create_document_type(
    body: DocumentTypeCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentTypeResponse:
    return await document_types_service.create_document_type(db, body)


@router.put("/{code}", response_model=DocumentTypeResponse, summary="Cập nhật loại văn bản")
async def update_document_type(
    code: str,
    body: DocumentTypeUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentTypeResponse:
    return await document_types_service.update_document_type(db, code, body)


@router.post(
    "/{code}/deactivate",
    response_model=DocumentTypeResponse,
    summary="Vô hiệu hóa loại văn bản",
)
async def deactivate_document_type(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentTypeResponse:
    return await document_types_service.deactivate_document_type(db, code)


@router.post(
    "/{code}/activate",
    response_model=DocumentTypeResponse,
    summary="Kích hoạt lại loại văn bản",
)
async def activate_document_type(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentTypeResponse:
    return await document_types_service.activate_document_type(db, code)


@router.post(
    "/sync", response_model=DocumentTypeSyncResponse, summary="Đồng bộ taxonomy từ qnu-ai-core"
)
async def sync_document_types(
    db: AsyncSession = Depends(get_db),
) -> DocumentTypeSyncResponse:
    return await document_types_service.sync_from_catalog(db)
