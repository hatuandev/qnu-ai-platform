"""API Integration tests for Core FastAPI endpoints and Exception Handlers."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import EntityNotFoundError
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify GET / returns service metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "QNU.AI Platform API"
    assert data["status"] == "online"
    assert "version" in data


@pytest.mark.asyncio
async def test_liveness_probe():
    """Verify GET /health/live returns 200 ok."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_correlation_id_and_timing_headers():
    """Verify incoming requests receive X-Correlation-ID and X-Process-Time-Ms headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert "X-Correlation-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers
    assert response.headers["X-Correlation-ID"].startswith("corr_")


@pytest.mark.asyncio
async def test_custom_correlation_id_header_propagation():
    """Verify custom X-Correlation-ID header passed from client is preserved."""
    custom_corr_id = "corr_custom_client_12345"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/", headers={"X-Correlation-ID": custom_corr_id})
    assert response.headers["X-Correlation-ID"] == custom_corr_id


@pytest.mark.asyncio
async def test_rfc7807_exception_handler():
    """Verify DomainException returns RFC 7807 Problem Details format."""

    # Temporarily register a test route raising EntityNotFoundError
    @app.get("/test/raise-not-found")
    async def raise_not_found():
        raise EntityNotFoundError(
            "Không tìm thấy tài liệu yêu cầu", details={"document_id": "doc_999"}
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/test/raise-not-found")

    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "entity_not_found"
    assert data["status"] == 404
    assert data["detail"] == "Không tìm thấy tài liệu yêu cầu"
    assert "correlation_id" in data
    assert data["details"]["document_id"] == "doc_999"
