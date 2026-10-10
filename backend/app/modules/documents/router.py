"""FastAPI Router for Central Document Repository."""

from __future__ import annotations

import io
from datetime import date
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthActor, require_permission
from app.modules.documents.group_service import document_group_service
from app.modules.documents.intake_service import document_intake_service
from app.modules.documents.revision_service import document_revision_service
from app.modules.documents.schemas import (
    AddGroupDocumentsRequest,
    AddGroupDocumentsResponse,
    AsyncUploadDocumentResponse,
    DocumentGroupCreate,
    DocumentGroupListResponse,
    DocumentGroupResponse,
    DocumentGroupUpdate,
    DocumentRevisionListItem,
    DocumentRevisionResponse,
    GroupDocumentsResponse,
    ReparseDocumentRequest,
    RepositoryDocumentResponse,
    RepositoryDocumentStatsResponse,
    RepositoryDocumentUpdate,
    ReviewRevisionContentRequest,
    SubmitRevisionReviewRequest,
)
from app.modules.documents.service import document_repository_service

router = APIRouter(prefix="/documents", tags=["04b Kho Tài Liệu Tập Trung (Document Repository)"])


@router.post(
    "/intake",
    response_model=AsyncUploadDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Tiếp nhận tệp bất đồng bộ vào Kho Tài Liệu (Chuẩn V2 ADR-011)",
)
async def intake_document(
    file: UploadFile = File(..., description="Tệp tài liệu gốc (PDF, Word, Excel, Text)"),
    title: str | None = Form(None, description="Tiêu đề hiển thị văn bản"),
    document_type_code: str | None = Form(None, description="Mã loại văn bản chuẩn NĐ 30"),
    document_number: str | None = Form(None, description="Số hiệu văn bản (vd: 2139/QĐ-ĐHQN)"),
    issuing_authority: str | None = Form(None, description="Cơ quan ban hành"),
    issued_date: date | None = Form(None, description="Ngày ký ban hành"),
    effective_date: date | None = Form(None, description="Ngày có hiệu lực"),
    ocr_engine: str | None = Form(None, description="Engine OCR (auto, pymupdf_ocr, qwen3-vl:8b)"),
    group_id: str | None = Form(None, description="Tự động gán tài liệu vào kho sau khi tiếp nhận"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key", description="Khóa idempotency client"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> AsyncUploadDocumentResponse:
    content = await file.read()
    return await document_intake_service.intake_document(
        db=db,
        file_bytes=content,
        file_name=file.filename or "tailieu_chuadattrang.pdf",
        title=title,
        document_type_code=document_type_code,
        document_number=document_number,
        issuing_authority=issuing_authority,
        issued_date=issued_date,
        effective_date=effective_date,
        ocr_engine=ocr_engine,
        group_id=group_id,
        idempotency_key=idempotency_key,
        actor=actor,
        tenant_id=actor.tenant_id if actor else None,
        workspace_id=actor.workspace_id if actor else None,
    )


@router.post(
    "/upload",
    response_model=RepositoryDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
    summary="Tải lên tệp vào Kho Tài Liệu Tập Trung (Compatibility V1 — Deprecated)",
)
async def upload_document(
    file: UploadFile = File(..., description="Tệp tài liệu gốc (PDF, Word, Excel, Text)"),
    title: str | None = Form(None, description="Tiêu đề hiển thị văn bản"),
    document_type_code: str | None = Form(None, description="Mã loại văn bản chuẩn NĐ 30"),
    document_number: str | None = Form(None, description="Số hiệu văn bản (vd: 2139/QĐ-ĐHQN)"),
    issuing_authority: str | None = Form(None, description="Cơ quan ban hành"),
    issued_date: date | None = Form(None, description="Ngày ký ban hành"),
    effective_date: date | None = Form(None, description="Ngày có hiệu lực"),
    ocr_engine: str | None = Form(None, description="Engine OCR (auto, pymupdf_ocr, qwen3-vl:8b)"),
    auto_parse: bool = Form(True, description="Tự động bóc tách sang Markdown ngay sau khi tải"),
    group_id: str | None = Form(None, description="Gán vào kho tài liệu (chuyển tiếp intake V2 an toàn)"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> RepositoryDocumentResponse:
    content = await file.read()
    # Compatibility adapter: All requests (with or without group_id) delegate to Intake V2
    intake_res = await document_intake_service.intake_document(
        db=db,
        file_bytes=content,
        file_name=file.filename or "tailieu_chuadattrang.pdf",
        title=title,
        document_type_code=document_type_code,
        document_number=document_number,
        issuing_authority=issuing_authority,
        issued_date=issued_date,
        effective_date=effective_date,
        ocr_engine=ocr_engine,
        group_id=group_id,
        idempotency_key=idempotency_key,
        actor=actor,
        tenant_id=actor.tenant_id if actor else None,
        workspace_id=actor.workspace_id if actor else None,
    )
    return await document_repository_service.get_document(db, intake_res.document_id, actor=actor)


@router.get(
    "",
    response_model=dict,
    summary="Danh sách tài liệu trong Kho Tài Liệu",
)
async def list_documents(
    search: str | None = Query(None, description="Tìm kiếm theo tiêu đề, số hiệu, tên tệp"),
    document_type_code: str | None = Query(None, description="Lọc theo mã loại văn bản"),
    file_type: str | None = Query(None, description="Lọc theo định dạng tệp (pdf, docx, xlsx...)"),
    parse_status: str | None = Query(
        None, description="Lọc theo trạng thái bóc tách (parsed, pending, failed)"
    ),
    group_id: str | None = Query(None, description="Lọc tài liệu thuộc nhóm"),
    exclude_group_id: str | None = Query(None, description="Lọc loại bỏ tài liệu đã thuộc nhóm"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> dict:
    items, total = await document_repository_service.list_documents(
        db=db,
        search=search,
        document_type_code=document_type_code,
        file_type=file_type,
        parse_status=parse_status,
        group_id=group_id,
        exclude_group_id=exclude_group_id,
        limit=limit,
        offset=offset,
        actor=actor,
    )
    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# =========================================================================
# Logical Document Groups Endpoints
# =========================================================================


@router.get(
    "/groups",
    response_model=DocumentGroupListResponse,
    summary="Danh sách các nhóm tài liệu logic",
)
async def list_document_groups(
    search: str | None = Query(None, description="Tìm kiếm tên hoặc mô tả nhóm"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> DocumentGroupListResponse:
    return await document_group_service.list_groups(
        db=db,
        search=search,
        page=page,
        page_size=page_size,
        actor=actor,
    )


@router.post(
    "/groups",
    response_model=DocumentGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo nhóm tài liệu mới",
)
async def create_document_group(
    body: DocumentGroupCreate,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> DocumentGroupResponse:
    return await document_group_service.create_group(
        db=db,
        req=body,
        actor=actor,
    )


@router.get(
    "/groups/{group_id}",
    response_model=DocumentGroupResponse,
    summary="Chi tiết một nhóm tài liệu kèm thống kê",
)
async def get_document_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> DocumentGroupResponse:
    return await document_group_service.get_group(
        db=db,
        group_id=group_id,
        actor=actor,
    )


@router.patch(
    "/groups/{group_id}",
    response_model=DocumentGroupResponse,
    summary="Cập nhật thông tin nhóm tài liệu",
)
async def update_document_group(
    group_id: str,
    body: DocumentGroupUpdate,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> DocumentGroupResponse:
    return await document_group_service.update_group(
        db=db,
        group_id=group_id,
        req=body,
        actor=actor,
    )


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa nhóm tài liệu (bảo toàn tài liệu và bindings)",
)
async def delete_document_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> Response:
    await document_group_service.delete_group(
        db=db,
        group_id=group_id,
        actor=actor,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/groups/{group_id}/documents",
    response_model=GroupDocumentsResponse,
    summary="Danh sách tài liệu trong nhóm",
)
async def get_group_documents(
    group_id: str,
    search: str | None = Query(None, description="Tìm kiếm tài liệu"),
    status_filter: str | None = Query(None, alias="status", description="Lọc trạng thái: ready, processing, error"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> GroupDocumentsResponse:
    return await document_group_service.get_group_documents(
        db=db,
        group_id=group_id,
        search=search,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
        actor=actor,
    )


@router.post(
    "/groups/{group_id}/documents",
    response_model=AddGroupDocumentsResponse,
    summary="Thêm nhiều tài liệu vào nhóm (Idempotent)",
)
async def add_documents_to_group(
    group_id: str,
    body: AddGroupDocumentsRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> AddGroupDocumentsResponse:
    return await document_group_service.add_documents_to_group(
        db=db,
        group_id=group_id,
        req=body,
        actor=actor,
    )


@router.delete(
    "/groups/{group_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa một tài liệu khỏi nhóm (không xóa tài liệu gốc)",
)
async def remove_document_from_group(
    group_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.upload")),
) -> Response:
    await document_group_service.remove_document_from_group(
        db=db,
        group_id=group_id,
        document_id=document_id,
        actor=actor,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/stats",
    response_model=RepositoryDocumentStatsResponse,
    summary="Thống kê KPI Kho Tài Liệu Tập Trung",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.view")),
) -> RepositoryDocumentStatsResponse:
    return await document_repository_service.get_stats(db)


@router.get(
    "/{document_id}",
    response_model=RepositoryDocumentResponse,
    summary="Chi tiết tài liệu và danh sách Kho Tri Thức đang sử dụng",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.view")),
) -> RepositoryDocumentResponse:
    return await document_repository_service.get_document(db, document_id)


@router.patch(
    "/{document_id}",
    response_model=RepositoryDocumentResponse,
    summary="Cập nhật metadata hành chính văn bản",
)
async def update_document(
    document_id: str,
    body: RepositoryDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.update")),
) -> RepositoryDocumentResponse:
    return await document_repository_service.update_document(db, document_id, body)


@router.delete(
    "/{document_id}",
    summary="Xóa tài liệu khỏi Kho Tài Liệu",
)
async def delete_document(
    document_id: str,
    force: bool = Query(
        False, description="Xóa cưỡng bức ngay cả khi đang được gắn vào Kho Tri Thức"
    ),
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.delete")),
) -> dict[str, str]:
    await document_repository_service.delete_document(db, document_id, force=force)
    return {"message": "Đã xóa tài liệu khỏi kho thành công", "id": document_id}


@router.post(
    "/{document_id}/reparse",
    response_model=RepositoryDocumentResponse,
    summary="Bóc tách lại tài liệu sang Markdown",
)
async def reparse_document(
    document_id: str,
    body: ReparseDocumentRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.update")),
) -> RepositoryDocumentResponse:
    doc_res = await document_repository_service.get_document(db, document_id)
    # Fetch database model
    from app.modules.documents.models import RepositoryDocument

    doc = await db.get(RepositoryDocument, document_id)

    if not doc:
        return doc_res

    engine = body.ocr_engine if body else None
    await document_repository_service.parse_and_cache_document(db, doc, ocr_engine=engine)
    await db.commit()
    return await document_repository_service.get_document(db, document_id)


@router.get(
    "/{document_id}/download",
    summary="Tải về tệp gốc từ MinIO S3",
)
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.view")),
):
    data, filename, ext = await document_repository_service.get_file_content(db, document_id)
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get(
    "/{document_id}/preview-pdf",
    summary="Xem trước nội dung PDF trực tiếp từ MinIO S3",
)
async def preview_pdf(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.view")),
):
    data, filename, ext = await document_repository_service.get_file_content(db, document_id)
    if ext != "pdf":
        return Response(content="Chỉ hỗ trợ xem trước cho định dạng PDF", status_code=400)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"},
    )


# =========================================================================
# V2 Revision Lifecycle & Human Review Endpoints
# =========================================================================


@router.get(
    "/{document_id}/revisions",
    response_model=list[DocumentRevisionListItem],
    summary="Danh sách toàn bộ các bản sửa đổi (Revisions) của tài liệu",
)
async def list_document_revisions(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> list[DocumentRevisionListItem]:
    return await document_revision_service.list_document_revisions(
        db, document_id, actor=actor
    )


@router.get(
    "/{document_id}/revisions/{revision_id}",
    response_model=DocumentRevisionResponse,
    summary="Chi tiết một bản sửa đổi tài liệu (Manifests, Provenance & Quality)",
)
async def get_document_revision(
    document_id: str,
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.view")),
) -> DocumentRevisionResponse:
    return await document_revision_service.get_document_revision(
        db, document_id, revision_id, actor=actor
    )


@router.patch(
    "/{document_id}/revisions/{revision_id}/content",
    response_model=DocumentRevisionResponse,
    summary="Hiệu đính nội dung Markdown trong giai đoạn xem xét (Review Phase)",
)
async def update_revision_content(
    document_id: str,
    revision_id: str,
    body: ReviewRevisionContentRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> DocumentRevisionResponse:
    return await document_revision_service.update_revision_content(
        db, document_id, revision_id, body, actor=actor
    )


@router.post(
    "/{document_id}/revisions/{revision_id}/review",
    response_model=DocumentRevisionResponse,
    summary="Phê duyệt hoặc từ chối bản sửa đổi tài liệu (Chuyển trạng thái Ready)",
)
async def submit_revision_review(
    document_id: str,
    revision_id: str,
    body: SubmitRevisionReviewRequest,
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> DocumentRevisionResponse:
    return await document_revision_service.submit_revision_review(
        db, document_id, revision_id, body, actor=actor
    )


@router.post(
    "/{document_id}/revisions/{revision_id}/retry",
    response_model=DocumentRevisionResponse,
    summary="Thử lại quy trình bóc tách và thẩm định chất lượng cho bản sửa đổi",
)
async def retry_revision(
    document_id: str,
    revision_id: str,
    ocr_engine: str | None = Query(None, description="Tùy chọn OCR engine khi retry"),
    db: AsyncSession = Depends(get_db),
    actor: AuthActor = Depends(require_permission("ai.knowledge.update")),
) -> DocumentRevisionResponse:
    rev = await document_revision_service.process_revision(
        db,
        revision_id=revision_id,
        document_id=document_id,
        actor=actor,
        ocr_engine=ocr_engine,
    )
    return document_revision_service._to_response_dto(rev)
