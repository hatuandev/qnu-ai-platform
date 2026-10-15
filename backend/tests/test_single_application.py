"""Single-application API migration keeps RBAC and immutable resource boundaries."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AppException
from app.core.redis import SemanticCache
from app.core.single_application import LEGACY_TENANT, LEGACY_WORKSPACE
from app.main import app
from app.modules.auth.dependencies import get_current_actor
from app.modules.auth.schemas import AuthActor
from app.modules.knowledge.services.scope_helper import get_scoped_collection
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


def test_legacy_scope_input_is_ignored_and_not_serialized():
    actor = AuthActor(username="viewer", tenant_id="untrusted", workspace_id="untrusted")
    request = AskRequest(question="Chính sách?", collection_id="col", tenant_id="untrusted",
                         workspace_id="untrusted")
    for value in (actor, request):
        assert not {"tenant_id", "workspace_id"}.intersection(value.model_dump())
        assert value.tenant_id == LEGACY_TENANT and value.workspace_id == LEGACY_WORKSPACE
    assert not actor.has_permission("ai.knowledge.update")


def test_public_openapi_has_no_tenant_workspace_fields_or_parameters():
    schema = app.openapi()
    for name, definition in schema["components"]["schemas"].items():
        assert not {"tenant_id", "workspace_id"}.intersection(definition.get("properties", {})), name
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            assert not any(parameter["name"] in {"tenant_id", "workspace_id"}
                           for parameter in operation.get("parameters", [])), path


def test_cache_ignores_legacy_namespaces_but_keeps_collection_policy_and_snapshot():
    cache = SemanticCache(client=MagicMock())
    baseline = cache._make_key("col", "question", tenant_id="a", workspace_id="a")
    assert baseline == cache._make_key("col", "question", tenant_id="b", workspace_id="b")
    assert baseline != cache._make_key("other", "question")
    assert baseline != cache._make_key("col", "question", snapshot_fingerprint="revision2")
    assert baseline != cache._make_key("col", "question", policy_version="glossary-v2")
    assert baseline.startswith("rag:cache:app-v1:col:")


@pytest.mark.asyncio
async def test_collection_lookup_keeps_exact_id_not_legacy_partition():
    row = SimpleNamespace(id="col", tenant_id="old", workspace_id="old")
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    actor = AuthActor(username="viewer", permissions=["ai.knowledge.view"])
    assert await get_scoped_collection(db, "col", actor) is row
    sql = str(db.execute.call_args.args[0].compile(dialect=postgresql.dialect(),
                                                  compile_kwargs={"literal_binds": True}))
    where = sql.split("WHERE", 1)[1]
    assert "knowledge_collections.id = 'col'" in where
    assert "tenant_id" not in where and "workspace_id" not in where
    result.scalar_one_or_none.return_value = None
    with pytest.raises(AppException) as exc:
        await get_scoped_collection(db, "missing", actor)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_snapshot_rejects_other_collection_even_without_partitions():
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(id="col", index_epoch=1, collection_metadata={})
    result = MagicMock()
    result.all.return_value = []
    db.execute.return_value = result
    pinned = RetrievalSnapshot(snapshot_id="s", collection_id="other")
    with pytest.raises(AppException) as exc:
        await hybrid_retriever.resolve_retrieval_snapshot(db, "col", pinned_snapshot=pinned)
    assert exc.value.code == "STALE_RETRIEVAL_SNAPSHOT"


@pytest.mark.asyncio
async def test_glossary_write_still_requires_server_permission():
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_actor] = lambda: AuthActor(username="viewer", permissions=[])
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/platform/v1alpha1/knowledge/collections/col/glossary",
                                         json={"user_phrase": "học bạ", "target_term": "kết quả học tập",
                                               "tenant_id": "admin", "workspace_id": "admin"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
