"""OCR Service with Engine Routing, Resilient Fallback, and Studio Intelligence."""

from __future__ import annotations

import hashlib
import io
import os
import re
import time
from pathlib import Path
from typing import Any

import openpyxl
import structlog
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.ocr.adapters.base import BaseOCRAdapter
from app.modules.ocr.adapters.docling_adapter import DoclingOCRAdapter
from app.modules.ocr.adapters.easyocr_adapter import EasyOCRAdapter
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter
from app.modules.ocr.layout_detector import smart_layout_detector
from app.modules.ocr.models import OCRJobLog
from app.modules.ocr.schemas import (
    OCREngineResponse,
    OCRExtractResponse,
    OCRPageResult,
    StudioOCRPageResponse,
    StudioOCRParseResponse,
    StudioOCRRegion,
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
        """Smart routing: fast text extraction first, heavy OCR only for scans."""
        default_adapter = self._adapters[self.default_engine]
        try:
            result_dict = await default_adapter.extract(content, filename)
        except Exception as exc:
            logger.error("auto_ocr_primary_failed", engine=default_adapter.name, error=str(exc))
            result_dict = {
                "engine_used": default_adapter.name,
                "raw_text": "",
                "pages": [],
                "total_pages": 0,
                "overall_confidence": 0.0,
            }

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
                    logger.info(
                        "auto_ocr_upgraded",
                        from_engine=default_adapter.name,
                        to_engine=candidate,
                        filename=filename,
                    )
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
        result_dict: dict[str, Any],
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
                blocks=p.get("blocks", []) or [],
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

    # --- Studio OCR Interactive Methods ---

    async def parse_studio_document(
        self,
        content: bytes,
        filename: str,
        engine_name: str | None = None,
        tenant_id: str = "tenant_qnu",
        workspace_id: str = "workspace_qnu",
    ) -> StudioOCRParseResponse:
        """Execute OCR recognition on all pages and extract layout bounding boxes for Studio UI."""
        start_time = time.perf_counter()
        file_hash = hashlib.md5(content).hexdigest()[:10]
        ext = os.path.splitext(filename)[1].lower().lstrip(".")

        requested = (engine_name or "").strip().lower() or "auto"
        adapter = self._adapters.get(requested)
        if adapter is None or not adapter.is_available():
            adapter = self._adapters[self.default_engine]

        try:
            ocr_res = await adapter.extract(content, filename)
        except Exception as exc:
            logger.warning("studio_ocr_adapter_failed_fallback", error=str(exc))
            adapter = self._adapters[self.default_engine]
            ocr_res = await adapter.extract(content, filename)

        pages_dict = {p["page_number"]: p for p in ocr_res.get("pages", [])}
        rendered_pages: list[StudioOCRPageResponse] = []

        if ext in ["pdf", "png", "jpg", "jpeg", "webp", "bmp"]:
            try:
                import pymupdf as fitz
                doc = fitz.open(stream=content, filetype=ext if ext != "pdf" else "pdf")
                for i, page in enumerate(doc):
                    pnum = i + 1
                    img_filename = f"page_{pnum}.jpg"
                    cache_key = f"ocr_cache/{file_hash}/{img_filename}"

                    img_bytes = await storage_service.get(cache_key)
                    if not img_bytes:
                        pix = page.get_pixmap(dpi=120)
                        img_bytes = pix.tobytes("jpeg")
                        await storage_service.save(cache_key, img_bytes)

                    p_info = pages_dict.get(pnum)
                    page_md = p_info["extracted_text"] if p_info else ""
                    lines = [l.strip() for l in page_md.splitlines() if l.strip() and not l.strip().startswith("|")]
                    title = lines[0] if lines else f"Trang {pnum}"

                    cv_regions = smart_layout_detector.detect_layout_regions(
                        img_bytes, page_md, page_number=pnum, fitz_page=page
                    )
                    filtered_regions = [r for r in cv_regions if r.get("type") != "image"]
                    has_table = any(r["type"] == "table" for r in filtered_regions) or ("|" in page_md)
                    is_signed = any(r["type"] == "signature" for r in filtered_regions)

                    regions_models = [
                        StudioOCRRegion(
                            type=r["type"],
                            label=r.get("label", r["type"]),
                            text=r.get("text", ""),
                            top=float(r["top"]),
                            left=float(r["left"]),
                            width=float(r["width"]),
                            height=float(r["height"]),
                        )
                        for r in filtered_regions
                    ]

                    img_url = f"/api/v1/ocr/studio/page-image/{file_hash}/{img_filename}"
                    rendered_pages.append(
                        StudioOCRPageResponse(
                            page_number=pnum,
                            title=title[:90],
                            is_signed=is_signed,
                            has_table=has_table,
                            image_url=img_url,
                            markdown=page_md,
                            raw_text=re.sub(r"[*_#`]", "", page_md).strip(),
                            regions=regions_models,
                            dimensions={"width": int(page.rect.width), "height": int(page.rect.height)},
                            word_count=len(page_md.split()),
                            line_count=len(page_md.splitlines()),
                        )
                    )
            except Exception as pdf_err:
                logger.error("error_rendering_pdf_pages_in_studio", error=str(pdf_err))

        if not rendered_pages:
            total_pages = max(1, ocr_res.get("total_pages", 1))
            for pnum in range(1, total_pages + 1):
                img_filename = f"page_{pnum}.jpg"
                cache_key = f"ocr_cache/{file_hash}/{img_filename}"
                img_bytes = await storage_service.get(cache_key)
                if not img_bytes:
                    img_bytes = self._generate_card_preview_image(filename, img_filename)
                    await storage_service.save(cache_key, img_bytes)

                p_info = pages_dict.get(pnum)
                page_md = p_info["extracted_text"] if p_info else ocr_res.get("raw_text", "")
                lines = [l.strip() for l in page_md.splitlines() if l.strip() and not l.strip().startswith("|")]
                title = lines[0] if lines else f"Trang {pnum}"

                img_url = f"/api/v1/ocr/studio/page-image/{file_hash}/{img_filename}"
                rendered_pages.append(
                    StudioOCRPageResponse(
                        page_number=pnum,
                        title=title[:90],
                        is_signed=False,
                        has_table="|" in page_md,
                        image_url=img_url,
                        markdown=page_md,
                        raw_text=page_md,
                        regions=[],
                        dimensions={"width": 1240, "height": 1754},
                        word_count=len(page_md.split()),
                        line_count=len(page_md.splitlines()),
                    )
                )

        sheets_data = None
        if ext in ["xlsx", "xls"]:
            sheets_data = self._extract_xlsx_sheets(content)
            if sheets_data and rendered_pages:
                for idx, sheet in enumerate(sheets_data):
                    if idx < len(rendered_pages):
                        rendered_pages[idx].sheet_data = sheet

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        size_str = (
            f"{len(content) / (1024 * 1024):.1f} MB"
            if len(content) >= 1024 * 1024
            else f"{len(content) / 1024:.1f} KB"
        )

        return StudioOCRParseResponse(
            filename=filename,
            total_pages=len(rendered_pages),
            size=size_str,
            provider="local",
            model=adapter.name,
            latency_ms=latency_ms,
            pages=rendered_pages,
            sheets_data=sheets_data,
        )

    def _generate_card_preview_image(self, filename: str, img_filename: str) -> bytes:
        """Generate a clean visual card placeholder for non-rendered Office / Spreadsheet pages."""
        img = Image.new("RGB", (1240, 1754), color=(248, 250, 252))
        draw = ImageDraw.Draw(img)
        draw.rectangle([60, 60, 1180, 1694], outline=(203, 213, 225), width=3)
        draw.rectangle([60, 60, 1180, 160], fill=(16, 185, 129))
        draw.text((100, 95), "QNU.AI STUDIO -- BAN TRINH CHIEU TAI LIEU", fill=(255, 255, 255))
        draw.text((100, 260), f"Tai lieu: {filename}", fill=(15, 23, 42))
        draw.text((100, 320), f"Dang hien thi: {img_filename}", fill=(100, 116, 139))
        draw.text((100, 420), "Da boc tach toan bo cau truc noi dung.", fill=(5, 150, 105))
        draw.text(
            (100, 470),
            "Vui long xem noi dung Markdown & Bieu mau chi tiet o khung ben phai.",
            fill=(71, 85, 105),
        )

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()

    def _extract_xlsx_sheets(self, content: bytes) -> list[dict[str, Any]]:
        """Extract table sheets from an Excel file bytes."""
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            sheets_data = []
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                rows = []
                for row in sheet.iter_rows(values_only=True):
                    row_str = ["" if v is None else str(v) for v in row]
                    if any(cell != "" for cell in row_str):
                        rows.append(row_str)
                if rows:
                    max_cols = max(len(r) for r in rows)
                    padded = [r + [""] * (max_cols - len(r)) for r in rows]
                    sheets_data.append({
                        "name": sheet_name,
                        "rows": padded,
                        "total_rows": len(padded),
                        "total_cols": max_cols,
                        "totalRows": len(padded),
                        "totalCols": max_cols,
                    })
            return sheets_data
        except Exception as exc:
            logger.warning("failed_to_extract_xlsx_sheets", error=str(exc))
            return []

    async def get_studio_page_image(self, file_hash: str, img_filename: str) -> bytes:
        """Stream rendered page image from storage cache with multiple fallback locations."""
        cache_key = f"ocr_cache/{file_hash}/{img_filename}"
        img_bytes = await storage_service.get(cache_key)
        if img_bytes:
            return img_bytes

        local_path = Path("frontend/public/ocr-cache") / file_hash / img_filename
        if local_path.is_file():
            return local_path.read_bytes()

        demo_path = Path("frontend/public/ocr-cache/doc_ts_2026") / img_filename
        if demo_path.is_file():
            return demo_path.read_bytes()

        # Generate on-demand fallback card
        card_bytes = self._generate_card_preview_image(file_hash, img_filename)
        await storage_service.save(cache_key, card_bytes)
        return card_bytes

    async def get_sample_document(self) -> StudioOCRParseResponse:
        """Return the pre-configured 14-page official QNU admissions sample document for instant studio testing."""
        pages: list[StudioOCRPageResponse] = []
        for pnum in range(1, 15):
            img_filename = f"page_{pnum}.jpg"
            img_url = f"/api/v1/ocr/studio/page-image/doc_ts_2026/{img_filename}"

            regions: list[StudioOCRRegion] = []
            if pnum == 1:
                regions.append(StudioOCRRegion(type="header", label="header", text="TRƯỜNG ĐẠI HỌC QUY NHƠN", top=4.5, left=7.2, width=38.0, height=5.5))
                regions.append(StudioOCRRegion(type="header", label="header", text="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", top=4.5, left=54.0, width=40.0, height=5.5))
                regions.append(StudioOCRRegion(type="title", label="title", text="THÔNG TIN TUYỂN SINH ĐẠI HỌC CHÍNH QUY NĂM 2026", top=14.0, left=15.0, width=70.0, height=6.0))
            elif pnum in (3, 4, 5, 8, 9, 10):
                regions.append(StudioOCRRegion(type="table", label="table", text="Bảng mã ngành, chỉ tiêu và tổ hợp xét tuyển", top=20.0, left=6.0, width=88.0, height=60.0))
            elif pnum == 14:
                regions.append(StudioOCRRegion(type="signature", label="signature", text="KT. HIỆU TRƯỞNG - PHÓ HIỆU TRƯỞNG (Đã ký & Đóng dấu)", top=72.0, left=58.0, width=35.0, height=18.0))

            sample_md = f"### Trang {pnum}: Thông Tin Tuyển Sinh Đại Học 2026\n\nNội dung văn bản quy chế tuyển sinh trường Đại học Quy Nhơn."
            if pnum in (3, 4, 5, 8, 9, 10):
                sample_md += "\n\n| STT | Mã ngành | Tên ngành đào tạo | Chỉ tiêu | Tổ hợp xét tuyển |\n|:---:|:---:|:---|:---:|:---:|\n| 1 | 7480201 | Công nghệ thông tin | 180 | A00, A01, D01, D07 |\n| 2 | 7480101 | Khoa học máy tính | 120 | A00, A01, D01 |\n| 3 | 7480108 | Kỹ thuật phần mềm | 100 | A00, A01, D01, D07 |"

            pages.append(
                StudioOCRPageResponse(
                    page_number=pnum,
                    title=f"Thông tin tuyển sinh 2026 - Trang {pnum}",
                    is_signed=(pnum == 14),
                    has_table=(pnum in (3, 4, 5, 8, 9, 10)),
                    image_url=img_url,
                    markdown=sample_md,
                    raw_text=sample_md,
                    regions=regions,
                    dimensions={"width": 1240, "height": 1754},
                    word_count=len(sample_md.split()),
                    line_count=len(sample_md.splitlines()),
                )
            )

        return StudioOCRParseResponse(
            filename="Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).pdf",
            total_pages=14,
            size="3.2 MB",
            provider="local",
            model="pymupdf_ocr",
            latency_ms=45.0,
            pages=pages,
            sheets_data=None,
        )
