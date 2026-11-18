"""Regressions for claim fencing and single-call reasoning (no model/DB I/O)."""

import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.compilation import execution
from qnu.domains.knowledge.compilation.drafting import SYSTEM_PROMPT
from qnu.domains.knowledge.compilation.lease import ClaimLost
from qnu.domains.modelops.reasoning import ReasoningDirective
from qnu.platform.errors import AppException, Conflict
from qnu.ports.chat_model import ChatResponseError


@pytest.mark.asyncio
async def test_lost_claim_settles_usage_but_cannot_write_error_artifacts(monkeypatch):
    settle, store, commit = AsyncMock(), AsyncMock(), AsyncMock()
    monkeypatch.setattr(execution, "_settle_part_usage", settle)
    monkeypatch.setattr(execution, "assert_claim", AsyncMock(side_effect=ClaimLost))
    monkeypatch.setattr(execution, "store_segment", store)
    monkeypatch.setattr(execution, "commit_owned", commit)
    part = SimpleNamespace(status="running", usage_tokens=None)
    error = ChatResponseError(AppException("truncated", code="chat_output_truncated"), b"raw", 123)
    with pytest.raises(ClaimLost):
        await execution._record_segment_error(None, None, None, part, "usage", error)
    settle.assert_awaited_once_with("usage", 123, failed=True)
    store.assert_not_called()
    commit.assert_not_called()
    assert part.status == "running" and part.usage_tokens is None


@pytest.mark.asyncio
async def test_recovery_cannot_downgrade_observed_usage_to_unknown(monkeypatch):
    accounting = SimpleNamespace(
        rollback=AsyncMock(), get=AsyncMock(return_value=SimpleNamespace(status="failed")),
    )

    class Session:
        async def __aenter__(self):
            return accounting

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(execution, "AsyncSessionFactory", Session)
    settle = AsyncMock(side_effect=Conflict("observed", code="usage_already_settled"))
    monkeypatch.setattr(execution.usage_service, "settle", settle)
    await execution._settle_part_usage("usage", None, failed=True)
    settle.assert_awaited_once_with(accounting, "usage", total_tokens=None, failed=True)
    accounting.rollback.assert_awaited_once()
    accounting.get.assert_awaited_once()
    # A contradictory measured result still fails; only unknown may be ignored.
    with pytest.raises(Conflict):
        await execution._settle_part_usage("usage", 124, failed=True)


@pytest.mark.asyncio
async def test_single_call_compiler_passes_the_pinned_reasoning(monkeypatch):
    directive = ReasoningDirective("toggle", "thinking", False, "off", "policy")
    runtime = SimpleNamespace(
        configuration_hash="provider", reasoning_directive=lambda: directive
    )
    request, budget = object(), SimpleNamespace(total_reserved_tokens=100)
    prepare = AsyncMock(return_value=(runtime, request, budget))
    monkeypatch.setattr(execution, "prepare_chat_request", prepare)
    monkeypatch.setattr(execution, "assert_claim", AsyncMock())
    monkeypatch.setattr(execution, "commit_owned", AsyncMock())
    monkeypatch.setattr(execution.usage_service, "reserve", AsyncMock(return_value=SimpleNamespace(id="usage")))
    monkeypatch.setattr(execution, "bind_usage", lambda req, usage: req)
    model = SimpleNamespace(complete=AsyncMock(side_effect=RuntimeError("stop at dispatch")))
    run = SimpleNamespace(
        id="run", workspace_id="ws", provider_id="provider",
        topic="Ngưỡng 2026", request_hash="request",
        config={
            "max_output_tokens": 8192, "provider": {"configuration_hash": "provider"},
            "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
            "reasoning_directive": directive.public_dict(),
        },
    )
    with pytest.raises(RuntimeError, match="stop at dispatch"):
        await execution._call(None, None, run, None, [], model)
    assert prepare.await_args.kwargs["task"] == "compiler"
    assert prepare.await_args.kwargs["reasoning"] == directive
    model.complete.assert_awaited_once()
