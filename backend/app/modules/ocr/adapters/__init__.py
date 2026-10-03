"""OCR Engine Adapters."""

from app.modules.ocr.adapters.base import BaseOCRAdapter
from app.modules.ocr.adapters.gemini_adapter import GeminiOCRAdapter
from app.modules.ocr.adapters.mistral_adapter import MistralOCRAdapter
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.openai_vision_adapter import (
    OpenAIVisionOCRAdapter,
    QwenOCRAdapter,
)
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter

__all__ = [
    "BaseOCRAdapter",
    "GeminiOCRAdapter",
    "MistralOCRAdapter",
    "MockOCRAdapter",
    "OpenAIVisionOCRAdapter",
    "PyMuPDFOCRAdapter",
    "QwenOCRAdapter",
]
