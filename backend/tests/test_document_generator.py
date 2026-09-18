"""Tests for Document Generator Service, Gotenberg PDF conversion, and Artifact download API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import AppException
from app.main import app
from app.modules.tools.builtin.document_exporter import DocumentExporterTool
from app.modules.tools.document_generator import (
    convert_docx_to_pdf_gotenberg,
    export_document_package,
    render_docx_template,
)


def test_render_docx_to_trinh_nd30():
    """Verify docxtpl renders official To Trinh template into valid DOCX bytes."""
    context = {
        "so_hieu": "12/TTr-ĐHQN",
        "trich_yeu": "Về việc mua sắm trang thiết bị phòng thí nghiệm AI",
        "noi_dung": "Kính trình Ban Giám hiệu xem xét phê duyệt danh mục thiết bị thực hành.",
        "chuc_vu_nguoi_ky": "HIỆU TRƯỞNG",
        "ho_ten_nguoi_ky": "PGS.TS. Đỗ Ngọc Mỹ",
    }
    docx_bytes = render_docx_template("to_trinh", context)
    assert docx_bytes.startswith(b"PK\x03\x04")  # Standard ZIP/DOCX magic bytes
    assert len(docx_bytes) > 20000


def test_render_docx_thong_bao_nd30():
    """Verify docxtpl renders official Thong Bao template into valid DOCX bytes."""
    context = {
        "so_hieu": "45/TB-ĐHQN",
        "trich_yeu": "Về việc tổ chức cuộc thi Nghiên cứu Khoa học Sinh viên 2026",
        "noi_dung": "Nhà trường thông báo tới toàn thể sinh viên thể lệ tham gia cuộc thi.",
    }
    docx_bytes = render_docx_template("thong_bao", context)
    assert docx_bytes.startswith(b"PK\x03\x04")
    assert len(docx_bytes) > 20000


def test_render_docx_quyet_dinh_nd30():
    """Verify docxtpl renders official Quyet Dinh template into valid DOCX bytes."""
    context = {
        "so_hieu": "88/QĐ-ĐHQN",
        "trich_yeu": "Về việc thành lập Hội đồng Đánh giá Luận án Tiến sĩ",
        "noi_dung": "Quyết định thành lập Hội đồng gồm 5 thành viên theo danh sách đính kèm.",
    }
    docx_bytes = render_docx_template("quyet_dinh", context)
    assert docx_bytes.startswith(b"PK\x03\x04")
    assert len(docx_bytes) > 20000


@pytest.mark.asyncio
async def test_convert_docx_to_pdf_gotenberg_offline_fallback():
    """Verify Gotenberg conversion returns None gracefully when service is unreachable."""
    dummy_bytes = b"PK\x03\x04dummy"
    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        pdf_bytes = await convert_docx_to_pdf_gotenberg(dummy_bytes, "test.docx")
        assert pdf_bytes is None


@pytest.mark.asyncio
async def test_convert_docx_to_pdf_gotenberg_success():
    """Verify Gotenberg conversion returns PDF bytes on successful response."""
    dummy_bytes = b"PK\x03\x04dummy"
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF-1.7 mock content"
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        pdf_bytes = await convert_docx_to_pdf_gotenberg(dummy_bytes, "test.docx")
        assert pdf_bytes is not None
        assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_export_document_package_creates_artifacts():
    """Verify export_document_package renders docx and registers download URLs."""
    context = {
        "trich_yeu": "Thử nghiệm kết xuất trọn gói",
        "noi_dung": "Nội dung kiểm tra tự động.",
    }
    with patch("app.core.storage.storage_service.save", new_callable=AsyncMock):
        artifacts = await export_document_package(
            template_code="to_trinh",
            context=context,
            formats=["docx"],
            base_name="test_doc",
        )
        assert len(artifacts) >= 1
        docx_art = artifacts[0]
        assert docx_art["type"] == "docx"
        assert docx_art["url"].startswith("/platform/v1alpha1/tools/artifacts/")
        assert docx_art["size"] > 20000


@pytest.mark.asyncio
async def test_document_exporter_tool_execution():
    """Verify DocumentExporterTool executes and returns expected structure."""
    tool = DocumentExporterTool()
    params = {
        "document_type": "to_trinh",
        "title": "Tờ trình kinh phí hội thảo",
        "body_paragraphs": ["Kính gửi Ban Giám hiệu", "Đề nghị cấp kinh phí 20 triệu."],
    }
    with patch("app.core.storage.storage_service.save", new_callable=AsyncMock):
        result = await tool.execute(params)
        assert result["status"] == "generated"
        assert result["document_type_code"] == "to_trinh"
        assert "artifacts" in result
        assert result["docx_url"] is not None


@pytest.mark.asyncio
async def test_document_exporter_tool_invalid_type():
    """Verify tool raises AppException for unsupported document types."""
    tool = DocumentExporterTool()
    with pytest.raises(AppException, match="Loại văn bản không được hỗ trợ"):
        await tool.execute({"document_type": "unknown_random_type"})


@pytest.mark.asyncio
async def test_api_download_artifact_success():
    """Verify GET /platform/v1alpha1/tools/artifacts/{filename} downloads stored file."""
    mock_file_bytes = b"PK\x03\x04test_content"
    with patch("app.core.storage.storage_service.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_file_bytes
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/tools/artifacts/test_export.docx")
            assert resp.status_code == 200
            assert resp.content == mock_file_bytes
            assert "attachment" in resp.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_api_download_artifact_not_found():
    """Verify GET /platform/v1alpha1/tools/artifacts/{filename} returns 404 when missing."""
    with patch("app.core.storage.storage_service.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/platform/v1alpha1/tools/artifacts/non_existent.docx")
            assert resp.status_code == 404
