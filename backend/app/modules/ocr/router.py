"""API Router for OCR Document Recognition & Studio Intelligence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.ocr.schemas import (
    OCREngineResponse,
    OCRExtractResponse,
    StudioOCRParseResponse,
)
from app.modules.ocr.service import OCRService

router = APIRouter(prefix="/ocr", tags=["OCR Document Recognition"])
service = OCRService()


@router.get("/engines", response_model=list[OCREngineResponse])
async def list_ocr_engines() -> list[OCREngineResponse]:
    """Danh sách các công cụ OCR đã đăng ký trong hệ thống."""
    return service.list_engines()


@router.post("/extract", response_model=OCRExtractResponse)
async def extract_document_text(
    file: UploadFile = File(..., description="Tệp tài liệu scan hoặc ảnh (PDF, PNG, JPG)"),
    engine_name: str | None = Form(None, description="Tên engine OCR (mặc định: pymupdf_ocr)"),
    tenant_id: str = Form("tenant_qnu", description="Mã tổ chức / tenant"),
    session: AsyncSession = Depends(get_db),
) -> OCRExtractResponse:
    """Bóc tách văn bản và bảng biểu từ tài liệu scan với cơ chế tự động Fallback."""
    max_size = 25 * 1024 * 1024  # 25 MB
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="Dung lượng tệp vượt quá giới hạn cho phép (25 MB)")

    filename = file.filename or "uploaded_doc.pdf"
    return await service.extract_document(
        session=session,
        content=content,
        filename=filename,
        engine_name=engine_name,
        tenant_id=tenant_id,
    )


# --- Studio OCR Interactive Endpoints ---


@router.post(
    "/studio/parse",
    response_model=StudioOCRParseResponse,
    summary="Phân tích văn bản scan, render ảnh trang và nhận diện layout Bounding Boxes cho Studio",
)
async def parse_studio_document(
    file: UploadFile | None = File(None, description="Tệp tài liệu scan hoặc văn bản (PDF, PNG, JPG, DOCX, XLSX)"),
    engine_id: str = Form("pymupdf_ocr", description="Mã engine OCR (pymupdf_ocr, docling, easyocr)"),
    tenant_id: str = Form("tenant_qnu", description="Mã tổ chức / tenant"),
    workspace_id: str = Form("workspace_qnu", description="Mã workspace"),
) -> StudioOCRParseResponse:
    """Thực hiện bóc tách OCR đa tầng, vẽ Bounding Boxes và render ảnh trang xem trước Split-Screen."""
    if file is None:
        # Fast path: trả về tài liệu mẫu mặc định của trường
        return await service.get_sample_document()

    max_size = 25 * 1024 * 1024  # 25 MB
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail="Dung lượng tệp vượt quá giới hạn cho phép (25 MB)")

    filename = file.filename or "uploaded_document.pdf"
    return await service.parse_studio_document(
        content=content,
        filename=filename,
        engine_name=engine_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )


@router.get(
    "/studio/page-image/{file_hash}/{img_filename}",
    summary="Stream ảnh trang scan preview theo file_hash và tên ảnh",
    response_class=Response,
)
async def get_studio_page_image(file_hash: str, img_filename: str) -> Response:
    """Stream ảnh JPEG của trang tài liệu scan phục vụ hiển thị Canvas trong Studio."""
    img_bytes = await service.get_studio_page_image(file_hash, img_filename)
    return Response(content=img_bytes, media_type="image/jpeg")


@router.get(
    "/studio/sample",
    response_model=StudioOCRParseResponse,
    summary="Lấy tài liệu tuyển sinh scan mẫu của ĐH Quy Nhơn để kiểm thử ngay lập tức",
)
async def get_studio_sample_document() -> StudioOCRParseResponse:
    """Trả về dữ liệu 14 trang scan tuyển sinh 2026 mẫu có sẵn bounding boxes và bảng biểu."""
    return await service.get_sample_document()
