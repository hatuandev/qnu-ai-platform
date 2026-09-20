"""FastAPI Router for Knowledge Base Management — Thin Controller Pattern."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.knowledge.schemas import (
    ApproveDocumentRequest,
    ApproveDocumentResponse,
    BatchApproveRequest,
    BatchApproveResponse,
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    DocumentDetailResponse,
    DocumentResponse,
    FactExcelImportResponse,
    FactListResponse,
    KnowledgeReconciliationResponse,
    ParsePreviewResponse,
    ReconcileFixResponse,
    ReindexDocumentResponse,
    StudioViewResponse,
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


@router.put(
    "/collections/{collection_id}",
    response_model=CollectionResponse,
    summary="Cập nhật Bộ sưu tập Tri thức",
)
async def update_collection(
    collection_id: str,
    body: CollectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    col = await knowledge_service.update_collection(db, collection_id, body)
    return CollectionResponse.model_validate(col)


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa Bộ sưu tập Tri thức (kèm tài liệu, chunks, facts)",
)
async def delete_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    await knowledge_service.delete_collection(db, collection_id)


@router.post(
    "/collections/{collection_id}/reindex",
    summary="Nạp lại toàn bộ chunks vào Qdrant qua job nền",
)
async def reindex_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.modules.jobs.service import jobs_service

    await knowledge_service.get_collection(db, collection_id)
    job = await jobs_service.enqueue_job(
        db, job_type="reindex", collection_id=collection_id
    )
    return {"job_id": job.id, "status": job.status, "collection_id": collection_id}


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
    summary="Tải lên Tài liệu vào Kho Tri thức",
)
async def upload_document(
    collection_id: str,
    file: UploadFile = File(..., description="Tệp tài liệu (PDF, Word, Excel, Text)"),
    title: str | None = Form(None, description="Tiêu đề hiển thị của tài liệu"),
    document_type_code: str | None = Form(
        None, description="Mã loại văn bản chuẩn từ taxonomy qnu-ai-core"
    ),
    ocr_engine: str | None = Form(
        None, description="Bộ máy OCR khi bóc scan: auto, pymupdf_ocr, docling, easyocr"
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    content = await file.read()
    doc = await knowledge_service.ingest_document(
        db=db,
        collection_id=collection_id,
        file_bytes=content,
        file_name=file.filename or "unknown_file.txt",
        title=title,
        document_type_code=document_type_code,
        ocr_engine=ocr_engine,
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
    ocr_engine: str | None = Query(
        None, description="Bộ máy OCR khi bóc scan: auto, pymupdf_ocr, docling, easyocr"
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
    view = await knowledge_service.get_studio_view(
        db, document_id, refresh_layout=refresh_layout
    )
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
            "Content-Disposition": f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{encoded_filename}'
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
    limit: int = Query(100, ge=1, le=500),
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
    summary="Lập chỉ mục lại Vector cho một Tài liệu",
)
async def reindex_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReindexDocumentResponse:
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
) -> KnowledgeReconciliationResponse:
    res = await knowledge_service.reconcile_collection(db, collection_id)
    return KnowledgeReconciliationResponse(**res)


@router.post(
    "/collections/{collection_id}/reconcile-fix",
    response_model=ReconcileFixResponse,
    summary="Tự động đồng bộ phục hồi các vector thiếu trong Kho Tri Thức",
)
async def reconcile_fix_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReconcileFixResponse:
    res = await knowledge_service.reconcile_fix_collection(db, collection_id)
    return ReconcileFixResponse(**res)

