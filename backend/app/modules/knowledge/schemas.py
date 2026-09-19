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
    document_type_code: str | None = None
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    version: int
    status: str
    index_status: str = "pending"
    index_error: str | None = None
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
    index_status: str = "indexed"
    total_chunks: int
    indexed_chunks: int


class BatchApproveRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1, max_length=50)


class BatchApproveFailure(BaseModel):
    document_id: str
    error: str


class BatchApproveResponse(BaseModel):
    approved: list[str] = Field(default_factory=list)
    failed: list[BatchApproveFailure] = Field(default_factory=list)
    indexed_chunks: int = 0


class StudioBox(BaseModel):
    id: str
    page_number: int
    type: str
    coordinates: dict[str, float]
    label: str
    confidence: float
    content_snippet: str = ""


class StudioRegion(BaseModel):
    id: str
    page_number: int
    title: str
    type: str
    confidence: float
    reading_order: int
    details: str = ""


class StudioPageView(BaseModel):
    page_number: int
    markdown_content: str
    raw_text: str
    word_count: int
    line_count: int
    image_url: str | None = None
    bounding_boxes: list[StudioBox] = Field(default_factory=list)
    regions: list[StudioRegion] = Field(default_factory=list)


class StudioViewResponse(BaseModel):
    document_id: str
    collection_id: str
    title: str
    filename: str
    engine: str
    total_pages: int
    file_size_bytes: int = 0
    total_chunks: int = 0
    pages: list[StudioPageView] = Field(default_factory=list)


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


class FactItemResponse(BaseModel):
    id: str
    collection_id: str
    document_id: str
    entity_name: str
    entity_type: str
    attribute_name: str
    attribute_value: str
    confidence: float
    raw_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class FactListResponse(BaseModel):
    collection_id: str
    total: int
    facts: list[FactItemResponse]


class FactExcelImportResponse(BaseModel):
    collection_id: str
    imported_count: int
    document_id: str
    message: str


# ==============================================================================
# 4. Reindex & Reconciliation Schemas
# ==============================================================================
class ReindexDocumentResponse(BaseModel):
    document_id: str
    status: str
    index_status: str
    indexed_chunks: int
    message: str


class KnowledgeReconciliationDiscrepancy(BaseModel):
    type: str  # missing_qdrant_vector, orphan_qdrant_point, missing_storage_file
    document_id: str | None = None
    details: str


class KnowledgeReconciliationResponse(BaseModel):
    collection_id: str
    db_documents_count: int
    indexed_documents_count: int
    failed_documents_count: int
    db_chunks_count: int
    qdrant_points_count: int
    storage_files_count: int
    is_consistent: bool
    discrepancies: list[KnowledgeReconciliationDiscrepancy] = Field(default_factory=list)


class ReconcileFixResponse(BaseModel):
    collection_id: str
    reindexed_documents: list[str] = Field(default_factory=list)
    failed_documents: list[str] = Field(default_factory=list)
    total_reindexed_chunks: int = 0
    message: str

