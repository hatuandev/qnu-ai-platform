"""Unit Tests for Document OCR Recognition, Adapters & Fallback Policy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from app.core.exceptions import AppException
from app.modules.ocr.adapters.mock_adapter import MockOCRAdapter
from app.modules.ocr.adapters.pymupdf_adapter import PyMuPDFOCRAdapter
from app.modules.ocr.service import OCRService


@pytest.mark.asyncio
async def test_mock_ocr_adapter():
    adapter = MockOCRAdapter()
    assert adapter.name == "mock_ocr"
    assert adapter.is_available() is True

    res = await adapter.extract(b"dummy_bytes", "qd_2699.pdf")
    assert res["engine_used"] == "mock_ocr"
    assert res["total_pages"] == 2
    assert res["overall_confidence"] >= 0.95
    assert len(res["pages"]) == 2
    assert "Điều 1" in res["raw_text"]


@pytest.mark.asyncio
async def test_pymupdf_ocr_adapter():
    # Create an in-memory PDF with 1 page
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Truong Dai hoc Quy Nhon - Quy che Dao tao tin chi QNU", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    adapter = PyMuPDFOCRAdapter()
    assert adapter.name == "pymupdf_ocr"
    res = await adapter.extract(pdf_bytes, "test_doc.pdf")

    assert res["engine_used"] == "pymupdf_ocr"
    assert res["total_pages"] == 1
    assert "Quy che Dao tao tin chi" in res["raw_text"]
    assert res["pages"][0]["confidence"] >= 0.90


@pytest.mark.asyncio
async def test_ocr_service_successful_extraction():
    service = OCRService()
    engines = service.list_engines()
    assert len(engines) >= 2

    # Create dummy PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Quyet dinh ban hanh ke hoach giang day QNU 2026", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    resp = await service.extract_document(
        session=mock_session,
        content=pdf_bytes,
        filename="ke_hoach_2026.pdf",
        engine_name="pymupdf_ocr",
    )

    assert resp.success is True
    assert resp.fallback_triggered is False
    assert resp.total_pages == 1
    assert "ke hoach giang day" in resp.raw_text
    assert resp.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_list_engines_reflects_real_availability():
    """Engine catalog must expose API OCR and native PDF extraction."""
    service = OCRService()
    engines = service.list_engines()
    by_name = {e.name: e for e in engines}
    assert set(by_name) == {"pymupdf_ocr", "gemini_ocr", "mock_ocr", "mistral_ocr", "qwen_ocr"}
    assert by_name["pymupdf_ocr"].is_active is True
    assert by_name["gemini_ocr"].is_active is service._adapters["gemini_ocr"].is_available()
    assert by_name["mistral_ocr"].is_active is service._adapters["mistral_ocr"].is_available()
    assert by_name["qwen_ocr"].is_active is service._adapters["qwen_ocr"].is_available()


@pytest.mark.asyncio
async def test_gemini_adapter_properties_and_availability():
    """Gemini OCR adapter exposes correct name, display_name, and availability check."""
    from app.modules.ocr.adapters.gemini_adapter import GeminiOCRAdapter

    adapter = GeminiOCRAdapter(model_name="gemini-2.5-flash")
    assert adapter.name == "gemini_ocr"
    assert "Google Gemini Vision OCR" in adapter.display_name
    assert adapter.model_name == "gemini-2.5-flash"

    with patch("app.core.config.settings.GEMINI_API_KEY", ""):
        empty_adapter = GeminiOCRAdapter()
        assert empty_adapter.is_available() is False

    with patch("app.core.config.settings.GEMINI_API_KEY", "test_key_fake_123"):
        active_adapter = GeminiOCRAdapter()
        assert active_adapter.is_available() is True


@pytest.mark.asyncio
async def test_openai_vision_adapter_properties_and_availability():
    """OpenAI Vision OCR adapter exposes correct name, display_name, and availability check."""
    from app.modules.ocr.adapters.openai_vision_adapter import (
        OpenAIVisionOCRAdapter,
        QwenOCRAdapter,
    )

    adapter = OpenAIVisionOCRAdapter(model_name="gpt-4o")
    assert adapter.name == "openai_vision_ocr"
    assert "OpenAI GPT Vision OCR" in adapter.display_name
    assert adapter.model_name == "gpt-4o"

    qwen = QwenOCRAdapter()
    assert qwen.name == "qwen_ocr"
    assert "Qwen Vision OCR" in qwen.display_name
    assert "qwen" in qwen.model_name.lower()

    with (
        patch("app.core.config.settings.OPENROUTER_API_KEY", ""),
        patch("app.core.config.settings.OPENAI_API_KEY", ""),
    ):
        empty_adapter = OpenAIVisionOCRAdapter()
        assert empty_adapter.is_available() is False

    with patch("app.core.config.settings.OPENROUTER_API_KEY", "test_router_key"):
        active_adapter = OpenAIVisionOCRAdapter()
        assert active_adapter.is_available() is True



@pytest.mark.asyncio
async def test_mistral_adapter_without_key_fails_closed():
    """A missing Mistral key must fail clearly instead of invoking a local model."""
    from app.modules.ocr.adapters.mistral_adapter import MistralOCRAdapter

    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Van ban mau giang day QNU", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    # Simulate missing key
    with patch("app.core.config.settings.MISTRAL_API_KEY", ""):
        adapter = MistralOCRAdapter()
        assert adapter.is_available() is False

        with (
            patch.dict(service._adapters, {"mistral_ocr": adapter}),
            pytest.raises(AppException) as exc_info,
        ):
            await service.extract_document(
                session=mock_session,
                content=pdf_bytes,
                filename="test.pdf",
                engine_name="mistral_ocr",
            )
        assert exc_info.value.code == "OCR_PROVIDER_CREDENTIALS_MISSING"
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_auto_routing_uses_mistral_when_key_present():
    """Auto mode on a scanned PDF must route to Mistral OCR when key is configured."""
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    class FakeMistral:
        name = "mistral_ocr"

        def is_available(self) -> bool:
            return True

        async def extract(self, content: bytes, filename: str) -> dict:
            return {
                "engine_used": "mistral_ocr",
                "total_pages": 1,
                "overall_confidence": 0.99,
                "pages": [
                    {
                        "page_number": 1,
                        "extracted_text": "Noi dung trich xuat tu Mistral Cloud OCR",
                        "confidence": 0.99,
                        "word_count": 8,
                        "line_count": 1,
                        "has_tables": False,
                    }
                ],
                "raw_text": "Noi dung trich xuat tu Mistral Cloud OCR",
            }

    with patch.dict(service._adapters, {"mistral_ocr": FakeMistral()}):
        resp = await service.extract_document(
            session=mock_session,
            content=_blank_pdf_bytes(),
            filename="scanned_van_ban.pdf",
            engine_name="auto",
        )
    assert resp.success is True
    assert resp.engine_used == "mistral_ocr"
    assert resp.fallback_triggered is True
    assert "Mistral Cloud OCR" in resp.raw_text


@pytest.mark.asyncio
async def test_explicit_unavailable_engine_raises_clear_error():
    """Retired local engines must be rejected explicitly."""
    service = OCRService()
    mock_session = AsyncMock()
    with pytest.raises(AppException) as exc_info:
        await service.extract_document(
            session=mock_session,
            content=b"%PDF-1.4 dummy",
            filename="scan.pdf",
            engine_name="docling",
        )
    assert exc_info.value.code == "OCR_LOCAL_ENGINE_REMOVED"
    assert exc_info.value.status_code == 400


def _blank_pdf_bytes() -> bytes:
    """Build a scanned-like PDF page with no extractable text."""
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_auto_routing_blank_scan_returns_honest_empty():
    """Auto mode on a blank scan with no heavy/cloud engines available returns empty text."""
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    # When cloud OCR APIs are unavailable, return an honest empty result.
    with (
        patch("app.core.config.settings.MISTRAL_API_KEY", ""),
        patch.object(service._adapters["mistral_ocr"], "is_available", return_value=False),
        patch.object(service._adapters["gemini_ocr"], "is_available", return_value=False),
    ):
        resp = await service.extract_document(
            session=mock_session,
            content=_blank_pdf_bytes(),
            filename="blank_scan.pdf",
            engine_name="auto",
        )
    assert resp.success is True
    assert resp.raw_text == ""
    assert resp.engine_used == "pymupdf_ocr"
    assert resp.fallback_triggered is False


@pytest.mark.asyncio
async def test_ocr_service_graceful_fallback():
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    # Intentionally corrupt or make primary adapter raise an exception
    with (
        patch.object(service._adapters["pymupdf_ocr"], "extract", side_effect=RuntimeError("Engine Out Of Memory")),
        patch.object(service, "_get_active_combo_chain", return_value=[]),
    ):
        resp = await service.extract_document(
            session=mock_session,
            content=b"corrupted_pdf_data",
            filename="corrupt.pdf",
            engine_name="pymupdf_ocr",
        )

        # Fallback should kick in seamlessly
        assert resp.success is True
        assert resp.fallback_triggered is True
        assert resp.engine_used == "mock_ocr"
        assert resp.total_pages >= 1
        assert resp.overall_confidence > 0.90


@pytest.mark.asyncio
async def test_studio_ocr_parse_document_and_page_image():
    service = OCRService()

    # Create dummy PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "TRUONG DAI HOC QUY NHON\n\nThong bao tuyen sinh 2026", fontsize=14)
    page.insert_text((50, 150), "| Ma | Nganh | Chi tieu |\n|---|---|---|\n| 7480201 | CNTT | 150 |", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()

    res = await service.parse_studio_document(
        content=pdf_bytes,
        filename="tb_tuyen_sinh.pdf",
        engine_name="pymupdf_ocr",
    )

    assert res.total_pages == 1
    assert len(res.pages) == 1
    assert res.filename == "tb_tuyen_sinh.pdf"
    assert "page_1.jpg" in res.pages[0].image_url
    assert res.pages[0].word_count > 0

    # Test image retrieval
    file_hash = res.pages[0].image_url.split("/")[-2]
    img_bytes = await service.get_studio_page_image(file_hash, "page_1.jpg")
    assert len(img_bytes) > 0


@pytest.mark.asyncio
async def test_studio_sample_document():
    service = OCRService()
    sample = await service.get_sample_document()

    assert sample.total_pages == 14
    assert len(sample.pages) == 14
    assert sample.pages[0].page_number == 1
    assert len(sample.pages[0].regions) > 0
    assert any(p.has_table for p in sample.pages)
    assert any(p.is_signed for p in sample.pages)


@pytest.mark.asyncio
async def test_ocr_combo_chain_sequential_failover_on_quota():
    """When Step 1 in OCR combo hits 429 Quota Exceeded, system sequentially moves to Step 2."""
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    custom_combo = [
        {"provider_id": "prov_gemini", "model_name": "gemini-2.5-flash", "is_active": True},
        {"provider_id": "prov_mistral", "model_name": "mistral-ocr-latest", "is_active": True},
    ]

    class FailingQuotaAdapter:
        name = "gemini-2.5-flash"

        def is_available(self) -> bool:
            return True

        async def extract(self, content: bytes, filename: str) -> dict:
            raise RuntimeError("429 Resource has been exhausted (Quota exceeded for project)")

    class SuccessfulSecondaryAdapter:
        name = "mistral-ocr-latest"

        def is_available(self) -> bool:
            return True

        async def extract(self, content: bytes, filename: str) -> dict:
            return {
                "engine_used": "mistral-ocr-latest",
                "total_pages": 1,
                "overall_confidence": 0.98,
                "pages": [
                    {
                        "page_number": 1,
                        "extracted_text": "Bóc tách thành công qua Mistral OCR dự phòng khi Gemini hết Quota",
                        "confidence": 0.98,
                        "word_count": 13,
                        "line_count": 1,
                        "has_tables": False,
                    }
                ],
                "raw_text": "Bóc tách thành công qua Mistral OCR dự phòng khi Gemini hết Quota",
            }

    with (
        patch.object(service, "_get_active_combo_chain", return_value=custom_combo),
        patch.object(service, "_resolve_adapter", side_effect=lambda m: FailingQuotaAdapter() if "gemini" in m else SuccessfulSecondaryAdapter()),
    ):
        resp = await service.extract_document(
            session=mock_session,
            content=b"dummy_scan_bytes",
            filename="tai_lieu_scan.png",
            engine_name="combo",
        )

        assert resp.success is True
        assert resp.fallback_triggered is True
        assert resp.fallback_engine == "mistral-ocr-latest"
        assert resp.engine_used == "mistral-ocr-latest"
        assert "Mistral OCR dự phòng khi Gemini hết Quota" in resp.raw_text
        assert len(resp.cascade_trace) >= 2
        assert any("429" in t or "Quota" in t for t in resp.cascade_trace)
        assert any("Thành công" in t for t in resp.cascade_trace)


@pytest.mark.asyncio
async def test_ocr_combo_explicit_engine_failure_triggers_combo_fallback():
    """When user requests single engine 'gemini_ocr' but it fails (429), system falls back through combo chain."""
    service = OCRService()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    custom_combo = [
        {"provider_id": "prov_gemini", "model_name": "gemini-2.5-flash", "is_active": True},
        {"provider_id": "prov_mistral", "model_name": "mistral-ocr-latest", "is_active": True},
    ]

    class QuotaErrorAdapter:
        name = "gemini_ocr"

        def is_available(self) -> bool:
            return True

        async def extract(self, content: bytes, filename: str) -> dict:
            raise RuntimeError("HTTP 429 Too Many Requests: Monthly Token Quota Exceeded")

    class BackupAdapter:
        name = "mistral-ocr-latest"

        def is_available(self) -> bool:
            return True

        async def extract(self, content: bytes, filename: str) -> dict:
            return {
                "engine_used": "mistral-ocr-latest",
                "total_pages": 1,
                "overall_confidence": 0.96,
                "pages": [
                    {
                        "page_number": 1,
                        "extracted_text": "Noi dung duoc cuu nguy boi Mistral OCR",
                        "confidence": 0.96,
                        "word_count": 8,
                        "line_count": 1,
                        "has_tables": False,
                    }
                ],
                "raw_text": "Noi dung duoc cuu nguy boi Mistral OCR",
            }

    with (
        patch.object(service, "_get_active_combo_chain", return_value=custom_combo),
        patch.object(service, "_resolve_adapter", side_effect=lambda m: QuotaErrorAdapter() if "gemini" in m else BackupAdapter()),
    ):
        resp = await service.extract_document(
            session=mock_session,
            content=b"dummy_bytes",
            filename="qd_scan.jpg",
            engine_name="gemini_ocr",
        )

        assert resp.success is True
        assert resp.fallback_triggered is True
        assert resp.fallback_engine == "mistral-ocr-latest"
        assert "cuu nguy boi Mistral OCR" in resp.raw_text


@pytest.mark.asyncio
async def test_resolve_adapter_dynamically_respects_default_ocr_model():
    """Verify that _resolve_adapter dynamically instantiates GeminiOCRAdapter with the configured default_ocr_model."""
    service = OCRService()

    # When dynamic default model is provided
    adapter_31 = service._resolve_adapter("gemini_ocr", default_gemini_model="gemini-3.1-flash-lite")
    assert getattr(adapter_31, "model_name", None) == "gemini-3.1-flash-lite"

    adapter_custom = service._resolve_adapter("gemini", default_gemini_model="gemini-3.5-flash-lite")
    assert getattr(adapter_custom, "model_name", None) == "gemini-3.5-flash-lite"

    # When no default model is provided, fallback to default static adapter
    adapter_default = service._resolve_adapter("gemini_ocr")
    assert getattr(adapter_default, "model_name", None) == "gemini-3.1-flash-lite"


@pytest.mark.asyncio
async def test_auto_routing_routes_to_combo_when_combo_mode_enabled():
    """When default_ocr_mode is 'combo', extract_document('auto') delegates to _extract_combo_chain."""
    service = OCRService()
    mock_session = AsyncMock()

    mock_defaults = {
        "default_ocr_mode": "combo",
        "default_ocr_model": "gemini-3.1-flash-lite",
        "ocr_combo_chain": [
            {"provider_id": "prov_gemini", "model_name": "gemini-3.1-flash-lite", "is_active": True}
        ],
    }

    mock_combo_resp = MagicMock()
    mock_combo_resp.engine_used = "gemini-3.1-flash-lite"

    with (
        patch.object(service, "_get_system_defaults", return_value=mock_defaults),
        patch.object(service, "_extract_combo_chain", return_value=mock_combo_resp) as mock_combo_fn,
    ):
        resp = await service.extract_document(
            session=mock_session,
            content=b"test_content",
            filename="document.pdf",
            engine_name="auto",
        )
        assert mock_combo_fn.called
        assert resp.engine_used == "gemini-3.1-flash-lite"



