"""Pydantic Schemas & DTOs for RAG (Retrieval-Augmented Generation)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=1000, description="Nội dung câu hỏi hoặc từ khóa tìm kiếm"
    )
    collection_id: str = Field(..., description="Mã bộ sưu tập tri thức cần tra cứu")
    module_code: str | None = Field(
        "general", description="Mã phân hệ: admissions, regulations, library..."
    )
    top_k: int = Field(8, ge=1, le=50, description="Số lượng chunk lấy ra ban đầu")
    rerank_top_k: int = Field(5, ge=1, le=20, description="Số lượng chunk sau khi tái xếp hạng")
    filters: dict[str, Any] | None = Field(
        default_factory=dict, description="Bộ lọc payload metadata"
    )
    tenant_id: str | None = Field(default=None, description="Mã tenant cô lập dữ liệu")
    workspace_id: str | None = Field(default=None, description="Mã workspace cô lập dữ liệu")


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    rank: int
    section: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    collection_id: str
    total_found: int
    items: list[SearchResultItem]
    execution_time_ms: float


class Citation(BaseModel):
    source_id: str
    title: str
    section: str | None = None
    page_number: int | None = None
    quote: str | None = None
    source_pages: list[int] | None = None
    entity_key: str | None = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Câu hỏi người dùng")
    collection_id: str = Field(..., description="Mã bộ sưu tập tri thức")
    module_code: str = Field(
        "admissions", description="Mã phân hệ: admissions, regulations, library, drafting..."
    )
    conversation_id: str | None = None
    system_prompt: str | None = None
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(2000, ge=100, le=32000)
    thinking_budget: int = Field(0, ge=0, le=4096, description="Ngân sách token suy nghĩ ngầm (0 = tắt)")
    preferred_model_name: str | None = None
    preferred_provider_id: str | None = None
    fallback_model: str | None = None
    tenant_id: str = Field("tenant_qnu", min_length=2, max_length=100)
    workspace_id: str = Field("workspace_qnu", min_length=2, max_length=100)
    history: list[dict[str, str]] | None = Field(
        default=None, description="Lịch sử các lượt hội thoại gần nhất [{'role': 'user'|'assistant', 'content': '...'}]"
    )


class AskResponse(BaseModel):
    status: str = Field(..., description="Trạng thái: answered hoặc insufficient_context")
    answer: str = Field(..., description="Nội dung câu trả lời")
    answer_format: str = Field(
        "paragraph",
        description="Định dạng: paragraph, markdown_table, bullet_list, checklist, timeline",
    )
    citations: list[Citation] = Field(
        default_factory=list, description="Danh sách nguồn tài liệu trích dẫn"
    )
    facts_used: list[dict[str, Any]] = Field(
        default_factory=list, description="Các bản ghi sự thật đã sử dụng"
    )
    latency_ms: float = 0.0
