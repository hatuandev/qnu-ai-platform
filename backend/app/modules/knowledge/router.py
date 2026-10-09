"""FastAPI Router for Knowledge Base Management — Thin Controller Pattern."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.schemas import (
    ApproveDocumentRequest,
    ApproveDocumentResponse,
    AvailableRepositoryDocumentsResponse,
    BackfillReport,
    BackfillRequest,
    BatchApproveRequest,
    BatchApproveResponse,
    BindingChunksListResponse,
    BuildStagingIndexRequest,
    CanaryPolicyResponse,
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    CreateKnowledgeBindingsRequest,
    CreateKnowledgeBindingsResponse,
    DocumentDetailResponse,
    DocumentResponse,
    FactExcelImportResponse,
    FactListResponse,
    GarbageCollectionReport,
    GarbageCollectionRequest,
    IndexActivationRequest,
    IndexActivationResponse,
    KnowledgeBindingResponse,
    KnowledgeIndexRevisionResponse,
    KnowledgeReconciliationResponse,
    LegacyAuditReport,
    ParsePreviewResponse,
    ReconcileFixResponse,
    ReindexDocumentResponse,
    RollbackIndexRevisionRequest,
    ShadowRetrievalReport,
    ShadowRetrievalRequest,
    StudioViewResponse,
    SystemDecommissioningAuditReport,
    SystemGarbageCollectionReport,
    SystemGarbageCollectionRequest,
    UpdateCanaryPolicyRequest,
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
    actor: AuthActor = Depends(require_permission("ai.knowledge.edit")),
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
) -> FactListResponse:
    return await knowledge_service.get_collection_facts(
        db=db,
        collection_id=collection_id,
        limit=limit,
        offset=offset,
    )


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
    actor: AuthActor = Depends(require_permission("ai.knowledge.edit")),
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
    actor: AuthActor = Depends(require_permission("ai.knowledge.edit")),
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
