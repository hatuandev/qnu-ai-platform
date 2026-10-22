"""Wiki navigation changes selection, never source scope or citation authority."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.wiki_schemas import WikiReadAction
from app.modules.rag.evidence_schemas import EvidenceBlock, QueryPlan
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot
from app.modules.rag.wiki_context import execute_read, read_wiki_context, section_matches


def block(uid="one", source="revision-a", text="PT4: mã 402B, năm 2025."):
    return EvidenceBlock(id=f"{source}:{uid}", unit_id=uid, binding_id="binding-a",
        index_revision_id="index-a", source_revision_id=source, title="Tuyển sinh",
        text=text, start=0, end=len(text), canonical_hash="hash-a")


def page():
    return {"id": "page-a", "title": "Phương thức tuyển sinh", "kind": "concept",
        "markdown": "# Phương thức\n\nNăm dữ liệu: 2025\n\nPT4: mã 402B.",
        "block_ids": ["revision-a:one"], "binding_id": "binding-a",
        "source_revision_id": "revision-a", "sections": []}


@pytest.mark.asyncio
async def test_model_opens_page_then_reads_original_source_and_only_returns_canonical_blocks():
    first, extra = block(), block("extra", text="Chỉ áp dụng khi có điều kiện bổ sung.")
    req = AskRequest(collection_id="collection-a", question="Phương thức năm 2025?")
    snap = RetrievalSnapshot(snapshot_id="snapshot", collection_id="collection-a",
        binding_revisions={"binding-a": "index-a"}, knowledge_wiki_enabled=True)
    source_page = {**page(), "block_ids": [first.id, extra.id]}
    actions = AsyncMock(return_value=WikiReadAction(action="read_pages", page_ids=["page-a"]))
    with patch("app.modules.rag.wiki_context.load_wiki_pages", AsyncMock(return_value=[source_page])), \
         patch("app.modules.rag.wiki_context.structured_call", actions):
        selected = await read_wiki_context(None, req, snap, QueryPlan(query=req.question, years=[2025]),
            [first, extra], candidate_mode=False)
        repeated = await read_wiki_context(None, req, snap, QueryPlan(query=req.question, years=[2025]),
            [first, extra], candidate_mode=False)
    assert selected == [first, extra] == repeated
    assert actions.await_count == 1
    assert all(item.origin == "canonical" for item in selected)
    assert actions.await_args.args[4]["catalog"][0]["page_id"] == "page-a"
    assert req._wiki_context["pages"][0]["usage"] == "navigation_only"
    assert req._retrieval_diagnostics["knowledge_wiki"]["calls"] == 1


@pytest.mark.parametrize("action", [
    WikiReadAction(action="read_pages", page_ids=["../../private"]),
    WikiReadAction(action="read_source", page_ids=["page-a"], unit_ids=["revision-b:private"]),
    WikiReadAction(action="read_source", page_ids=["unopened-page"], unit_ids=["revision-a:one"]),
])
def test_tool_rejects_unknown_page_and_foreign_or_unopened_source(action):
    own, foreign = block(), block("private", source="revision-b")
    with pytest.raises(AppException):
        execute_read(action, {"page-a": page()}, {"page-a": page()}, {own.id: own, foreign.id: foreign}, 14000)


def test_page_budget_never_slices_conditions_or_source_evidence():
    opened = {}
    result, spent = execute_read(WikiReadAction(action="read_pages", page_ids=["page-a"]),
        {"page-a": page()}, opened, {block().id: block()}, 10)
    assert result == [] and spent == 0 and not opened


@pytest.mark.parametrize("role,requested,expected", [
    ("data", [2024], False), ("data", [2025], True),
    ("publication", [2023], False), ("publication", [2025], True),
    ("event", [2024], False),
])
def test_year_filter_uses_role_instead_of_source_filename_or_publication(role, requested, expected):
    section = {"temporal": [{"role": role, "years": [2025]}]}
    plan = QueryPlan(query="Q", **{{"data": "years", "publication": "document_years", "event": "event_years"}[role]: requested})
    assert section_matches(section, plan) is expected
    if role == "publication":
        assert section_matches(section, QueryPlan(query="Q", years=[2024]))  # Not a DATA-year override.


@pytest.mark.asyncio
async def test_historical_snapshot_without_wiki_makes_no_additional_calls():
    req = AskRequest(collection_id="collection-a", question="Q")
    snap = RetrievalSnapshot(snapshot_id="s", collection_id="collection-a")
    with patch("app.modules.rag.wiki_context.load_wiki_pages", AsyncMock()) as load:
        assert await read_wiki_context(None, req, snap, QueryPlan(query="Q"), [block()], candidate_mode=False) == []
    load.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("selected_items", [False, True])
@pytest.mark.parametrize("report,enabled", [({}, False), ({"knowledge_wiki": None}, False),
                                          ({"knowledge_wiki": {"status": "ready"}}, True)])
async def test_candidate_snapshot_accepts_legacy_optional_wiki_without_changing_source_scope(
        monkeypatch, selected_items, report, enabled):
    from app.modules.knowledge.services.generation_candidate import resolve_candidate_snapshot

    collection = SimpleNamespace(id="collection-a", index_epoch=1, tenant_id="tenant_qnu", workspace_id=None)
    binding = SimpleNamespace(id="binding-a", active_index_revision_id="index-a", active_source_revision_id="source-a")
    index = SimpleNamespace(id="index-a", binding_id=binding.id, parity_report=report)
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(id="generation-a", collection_id=collection.id)
    binding_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [binding]))
    index_result = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: index))
    db.execute.side_effect = [binding_result, index_result]
    monkeypatch.setattr("app.modules.knowledge.services.scope_helper.get_scoped_collection",
                        AsyncMock(return_value=collection))
    monkeypatch.setattr("app.modules.knowledge.services.generation_candidate.validate_candidate_artifacts", AsyncMock())
    monkeypatch.setattr("app.modules.knowledge.services.selected_vector_publish.resolve_selected_publication",
        AsyncMock(return_value=SimpleNamespace(collection=collection, bindings=[binding], indexes={binding.id: index})))
    snapshot = await resolve_candidate_snapshot(db, collection.id, "generation-a", None,
                                                items=[] if selected_items else None)
    assert snapshot.knowledge_wiki_enabled is enabled
    assert snapshot.binding_revisions == {binding.id: index.id}
    assert snapshot.vector_generations == {binding.id: "generation-a"}


@pytest.mark.asyncio
async def test_same_request_budget_does_not_restart_for_another_year_or_corrective_pass():
    req = AskRequest(collection_id="collection-a", question="Q")
    snap = RetrievalSnapshot(snapshot_id="s", collection_id="collection-a", knowledge_wiki_enabled=True)
    req._retrieval_diagnostics["knowledge_wiki"] = {"calls": 2, "actions": []}
    req._wiki_context.update(key="old-year", pages=[{"markdown": "Năm 2024"}], block_ids=[block().id])
    with patch("app.modules.rag.wiki_context.load_wiki_pages", AsyncMock()) as load:
        assert await read_wiki_context(None, req, snap, QueryPlan(query="Q", years=[2025]),
            [block()], candidate_mode=False) == []
    assert not req._wiki_context
    load.assert_not_awaited()


@pytest.mark.asyncio
async def test_page_loader_rejects_index_outside_snapshot_and_source_revision_mixup():
    from app.modules.rag.wiki_context import load_wiki_pages
    req = SimpleNamespace(binding_revisions={"binding-a": "index-a"}, collection_id="collection-a")
    source = SimpleNamespace(id="revision-b", binding_id="binding-b")
    index = SimpleNamespace(id="index-a", parity_report={"knowledge_wiki": {"pages": []}})
    binding = SimpleNamespace(id="binding-a")
    db = AsyncMock()
    db.execute.return_value.all = lambda: [(source, index, binding)]
    with patch("app.modules.rag.wiki_context.validate_wiki_bundle") as validate:
        assert await load_wiki_pages(db, req, [block()], QueryPlan(query="Q"), False) == []
    validate.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("allowed", [False, True])
async def test_revision_pages_http_handler_checks_permission_and_never_compiles(monkeypatch, allowed):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.modules.auth.dependencies import get_current_actor
    from app.modules.auth.schemas import AuthActor
    from app.modules.knowledge.wiki_router import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_current_actor] = lambda: AuthActor(username="wiki-reader",
        permissions=["ai.knowledge.view"] if allowed else [])
    @app.exception_handler(AppException)
    async def handle(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"code": exc.code})
    view = AsyncMock(return_value={"status": "pending", "pages": []})
    monkeypatch.setattr("app.modules.knowledge.wiki_router.read_revision_pages", view)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/collections/c/sources/b/revisions/r/knowledge-pages")
    assert response.status_code == (200 if allowed else 403)
    if allowed:
        assert view.await_args.args[1:4] == ("c", "b", "r")
    else:
        view.assert_not_awaited()
