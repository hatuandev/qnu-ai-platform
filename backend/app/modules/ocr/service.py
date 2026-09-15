"""OCR Service with Engine Routing, Resilient Fallback, and Job Auditing."""

from __future__ import annotations

import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.ocr.adapters.base import BaseOCRAdapter
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter
from app.modules.ocr.models import OCRJobLog
from app.modules.ocr.schemas import (
    OCREngineResponse,
    OCRExtractResponse,
    OCRPageResult,
)

logger = structlog.get_logger(__name__)


class OCRService:
    """Service orchestrating OCR document recognition with automated fallback."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseOCRAdapter] = {
            "pymupdf_ocr": PyMuPDFOCRAdapter(),
            "mock_ocr": MockOCRAdapter(),
        }
        self.default_engine = "pymupdf_ocr"

    def list_engines(self) -> list[OCREngineResponse]:
        """List registered OCR engines and their operational status."""
        return [
            OCREngineResponse(
                id="eng_pymupdf",
                name="pymupdf_ocr",
                display_name="PyMuPDF Fast Document Extractor",
                engine_type="pymupdf",
                provider_category="local",
                capabilities=["pdf", "png", "jpg", "tables"],
                avg_confidence=0.95,
                is_active=True,
                is_default=True,
            ),
            OCREngineResponse(
                id="eng_mock",
                name="mock_ocr",
                display_name="Mock High-Fidelity OCR Adapter",
                engine_type="mock",
                provider_category="local",
                capabilities=["pdf", "text", "fallback"],
                avg_confidence=0.98,
                is_active=True,
                is_default=False,
            ),
        ]

    async def extract_document(
        self,
        session: AsyncSession,
        content: bytes,
        filename: str,
        engine_name: str | None = None,
        tenant_id: str = "tenant_qnu",
    ) -> OCRExtractResponse:
        """Extract text from document bytes with automatic graceful fallback."""
        start_time = time.perf_counter()
        target_engine = engine_name or self.default_engine

        adapter = self._adapters.get(target_engine)
        if not adapter:
            logger.warning("requested_ocr_engine_not_found_fallback_to_default", engine=target_engine)
            adapter = self._adapters[self.default_engine]

        fallback_triggered = False
        result_dict = None
        error_msg = None

        try:
            result_dict = await adapter.extract(content, filename)
        except Exception as exc:
            logger.error("primary_ocr_failed_triggering_fallback", engine=adapter.name, error=str(exc))
            fallback_triggered = True
            # Fallback to mock adapter
            fallback_adapter = self._adapters["mock_ocr"]
            try:
                result_dict = await fallback_adapter.extract(content, filename)
                result_dict["engine_used"] = fallback_adapter.name
            except Exception as fb_exc:
                error_msg = f"OCR and fallback both failed: {fb_exc}"
                logger.error("ocr_fallback_failed", error=error_msg)
                raise AppException(error_msg, status_code=500) from fb_exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        total_pages = int(result_dict.get("total_pages", 1))
        confidence = float(result_dict.get("overall_confidence", 0.90))

        # Audit log to PostgreSQL
        job_log = OCRJobLog(
            tenant_id=tenant_id,
            filename=filename,
            engine_used=result_dict.get("engine_used", target_engine),
            total_pages=total_pages,
            confidence=confidence,
            latency_ms=latency_ms,
            status="success",
            error_message=error_msg,
        )
        try:
            session.add(job_log)
            await session.commit()
        except Exception as db_exc:
            logger.warning("failed_to_save_ocr_job_log", error=str(db_exc))
            await session.rollback()

        pages = [
            OCRPageResult(
                page_number=p["page_number"],
                extracted_text=p["extracted_text"],
                confidence=p["confidence"],
                word_count=p["word_count"],
                line_count=p["line_count"],
                has_tables=p.get("has_tables", False),
            )
            for p in result_dict.get("pages", [])
        ]

        return OCRExtractResponse(
            filename=filename,
            success=True,
            engine_used=result_dict.get("engine_used", target_engine),
            fallback_triggered=fallback_triggered,
            total_pages=total_pages,
            overall_confidence=confidence,
            latency_ms=latency_ms,
            raw_text=result_dict.get("raw_text", ""),
            pages=pages,
        )
