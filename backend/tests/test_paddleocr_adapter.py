"""Unit tests for PaddleOCRVLAdapter — Response mapping, error handling, and Unicode NFC normalization."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.exceptions import AppException
from app.modules.ocr.adapters.paddleocr_adapter import PaddleOCRVLAdapter


@pytest.mark.asyncio
async def test_paddleocr_adapter_properties_and_availability():
    adapter = PaddleOCRVLAdapter(base_url="http://100.105.13.53:8080")
    assert adapter.name == "paddleocr_ocr"
    assert "PaddleOCR-VL" in adapter.display_name
    assert adapter.is_available() is True

    empty_adapter = PaddleOCRVLAdapter(base_url="")
    assert empty_adapter.is_available() is False


@pytest.mark.asyncio
async def test_paddleocr_adapter_extract_empty_content_raises_app_exception():
    adapter = PaddleOCRVLAdapter(base_url="http://100.105.13.53:8080")
    with pytest.raises(AppException) as exc_info:
        await adapter.extract(b"", "empty.pdf")
    assert exc_info.value.code == "DOCUMENT_CONTENT_EMPTY"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_paddleocr_adapter_extract_success_pdf_and_nfc():
    adapter = PaddleOCRVLAdapter(base_url="http://100.105.13.53:8080")
    mock_response_data = {
        "errorCode": 0,
        "errorMsg": "Success",
        "result": {
            "layoutParsingResults": [
                {
                    "markdown": {
                        "text": "# TRƯỜNG ĐẠI HỌC QUY NHƠN\n\n| Mã Ngành | Tên Ngành |\n| 7480201 | CNTT |",
                    },
                    "prunedResult": {"table_count": 1},
                },
                {
                    "markdown": {
                        "text": "Trang 2: Điểm chuẩn năm 2026",
                    },
                    "prunedResult": {},
                },
            ],
            "dataInfo": {},
        },
    }

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await adapter.extract(b"%PDF-1.4 test", "test_file.pdf")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert payload.get("fileType") == 0  # 0 for PDF

        assert res["engine_used"] == "paddleocr_vl"
        assert res["total_pages"] == 2
        assert len(res["pages"]) == 2
        assert res["pages"][0]["page_number"] == 1
        assert res["pages"][0]["has_tables"] is True
        assert "TRƯỜNG ĐẠI HỌC QUY NHƠN" in res["pages"][0]["extracted_text"]
        assert "Trang 2: Điểm chuẩn năm 2026" in res["pages"][1]["extracted_text"]
        assert "TRƯỜNG ĐẠI HỌC QUY NHƠN" in res["raw_text"]


@pytest.mark.asyncio
async def test_paddleocr_adapter_extract_image_file_type():
    adapter = PaddleOCRVLAdapter(base_url="http://100.105.13.53:8080")
    mock_response_data = {
        "errorCode": 0,
        "errorMsg": "Success",
        "result": {
            "layoutParsingResults": [
                {
                    "markdown": {"text": "Ảnh chụp văn bản tuyển sinh"},
                    "prunedResult": {},
                }
            ]
        },
    }
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        res = await adapter.extract(b"\x89PNG test", "scan.png")
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs.get("json", {})
        assert payload.get("fileType") == 1  # 1 for Image
        assert res["total_pages"] == 1


@pytest.mark.asyncio
async def test_paddleocr_adapter_timeout_raises_app_exception():
    adapter = PaddleOCRVLAdapter(base_url="http://100.105.13.53:8080", timeout=5.0)

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(AppException) as exc_info:
            await adapter.extract(b"%PDF-1.4 test", "timeout.pdf")
        assert exc_info.value.code == "OCR_SERVICE_TIMEOUT"
        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_paddleocr_adapter_http_error_raises_app_exception():
    adapter = PaddleOCRVLAdapter(base_url="http://100.105.13.53:8080")
    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(AppException) as exc_info:
            await adapter.extract(b"%PDF-1.4 test", "error.pdf")
        assert exc_info.value.code == "OCR_INFERENCE_ERROR"
        assert exc_info.value.status_code == 502
