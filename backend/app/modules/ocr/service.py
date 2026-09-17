"""OCR Service with Engine Routing, Resilient Fallback, and Job Auditing."""

from __future__ import annotations

import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.ocr.adapters.base import BaseOCRAdapter
from app.modules.ocr.adapters.docling_adapter import DoclingOCRAdapter
from app.modules.ocr.adapters.easyocr_adapter import EasyOCRAdapter
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter
from app.modules.ocr.models import OCRJobLog
from app.modules.ocr.schemas import (
    OCREngineResponse,
    OCRExtractResponse,
    OCRPageResult,
)

logger = structlog.get_logger(__name__)

#: Install hints shown when an optional engine is requested but missing.
_ENGINE_INSTALL_HINTS: dict[str, str] = {
    "docling": "uv add docling",
    "easyocr": "uv add easyocr",
}


class OCRService:
    """Service orchestrating OCR document recognition with automated fallback."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseOCRAdapter] = {
            "pymupdf_ocr": PyMuPDFOCRAdapter(),
            "docling": DoclingOCRAdapter(),
            "easyocr": EasyOCRAdapter(),
            "mock_ocr": MockOCRAdapter(),
        }
        self.default_engine = "pymupdf_ocr"

    def list_engines(self) -> list[OCREngineResponse]:
        """List registered OCR engines with real availability status."""
        catalog = [
            ("eng_pymupdf", "pymupdf_ocr", "pymupdf", ["pdf", "png", "jpg", "tables"], 0.95, True),
            ("eng_docling", "docling", "docling", ["pdf", "tables", "layout", "markdown"], 0.97, False),
            ("eng_easyocr", "easyocr", "easyocr", ["png", "jpg", "scan", "stamp"], 0.90, False),
            ("eng_mock", "mock_ocr", "mock", ["pdf", "text", "fallback"], 0.98, False),
        ]
        engines: list[OCREngineResponse] = []
        for engine_id, name, engine_type, capabilities, confidence, is_default in catalog:
            adapter = self._adapters[name]
            engines.append(
                OCREngineResponse(
                    id=engine_id,
                    name=name,
                    display_name=adapter.display_name,
                    engine_type=engine_type,
                    provider_category="local",
                    capabilities=capabilities,
                    avg_confidence=confidence,
                    is_active=adapter.is_available(),
                    is_default=is_default,
                )
            )
        return engines

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
        requested = (engine_name or "").strip().lower() or "auto"

        if requested == "auto":
            return await self._extract_auto(session, content, filename, tenant_id, start_time)

        adapter = self._adapters.get(requested)
        if adapter is None:
            logger.warning("requested_ocr_engine_not_found_fallback_to_default", engine=requested)
            adapter = self._adapters[self.default_engine]

        if not adapter.is_available():
            hint = _ENGINE_INSTALL_HINTS.get(requested, "lien he quan tri vien")
            raise AppException(
                f"Engine OCR '{requested}' chua san sang (thieu dependency). Cai dat voi: {hint}",
                code="ocr_engine_unavailable",
                status_code=400,
                details={"engine": requested, "install_hint": hint},
            )

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

        return await self._build_response(
            session=session,
            result_dict=result_dict,
            filename=filename,
            tenant_id=tenant_id,
            start_time=start_time,
            fallback_triggered=fallback_triggered,
            error_msg=error_msg,
        )

    async def _extract_auto(
        self,
        session: AsyncSession,
        content: bytes,
        filename: str,
        tenant_id: str,
        start_time: float,
    ) -> OCRExtractResponse:
        """Smart routing: fast text extraction first, heavy OCR only for scans.

        Runs PyMuPDF; when it returns blank text (scanned PDF/image-only pages),
        upgrades to Docling (layout+tables) then EasyOCR (stamps/photos) if
        installed. Never invents text: an empty result is returned honestly.
        """
        default_adapter = self._adapters[self.default_engine]
        try:
            result_dict = await default_adapter.extract(content, filename)
        except Exception as exc:
            logger.error("auto_ocr_primary_failed", engine=default_adapter.name, error=str(exc))
            result_dict = {"engine_used": default_adapter.name, "raw_text": "", "pages": [],
                           "total_pages": 0, "overall_confidence": 0.0}

        if not (result_dict.get("raw_text") or "").strip():
            for candidate in ("docling", "easyocr"):
                upgrade = self._adapters[candidate]
                if not upgrade.is_available():
                    continue
                try:
                    upgraded = await upgrade.extract(content, filename)
                except Exception as exc:
                    logger.warning("auto_ocr_upgrade_failed", engine=candidate, error=str(exc))
                    continue
                if (upgraded.get("raw_text") or "").strip():
                    logger.info("auto_ocr_upgraded", from_engine=default_adapter.name,
                                to_engine=candidate, filename=filename)
                    return await self._build_response(
                        session=session,
                        result_dict=upgraded,
                        filename=filename,
                        tenant_id=tenant_id,
                        start_time=start_time,
                        fallback_triggered=True,
                    )

        return await self._build_response(
            session=session,
            result_dict=result_dict,
            filename=filename,
            tenant_id=tenant_id,
            start_time=start_time,
            fallback_triggered=False,
        )

    async def _build_response(
        self,
        session: AsyncSession,
        result_dict: dict,
        filename: str,
        tenant_id: str,
        start_time: float,
        fallback_triggered: bool,
        error_msg: str | None = None,
    ) -> OCRExtractResponse:
        """Persist the audit log and shape the final OCR response."""
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        total_pages = int(result_dict.get("total_pages", 1))
        confidence = float(result_dict.get("overall_confidence", 0.90))

        # Audit log to PostgreSQL
        job_log = OCRJobLog(
            tenant_id=tenant_id,
            filename=filename,
            engine_used=result_dict.get("engine_used", self.default_engine),
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
            engine_used=result_dict.get("engine_used", self.default_engine),
            fallback_triggered=fallback_triggered,
            total_pages=total_pages,
            overall_confidence=confidence,
            latency_ms=latency_ms,
            raw_text=result_dict.get("raw_text", ""),
            pages=pages,
        )
