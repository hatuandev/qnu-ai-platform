"""Ownership and output-pair failures must not publish stale results."""

import asyncio
from contextlib import asynccontextmanager, nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from qnu.domains.knowledge.compilation import execution as compiler
from qnu.domains.knowledge.compilation import outputs
from qnu.domains.knowledge.compilation.review import execution
from qnu.domains.modelops.resilience import execution as modelops
from qnu.platform.errors import AppException, Conflict
from qnu.ports.chat_model import ChatRequest


@pytest.mark.asyncio
async def test_model_completion_budget_starts_after_queue_and_keeps_uncertain_outcome(monkeypatch):
    @asynccontextmanager
    async def queue(request):
        await asyncio.sleep(0.02)
        yield

    monkeypatch.setattr(modelops, "chat_slot", queue)
    request = ChatRequest(
        "http://model",
        "model",
        8192,
        0.01,
        "",
        wait_for_completion=True,
        enforce_completion_timeout=True,
    )
    executor = modelops.CredentialExecutor()
    quick = AsyncMock(return_value="completed")
    assert await executor.call("chat", request, quick) == "completed"

    async def stuck(request):
        await asyncio.Event().wait()

    slow = AsyncMock(side_effect=stuck)
    with pytest.raises(AppException) as exhausted:
        await executor.call("chat", request, slow)
    assert exhausted.value.code == "chat_provider_uncertain"
    slow.assert_awaited_once()


@pytest.mark.asyncio
async def test_segmented_compiler_releases_parent_connection_before_child_sessions(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    run = SimpleNamespace(id="run", config={})
    segment = SimpleNamespace(id="part", segment_index=1, status="pending")
    monkeypatch.setattr(compiler, "_segments", AsyncMock(return_value=[segment]))
    monkeypatch.setattr(compiler, "_verify_manifest", AsyncMock())
    monkeypatch.setattr(compiler, "_resume_segment", AsyncMock())
    monkeypatch.setattr(compiler, "_mark_uncertain_segments", AsyncMock())
    partial = AsyncMock()
    monkeypatch.setattr(compiler, "_write_partial", partial)
    monkeypatch.setattr(compiler, "_finalize_segmented", AsyncMock(return_value="completed"))

    async def execute_children(*args, **kwargs):
        db.commit.assert_awaited_once()
        segment.status = "completed"
        return []

    monkeypatch.setattr(compiler, "_run_parts", execute_children)
    assert await compiler._compile_segmented(db, None, run, [], None) == "completed"
    partial.assert_awaited_once_with(db, None, run, [], force=True)


@pytest.mark.asyncio
async def test_partial_output_throttles_merges_and_flushes_new_completed_parts(monkeypatch):
    db = SimpleNamespace(commit=AsyncMock())
    run = SimpleNamespace(id="run", config={}, selective_supplement=False)
    first = SimpleNamespace(id="first", status="completed", segment_index=1)
    second = SimpleNamespace(id="second", status="completed", segment_index=2)
    latest = SimpleNamespace(
        created_at=compiler.utcnow(), coverage={"completed_node_ids": [first.id]}
    )
    monkeypatch.setattr(outputs, "latest", AsyncMock(return_value=latest))
    monkeypatch.setattr(compiler, "_segments", AsyncMock(return_value=[first, second]))
    read_parts = AsyncMock(return_value=[])
    monkeypatch.setattr(compiler, "_completed_parts", read_parts)
    monkeypatch.setattr(compiler, "_merged_draft", AsyncMock(return_value={}))
    monkeypatch.setattr(compiler.split, "partial_markdown", Mock(return_value=b"draft"))
    monkeypatch.setattr(compiler, "commit_owned", AsyncMock())
    store_output = AsyncMock()
    monkeypatch.setattr(outputs, "store_output", store_output)

    await compiler._write_partial(db, None, run, [])
    read_parts.assert_not_awaited()
    await compiler._write_partial(db, None, run, [], force=True)
    read_parts.assert_awaited_once()
    latest.coverage = store_output.await_args.kwargs["coverage"]
    assert latest.coverage["completed_node_ids"] == [first.id, second.id]

    await compiler._write_partial(db, None, run, [], force=True)
    store_output.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_run_reconciles_every_interrupted_part_before_returning(monkeypatch):
    db = SimpleNamespace()
    run = SimpleNamespace(id="run", config={})
    parts = [
        SimpleNamespace(id=f"part-{index}", status="running", error_code=None) for index in (1, 2)
    ]
    monkeypatch.setattr(compiler, "_segments", AsyncMock(return_value=parts))
    monkeypatch.setattr(compiler, "_verify_manifest", AsyncMock())
    provider_jobs = AsyncMock()
    monkeypatch.setattr(compiler, "_run_parts", provider_jobs)
    finish = AsyncMock(return_value="uncertain")
    monkeypatch.setattr(compiler, "_finish_segment_problem", finish)

    async def recover(db, blob, run, part):
        part.status = "uncertain"
        part.error_code = "compilation_request_interrupted"

    monkeypatch.setattr(compiler, "_resume_segment", recover)
    assert await compiler._compile_segmented(db, None, run, [], None) == "uncertain"
    assert [p.status for p in parts] == ["uncertain", "uncertain"]
    finish.assert_awaited_once_with(
        db, None, run, [], parts, "uncertain", "compilation_request_interrupted"
    )
    provider_jobs.assert_not_called()


@pytest.mark.asyncio
async def test_review_checkpoint_refuses_a_superseded_execution(monkeypatch):
    db = SimpleNamespace(no_autoflush=nullcontext())
    row = SimpleNamespace(trace={"execution_token": "old"})

    async def refreshed(*args):
        row.trace = {"execution_token": "new"}

    monkeypatch.setattr(execution.service, "checkpoint", refreshed)
    provider = AsyncMock()
    monkeypatch.setattr(execution, "require_provider", provider)
    with pytest.raises(Conflict) as error:
        await execution._owned_checkpoint(db, None, None, row, None, "old")
    assert error.value.code == "compilation_review_claim_lost"
    provider.assert_not_called()


@pytest.mark.asyncio
async def test_failed_markdown_write_keeps_old_output_pointer(monkeypatch):
    db = SimpleNamespace(scalar=AsyncMock(return_value=1), add=Mock(), flush=AsyncMock())
    run = SimpleNamespace(id="run_one", workspace_id="ws_one", output_id="previous")
    put = AsyncMock(side_effect=[("sha_json", 10), RuntimeError("storage failed")])
    monkeypatch.setattr(outputs, "_put_verified", put)
    with pytest.raises(RuntimeError, match="storage failed"):
        await outputs.store_output(
            db,
            None,
            run,
            draft_payload=b"{}",
            markdown_payload=b"text",
            coverage={},
            partial=False,
        )
    assert run.output_id == "previous"
    db.add.assert_not_called()
    db.flush.assert_not_called()
