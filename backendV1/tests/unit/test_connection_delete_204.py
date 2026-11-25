"""Unit tests for ModelOps connection 204 responses and document-model deletion guards."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from qnu.domains.identity.actor import AuthActor
from qnu.domains.modelops.connections import router as connections_router
from qnu.domains.modelops.connections.schemas import ConnectionCreate
from qnu.domains.modelops.connections.service import _provider_references


def _admin_actor() -> AuthActor:
    return AuthActor(
        actor_id="usr_admin",
        username="admin",
        email="admin@qnu.edu.vn",
        name="Admin",
        roles=("platform_admin",),
        permissions=("ai.models.manage",),
    )


def test_connection_create_schema_forbids_is_active():
    valid = ConnectionCreate(
        name="9router Luna",
        family="openai",
        base_url="https://example.com/v1",
        timeout_seconds=30,
    )
    assert valid.name == "9router Luna"
    with pytest.raises(ValidationError):
        ConnectionCreate(
            name="9router Luna",
            family="openai",
            base_url="https://example.com/v1",
            timeout_seconds=30,
            is_active=True,
        )


@pytest.mark.asyncio
async def test_connection_delete_routes_return_empty_204_response(monkeypatch):
    monkeypatch.setattr(connections_router.service, "delete_connection", AsyncMock())
    monkeypatch.setattr(connections_router.service, "delete_model", AsyncMock())
    monkeypatch.setattr(connections_router.service, "delete_key", AsyncMock())

    actor = _admin_actor()
    for resp in (
        await connections_router.delete("conn_1", db=None, actor=actor),
        await connections_router.delete_model("conn_1", "prv_1", db=None, actor=actor),
        await connections_router.delete_key("conn_1", "key_1", db=None, actor=actor),
    ):
        assert resp.status_code == 204
        assert resp.body == b""
        assert "application/json" not in (resp.headers.get("content-type") or "").lower()


@pytest.mark.asyncio
async def test_provider_references_detects_document_models_jsonb():
    class FakeDB:
        def __init__(self, scalar_results):
            self._results = list(scalar_results)

        async def scalar(self, _stmt):
            return self._results.pop(0) if self._results else None

    # First 6 table checks return None, 7th call returns ModelDefaults row with document_models.
    defaults_row = SimpleNamespace(
        document_models=[{"provider_id": "prv_doc_1", "model_name": "cx/gpt-6-luna"}]
    )
    db = FakeDB([None, None, None, None, None, None, defaults_row])
    refs = await _provider_references(db, {"prv_doc_1"})
    assert "cấu hình xử lý tài liệu" in refs
