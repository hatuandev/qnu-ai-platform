"""HTTP and scoped lookup regressions for compact workspace links."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qnu.api.dependencies import get_actor, get_db
from qnu.api.handlers import register_exception_handlers
from qnu.domains.identity.actor import AuthActor
from qnu.domains.workspaces import navigation
from qnu.domains.workspaces.router import router
from qnu.platform.errors import EntityNotFound


def result(value):
    output = MagicMock()
    output.scalar_one_or_none.return_value = value
    output.scalars.return_value.first.return_value = value
    return output


@pytest.mark.asyncio
async def test_authorization_failure_does_not_lookup_source(monkeypatch):
    db = SimpleNamespace(execute=AsyncMock(return_value=result(SimpleNamespace(id="ws"))))
    guard = AsyncMock(side_effect=EntityNotFound("Không tìm thấy workspace."))
    monkeypatch.setattr(navigation, "resolve_workspace_access", guard)
    with pytest.raises(EntityNotFound):
        await navigation.resolve_navigation(db, AuthActor(username="test"), "ctsv", "other")
    assert db.execute.await_count == 1
    guard.assert_awaited_once()


def test_http_resolver_uses_access_and_source_lifecycle_guards(monkeypatch):
    workspace = SimpleNamespace(id="ws", code="ctsv")
    source = SimpleNamespace(id="src", collection_id="col")
    db = SimpleNamespace(execute=AsyncMock(side_effect=[result(workspace), result(source)]))
    guard = AsyncMock(return_value=workspace)
    source_guard = AsyncMock(return_value=source)
    monkeypatch.setattr(navigation, "resolve_workspace_access", guard)
    monkeypatch.setattr(navigation, "load_collection", AsyncMock())
    monkeypatch.setattr(navigation, "load_source", source_guard)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    actor = AuthActor(username="test")
    app.dependency_overrides[get_actor] = lambda: actor
    with TestClient(app) as client:
        response = client.get("/workspaces/resolve-route?code=ctsv&source_id=src")
    assert response.status_code == 200
    assert response.json() == {"workspace_id": "ws", "code": "ctsv", "collection_id": "col"}
    guard.assert_awaited_once_with(db, actor, "ws")
    source_guard.assert_awaited_once_with(db, "ws", "col", "src")
    statement = db.execute.await_args_list[1].args[0]
    assert "kb_sources.workspace_id" in str(statement)


@pytest.mark.asyncio
async def test_source_outside_workspace_is_not_resolved(monkeypatch):
    workspace = SimpleNamespace(id="ws", code="ctsv")
    db = SimpleNamespace(execute=AsyncMock(side_effect=[result(workspace), result(None)]))
    monkeypatch.setattr(navigation, "resolve_workspace_access", AsyncMock(return_value=workspace))
    with pytest.raises(EntityNotFound):
        await navigation.resolve_navigation(db, AuthActor(username="test"), "ctsv", "foreign")


@pytest.mark.parametrize(
    ("status", "membership", "expected"),
    [("active", None, 404), ("suspended", SimpleNamespace(role="member"), 403)],
)
def test_http_real_access_guard_blocks_nonmember_and_suspension(status, membership, expected):
    workspace = SimpleNamespace(id="ws", code="ctsv", status=status)
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[result(workspace), result(workspace), result(membership)])
    )
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_actor] = lambda: AuthActor(username="test", actor_id="reader")
    with TestClient(app) as client:
        response = client.get("/workspaces/resolve-route?code=ctsv&source_id=foreign")
    assert response.status_code == expected
    assert db.execute.await_count == 3
    assert "collection_id" not in response.json()
