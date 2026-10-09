"""End-to-End Integration test for Admissions Consulting Agent & File Export."""

import os

import pytest

from app.core.database import AsyncSessionFactory, engine
from app.modules.assistants.schemas import AssistantChatRequest
from app.modules.assistants.services.assistant_chat_service import assistant_chat_service


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("QNU_RUN_LIVE_INTEGRATION") != "1",
    reason="Yêu cầu PostgreSQL, ModelOps provider và dữ liệu tuyển sinh V2 đang hoạt động.",
)
async def test_admissions_consulting_chat_flow_returns_artifacts():
    """Verify that chatting with ast_admissions with an export intent produces downloadable artifacts."""
    await engine.dispose()
    async with AsyncSessionFactory() as db:
        req = AssistantChatRequest(
            message="Em tên là Trần Hữu Nam, thi khối A00 được 24.5 điểm ở KV1, hãy tư vấn ngành và xuất file Excel kế hoạch nguyện vọng giúp em",
            tenant_id="tenant_qnu",
        )
        response = await assistant_chat_service.chat(db, "admissions", req)
        assert response.status == "answered"
        assert response.answer is not None
        assert len(response.answer) > 50

        # Verify artifacts were generated and attached
        assert len(response.artifacts) == 1
        types = [a["type"] for a in response.artifacts]
        assert "xlsx" in types

        for art in response.artifacts:
            assert art["url"].startswith("/platform/v1alpha1/tools/artifacts/")
            assert art["size"] > 0
            assert "tu_van_tuyen_sinh" in art["name"]
