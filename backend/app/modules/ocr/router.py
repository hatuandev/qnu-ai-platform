"""API Router for OCR Document Recognition & Engine Management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.ocr.schemas import OCREngineResponse, OCRExtractResponse
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
