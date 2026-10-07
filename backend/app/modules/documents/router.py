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
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import require_permission
from app.modules.documents.schemas import (
    ReparseDocumentRequest,
    RepositoryDocumentResponse,
    RepositoryDocumentStatsResponse,
    RepositoryDocumentUpdate,
)
from app.modules.documents.service import document_repository_service

router = APIRouter(prefix="/documents", tags=["04b Kho Tài Liệu Tập Trung (Document Repository)"])


@router.post(
    "/upload",
    response_model=RepositoryDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên tệp vào Kho Tài Liệu Tập Trung",
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
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.upload")),
) -> RepositoryDocumentResponse:
    content = await file.read()
    doc = await document_repository_service.upload_document(
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
        auto_parse=auto_parse,
    )
    return await document_repository_service.get_document(db, doc.id)


@router.get(
    "",
    response_model=dict,
    summary="Danh sách tài liệu trong Kho Tài Liệu",
)
async def list_documents(
    search: str | None = Query(None, description="Tìm kiếm theo tiêu đề, số hiệu, tên tệp"),
    document_type_code: str | None = Query(None, description="Lọc theo mã loại văn bản"),
    file_type: str | None = Query(None, description="Lọc theo định dạng tệp (pdf, docx, xlsx...)"),
    parse_status: str | None = Query(None, description="Lọc theo trạng thái bóc tách (parsed, pending, failed)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _auth: object = Depends(require_permission("ai.knowledge.view")),
) -> dict:
    items, total = await document_repository_service.list_documents(
        db=db,
        search=search,
        document_type_code=document_type_code,
        file_type=file_type,
        parse_status=parse_status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [item.model_dump() for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


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
    _auth: object = Depends(require_permission("ai.knowledge.edit")),
) -> RepositoryDocumentResponse:
    return await document_repository_service.update_document(db, document_id, body)


@router.delete(
    "/{document_id}",
    summary="Xóa tài liệu khỏi Kho Tài Liệu",
)
async def delete_document(
    document_id: str,
    force: bool = Query(False, description="Xóa cưỡng bức ngay cả khi đang được gắn vào Kho Tri Thức"),
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
    _auth: object = Depends(require_permission("ai.knowledge.edit")),
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
