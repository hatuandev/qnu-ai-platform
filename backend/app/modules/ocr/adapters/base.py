"""Base Strategy Interface for Document OCR Recognition Adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseOCRAdapter(ABC):
    """Abstract Strategy interface for an OCR recognition engine."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine identifier (e.g. pymupdf_ocr, paddleocr, mock_ocr)."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if OCR runtime dependencies and model weights are installed."""
        ...

    @abstractmethod
    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        """Extract structured text and pages from document binary stream.

        Returns:
            dict containing:
                - engine_used (str)
                - total_pages (int)
                - overall_confidence (float)
                - pages (list of dict with page_number, extracted_text, confidence, word_count, line_count, has_tables)
                - raw_text (str)
        """
        ...
