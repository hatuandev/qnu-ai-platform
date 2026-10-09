"""Pydantic Schemas & DTOs for Knowledge Base Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# 1. Collection Schemas
# ==============================================================================
class CollectionDataProcessingConfig(BaseModel):
    """Cấu hình xử lý dữ liệu đặc thù cho từng Kho Tri Thức (Embedding & Vision OCR)."""

    embedding_provider_id: str = Field("prov_rtx5090_vllm", description="ID nhà cung cấp embedding")
    embedding_model: str = Field("bge-m3", description="Mô hình vector embedding")
    embedding_dimension: int = Field(1024, description="Số chiều vector (1024, 2560, 768, 1536)")
    ocr_mode: str = Field("combo", description="single hoặc combo")
    primary_ocr_provider_id: str = Field("prov_gemini", description="ID nhà cung cấp OCR chính")
    primary_ocr_model: str = Field("gemini-3.1-flash-lite", description="Mô hình OCR chính")
    fallback_ocr_provider_id: str | None = Field(
        "prov_mistral", description="ID nhà cung cấp OCR dự phòng"
    )
    fallback_ocr_model: str | None = Field("mistral-ocr-latest", description="Mô hình OCR dự phòng")


class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Tên bộ sưu tập tri thức")
    description: str | None = Field(None, max_length=2000, description="Mô tả chi tiết")
    module_code: str = Field(
        ..., max_length=64, description="Mã phân hệ: admissions, regulations, library, drafting..."
    )
    tenant_id: str = Field("tenant_qnu", max_length=64)
    workspace_id: str = Field("workspace_qnu", max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_processing: CollectionDataProcessingConfig | None = None


class CollectionUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None
    data_processing: CollectionDataProcessingConfig | None = None


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
    status: str = "pending"
    index_status: str | None = None
    total_pages: int
    file_size_bytes: int = 0
    total_chunks: int = 0
    pdf_url: str | None = None
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


# ==============================================================================
# 5. Knowledge Publishing V2 Schemas (ADR-011)
# ==============================================================================
class AvailableRepositoryDocumentItem(BaseModel):
    id: str
    document_code: str
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int = 0
    current_revision_id: str | None = None
    current_revision_no: int | None = None
    revision_count: int = 0
    status: str
    is_bound: bool = False
    bound_binding_id: str | None = None
    created_at: datetime
    updated_at: datetime


class AvailableRepositoryDocumentsResponse(BaseModel):
    items: list[AvailableRepositoryDocumentItem]
    total: int


class BindingSelectionItem(BaseModel):
    repository_document_id: str
    target_revision_id: str | None = None
    chunk_strategy: str = "ClauseBasedChunker"
    sync_policy: str = "manual"  # manual, auto_on_ready
    auto_activate: bool = False


class CreateKnowledgeBindingsRequest(BaseModel):
    items: list[BindingSelectionItem]


class BindingResultItem(BaseModel):
    binding_id: str | None = None
    repository_document_id: str
    source_revision_id: str | None = None
    status: str  # created, already_bound, failed
    message: str | None = None
    index_revision_id: str | None = None


class CreateKnowledgeBindingsResponse(BaseModel):
    collection_id: str
    created_count: int
    skipped_count: int
    failed_count: int
    bindings: list[BindingResultItem]


class KnowledgeBindingResponse(BaseModel):
    id: str
    collection_id: str
    repository_document_id: str
    source_revision_id: str
    active_index_revision_id: str | None = None
    active_epoch: int = 0
    chunk_strategy: str = "ClauseBasedChunker"
    sync_policy: str = "manual"
    status: str = "active"
    document_title: str | None = None
    document_code: str | None = None
    file_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeChunkItemResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int = 0
    section: str | None = None
    page_number: int | None = None
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)
    index_revision_id: str | None = None

    model_config = {"from_attributes": True}


class BindingChunksListResponse(BaseModel):
    binding_id: str
    index_revision_id: str | None = None
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[KnowledgeChunkItemResponse] = Field(default_factory=list)


class ParityReportDTO(BaseModel):
    expected_chunks: int = 0
    indexed_points: int = 0
    verified_points: int = 0
    point_ids_count: int = 0
    parity_status: str = "pending"  # "passed" | "failed" | "pending"
    reason: str = ""
    checked_at: str = ""


class KnowledgeIndexRevisionResponse(BaseModel):
    id: str
    binding_id: str
    source_revision_id: str
    vector_generation_id: str
    revision_no: int
    chunk_count: int = 0
    fact_count: int = 0
    point_ids: list[str] = Field(default_factory=list)
    parity_report: ParityReportDTO = Field(default_factory=ParityReportDTO)
    status: str = "building"
    failure_code: str | None = None
    failure_detail: str | None = None
    is_rollback_available: bool = False
    storage_state: str = "available"  # "available" | "pruned"
    created_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class BuildStagingIndexRequest(BaseModel):
    source_revision_id: str | None = None
    chunk_strategy: str | None = None
    auto_activate: bool = False


class IndexActivationRequest(BaseModel):
    to_index_revision_id: str
    expected_epoch: int = Field(..., ge=0, description="Epoch hiện tại của binding để chống xung đột CAS")
    reason: str | None = None


class IndexActivationResponse(BaseModel):
    id: str
    binding_id: str
    from_index_revision_id: str | None = None
    to_index_revision_id: str
    action: str = "promote"
    epoch: int = 0
    reason: str | None = None
    activated_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RollbackIndexRevisionRequest(BaseModel):
    target_index_revision_id: str
    expected_epoch: int = Field(..., ge=0)
    reason: str | None = None


# ==============================================================================
# 6. Legacy Backfill, Canary & Shadow Retrieval Schemas (ADR-011 Phase 6)
# ==============================================================================
class LegacyAuditItem(BaseModel):
    document_id: str
    document_title: str
    repository_document_id: str | None = None
    binding_id: str | None = None
    active_index_revision_id: str | None = None
    db_chunks_count: int = 0
    qdrant_points_count: int = 0
    classification: str  # 'active-parity-ok', 'needs-rebuild', 'pending-intake'
    discrepancy_reason: str | None = None


class LegacyAuditReport(BaseModel):
    collection_id: str
    total_documents: int
    active_parity_ok_count: int
    needs_rebuild_count: int
    pending_intake_count: int
    parity_ratio: float
    items: list[LegacyAuditItem] = Field(default_factory=list)
    audited_at: datetime


class BackfillRequest(BaseModel):
    force_rebuild: bool = False
    default_chunk_strategy: str = "ClauseBasedChunker"


class BackfillItemResult(BaseModel):
    document_id: str
    binding_id: str
    index_revision_id: str
    chunks_tagged: int
    facts_tagged: int
    classification: str
    status: str  # 'created', 'updated', 'skipped', 'failed'


class BackfillReport(BaseModel):
    collection_id: str
    documents_processed: int
    bindings_created: int
    index_revisions_created: int
    chunks_tagged: int
    facts_tagged: int
    collection_epoch: int
    status: str  # 'completed', 'partial', 'failed'
    items: list[BackfillItemResult] = Field(default_factory=list)
    completed_at: datetime


class ShadowRetrievalRequest(BaseModel):
    query: str
    top_k: int = 5


class ShadowRetrievalReport(BaseModel):
    collection_id: str
    query: str
    v1_result_count: int
    v2_result_count: int
    overlap_count: int
    jaccard_similarity: float
    latency_v1_ms: float
    latency_v2_ms: float
    latency_delta_pct: float
    retrieval_revision_leak_total: int
    leak_detected: bool
    v1_chunk_ids: list[str] = Field(default_factory=list)
    v2_chunk_ids: list[str] = Field(default_factory=list)
    tested_at: datetime


class GarbageCollectionRequest(BaseModel):
    keep_revisions: int = Field(
        2, ge=1, le=10, description="Số lượng revision superseded gần nhất giữ lại cho rollback"
    )
    dry_run: bool = Field(False, description="Nếu true, chỉ tính toán và báo cáo không xóa dữ liệu")


class GarbageCollectionReport(BaseModel):
    collection_id: str
    dry_run: bool
    keep_revisions: int
    total_bindings_scanned: int
    pruned_revisions_count: int
    pruned_revision_ids: list[str] = Field(default_factory=list)
    pruned_chunks_count: int
    pruned_facts_count: int
    pruned_points_count: int
    message: str
    executed_at: datetime


class CanaryPolicyResponse(BaseModel):
    collection_id: str
    read_mode: str  # "system" | "revisioned" | "shadow" | "legacy"
    system_read_mode: str
    effective_read_mode: str
    retention_revisions: int
    last_gc_report: dict[str, Any] | None = None


class UpdateCanaryPolicyRequest(BaseModel):
    read_mode: str = Field("system", description="Chế độ đọc: system, revisioned, shadow, legacy")
    retention_revisions: int = Field(
        2, ge=1, le=10, description="Số bản superseded lưu lại cho rollback"
    )


class SystemGarbageCollectionRequest(BaseModel):
    dry_run: bool = Field(
        False, description="Nếu true, chỉ tính toán và mô phỏng dọn dẹp toàn hệ thống"
    )
    default_keep_revisions: int = Field(
        2,
        ge=1,
        le=10,
        description="Số bản superseded lưu trữ mặc định nếu collection chưa cấu hình",
    )


class SystemGarbageCollectionReport(BaseModel):
    total_collections_scanned: int
    total_bindings_scanned: int
    total_pruned_revisions_count: int
    total_pruned_chunks_count: int
    total_pruned_facts_count: int
    total_pruned_points_count: int
    dry_run: bool
    reports: list[GarbageCollectionReport] = Field(default_factory=list)
    message: str
    executed_at: datetime


class SystemDecommissioningAuditReport(BaseModel):
    total_collections: int
    total_legacy_documents: int
    total_v2_bindings: int
    v2_adoption_rate_pct: float
    collections_in_revisioned_mode: int
    collections_in_shadow_mode: int
    collections_in_legacy_mode: int
    total_prunable_revisions_estimate: int
    audited_at: datetime


# ==============================================================================
# 9. Document Group Attachment Schemas
# ==============================================================================
SUPPORTED_CHUNK_STRATEGIES: set[str] = {
    "ClauseBasedChunker",
    "SemanticChunker",
    "AdmissionsRecordChunker",
    "ImplementationTaskChunker",
}


class PreviewDocumentGroupRequest(BaseModel):
    """Request payload to preview attaching a group to a collection."""

    group_id: str = Field(..., description="ID của nhóm tài liệu cần xem trước")

    @field_validator("group_id", mode="before")
    @classmethod
    def validate_group_id(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError("group_id phải là chuỗi ký tự.")
        val = v.strip()
        if not val:
            raise ValueError("ID nhóm tài liệu không được để trống.")
        return val


class PreviewDocumentGroupItem(BaseModel):
    """Preview status of a single document member in the group."""

    document_id: str
    title: str
    file_name: str
    current_revision_id: str | None = None
    revision_status: str | None = None
    already_bound: bool = False
    eligible_for_binding: bool = False
    reason: str = ""


class PreviewDocumentGroupResponse(BaseModel):
    """Server-side preview breakdown of a document group before attaching."""

    collection_id: str
    group_id: str
    group_name: str
    total_documents: int
    ready_count: int
    already_bound_count: int
    not_ready_count: int
    failed_count: int
    items: list[PreviewDocumentGroupItem]


class AttachDocumentGroupRequest(BaseModel):
    """Request payload to snapshot and attach all ready documents of a group to a collection."""

    group_id: str = Field(..., description="ID của nhóm tài liệu cần đưa vào kho")
    chunk_strategy: str = Field("ClauseBasedChunker", description="Chiến lược cắt đoạn")
    sync_policy: Literal["manual"] = Field("manual", description="Chính sách đồng bộ (chỉ cho phép manual)")
    auto_activate: bool = Field(False, description="Tự động kích hoạt lập chỉ mục tức thì sau khi gắn")
    strict_ready: bool = Field(
        False, description="Nếu true và có tài liệu chưa ready, từ chối toàn bộ và báo lỗi"
    )

    @field_validator("group_id", mode="before")
    @classmethod
    def validate_group_id(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError("group_id phải là chuỗi ký tự.")
        val = v.strip()
        if not val:
            raise ValueError("ID nhóm tài liệu không được để trống.")
        return val

    @field_validator("chunk_strategy", mode="before")
    @classmethod
    def validate_chunk_strategy(cls, v: Any) -> str:
        if v is None:
            return "ClauseBasedChunker"
        if not isinstance(v, str):
            raise TypeError("chunk_strategy phải là chuỗi ký tự.")
        val = v.strip()
        if val not in SUPPORTED_CHUNK_STRATEGIES:
            supported = ", ".join(sorted(SUPPORTED_CHUNK_STRATEGIES))
            raise ValueError(
                f"Chiến lược phân đoạn '{val}' không được hỗ trợ. Các chiến lược hợp lệ: {supported}"
            )
        return val


class AttachDocumentGroupItemResult(BaseModel):
    """Result for each document evaluated during group attachment."""

    document_id: str
    document_title: str | None = None
    source_revision_id: str | None = None
    binding_id: str | None = None
    status: str = Field(..., description="created, already_bound, not_ready, failed")
    message: str | None = None
    index_revision_id: str | None = None


class AttachDocumentGroupResponse(BaseModel):
    """Summary response when attaching a document group to a knowledge collection."""

    collection_id: str
    group_id: str
    group_name: str
    total_documents: int
    created_count: int
    already_bound_count: int
    not_ready_count: int
    failed_count: int
    items: list[AttachDocumentGroupItemResult]
