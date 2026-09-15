"""Unit & Integration Tests for 05 Official QNU AI Assistants."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import EntityNotFoundError
from app.main import app
from app.modules.assistants.service import assistant_service


@pytest.mark.asyncio
async def test_assistants_catalog_contains_5_official_assistants():
    """Verify that catalog includes exactly 5 official assistants with full metadata."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    assistants = await assistant_service.list_assistants(mock_db)
    assert len(assistants) == 5

    codes = [a.code for a in assistants]
    assert "admissions" in codes
    assert "regulations" in codes
    assert "library" in codes
    assert "drafting" in codes
    assert "question_bank" in codes

    for a in assistants:
        assert len(a.sample_questions) >= 3
        assert a.workflow_id is not None
        assert a.collection_id is not None


@pytest.mark.asyncio
async def test_get_assistant_detail_and_not_found():
    """Verify get_assistant fetches by code and raises 404 on invalid code."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    ast = await assistant_service.get_assistant(mock_db, "admissions")
    assert ast.code == "admissions"
    assert "Tuyển sinh" in ast.name

    with pytest.raises(EntityNotFoundError):
        await assistant_service.get_assistant(mock_db, "non_existent_code")


@pytest.mark.asyncio
async def test_api_list_assistants():
    """Verify GET /platform/v1alpha1/assistants returns 200 with 5 assistants."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/platform/v1alpha1/assistants")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    codes = {a["code"] for a in data}
    assert codes == {"admissions", "regulations", "library", "drafting", "question_bank"}


@pytest.mark.asyncio
async def test_api_chat_admissions_greeting():
    """Verify POST /platform/v1alpha1/assistants/admissions/chat responds with admissions greeting."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        payload = {"message": "Xin chào Trợ lý Tuyển sinh QNU!"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/platform/v1alpha1/assistants/admissions/chat", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    res = response.json()
    assert res["assistant_code"] == "admissions"
    assert "Tuyển sinh" in res["assistant_name"]
    assert "Chào bạn" in res["answer"]
    assert len(res["suggested_questions"]) >= 1


@pytest.mark.asyncio
async def test_api_chat_regulations_knowledge_query():
    """Verify POST /platform/v1alpha1/assistants/regulations/chat processes academic query."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        payload = {"message": "Quy định cảnh báo học tập như thế nào?"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/platform/v1alpha1/assistants/regulations/chat", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    res = response.json()
    assert res["assistant_code"] == "regulations"
    assert len(res["answer"]) > 0
