"""Ownership and output-pair failures must not publish stale results."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from qnu.domains.knowledge.compilation import outputs
from qnu.domains.knowledge.compilation.review import execution
from qnu.platform.errors import Conflict


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
            db, None, run, draft_payload=b"{}", markdown_payload=b"text",
            coverage={}, partial=False,
        )
    assert run.output_id == "previous"
    db.add.assert_not_called()
    db.flush.assert_not_called()
