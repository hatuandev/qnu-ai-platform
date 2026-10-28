"""Pure OCR contract checks available to other domains and provider diagnostics."""

from qnu.domains.ocr.config import OCR_PROMPT
from qnu.domains.ocr.layout import parse_page
from qnu.platform.errors import AppException


def validate_located_text(text: str) -> None:
    if not parse_page(text).blocks:
        raise AppException("OCR thiếu khối có tọa độ.", code="ocr_layout_invalid", status_code=502)


__all__ = ["OCR_PROMPT", "validate_located_text"]
