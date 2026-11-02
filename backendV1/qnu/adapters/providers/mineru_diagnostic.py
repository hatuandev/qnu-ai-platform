"""Verify OCR with a generated PDF, not a health response or fabricated catalog."""

import asyncio
import time

import pymupdf

from qnu.adapters.providers.mineru import MineruOcrEngine
from qnu.domains.ocr.mineru_layout import archive_pages, parse_mineru_page
from qnu.platform.errors import AppException
from qnu.ports.ocr_engine import OcrDocumentRequest
from qnu.ports.provider_diagnostics import DiagnosticResult


def sample_pdf():
    with pymupdf.open() as document:
        page = document.new_page(width=420, height=160)
        page.insert_text((20, 80), "QNU OCR TEST 123", fontsize=24)
        return document.tobytes()


async def check_mineru(target, transport=None):
    started = time.monotonic()

    async def save(state):
        # Diagnostic samples are disposable; no automatic retry, including after timeout.
        return None

    async def guard():
        return None

    try:
        pdf = await asyncio.to_thread(sample_pdf)
        result = await MineruOcrEngine(transport=transport).extract_document(
            pdf,
            OcrDocumentRequest(
                target.endpoint, target.model, target.timeout_seconds, target.api_key
            ),
            checkpoint={},
            save=save,
            guard=guard,
        )
        pages = await asyncio.to_thread(archive_pages, result.archive, 1)
        layout = await asyncio.to_thread(parse_mineru_page, pages[1])
        if not layout.text.strip():
            raise AppException("", code="mineru_page_empty")
        return DiagnosticResult(
            "ok",
            "diagnostic_ok",
            "MinerU OCR trả cấu trúc PDF hợp lệ; chưa đo chất lượng tài liệu thực tế.",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
    except AppException as exc:
        return DiagnosticResult(
            "failed",
            exc.code,
            "MinerU chưa trả kết quả OCR hợp lệ; không tự gửi lại.",
            latency_ms=int((time.monotonic() - started) * 1000),
        )
