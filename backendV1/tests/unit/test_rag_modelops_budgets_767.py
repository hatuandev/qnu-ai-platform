"""Budget boundaries and usage settlement; no external provider or database."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.compilation.models import utcnow
from qnu.domains.knowledge.compilation.review import refinement
from qnu.domains.knowledge.index import hybrid
from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.domains.modelops.public_api import ChatRuntime
from qnu.domains.modelops.reasoning import ReasoningPolicy
from qnu.domains.rag.answer.context import evidence_size, expand_context
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.platform.errors import AppException


def hit(text="Short evidence", kind="paragraph"):
    return SearchHit(
        chunk_id="chunk",
        document_id="document",
        version_id="version",
        publication_decision_id="decision",
        score=1,
        kind=kind,
        text=text,
        citations={},
        structure=None,
    )


def result(hits):
    return SearchResponse(
        index_run_id="index",
        generation=1,
        status="results",
        hits=hits,
        eligible_documents=1,
    )


@pytest.mark.asyncio
async def test_window_zero_still_rejects_oversized_primary_evidence():
    with pytest.raises(AppException) as caught:
        await expand_context(
            None,
            None,
            None,
            "workspace",
            "collection",
            result([hit("A" * 10000)]),
            AnswerRequest(question="Question", context_max_bytes=256, context_window=0),
        )
    assert caught.value.code == "answer_context_budget_exceeded"


@pytest.mark.asyncio
async def test_window_zero_records_bounded_bytes_and_keeps_whole_evidence():
    # Paragraph hits need DB-backed clause expansion; table-only hits short-circuit before DB.
    source = hit(kind="table")
    original = result([source])
    expanded, trace = await expand_context(
        None,
        None,
        None,
        "workspace",
        "collection",
        original,
        AnswerRequest(question="Question", context_max_bytes=256, context_window=0),
    )
    assert expanded is original and expanded.hits == [source]
    assert trace["status"] == "disabled"
    assert trace["bytes_used"] == 2 + evidence_size(source) <= 256


def runtime():
    return ChatRuntime(
        provider_id="provider",
        provider_name="Test",
        provider_type="openai_compatible",
        model_name="test",
        base_url="https://example.test/v1",
        timeout_seconds=5,
        token_limits=ModelTokenLimits(context_window_tokens=8192),
        capacity_status="configured",
    )


@pytest.mark.parametrize("tokens", [0, 37, None, -1, True, "37", 10**15 + 1])
@pytest.mark.asyncio
async def test_rerank_failure_preserves_only_valid_measured_usage(monkeypatch, tokens):
    target = runtime()
    error = AppException("Rejected", code="rerank_auth_failed", status_code=502)
    error.usage_tokens = tokens
    settle = AsyncMock()
    monkeypatch.setattr(hybrid.runtime_service, "resolve", AsyncMock(return_value=target))
    monkeypatch.setattr(
        hybrid.usage_service, "reserve", AsyncMock(return_value=SimpleNamespace(id="usage"))
    )
    monkeypatch.setattr(hybrid.usage_service, "settle", settle)
    with pytest.raises(AppException) as caught:
        await hybrid.rerank(
            SimpleNamespace(commit=AsyncMock()),
            None,
            "workspace",
            SimpleNamespace(query="Question", rerank_provider_id="provider", top_k=1),
            [hit()],
            SimpleNamespace(rerank=AsyncMock(side_effect=error)),
            {},
            AsyncMock(return_value="proof"),
        )
    assert caught.value is error
    expected = tokens if type(tokens) is int and 0 <= tokens <= 10**15 else None
    assert settle.await_args.kwargs == {"total_tokens": expected, "failed": True}


@pytest.mark.asyncio
async def test_rerank_cancellation_keeps_unknown_usage(monkeypatch):
    target = runtime()
    settle = AsyncMock()
    monkeypatch.setattr(hybrid.runtime_service, "resolve", AsyncMock(return_value=target))
    monkeypatch.setattr(
        hybrid.usage_service, "reserve", AsyncMock(return_value=SimpleNamespace(id="usage"))
    )
    monkeypatch.setattr(hybrid.usage_service, "settle", settle)
    with pytest.raises(asyncio.CancelledError):
        await hybrid.rerank(
            SimpleNamespace(commit=AsyncMock()),
            None,
            "workspace",
            SimpleNamespace(query="Question", rerank_provider_id="provider", top_k=1),
            [hit()],
            SimpleNamespace(rerank=AsyncMock(side_effect=asyncio.CancelledError())),
            {},
            AsyncMock(return_value="proof"),
        )
    assert settle.await_args.kwargs == {"total_tokens": None, "failed": True}


def test_inference_identity_tracks_reasoning_without_invalidating_old_run_hashes():
    before = runtime()
    policy = ReasoningPolicy(
        mode="chat_template_kwarg",
        parameter="enable_thinking",
        off_value=False,
        tasks={"off": ["answer"]},
        verified=True,
    )
    after = replace(before, reasoning_policy=policy)
    assert before.configuration_hash == after.configuration_hash  # legacy run identity stays stable
    assert before.inference_configuration_hash("answer") != after.inference_configuration_hash(
        "answer"
    )


def test_review_budget_accumulates_active_claims(monkeypatch):
    now = utcnow()
    monkeypatch.setattr(refinement, "utcnow", lambda: now)
    review = SimpleNamespace(
        created_at=now - timedelta(hours=1),
        finished_at=None,
        status="running",
        trace={
            "execution_elapsed_seconds": 40,
            "execution_started_at": (now - timedelta(seconds=35)).isoformat(),
        },
    )
    assert refinement.execution_elapsed_seconds(review) == 75
    with pytest.raises(AppException) as caught:
        refinement.check_request_budget(
            review,
            [],
            refinement.ReviewRefinementLimits(max_seconds=60),
            estimate_tokens=1,
        )
    assert caught.value.code == "compilation_review_budget_time_exceeded"


def test_stopped_review_does_not_charge_paused_time(monkeypatch):
    now = utcnow()
    monkeypatch.setattr(refinement, "utcnow", lambda: now)
    review = SimpleNamespace(
        created_at=now - timedelta(hours=1),
        status="failed",
        finished_at=now - timedelta(minutes=5),
        trace={
            "execution_elapsed_seconds": 40,
            "execution_started_at": (now - timedelta(minutes=5, seconds=35)).isoformat(),
        },
    )
    assert refinement.execution_elapsed_seconds(review) == 75


def test_resume_keeps_prior_time_and_charges_only_new_active_interval(monkeypatch):
    now = utcnow()
    monkeypatch.setattr(refinement, "utcnow", lambda: now)
    review = SimpleNamespace(
        created_at=now - timedelta(hours=1),
        status="failed",
        finished_at=now - timedelta(minutes=5),
        trace={
            "execution_elapsed_seconds": 10,
            "execution_started_at": (now - timedelta(minutes=5, seconds=20)).isoformat(),
            "execution_budget_basis": "cumulative_active/v1",
        },
    )
    review.trace = refinement.resume_execution_trace(review)
    assert review.trace["execution_elapsed_seconds"] == 30
    review.status, review.finished_at = "running", None
    monkeypatch.setattr(refinement, "utcnow", lambda: now + timedelta(seconds=15))
    assert refinement.execution_elapsed_seconds(review) == 45


def test_legacy_review_uses_conservative_lifetime_instead_of_zero(monkeypatch):
    now = utcnow()
    monkeypatch.setattr(refinement, "utcnow", lambda: now)
    review = SimpleNamespace(
        created_at=now - timedelta(seconds=100),
        status="failed",
        finished_at=now,
        trace={"execution_started_at": (now - timedelta(seconds=10)).isoformat()},
    )
    resumed = refinement.resume_execution_trace(review)
    assert resumed["execution_elapsed_seconds"] == 100
    assert resumed["execution_budget_basis"] == "legacy_wall_clock_upper_bound/v1"
