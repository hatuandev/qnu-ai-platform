"""Pydantic Schemas & DTOs for Knowledge Base Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ==============================================================================
# 1. Collection Schemas
# ==============================================================================
class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Tên bộ sưu tập tri thức")
    description: str | None = Field(None, max_length=2000, description="Mô tả chi tiết")
    module_code: str = Field(
        ..., max_length=64, description="Mã phân hệ: admissions, regulations, library, drafting..."
    )
    tenant_id: str = Field("tenant_qnu", max_length=64)
    workspace_id: str = Field("workspace_qnu", max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    module_code: str
    tenant_id: str
    workspace_id: str
    is_active: bool
    metadata: dict[str, Any] = Field(default_factory=dict, alias="collection_metadata")
    created_at: datetime
    updated_at: datetime
    document_count: int | None = 0
    chunk_count: int | None = 0

    model_config = {"from_attributes": True, "populate_by_name": True}


# ==============================================================================
# 2. Chunk & Fact Schemas
# ==============================================================================
class ChunkItem(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    section: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, alias="chunk_metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}


class FactItem(BaseModel):
    id: str
    entity_name: str
    entity_type: str
    attribute_name: str
    attribute_value: str
    confidence: float
    raw_data: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


# ==============================================================================
# 3. Document Schemas
# ==============================================================================
class DocumentResponse(BaseModel):
    id: str
    collection_id: str
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    version: int
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    chunk_count: int | None = 0
    ocr_method: str | None = None

    model_config = {"from_attributes": True}


class ApprovePageEdit(BaseModel):
    page_number: int = Field(..., ge=1, description="Số thứ tự trang được sửa tay")
    markdown_content: str = Field(..., description="Nội dung Markdown đã hiệu đính của trang")


class ApproveDocumentRequest(BaseModel):
    pages: list[ApprovePageEdit] | None = Field(
        None, description="Các trang đã sửa tay; bỏ trống để duyệt nguyên bản bóc tách"
    )


class ApproveDocumentResponse(BaseModel):
    document_id: str
    status: str
    total_chunks: int
    indexed_chunks: int


class DocumentDetailResponse(DocumentResponse):
    chunks: list[ChunkItem] = Field(default_factory=list)
    doc_metadata: dict[str, Any] = Field(default_factory=dict)


class ParsePreviewResponse(BaseModel):
    file_name: str
    file_type: str
    file_size_bytes: int
    raw_markdown: str
    chunk_count: int
    estimated_tokens: int
    extracted_tables_count: int
    preview_chunks: list[dict[str, Any]]
    ocr_method: str = "PyMuPdfParser"
