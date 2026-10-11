"""Selected-source vector loading must not index a different Markdown revision."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.schemas import VectorLoadItem, VectorLoadRequest
from app.modules.knowledge.services import vector_load_service as loader
from app.modules.knowledge.services.vector_generation_service import vector_generation_service


@pytest.mark.asyncio
async def test_build_rejects_changed_markdown_before_chunking():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(
        status="active", active_source_revision=SimpleNamespace(id="new", status="ready")
    )
    db.execute.return_value = result
    with patch(
        "app.modules.knowledge.services.vector_generation_service.get_scoped_collection",
        AsyncMock(return_value=SimpleNamespace(id="col")),
    ), patch(
        "app.modules.knowledge.services.vector_generation_service.chunk_set_service.get_or_create_chunk_set",
        AsyncMock(),
    ) as chunks:
        with pytest.raises(AppException) as error:
            await vector_generation_service.build_generation_for_source(
                db, "col", "source", "gen", expected_source_revision_id="old"
            )
        assert error.value.code == "SOURCE_REVISION_CHANGED"
        chunks.assert_not_awaited()


def request(*items):
    return VectorLoadRequest(generation_id="gen", items=[
        VectorLoadItem(binding_id=binding, source_revision_id=revision)
        for binding, revision in (items or [("source", "revision")])
    ])


def session():
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.side_effect = [SimpleNamespace(status="active", active_source_revision_id="revision", chunk_strategy="ClauseBasedChunker"), None]
    db.get.return_value = SimpleNamespace(binding_id="source", status="ready")

    async def commit():
        for call in db.add.call_args_list:
            call.args[0].id = "job"
            call.args[0].dispatch_status = "pending"
    db.commit.side_effect = commit
    return db


@pytest.fixture
def queue_dependencies():
    with (
        patch.object(loader, "get_scoped_collection", AsyncMock(return_value=SimpleNamespace(id="col", tenant_id="tenant", workspace_id="workspace"))),
        patch.object(vector_generation_service, "get_vector_generation", AsyncMock(return_value=SimpleNamespace(status="building"))),
        patch.object(loader, "enqueue_arq_job", AsyncMock(return_value="broker")) as enqueue,
    ):
        yield enqueue


@pytest.mark.asyncio
async def test_selected_source_job_pins_revision_and_never_publishes(queue_dependencies):
    db = session()
    jobs = await loader.queue_vector_load(db, "col", request(), None)
    assert len(jobs) == 1
    assert jobs[0].payload == {"binding_id": "source", "source_revision_id": "revision", "generation_id": "gen", "chunk_strategy": "ClauseBasedChunker"}
    assert jobs[0].tenant_id == "tenant"
    queue_dependencies.assert_awaited_once()
    assert queue_dependencies.call_args.args[:2] == ("task_knowledge_index_build", "job")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid,code", [
    ("stale", "SOURCE_REVISION_CHANGED"), ("review", "SOURCE_REVISION_NOT_READY"),
    ("scope", "SOURCE_NOT_FOUND"), ("duplicate", "DUPLICATE_SOURCE_SELECTION"),
    ("busy", "SOURCE_INDEX_BUSY"),
])
async def test_invalid_selection_never_dispatches(invalid, code, queue_dependencies):
    db = session()
    selection = request()
    if invalid == "stale":
        db.get.return_value = None
    elif invalid == "review":
        db.get.return_value.status = "review_required"
    elif invalid == "scope":
        db.scalar.side_effect = [None]
    elif invalid == "duplicate":
        selection = request(("source", "revision"), ("source", "revision"))
    elif invalid == "busy":
        db.scalar.side_effect = [SimpleNamespace(status="active", active_source_revision_id="revision"), SimpleNamespace(payload={"generation_id": "other"})]
    with pytest.raises(AppException) as error:
        await loader.queue_vector_load(db, "col", selection, None)
    assert error.value.code == code
    db.commit.assert_not_awaited()
    queue_dependencies.assert_not_awaited()


@pytest.mark.asyncio
async def test_pending_same_revision_reuses_job(queue_dependencies):
    db = session()
    existing = SimpleNamespace(payload={"generation_id": "gen", "source_revision_id": "revision"}, dispatch_status="dispatched")
    db.scalar.side_effect = [SimpleNamespace(status="active", active_source_revision_id="revision"), existing]
    assert await loader.queue_vector_load(db, "col", request(), None) == [existing]
    db.add.assert_not_called()
    queue_dependencies.assert_not_awaited()


@pytest.mark.asyncio
async def test_queue_offline_preserves_pending_job_without_fake_success(queue_dependencies):
    db = session()
    queue_dependencies.return_value = None
    jobs = await loader.queue_vector_load(db, "col", request(), None)
    assert jobs[0].status == "queued"
    assert jobs[0].dispatch_status == "pending"
    assert "hàng đợi" in jobs[0].error


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_after_build", [False, True])
async def test_worker_uses_new_generation_and_preserves_active_index(cancel_after_build):
    from app.workers import tasks

    db = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = db
    job = SimpleNamespace(id="job", collection_id="col", payload={"binding_id": "source", "source_revision_id": "revision", "generation_id": "gen"})
    index = SimpleNamespace(id="index", status="active", failure_detail=None, chunk_count=3, fact_count=0, parity_report={"parity_passed": True})
    with (
        patch.object(tasks, "AsyncSessionFactory", MagicMock(return_value=cm)),
        patch.object(tasks, "_load_job", AsyncMock(return_value=job)),
        patch.object(tasks, "_check_pre_execution_cancelled", AsyncMock(return_value=False)),
        patch.object(tasks, "_is_cancelled", AsyncMock(side_effect=[False, cancel_after_build])),
        patch.object(tasks, "_set_job", AsyncMock(return_value=True)) as update,
        patch.object(vector_generation_service, "build_generation_for_source", AsyncMock(return_value=index)) as build,
        patch("app.modules.knowledge.services.index_build_service.index_build_service.build_staging_index", AsyncMock()) as legacy,
    ):
        result = await tasks.task_knowledge_index_build({}, "job")
    assert result["status"] == ("cancelled" if cancel_after_build else "completed")
    assert index.status == "active"
    assert build.call_args.kwargs["expected_source_revision_id"] == "revision"
    legacy.assert_not_awaited()
    if not cancel_after_build:
        assert update.call_args.kwargs["result"]["parity_passed"] is True


@pytest.mark.asyncio
async def test_state_queries_compile_with_cyclic_binding_index_foreign_keys(queue_dependencies):
    from sqlalchemy.dialects import postgresql

    db = AsyncMock()
    async def scalars(statement):
        statement.compile(dialect=postgresql.dialect())
        result = MagicMock()
        result.all.return_value = []
        return result
    db.scalars.side_effect = scalars
    assert await loader.get_vector_load_state(db, "col", None) == {"jobs": [], "indexes": []}
