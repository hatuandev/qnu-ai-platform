"""FastAPI Router for Knowledge Base Management — Thin Controller Pattern."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import AuthActor
from app.modules.jobs.schemas import JobResponse
from app.modules.knowledge.schemas import (
    ActivateVectorGenerationResponse,
    ApproveDocumentRequest,
    ApproveDocumentResponse,
    AttachDocumentGroupRequest,
    AttachDocumentGroupResponse,
    AttachGroupSourceRequest,
    AvailableRepositoryDocumentsResponse,
    BackfillReport,
    BackfillRequest,
    BatchApproveRequest,
    BatchApproveResponse,
    BindingChunksListResponse,
    BuildStagingIndexRequest,
    BuildVectorGenerationRequest,
    BuildVectorGenerationResponse,
    CanaryPolicyResponse,
    CandidateGroupListResponse,
    CandidateListResponse,
    CandidateQueryRequest,
    CollectionCreateRequest,
    CollectionResponse,
    CollectionSummaryMetrics,
    CollectionUpdateRequest,
    CreateKnowledgeBindingsRequest,
    CreateKnowledgeBindingsResponse,
    CreateVectorGenerationRequest,
    DetachGroupSourceRequest,
    DetachGroupSourceResponse,
    DocumentDetailResponse,
    DocumentResponse,
    FactExcelImportResponse,
    FactListResponse,
    GarbageCollectionReport,
    GarbageCollectionRequest,
    IndexActivationRequest,
    IndexActivationResponse,
    KnowledgeBindingResponse,
    KnowledgeChunkSetResponse,
    KnowledgeGroupSourceResponse,
    KnowledgeImportBatchCreateRequest,
    KnowledgeImportBatchResponse,
    KnowledgeIndexRevisionResponse,
    KnowledgeReconciliationResponse,
    KnowledgeSourceDetailResponse,
    KnowledgeSourceRevisionResponse,
    KnowledgeVectorGenerationResponse,
    LegacyAuditReport,
    ParsePreviewResponse,
    PreviewDocumentGroupRequest,
    PreviewDocumentGroupResponse,
    PreviewGroupSourceDiffResponse,
    PublishGroupSourceResponse,
    ReconcileFixResponse,
    ReindexDocumentResponse,
    ReparseSourceRequest,
    ReviewSourceRevisionRequest,
    RollbackIndexRevisionRequest,
    ShadowRetrievalReport,
    ShadowRetrievalRequest,
    StudioViewResponse,
    SyncGroupSourceRequest,
    SyncGroupSourceResponse,
    SystemDecommissioningAuditReport,
    SystemGarbageCollectionReport,
    SystemGarbageCollectionRequest,
    UpdateCanaryPolicyRequest,
    UpdateSourceContentRequest,
    VectorLoadRequest,
)
from app.modules.knowledge.service import knowledge_service
from app.modules.knowledge.services.backfill_service import BackfillV3Report, backfill_v3_service
from app.modules.knowledge.services.candidate_service import candidate_service
from app.modules.knowledge.services.chunk_set_service import chunk_set_service
from app.modules.knowledge.services.group_source_service import group_source_service
from app.modules.knowledge.services.import_batch_service import import_batch_service
from app.modules.knowledge.services.reconciliation_service import (
    ReconciliationReport,
    reconciliation_service,
)
from app.modules.knowledge.services.source_ingestion_service import source_ingestion_service
from app.modules.knowledge.services.vector_generation_service import vector_generation_service
from app.modules.knowledge.services.vector_load_service import (
    get_vector_load_state,
    queue_vector_load,
)
from app.modules.rag.schemas import AskResponse

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
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> CollectionResponse:
    col = await knowledge_service.create_collection(db, body, actor=actor)
    return CollectionResponse.model_validate(col)


@router.get(
    "/collections",
    response_model=list[CollectionResponse],
    summary="Danh sách Bộ sưu tập Tri thức",
)
async def list_collections(
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[CollectionResponse]:
    cols = await knowledge_service.list_collections(
        db, actor=actor
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
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> CollectionResponse:
    col = await knowledge_service.get_collection(db, collection_id, actor=actor)
    return CollectionResponse.model_validate(col)


@router.put(
    "/collections/{collection_id}",
    response_model=CollectionResponse,
    summary="Cập nhật Bộ sưu tập Tri thức",
)
async def update_collection(
    collection_id: str,
    body: CollectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> CollectionResponse:
    col = await knowledge_service.update_collection(db, collection_id, body, actor=actor)
    return CollectionResponse.model_validate(col)


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa Bộ sưu tập Tri thức (kèm tài liệu, chunks, facts)",
)
async def delete_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.delete")),
) -> None:
    await knowledge_service.delete_collection(db, collection_id, actor=actor)


@router.post(
    "/collections/{collection_id}/reindex",
    summary="Nạp lại toàn bộ chunks vào Qdrant qua job nền (Deprecated Legacy Endpoint)",
    deprecated=True,
)
async def reindex_collection(
    collection_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.modules.jobs.service import jobs_service

    response.headers["Deprecation"] = "@2026-10-07"
    response.headers["X-API-Deprecation-Warning"] = (
        "Endpoint deprecated per ADR-011. Use V2 Staging Index Build instead."
    )

    await knowledge_service.get_collection(db, collection_id)
    job = await jobs_service.enqueue_job(db, job_type="reindex", collection_id=collection_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "collection_id": collection_id,
        "warning": "Endpoint đã lỗi thời theo ADR-011 (Pha 7 Cutover). Vui lòng dùng quy trình xuất bản V2.",
    }


@router.post(
    "/collections/{collection_id}/test",
    summary="Thử truy xuất Hybrid RAG trên collection (không ghi DB)",
)
async def test_collection_retrieval(
    collection_id: str,
    query: str = Query(..., min_length=2, description="Câu truy vấn thử"),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.modules.rag.retriever import hybrid_retriever

    await knowledge_service.get_collection(db, collection_id)
    candidates = await hybrid_retriever.retrieve(
        db=db, collection_id=collection_id, query=query, top_k=top_k, rerank_top_k=top_k
    )
    return {
        "query": query,
        "collection_id": collection_id,
        "total_found": len(candidates),
        "items": [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "content": c.content[:500],
                "score": round(c.rrf_score, 4),
                "section": c.section,
                "page_number": c.page_number,
            }
            for c in candidates
        ],
    }


@router.post(
    "/collections/{collection_id}/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên Tài liệu vào Kho Tri thức (Legacy Compatibility Façade)",
    deprecated=True,
)
async def upload_document(
    collection_id: str,
    response: Response,
    file: UploadFile = File(..., description="Tệp tài liệu (PDF, Word, Excel, Text)"),
    title: str | None = Form(None, description="Tiêu đề hiển thị của tài liệu"),
    document_type_code: str | None = Form(
        None, description="Mã loại văn bản chuẩn từ taxonomy qnu-ai-core"
    ),
    ocr_engine: str | None = Form(
        None, description="Bộ máy OCR: auto, pymupdf_ocr hoặc provider API"
    ),
    auto_approve: bool = Form(
        False, description="Tự động phê duyệt & nạp vector nếu dữ liệu sạch (Fast-Track)"
    ),
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.upload")),
) -> DocumentResponse:
    response.headers["Deprecation"] = "@2026-10-07"
    response.headers["X-API-Deprecation-Warning"] = (
        "Endpoint deprecated per ADR-011. Use POST /documents/intake and /knowledge/collections/{id}/bindings instead."
    )
    from app.core.config import settings

    if not getattr(settings, "KNOWLEDGE_ALLOW_DIRECT_UPLOAD", False):
        from app.core.exceptions import AppException

        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="DIRECT_UPLOAD_DEPRECATED_USE_CENTRAL_REPOSITORY",
            detail=(
                "Nạp trực tiếp vào Kho tri thức đã bị vô hiệu hóa theo lộ trình cắt chuyển ADR-011. "
                "Vui lòng nạp tệp qua Kho Tài Liệu Tập Trung (/documents) để thẩm định Quality Gate và liên kết an toàn."
            ),
        )
    content = await file.read()
    doc = await knowledge_service.ingest_document(
        db=db,
        collection_id=collection_id,
        file_bytes=content,
        file_name=file.filename or "unknown_file.txt",
        title=title,
        document_type_code=document_type_code,
        ocr_engine=ocr_engine,
        auto_approve=auto_approve,
    )
    return DocumentResponse.model_validate(doc)


@router.post(
    "/collections/{collection_id}/attach-repository-documents",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Gắn tài liệu từ Kho Tài Liệu vào Kho Tri Thức và lập chỉ mục Vector",
)
async def attach_repository_documents(
    collection_id: str,
    document_ids: list[str] = Query(..., description="Danh sách ID tài liệu từ Kho Tài Liệu"),
    chunk_strategy: str | None = Query(
        None, description="Chiến lược cắt đoạn: clause, semantic hoặc auto"
    ),
    auto_approve: bool = Query(True, description="Tự động duyệt và lập chỉ mục Vector tức thì"),
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.upload")),
) -> dict:
    docs = await knowledge_service.attach_repository_documents(
        db=db,
        collection_id=collection_id,
        document_ids=document_ids,
        chunk_strategy=chunk_strategy,
        auto_approve=auto_approve,
    )
    return {
        "collection_id": collection_id,
        "attached_count": len(docs),
        "created_document_ids": [d.id for d in docs],
        "message": f"Đã gắn và lập chỉ mục thành công {len(docs)} tài liệu vào kho tri thức.",
    }


@router.post(
    "/collections/{collection_id}/parse-preview",
    response_model=ParsePreviewResponse,
    summary="Xem trước Bóc tách & Chia đoạn Tài liệu (Không lưu DB)",
)
async def parse_preview(
    collection_id: str,
    file: UploadFile = File(...),
    strategy: str = Query("semantic", description="Chiến lược chia đoạn: semantic hoặc clause"),
    ocr_engine: str | None = Query(
        None, description="Bộ máy OCR: auto, pymupdf_ocr hoặc provider API"
    ),
    db: AsyncSession = Depends(get_db),
) -> ParsePreviewResponse:
    content = await file.read()
    return await knowledge_service.parse_preview(
        file_bytes=content,
        file_name=file.filename or "sample.txt",
        strategy=strategy,
        db=db,
        ocr_engine=ocr_engine,
    )


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    summary="Danh sách Tài liệu Tri thức",
)
async def list_documents(
    collection_id: str | None = Query(None, description="Lọc theo mã bộ sưu tập"),
    document_type_code: str | None = Query(None, description="Lọc theo mã loại văn bản chuẩn"),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    docs = await knowledge_service.list_documents(
        db, collection_id=collection_id, document_type_code=document_type_code
    )
    return [DocumentResponse.model_validate(d) for d in docs]


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
    "/documents/{document_id}/approve",
    response_model=ApproveDocumentResponse,
    summary="Phê duyệt & Nạp Tài liệu vào Vector DB (kèm bản sửa tay)",
)
async def approve_document(
    document_id: str,
    body: ApproveDocumentRequest,
    db: AsyncSession = Depends(get_db),
) -> ApproveDocumentResponse:
    result = await knowledge_service.approve_document(
        db=db,
        document_id=document_id,
        pages=[p.model_dump() for p in body.pages] if body.pages else None,
    )
    return ApproveDocumentResponse.model_validate(result)


@router.get(
    "/documents/{document_id}/studio-view",
    response_model=StudioViewResponse,
    summary="Chế độ Studio: Markdown + BBoxes + Regions theo trang (dữ liệu thật)",
)
async def studio_view(
    document_id: str,
    refresh_layout: bool = False,
    db: AsyncSession = Depends(get_db),
) -> StudioViewResponse:
    view = await knowledge_service.get_studio_view(db, document_id, refresh_layout=refresh_layout)
    for page in view["pages"]:
        page["image_url"] = (
            f"/platform/v1alpha1/knowledge/documents/{document_id}"
            f"/pages/{page['page_number']}/image"
        )
    return StudioViewResponse.model_validate(view)


@router.get(
    "/documents/{document_id}/pages/{page_number}/image",
    summary="Render ảnh PNG của trang tài liệu (cache trong storage)",
    response_class=Response,
)
async def page_image(
    document_id: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    png_bytes = await knowledge_service.render_page_image(db, document_id, page_number)
    return Response(content=png_bytes, media_type="image/png")


@router.get(
    "/documents/{document_id}/preview-pdf",
    summary="Stream file PDF preview phục vụ Scan Studio (hỗ trợ cả PDF gốc, Word DOCX và ảnh)",
    response_class=Response,
)
async def preview_pdf(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf_bytes, filename = await knowledge_service.get_preview_pdf(db, document_id)
    from urllib.parse import quote

    clean_filename = filename.rsplit(".", 1)[0]
    safe_ascii_name = f"{document_id}.pdf"
    encoded_filename = quote(f"{clean_filename}.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=\"{safe_ascii_name}\"; filename*=UTF-8''{encoded_filename}"
        },
    )


@router.post(
    "/documents/batch-approve",
    response_model=BatchApproveResponse,
    summary="Phê duyệt hàng loạt tài liệu (lỗi từng file không chặn cả lô)",
)
async def batch_approve_documents(
    body: BatchApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchApproveResponse:
    result = await knowledge_service.batch_approve_documents(db, body.document_ids)
    return BatchApproveResponse.model_validate(result)


@router.get(
    "/documents/{document_id}/download",
    summary="Tải tệp gốc của tài liệu",
    response_class=Response,
)
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    content, filename, media_type = await knowledge_service.download_document(db, document_id)
    from urllib.parse import quote

    safe_ascii = "downloaded_document"
    encoded_filename = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{safe_ascii}\"; filename*=UTF-8''{encoded_filename}"
        },
    )


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
    _auth: object = Depends(require_permission("ai.knowledge.delete")),
) -> None:
    await knowledge_service.delete_document(db, document_id)


@router.post(
    "/collections/{collection_id}/facts/import-excel",
    response_model=FactExcelImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nạp Bảng biểu Excel vào Structured Facts Layer",
)
async def import_collection_facts_excel(
    collection_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.facts.manage")),
) -> FactExcelImportResponse:
    content = await file.read()
    return await knowledge_service.import_facts_from_excel(
        db=db,
        collection_id=collection_id,
        file_bytes=content,
        filename=file.filename or "facts.xlsx",
    )


@router.get(
    "/collections/{collection_id}/facts",
    response_model=FactListResponse,
    summary="Danh sách Facts số hóa của Bộ sưu tập",
)
async def get_collection_facts(
    collection_id: str,
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> FactListResponse:
    return await knowledge_service.get_collection_facts(
        db=db,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
        actor=actor,
    )


@router.post("/collections/{collection_id}/vector-generations/{generation_id}/preview", response_model=AskResponse)
async def preview_vector_generation(
    collection_id: str, generation_id: str, body: CandidateQueryRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> AskResponse:
    from app.modules.knowledge.services.generation_candidate import ask_candidate

    return await ask_candidate(db, collection_id, generation_id, body.question, body.module_code, actor)


@router.post(
    "/documents/{document_id}/reindex",
    response_model=ReindexDocumentResponse,
    summary="Lập chỉ mục lại Vector cho một Tài liệu (Deprecated Legacy Endpoint)",
    deprecated=True,
)
async def reindex_document(
    document_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> ReindexDocumentResponse:
    response.headers["Deprecation"] = "@2026-10-07"
    response.headers["X-API-Deprecation-Warning"] = (
        "Endpoint deprecated per ADR-011. Use V2 Publishing instead."
    )
    res = await knowledge_service.reindex_document(db, document_id)
    return ReindexDocumentResponse(**res)


@router.get(
    "/collections/{collection_id}/reconcile",
    response_model=KnowledgeReconciliationResponse,
    summary="Đối soát Kiểm toán Dữ liệu 4 Tầng (DB, Qdrant, Storage, Cache)",
)
async def reconcile_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> KnowledgeReconciliationResponse:
    res = await knowledge_service.reconcile_collection(db, collection_id, actor=actor)
    return KnowledgeReconciliationResponse(**res)


@router.post(
    "/collections/{collection_id}/reconcile-fix",
    response_model=ReconcileFixResponse,
    summary="Tự động đồng bộ phục hồi các vector thiếu trong Kho Tri Thức",
)
async def reconcile_fix_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> ReconcileFixResponse:
    res = await knowledge_service.reconcile_fix_collection(db, collection_id, actor=actor)
    return ReconcileFixResponse(**res)


# ==============================================================================
# 5. Knowledge Publishing V2 Endpoints (ADR-011)
# ==============================================================================
@router.get(
    "/collections/{collection_id}/available-documents",
    response_model=AvailableRepositoryDocumentsResponse,
    summary="Lấy danh sách tài liệu từ kho trung tâm có thể liên kết vào bộ sưu tập",
)
async def get_available_documents(
    collection_id: str,
    search: str | None = Query(None, description="Từ khóa tìm kiếm theo tên hoặc số hiệu"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> AvailableRepositoryDocumentsResponse:
    return await knowledge_service.get_available_documents(
        db,
        collection_id=collection_id,
        search=search,
        page=page,
        page_size=page_size,
        actor=actor,
    )


@router.post(
    "/collections/{collection_id}/bindings",
    response_model=CreateKnowledgeBindingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo liên kết tri thức từ kho tài liệu trung tâm",
)
async def create_bindings(
    collection_id: str,
    body: CreateKnowledgeBindingsRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> CreateKnowledgeBindingsResponse:
    return await knowledge_service.create_bindings(
        db,
        collection_id=collection_id,
        req=body,
        actor=actor,
    )


@router.post(
    "/collections/{collection_id}/preview-document-group",
    response_model=PreviewDocumentGroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem trước phân tích nhóm tài liệu trước khi đưa vào kho tri thức (Server-side Read-only)",
)
async def preview_document_group(
    collection_id: str,
    body: PreviewDocumentGroupRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> PreviewDocumentGroupResponse:
    return await knowledge_service.preview_document_group(
        db,
        collection_id=collection_id,
        req=body,
        actor=actor,
    )


@router.post(
    "/collections/{collection_id}/attach-document-group",
    response_model=AttachDocumentGroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Đưa toàn bộ tài liệu sẵn sàng của nhóm vào kho tri thức (Snapshot thủ công)",
)
async def attach_document_group(
    collection_id: str,
    body: AttachDocumentGroupRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.sync")),
) -> AttachDocumentGroupResponse:
    return await knowledge_service.attach_document_group(
        db,
        collection_id=collection_id,
        req=body,
        actor=actor,
    )


@router.get(
    "/collections/{collection_id}/bindings",
    response_model=list[KnowledgeBindingResponse],
    summary="Danh sách các liên kết tài liệu trong bộ sưu tập",
)
async def list_bindings(
    collection_id: str,
    status: str | None = Query(None, description="Lọc theo trạng thái binding"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[KnowledgeBindingResponse]:
    return await knowledge_service.list_bindings(
        db,
        collection_id=collection_id,
        status=status,
        page=page,
        page_size=page_size,
        actor=actor,
    )


@router.get(
    "/bindings/{binding_id}",
    response_model=KnowledgeBindingResponse,
    summary="Chi tiết một liên kết tài liệu tri thức",
)
async def get_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> KnowledgeBindingResponse:
    return await knowledge_service.get_binding(db, binding_id=binding_id, actor=actor)


@router.post("/bindings/{binding_id}/pause", response_model=KnowledgeBindingResponse,
             summary="Ngừng dùng nguồn, giữ nguyên nội dung và chỉ mục")
async def pause_source(binding_id: str, db: AsyncSession = Depends(get_db),
                       actor: AuthActor = Depends(require_permission("ai.knowledge.delete"))) -> KnowledgeBindingResponse:
    from app.modules.knowledge.services.source_pause import pause_source as pause

    return await pause(db, binding_id, actor=actor)


@router.delete(
    "/bindings/{binding_id}",
    response_model=KnowledgeBindingResponse,
    summary="Hủy liên kết tài liệu khỏi bộ sưu tập",
)
async def detach_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.delete")),
) -> KnowledgeBindingResponse:
    return await knowledge_service.detach_binding(db, binding_id=binding_id, actor=actor)


@router.delete("/bindings/{binding_id}/purge", response_model=JobResponse,
               status_code=202, summary="Xóa vĩnh viễn nguồn trong Kho tri thức")
async def purge_source(binding_id: str, db: AsyncSession = Depends(get_db),
                       actor: AuthActor = Depends(require_permission("ai.knowledge.delete"))) -> JobResponse:
    from app.modules.knowledge.services.source_purge import request_purge

    return await request_purge(db, binding_id, actor=actor)


@router.get("/bindings/{binding_id}/purge/jobs/{job_id}", response_model=JobResponse)
async def get_source_purge_job(binding_id: str, job_id: str, db: AsyncSession = Depends(get_db),
                              actor: AuthActor = Depends(require_permission("ai.knowledge.delete"))) -> JobResponse:
    from app.core.exceptions import EntityNotFoundError
    from app.modules.jobs.service import jobs_service

    job = await jobs_service.get_job(db, job_id, actor=actor)
    if job.job_type != "knowledge_source_purge" or job.payload.get("binding_id") != binding_id:
        raise EntityNotFoundError("Không tìm thấy tác vụ xóa nguồn.")
    return job


@router.post(
    "/bindings/{binding_id}/build-index",
    response_model=KnowledgeIndexRevisionResponse,
    summary="Xây dựng chỉ mục staging và kiểm tra Parity Gate cho một binding",
)
async def build_staging_index(
    binding_id: str,
    body: BuildStagingIndexRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> KnowledgeIndexRevisionResponse:
    idx_rev = await knowledge_service.build_staging_index(
        db,
        binding_id=binding_id,
        source_revision_id=body.source_revision_id,
        chunk_strategy=body.chunk_strategy,
        auto_activate=body.auto_activate,
        actor=actor,
    )
    return KnowledgeIndexRevisionResponse.model_validate(idx_rev)


@router.post(
    "/bindings/{binding_id}/promote",
    response_model=IndexActivationResponse,
    summary="Kích hoạt nguyên tử (Atomic Pointer Swap) index revision cho một binding",
)
async def promote_index_revision(
    binding_id: str,
    body: IndexActivationRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> IndexActivationResponse:
    return await knowledge_service.promote_index_revision(
        db,
        binding_id=binding_id,
        index_revision_id=body.to_index_revision_id,
        expected_epoch=body.expected_epoch,
        reason=body.reason,
        activated_by=actor.actor_id or actor.username,
        actor=actor,
    )


@router.post(
    "/bindings/{binding_id}/rollback",
    response_model=IndexActivationResponse,
    summary="Hoàn tác tức thì (Instant Zero-Reindex Rollback) về index revision trước đó",
)
async def rollback_index_revision(
    binding_id: str,
    body: RollbackIndexRevisionRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> IndexActivationResponse:
    return await knowledge_service.rollback_index_revision(
        db,
        binding_id=binding_id,
        target_index_revision_id=body.target_index_revision_id,
        expected_epoch=body.expected_epoch,
        reason=body.reason,
        activated_by=actor.actor_id or actor.username,
        actor=actor,
    )


@router.get(
    "/bindings/{binding_id}/revisions",
    response_model=list[KnowledgeIndexRevisionResponse],
    summary="Lịch sử các phiên bản chỉ mục (Index Revisions) của binding",
)
async def list_index_revisions(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[KnowledgeIndexRevisionResponse]:
    return await knowledge_service.list_index_revisions(db, binding_id=binding_id, actor=actor)


@router.get(
    "/bindings/{binding_id}/chunks",
    response_model=BindingChunksListResponse,
    summary="Danh sách các chunk phân đoạn của binding hoặc index revision cụ thể",
)
async def list_binding_chunks(
    binding_id: str,
    index_revision_id: str | None = Query(
        None, description="Lọc theo Index Revision ID (mặc định lấy active)"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> BindingChunksListResponse:
    return await knowledge_service.list_binding_chunks(
        db,
        binding_id=binding_id,
        index_revision_id=index_revision_id,
        page=page,
        page_size=page_size,
        actor=actor,
    )


# ==============================================================================
# Legacy Canary, Backfill & Shadow Retrieval Endpoints (ADR-011 Phase 6)
# ==============================================================================
@router.post(
    "/collections/{collection_id}/canary/audit",
    response_model=LegacyAuditReport,
    summary="Kiểm kê và phân loại dữ liệu legacy của collection (active-parity-ok / needs-rebuild)",
)
async def audit_legacy_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> LegacyAuditReport:
    return await knowledge_service.audit_collection_legacy_state(
        db, collection_id=collection_id, actor=actor
    )


@router.post(
    "/collections/{collection_id}/canary/backfill",
    response_model=BackfillReport,
    summary="Chạy backfill an toàn (idempotent) chuyển đổi collection legacy sang chuẩn V2",
)
async def backfill_legacy_collection(
    collection_id: str,
    body: BackfillRequest = BackfillRequest(),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> BackfillReport:
    return await knowledge_service.backfill_legacy_collection(
        db,
        collection_id=collection_id,
        actor_id=actor.actor_id or actor.username,
        force_rebuild=body.force_rebuild,
        default_chunk_strategy=body.default_chunk_strategy,
        actor=actor,
    )


@router.post(
    "/collections/{collection_id}/canary/shadow-test",
    response_model=ShadowRetrievalReport,
    summary="Chạy shadow retrieval đối soát song song V1 Legacy và V2 Snapshot Isolation",
)
async def shadow_test_collection(
    collection_id: str,
    body: ShadowRetrievalRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> ShadowRetrievalReport:
    return await knowledge_service.run_shadow_retrieval_comparison(
        db,
        collection_id=collection_id,
        query=body.query,
        top_k=body.top_k,
        actor=actor,
    )


@router.get(
    "/collections/{collection_id}/canary/policy",
    response_model=CanaryPolicyResponse,
    summary="Lấy chính sách Canary phục vụ RAG và cấu hình lưu trữ per-collection",
)
async def get_collection_canary_policy(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> CanaryPolicyResponse:
    return await knowledge_service.get_collection_canary_policy(
        db, collection_id=collection_id, actor=actor
    )


@router.put(
    "/collections/{collection_id}/canary/policy",
    response_model=CanaryPolicyResponse,
    summary="Cập nhật chính sách Canary phục vụ RAG và retention revisions per-collection",
)
async def update_collection_canary_policy(
    collection_id: str,
    body: UpdateCanaryPolicyRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> CanaryPolicyResponse:
    return await knowledge_service.update_collection_canary_policy(
        db, collection_id=collection_id, req=body, actor=actor
    )


@router.post(
    "/collections/{collection_id}/gc",
    response_model=GarbageCollectionReport,
    summary="Dọn dẹp các Index Revision cũ không còn sử dụng (Artifact GC với Rollback Protection)",
)
async def run_artifact_garbage_collection(
    collection_id: str,
    body: GarbageCollectionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.delete")),
) -> GarbageCollectionReport:
    req = body or GarbageCollectionRequest()
    return await knowledge_service.collect_garbage(
        db,
        collection_id=collection_id,
        keep_revisions=req.keep_revisions,
        dry_run=req.dry_run,
        actor=actor,
    )


@router.post(
    "/gc/system-wide",
    response_model=SystemGarbageCollectionReport,
    summary="Dọn dẹp các Index Revision cũ trên toàn bộ Kho Tri Thức (System-wide Artifact GC)",
)
async def run_system_wide_garbage_collection(
    body: SystemGarbageCollectionRequest | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.delete")),
) -> SystemGarbageCollectionReport:
    req = body or SystemGarbageCollectionRequest()
    return await knowledge_service.collect_garbage_system_wide(
        db,
        default_keep_revisions=req.default_keep_revisions,
        dry_run=req.dry_run,
        actor=actor,
    )


@router.get(
    "/decommissioning/audit",
    response_model=SystemDecommissioningAuditReport,
    summary="Kiểm kê toàn trường về tiến độ di trú V2, chế độ đọc và mức độ sẵn sàng loại bỏ legacy",
)
async def audit_system_decommissioning(
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> SystemDecommissioningAuditReport:
    return await knowledge_service.audit_system_decommissioning(db, actor=actor)


# ==============================================================================
# Long-Lived Knowledge Group Sources Endpoints
# ==============================================================================


@router.get(
    "/collections/{collection_id}/sources",
    response_model=list[KnowledgeGroupSourceResponse],
    summary="Lấy danh sách các Nhóm tài liệu đang làm nguồn lâu dài cho Kho Tri Thức",
)
async def list_collection_group_sources(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[KnowledgeGroupSourceResponse]:
    return await group_source_service.list_group_sources(
        db, collection_id=collection_id, actor=actor
    )


@router.post(
    "/collections/{collection_id}/sources/preview-attach",
    response_model=PreviewGroupSourceDiffResponse,
    summary="Xem trước phân loại tài liệu (thêm mới, trùng lặp, chưa ready) trước khi liên kết nhóm",
)
async def preview_attach_group_source(
    collection_id: str,
    body: PreviewDocumentGroupRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> PreviewGroupSourceDiffResponse:
    return await group_source_service.preview_attach_group(
        db, collection_id=collection_id, group_id=body.group_id, actor=actor
    )


@router.post(
    "/collections/{collection_id}/sources",
    response_model=KnowledgeGroupSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Liên kết một Nhóm tài liệu làm nguồn lâu dài cho Kho Tri Thức (idempotent)",
)
async def attach_group_source(
    collection_id: str,
    body: AttachGroupSourceRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.create")),
) -> KnowledgeGroupSourceResponse:
    return await group_source_service.attach_group_source(
        db, collection_id=collection_id, req=body, actor=actor
    )


@router.get(
    "/collections/{collection_id}/sources/{source_id}/preview",
    response_model=PreviewGroupSourceDiffResponse,
    summary="Xem trước các thay đổi (added, updated, removed) của nguồn nhóm tài liệu",
)
async def preview_group_source_sync(
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> PreviewGroupSourceDiffResponse:
    return await group_source_service.preview_source_sync(
        db, collection_id=collection_id, source_id=source_id, actor=actor
    )


@router.post(
    "/collections/{collection_id}/sources/{source_id}/sync",
    response_model=SyncGroupSourceResponse,
    summary="Đồng bộ các tài liệu mới và revision mới từ Nhóm tài liệu vào Kho Tri Thức",
)
async def sync_group_source(
    collection_id: str,
    source_id: str,
    body: SyncGroupSourceRequest | None = None,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> SyncGroupSourceResponse:
    req = body or SyncGroupSourceRequest()
    return await group_source_service.sync_group_source(
        db, collection_id=collection_id, source_id=source_id, req=req, actor=actor
    )


@router.post(
    "/collections/{collection_id}/sources/{source_id}/publish",
    response_model=PublishGroupSourceResponse,
    summary="Xuất bản các chỉ mục đã xác thực thành công ở staging lên chỉ mục hoạt động RAG",
)
async def publish_group_source(
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> PublishGroupSourceResponse:
    return await group_source_service.publish_group_source(
        db, collection_id=collection_id, source_id=source_id, actor=actor
    )


@router.delete(
    "/collections/{collection_id}/sources/{source_id}",
    response_model=DetachGroupSourceResponse,
    summary="Gỡ một Nhóm tài liệu khỏi nguồn Kho Tri Thức",
)
async def detach_group_source(
    collection_id: str,
    source_id: str,
    detach_bindings: bool = Query(True, description="Nếu true, chuyển các bindings sang detached"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.delete")),
) -> DetachGroupSourceResponse:
    req = DetachGroupSourceRequest(detach_bindings=detach_bindings)
    return await group_source_service.detach_group_source(
        db, collection_id=collection_id, source_id=source_id, req=req, actor=actor
    )


@router.get(
    "/collections/{collection_id}/summary-metrics",
    response_model=CollectionSummaryMetrics,
    summary="Lấy trạng thái thực tế và các chỉ số đo lường tổng hợp của Kho Tri Thức",
)
async def get_collection_summary_metrics(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> CollectionSummaryMetrics:
    return await group_source_service.get_collection_summary_metrics(
        db, collection_id=collection_id, actor=actor
    )


# ==============================================================================
# 11. Candidate Groups & Documents Diffing (ADR-012)
# ==============================================================================
@router.get(
    "/collections/{collection_id}/candidate-groups",
    response_model=CandidateGroupListResponse,
    summary="Duyệt danh sách các nhóm/kho tài liệu ứng viên và thống kê số lượng tài liệu đã nạp",
)
async def get_candidate_groups(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> CandidateGroupListResponse:
    return await candidate_service.get_candidate_groups(
        collection_id=collection_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        db=db,
    )


@router.get(
    "/collections/{collection_id}/candidate-documents",
    response_model=CandidateListResponse,
    summary="Duyệt danh sách tài liệu ứng viên từ kho tài liệu và đánh giá trạng thái 2 chiều (nguồn/vector)",
)
@router.get(
    "/collections/{collection_id}/repository-candidates",
    response_model=CandidateListResponse,
    include_in_schema=False,
)
async def get_candidate_documents(
    collection_id: str,
    group_id: str | None = Query(None, description="Lọc theo nhóm tài liệu"),
    vector_generation_id: str | None = Query(None, description="Thế hệ vector mục tiêu"),
    source_state: str | None = Query(None, description="Lọc theo trạng thái nguồn (not_imported, current, update_available)"),
    source_status: str | None = Query(None, description="Alias cho source_state"),
    search: str | None = Query(None, description="Tìm kiếm theo tiêu đề hoặc tên tệp"),
    limit: int = Query(50, ge=1, le=1000, description="Số lượng mục trên mỗi trang"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> CandidateListResponse:
    effective_state_filter = source_state or source_status
    return await candidate_service.get_candidate_documents(
        collection_id=collection_id,
        group_id=group_id,
        vector_generation_id=vector_generation_id,
        source_state_filter=effective_state_filter,
        search=search,
        limit=limit,
        offset=offset,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        db=db,
    )


# ==============================================================================
# 12. Snapshot Import Batches (ADR-012)
# ==============================================================================
@router.post(
    "/collections/{collection_id}/imports",
    response_model=KnowledgeImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Khởi tạo đợt nạp tài liệu hàng loạt (snapshot import batch) độc lập",
)
async def create_import_batch(
    collection_id: str,
    payload: KnowledgeImportBatchCreateRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    response: Response = None,  # type: ignore
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> KnowledgeImportBatchResponse:
    batch = await import_batch_service.create_import_batch(
        collection_id=collection_id,
        payload=payload,
        idempotency_key=idempotency_key,
        created_by=actor.actor_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        db=db,
    )
    return KnowledgeImportBatchResponse.model_validate(batch)


@router.get(
    "/collections/{collection_id}/imports/{batch_id}",
    response_model=KnowledgeImportBatchResponse,
    summary="Lấy chi tiết trạng thái đợt nạp snapshot và danh sách tài liệu con",
)
async def get_import_batch(
    collection_id: str,
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> KnowledgeImportBatchResponse:
    batch = await import_batch_service.get_import_batch(
        collection_id=collection_id,
        batch_id=batch_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        db=db,
    )
    return KnowledgeImportBatchResponse.model_validate(batch)


@router.post(
    "/collections/{collection_id}/imports/{batch_id}/retry-failed",
    response_model=KnowledgeImportBatchResponse,
    summary="Thử lại các tài liệu bị lỗi trong đợt nạp snapshot",
)
async def retry_failed_import_items(
    collection_id: str,
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> KnowledgeImportBatchResponse:
    batch = await import_batch_service.retry_failed_items(
        collection_id=collection_id,
        batch_id=batch_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        db=db,
    )
    return KnowledgeImportBatchResponse.model_validate(batch)


@router.post(
    "/collections/{collection_id}/imports/{batch_id}/cancel",
    response_model=KnowledgeImportBatchResponse,
    summary="Hủy đợt nạp snapshot đang chờ hoặc đang xử lý",
)
async def cancel_import_batch(
    collection_id: str,
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> KnowledgeImportBatchResponse:
    batch = await import_batch_service.cancel_import_batch(
        collection_id=collection_id,
        batch_id=batch_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
        db=db,
    )
    return KnowledgeImportBatchResponse.model_validate(batch)


# ==============================================================================
# 13. Knowledge Source Lifecycle & Human Review (ADR-012)
# ==============================================================================
@router.get(
    "/collections/{collection_id}/sources/{source_id}",
    response_model=KnowledgeSourceDetailResponse,
    summary="Lấy chi tiết nguồn tri thức kèm bản bóc tách hoạt động và lịch sử sửa đổi",
)
async def get_knowledge_source(
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> KnowledgeSourceDetailResponse:
    binding = await source_ingestion_service.get_source(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    response = KnowledgeSourceDetailResponse.model_validate(binding)
    revisions = await source_ingestion_service.get_source_revisions(
        db, collection_id, source_id, actor.tenant_id, actor.workspace_id,
    )
    response.revisions = [KnowledgeSourceRevisionResponse.model_validate(rev) for rev in revisions]
    return response


@router.get(
    "/collections/{collection_id}/sources/{source_id}/revisions",
    response_model=list[KnowledgeSourceRevisionResponse],
    summary="Danh sách các bản bóc tách và chuẩn hóa nội dung của một nguồn tri thức",
)
async def list_source_revisions(
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[KnowledgeSourceRevisionResponse]:
    revs = await source_ingestion_service.get_source_revisions(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    return [KnowledgeSourceRevisionResponse.model_validate(r) for r in revs]


@router.patch(
    "/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/content",
    response_model=KnowledgeSourceRevisionResponse,
    summary="Hiệu đính nội dung Markdown chuẩn và đánh giá lại Quality Gate",
)
async def update_source_revision_content(
    collection_id: str,
    source_id: str,
    revision_id: str,
    payload: UpdateSourceContentRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> KnowledgeSourceRevisionResponse:
    rev = await source_ingestion_service.update_revision_content(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        revision_id=revision_id,
        new_markdown=payload.canonical_markdown,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    return KnowledgeSourceRevisionResponse.model_validate(rev)


@router.post(
    "/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/review",
    response_model=KnowledgeSourceRevisionResponse,
    summary="Phê duyệt hoặc từ chối bản bóc tách nguồn tri thức cần kiểm tra (review_required)",
)
async def review_source_revision(
    collection_id: str,
    source_id: str,
    revision_id: str,
    payload: ReviewSourceRevisionRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> KnowledgeSourceRevisionResponse:
    rev = await source_ingestion_service.review_source_revision(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        revision_id=revision_id,
        decision=payload.decision,
        comment=payload.comment,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    return KnowledgeSourceRevisionResponse.model_validate(rev)


@router.get(
    "/collections/{collection_id}/sources/{source_id}/studio",
    response_model=StudioViewResponse,
    summary="Lấy dữ liệu đối soát Studio OCR (ảnh, khung bbox, regions, markdown) cho nguồn tri thức",
)
async def get_knowledge_source_studio_view(
    collection_id: str,
    source_id: str,
    revision_id: str | None = Query(None, description="Lọc theo bản sửa đổi cụ thể"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> StudioViewResponse:
    return await source_ingestion_service.get_source_studio_data(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        revision_id=revision_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )


@router.get(
    "/collections/{collection_id}/sources/{source_id}/pages/{page_number}/image",
    summary="Tải ảnh trang độ phân giải cao phục vụ đối soát Studio từ snapshot độc lập",
    response_class=Response,
)
async def get_knowledge_source_page_image(
    collection_id: str,
    source_id: str,
    page_number: int,
    revision_id: str | None = Query(None, description="Lọc theo bản sửa đổi cụ thể"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> Response:
    content, media_type = await source_ingestion_service.get_source_page_image(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        page_number=page_number,
        revision_id=revision_id,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post(
    "/collections/{collection_id}/sources/{source_id}/reparse",
    response_model=KnowledgeSourceRevisionResponse,
    summary="Bóc tách lại nguồn tri thức bằng snapshot độc lập (chống chạy trùng)",
)
async def reparse_knowledge_source(
    collection_id: str,
    source_id: str,
    payload: ReparseSourceRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> KnowledgeSourceRevisionResponse:
    rev = await source_ingestion_service.reparse_source(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
        parser_profile=payload.parser_profile,
        ocr_engine=payload.ocr_engine,
        tenant_id=actor.tenant_id,
        workspace_id=actor.workspace_id,
    )
    return KnowledgeSourceRevisionResponse.model_validate(rev)


# ==============================================================================
# Vector Generations & Multi-Vector Spaces Endpoints (Mục 7.5 ADR-012)
# ==============================================================================
@router.get(
    "/collections/{collection_id}/vector-generations",
    response_model=list[KnowledgeVectorGenerationResponse],
    summary="Danh sách các thế hệ không gian vector của bộ sưu tập",
)
async def list_vector_generations(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[KnowledgeVectorGenerationResponse]:
    generations = await vector_generation_service.list_vector_generations(
        db=db,
        collection_id=collection_id,
        actor=actor,
    )
    return [KnowledgeVectorGenerationResponse.model_validate(g) for g in generations]


@router.post(
    "/collections/{collection_id}/vector-generations",
    response_model=KnowledgeVectorGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Khởi tạo một thế hệ không gian vector mới (ModelOps dynamic resolution)",
)
async def create_vector_generation(
    collection_id: str,
    payload: CreateVectorGenerationRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> KnowledgeVectorGenerationResponse:
    gen = await vector_generation_service.create_vector_generation(
        db=db,
        collection_id=collection_id,
        model_name=payload.embedding_model,
        provider_id=payload.provider_id,
        dimension=payload.embedding_dimension,
        actor=actor,
    )
    return KnowledgeVectorGenerationResponse.model_validate(gen)


@router.post(
    "/collections/{collection_id}/vector-generations/{generation_id}/build",
    response_model=BuildVectorGenerationResponse,
    summary="Kích hoạt lập chỉ mục hàng loạt cho thế hệ vector từ các ChunkSet sẵn có (Parse Once, Embed Many)",
)
async def build_vector_generation(
    collection_id: str,
    generation_id: str,
    payload: BuildVectorGenerationRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> BuildVectorGenerationResponse:
    return await vector_generation_service.build_all_sources_for_generation(
        db=db,
        collection_id=collection_id,
        generation_id=generation_id,
        chunk_strategy=payload.chunk_strategy,
        chunk_config=payload.chunk_config,
        actor=actor,
    )


@router.post("/collections/{collection_id}/vector-load", response_model=list[JobResponse], status_code=202)
async def load_selected_sources(
    collection_id: str, payload: VectorLoadRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> list[JobResponse]:
    jobs = await queue_vector_load(db, collection_id, payload, actor)
    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/collections/{collection_id}/vector-load")
async def vector_load_state(
    collection_id: str, db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> dict:
    return await get_vector_load_state(db, collection_id, actor)


@router.post(
    "/collections/{collection_id}/vector-generations/{generation_id}/activate",
    response_model=ActivateVectorGenerationResponse,
    summary="Kích hoạt thế hệ vector thành không gian truy vấn mặc định qua Check-And-Set (CAS)",
)
async def activate_vector_generation(
    collection_id: str,
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> ActivateVectorGenerationResponse:
    return await vector_generation_service.activate_vector_generation(
        db=db,
        collection_id=collection_id,
        generation_id=generation_id,
        actor=actor,
    )


@router.get(
    "/collections/{collection_id}/sources/{source_id}/chunk-sets",
    response_model=list[KnowledgeChunkSetResponse],
    summary="Danh sách các tập đoạn cắt (ChunkSets) của nguồn tri thức",
)
async def list_source_chunk_sets(
    collection_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[KnowledgeChunkSetResponse]:
    chunk_sets = await chunk_set_service.list_chunk_sets_for_source(
        db=db,
        collection_id=collection_id,
        source_id=source_id,
    )
    return [KnowledgeChunkSetResponse.model_validate(cs) for cs in chunk_sets]


@router.post(
    "/collections/{collection_id}/backfill-v3",
    response_model=BackfillV3Report,
    summary="Backfill dữ liệu nguồn và index cũ sang KnowledgeSourceRevision, ChunkSets và VectorGenerations (ADR-012)",
)
async def backfill_collection_v3_endpoint(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> BackfillV3Report:
    return await backfill_v3_service.backfill_collection_v3(
        db=db,
        collection_id=collection_id,
        actor=actor,
    )


@router.post(
    "/collections/{collection_id}/vector-generations/{generation_id}/rollback",
    response_model=ActivateVectorGenerationResponse,
    summary="Rollback thế hệ vector về một thế hệ trước đó an toàn qua atomic pointer swap",
)
async def rollback_vector_generation(
    collection_id: str,
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> ActivateVectorGenerationResponse:
    return await vector_generation_service.rollback_vector_generation(
        db=db,
        collection_id=collection_id,
        target_generation_id=generation_id,
        actor=actor,
    )


@router.get(
    "/collections/{collection_id}/reconciliation",
    response_model=ReconciliationReport,
    summary="Đối soát tính nhất quán 3 chiều giữa PostgreSQL, Qdrant và MinIO",
)
async def reconcile_collection_endpoint(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> ReconciliationReport:
    return await reconciliation_service.reconcile_collection(
        db=db,
        collection_id=collection_id,
        actor=actor,
    )


@router.post(
    "/collections/{collection_id}/reconciliation/clean-orphans",
    summary="Dọn dẹp các vector points mồ côi trong Qdrant không còn thuộc revision active",
)
async def clean_orphan_points_endpoint(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.delete")),
) -> dict[str, Any]:
    cleaned = await reconciliation_service.clean_orphan_points(
        db=db,
        collection_id=collection_id,
        actor=actor,
    )
    return {"collection_id": collection_id, "cleaned_points": cleaned}
