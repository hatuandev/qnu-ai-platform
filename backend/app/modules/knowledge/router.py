"""FastAPI Router for Knowledge Base Management — Thin Controller Pattern."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.knowledge.schemas import (
    CollectionCreateRequest,
    CollectionResponse,
    DocumentDetailResponse,
    DocumentResponse,
    ParsePreviewResponse,
)
from app.modules.knowledge.service import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["Knowledge Bases"])


@router.post(
    "/collections",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo Bộ sưu tập Tri thức Mới",
)
async def create_collection(
    body: CollectionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    col = await knowledge_service.create_collection(db, body)
    return CollectionResponse.model_validate(col)


@router.get(
    "/collections",
    response_model=list[CollectionResponse],
    summary="Danh sách Bộ sưu tập Tri thức",
)
async def list_collections(
    tenant_id: str = Header("tenant_qnu", alias="X-Tenant-Id"),
    workspace_id: str = Header("workspace_qnu", alias="X-Workspace-Id"),
    db: AsyncSession = Depends(get_db),
) -> list[CollectionResponse]:
    cols = await knowledge_service.list_collections(
        db, tenant_id=tenant_id, workspace_id=workspace_id
    )
    return [CollectionResponse.model_validate(c) for c in cols]


@router.get(
    "/collections/{collection_id}",
    response_model=CollectionResponse,
    summary="Chi tiết Bộ sưu tập Tri thức",
)
async def get_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    col = await knowledge_service.get_collection(db, collection_id)
    return CollectionResponse.model_validate(col)


@router.post(
    "/collections/{collection_id}/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên Tài liệu vào Kho Tri thức",
)
async def upload_document(
    collection_id: str,
    file: UploadFile = File(..., description="Tệp tài liệu (PDF, Word, Excel, Text)"),
    title: str | None = Form(None, description="Tiêu đề hiển thị của tài liệu"),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    content = await file.read()
    doc = await knowledge_service.ingest_document(
        db=db,
        collection_id=collection_id,
        file_bytes=content,
        file_name=file.filename or "unknown_file.txt",
        title=title,
    )
    return DocumentResponse.model_validate(doc)


@router.post(
    "/collections/{collection_id}/parse-preview",
    response_model=ParsePreviewResponse,
    summary="Xem trước Bóc tách & Chia đoạn Tài liệu (Không lưu DB)",
)
async def parse_preview(
    collection_id: str,
    file: UploadFile = File(...),
    strategy: str = Query("semantic", description="Chiến lược chia đoạn: semantic hoặc clause"),
) -> ParsePreviewResponse:
    content = await file.read()
    return await knowledge_service.parse_preview(
        file_bytes=content,
        file_name=file.filename or "sample.txt",
        strategy=strategy,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Chi tiết Tài liệu & Danh sách Chunks",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    doc = await knowledge_service.get_document(db, document_id)
    return DocumentDetailResponse.model_validate(doc)


@router.post(
    "/documents/{document_id}/archive",
    response_model=DocumentResponse,
    summary="Lưu trữ (Ẩn) Tài liệu Cũ",
)
async def archive_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc = await knowledge_service.archive_document(db, document_id)
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa vĩnh viễn Tài liệu",
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    await knowledge_service.delete_document(db, document_id)
