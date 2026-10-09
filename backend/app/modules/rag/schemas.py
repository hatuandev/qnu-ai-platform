"""Pydantic Schemas & DTOs for RAG (Retrieval-Augmented Generation)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RetrievalSnapshot(BaseModel):
    """Immutable snapshot pinning collection epochs and binding index revisions for session consistency."""

    snapshot_id: str = Field(..., description="Mã định danh duy nhất của snapshot")
    collection_id: str = Field(..., description="Mã bộ sưu tập tri thức")
    collection_epoch: int = Field(1, description="Epoch hiện hành của bộ sưu tập")
    binding_revisions: dict[str, str] = Field(
        default_factory=dict,
        description="Bản đồ khóa phiên bản {binding_id: active_index_revision_id}",
    )
    vector_generations: dict[str, str] = Field(default_factory=dict)
    tenant_id: str | None = None
    workspace_id: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Thời điểm tạo snapshot ISO-8601",
    )

    def cache_fingerprint(self) -> str:
        """Stable fingerprint for cache isolation across immutable retrieval snapshots."""
        payload = {
            "collection_id": self.collection_id,
            "collection_epoch": self.collection_epoch,
            "binding_revisions": sorted(self.binding_revisions.items()),
            "vector_generations": sorted(self.vector_generations.items()),
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
        }
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]


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
    snapshot_id: str | None = Field(default=None, description="ID snapshot cố định phiên tra cứu")
    retrieval_snapshot: RetrievalSnapshot | None = Field(
        default=None, description="Chi tiết snapshot được pin cho phiên"
    )

    @property
    def snapshot(self) -> RetrievalSnapshot | None:
        return self.retrieval_snapshot


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    rank: int
    section: str | None = None
    page_number: int | None = None
    binding_id: str | None = None
    index_revision_id: str | None = None
    revision_no: int | None = None
    document_revision: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    collection_id: str
    total_found: int
    items: list[SearchResultItem]
    execution_time_ms: float
    retrieval_snapshot: RetrievalSnapshot | None = None
    snapshot: RetrievalSnapshot | None = None


class Citation(BaseModel):
    source_id: str
    title: str
    section: str | None = None
    page_number: int | None = None
    quote: str | None = None
    source_pages: list[int] | None = None
    entity_key: str | None = None
    binding_id: str | None = None
    index_revision_id: str | None = None
    source_revision_id: str | None = None
    revision_no: int | None = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="Câu hỏi người dùng")
    collection_id: str = Field(..., description="Mã bộ sưu tập tri thức")
    module_code: str = Field(
        "general", description="Mã phân hệ: admissions, regulations, library, drafting..."
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
    reranker_policy: dict[str, Any] | None = None
    snapshot_id: str | None = Field(default=None, description="ID snapshot cố định phiên tra cứu")
    retrieval_snapshot: RetrievalSnapshot | None = Field(
        default=None, description="Chi tiết snapshot được pin cho phiên"
    )

    @property
    def snapshot(self) -> RetrievalSnapshot | None:
        return self.retrieval_snapshot


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
    suggested_questions: list[str] = Field(
        default_factory=list, description="Danh sách câu hỏi gợi ý tiếp theo"
    )
    latency_ms: float = 0.0
    contexts: list[str] = Field(
        default_factory=list, description="Nội dung các chunk tri thức được truy xuất làm ngữ cảnh"
    )
    retrieval_snapshot: RetrievalSnapshot | None = None
    snapshot: RetrievalSnapshot | None = None
