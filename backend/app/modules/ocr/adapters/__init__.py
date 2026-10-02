"""OCR Engine Adapters."""

from app.modules.ocr.adapters.base import BaseOCRAdapter
from app.modules.ocr.adapters.mistral_adapter import MistralOCRAdapter
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter

__all__ = [
    "BaseOCRAdapter",
    "MistralOCRAdapter",
    "MockOCRAdapter",
    "PyMuPDFOCRAdapter",
]
