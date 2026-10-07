"""Pydantic Request and Response Schemas for Central Document Repository."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AttachedCollectionInfo(BaseModel):
    """Summary of a Knowledge Collection referencing this repository document."""

    model_config = ConfigDict(from_attributes=True)

    collection_id: str
    collection_name: str
    document_id: str
    index_status: str
    created_at: datetime


class RepositoryDocumentListItem(BaseModel):
    """Compact summary of a document in the repository for tables and grids."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    document_type_code: str | None = None
    document_type_name: str | None = None
    document_number: str | None = None
    issuing_authority: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    parse_status: str
    ocr_engine: str | None = None
    attached_collections_count: int = 0
    created_at: datetime
    updated_at: datetime


class RepositoryDocumentResponse(BaseModel):
    """Detailed response of a document in the repository."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    storage_path: str
    document_type_code: str | None = None
    document_type_name: str | None = None
    document_number: str | None = None
    issuing_authority: str | None = None
    issued_date: date | None = None
    effective_date: date | None = None
    parse_status: str
    ocr_engine: str | None = None
    parsed_markdown: str | None = None
    doc_metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    attached_collections: list[AttachedCollectionInfo] = Field(default_factory=list)
    attached_collections_count: int = 0
    created_at: datetime
    updated_at: datetime


class RepositoryDocumentUpdate(BaseModel):
    """Payload to update administrative metadata of a document."""

    title: str | None = Field(None, max_length=255)
    document_type_code: str | None = Field(None, max_length=64)
    document_number: str | None = Field(None, max_length=128)
    issuing_authority: str | None = Field(None, max_length=255)
    issued_date: date | None = None
    effective_date: date | None = None
    doc_metadata: dict[str, Any] | None = None


class RepositoryDocumentStatsResponse(BaseModel):
    """Aggregated KPI metrics for Central Document Repository."""

    total_documents: int = 0
    parsed_documents: int = 0
    pending_documents: int = 0
    failed_documents: int = 0
    total_size_bytes: int = 0
    document_types_count: int = 0
    attached_usages_count: int = 0


class ReparseDocumentRequest(BaseModel):
    """Request payload to re-trigger document parsing or OCR."""

    ocr_engine: str | None = Field(None, description="Tùy chọn engine OCR: auto, pymupdf_ocr, qwen3-vl:8b, gemini")
    force: bool = Field(False, description="Buộc bóc tách lại ngay cả khi đã thành công")


class AttachRepositoryDocumentsRequest(BaseModel):
    """Request payload to bind repository documents to a knowledge collection."""

    document_ids: list[str] = Field(..., min_length=1, description="Danh sách ID tài liệu từ Kho Tài Liệu")
    chunk_strategy: str | None = Field(None, description="Chiến lược cắt đoạn: clause, semantic hoặc auto")
    auto_approve: bool = Field(True, description="Tự động duyệt và lập chỉ mục Vector tức thì")


class AttachRepositoryDocumentsResponse(BaseModel):
    """Response returned when documents from repository are attached to a collection."""

    collection_id: str
    attached_count: int
    created_document_ids: list[str]
    message: str
