"""Unit tests for per-turn chat model override resolution and schema validation."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.conversations.execution import _resolve_turn_provider_id
from qnu.domains.conversations.schemas import TurnRequest
from qnu.domains.identity.actor import AuthActor
from qnu.platform.errors import Conflict, EntityNotFound


def _actor() -> AuthActor:
    return AuthActor(
        actor_id="usr_test",
        username="tester",
        email="tester@qnu.edu.vn",
        name="Tester",
        roles=("workspace_member",),
        permissions=(),
    )


def _provider(
    pid: str,
    model_name: str,
    *,
    capabilities: list[str] | None = None,
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        model_name=model_name,
        capabilities=capabilities if capabilities is not None else ["chat"],
        is_active=is_active,
    )


def test_turn_request_normalizes_optional_model_fields():
    req = TurnRequest(question="  Xin chào  ", expected_turn_no=0, model="  ", provider_id="")
    assert req.question == "Xin chào"
    assert req.model is None
    assert req.provider_id is None

    req_model = TurnRequest(question="Soạn kế hoạch", expected_turn_no=1, model=" prv_luna ")
    assert req_model.model == "prv_luna"


@pytest.mark.asyncio
async def test_resolve_turn_provider_id_falls_back_to_assistant_default_when_omitted(monkeypatch):
    visible_mock = AsyncMock()
    monkeypatch.setattr(
        "qnu.domains.conversations.execution.catalog_service.visible_providers", visible_mock
    )

    for selector in (None, "default", "__default__", "DEFAULT"):
        req = TurnRequest(question="Hỏi", expected_turn_no=0, model=selector)
        provider_id, requested = await _resolve_turn_provider_id(
            None, _actor(), "ws_1", req, "prv_assistant_default"
        )
        assert provider_id == "prv_assistant_default"
        assert requested is None

    visible_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_turn_provider_id_prefers_valid_provider_id(monkeypatch):
    luna = _provider("prv_luna", "9router-luna")
    other = _provider("prv_gemini", "gemini-2.5-flash")
    monkeypatch.setattr(
        "qnu.domains.conversations.execution.catalog_service.visible_providers",
        AsyncMock(return_value=[other, luna]),
    )
    require_mock = AsyncMock(return_value=luna)
    monkeypatch.setattr(
        "qnu.domains.conversations.execution.provider_service.require_capability",
        require_mock,
    )

    req = TurnRequest(question="Soạn kế hoạch", expected_turn_no=0, model="prv_luna")
    provider_id, requested = await _resolve_turn_provider_id(
        None, _actor(), "ws_1", req, "prv_gemini"
    )
    assert provider_id == "prv_luna"
    assert requested == "prv_luna"
    require_mock.assert_awaited_once_with(None, "prv_luna", "chat")


@pytest.mark.asyncio
async def test_resolve_turn_provider_id_matches_model_name(monkeypatch):
    luna = _provider("prv_luna", "luna")
    embed = _provider("prv_embed", "luna", capabilities=["embedding"])
    monkeypatch.setattr(
        "qnu.domains.conversations.execution.catalog_service.visible_providers",
        AsyncMock(return_value=[embed, luna]),
    )
    require_mock = AsyncMock(return_value=luna)
    monkeypatch.setattr(
        "qnu.domains.conversations.execution.provider_service.require_capability",
        require_mock,
    )

    req = TurnRequest(question="Soạn kế hoạch", expected_turn_no=0, model="luna")
    provider_id, requested = await _resolve_turn_provider_id(
        None, _actor(), "ws_1", req, None
    )
    assert provider_id == "prv_luna"
    assert requested == "luna"
    require_mock.assert_awaited_once_with(None, "prv_luna", "chat")


@pytest.mark.asyncio
async def test_resolve_turn_provider_id_rejects_unknown_or_non_chat_model(monkeypatch):
    embed = _provider("prv_embed", "bge-m3", capabilities=["embedding"])
    monkeypatch.setattr(
        "qnu.domains.conversations.execution.catalog_service.visible_providers",
        AsyncMock(return_value=[embed]),
    )

    monkeypatch.setattr(
        "qnu.domains.conversations.execution.provider_service.require_capability",
        AsyncMock(side_effect=EntityNotFound("Không tìm thấy provider.", code="provider_not_found")),
    )
    with pytest.raises(EntityNotFound):
        await _resolve_turn_provider_id(
            None,
            _actor(),
            "ws_1",
            TurnRequest(question="Hi", expected_turn_no=0, model="prv_missing"),
            "prv_default",
        )

    monkeypatch.setattr(
        "qnu.domains.conversations.execution.provider_service.require_capability",
        AsyncMock(
            side_effect=Conflict(
                "Provider không có capability 'chat'.", code="provider_capability_mismatch"
            )
        ),
    )
    with pytest.raises(Conflict):
        await _resolve_turn_provider_id(
            None,
            _actor(),
            "ws_1",
            TurnRequest(question="Hi", expected_turn_no=0, model="prv_embed"),
            "prv_default",
        )
