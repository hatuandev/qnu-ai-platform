"""Firecrawl PDF Inspector Adapter — High-performance Rust-based classification & extraction.

Wraps the official `pdf-inspector` library developed by Firecrawl (Rust native core)
to provide instant classification (text_based, scanned, mixed), structured Markdown
extraction, and selective OCR routing in 10-30ms.
"""

from __future__ import annotations

import logging
import time
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PDFType = Literal["text_based", "scanned", "image_based", "mixed", "unknown"]


class PageInspectionResult(BaseModel):
    """Per-page inspection and classification result."""

    page_number: int
    markdown: str = ""
    needs_ocr: bool = False
    ocr_reason: str | None = None


class PDFInspectionResult(BaseModel):
    """Complete inspection and extraction result from Firecrawl pdf-inspector."""

    pdf_type: PDFType = "unknown"
    confidence: float = 0.0
    page_count: int = 0
    pages_needing_ocr: list[int] = Field(default_factory=list)
    has_encoding_issues: bool = False
    is_complex_layout: bool = False
    pages_with_tables: list[int] = Field(default_factory=list)
    pages_with_columns: list[int] = Field(default_factory=list)
    markdown: str | None = None
    page_markdowns: dict[int, str] = Field(default_factory=dict)
    pages_detail: list[PageInspectionResult] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    inspector_engine: str = "firecrawl/pdf-inspector"

    @property
    def is_text_based(self) -> bool:
        """Return True if the entire document is clean digital text."""
        return self.pdf_type == "text_based"

    @property
    def is_scanned(self) -> bool:
        """Return True if the document consists entirely of scanned/raster images."""
        return self.pdf_type in ("scanned", "image_based")

    @property
    def is_mixed(self) -> bool:
        """Return True if the document contains both digital text and scanned pages."""
        return self.pdf_type == "mixed"

    @property
    def can_skip_ocr(self) -> bool:
        """Return True if OCR is completely unnecessary."""
        return self.is_text_based and bool(self.markdown and self.markdown.strip())


class PDFInspector:
    """Enterprise Inspector wrapping Firecrawl's Rust engine with graceful degradation."""

    @classmethod
    def inspect_bytes(
        cls,
        data: bytes,
        pages: list[int] | None = None,
    ) -> PDFInspectionResult:
        """Inspect and classify PDF bytes in 10-30ms using Firecrawl's Rust engine.

        If the binary data is malformed or an unhandled exception occurs,
        falls back gracefully to unknown type without breaking the pipeline.
        """
        if not data:
            return PDFInspectionResult(
                pdf_type="unknown",
                confidence=0.0,
                page_count=0,
                markdown="",
            )

        start_time = time.perf_counter()

        try:
            import pdf_inspector

            # 1. Run full Rust-based classification and extraction
            res = pdf_inspector.process_pdf_bytes(data, pages=pages)

            raw_type = str(getattr(res, "pdf_type", "unknown")).lower()
            if raw_type in ("text_based", "scanned", "image_based", "mixed"):
                pdf_type: PDFType = raw_type  # type: ignore[assignment]
            else:
                pdf_type = "unknown"

            confidence = float(getattr(res, "confidence", 0.0) or 0.0)
            page_count = int(getattr(res, "page_count", 0) or 0)
            pages_needing_ocr = [int(p) for p in (getattr(res, "pages_needing_ocr", []) or [])]
            has_encoding_issues = bool(getattr(res, "has_encoding_issues", False))
            is_complex_layout = bool(getattr(res, "is_complex_layout", False))
            pages_with_tables = [int(p) for p in (getattr(res, "pages_with_tables", []) or [])]
            pages_with_columns = [int(p) for p in (getattr(res, "pages_with_columns", []) or [])]
            markdown_content = getattr(res, "markdown", None)
            processing_time = float(getattr(res, "processing_time_ms", 0.0) or 0.0)
            if processing_time <= 0:
                processing_time = (time.perf_counter() - start_time) * 1000

            # 2. Extract per-page markdown breakdowns for Studio and Chunking
            page_markdowns: dict[int, str] = {}
            pages_detail: list[PageInspectionResult] = []

            try:
                pages_res = pdf_inspector.extract_pages_markdown_bytes(data)
                raw_pages = getattr(pages_res, "pages", []) or []
                for p in raw_pages:
                    p_raw = int(getattr(p, "page", 0))
                    p_num = p_raw + 1 if p_raw == 0 else p_raw
                    p_md = str(getattr(p, "markdown", "") or "")
                    p_needs_ocr = bool(getattr(p, "needs_ocr", False))
                    p_reason = getattr(p, "ocr_reason", None)
                    page_markdowns[p_num] = p_md
                    pages_detail.append(
                        PageInspectionResult(
                            page_number=p_num,
                            markdown=p_md,
                            needs_ocr=p_needs_ocr,
                            ocr_reason=p_reason,
                        )
                    )
            except Exception as page_exc:
                logger.debug("Failed per-page markdown extraction from pdf_inspector: %s", page_exc)

            logger.info(
                "pdf_inspector_success: type=%s, pages=%d, ocr_needed=%s, time=%.2fms",
                pdf_type,
                page_count,
                pages_needing_ocr,
                processing_time,
            )

            return PDFInspectionResult(
                pdf_type=pdf_type,
                confidence=confidence,
                page_count=page_count,
                pages_needing_ocr=pages_needing_ocr,
                has_encoding_issues=has_encoding_issues,
                is_complex_layout=is_complex_layout,
                pages_with_tables=pages_with_tables,
                pages_with_columns=pages_with_columns,
                markdown=markdown_content,
                page_markdowns=page_markdowns,
                pages_detail=pages_detail,
                processing_time_ms=processing_time,
                inspector_engine="firecrawl/pdf-inspector-1.22.1",
            )

        except Exception as exc:
            elapsed = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "pdf_inspector_failed_falling_back: error=%s, elapsed_ms=%.2f",
                str(exc),
                elapsed,
            )
            return PDFInspectionResult(
                pdf_type="unknown",
                confidence=0.0,
                page_count=0,
                markdown=None,
                processing_time_ms=elapsed,
                inspector_engine="firecrawl/pdf-inspector-fallback",
            )
