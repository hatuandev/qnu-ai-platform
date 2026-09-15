"""OCR Module for QNU AI Platform."""

from app.modules.ocr.models import OCREngineModel, OCRJobLog
from app.modules.ocr.router import router
from app.modules.ocr.schemas import OCREngineResponse, OCRExtractResponse, OCRPageResult
from app.modules.ocr.service import OCRService

ocr_router = router

__all__ = [
    "OCREngineModel",
    "OCREngineResponse",
    "OCRExtractResponse",
    "OCRJobLog",
    "OCRPageResult",
    "OCRService",
    "ocr_router",
    "router",
]
