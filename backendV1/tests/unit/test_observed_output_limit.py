"""Observed output ceilings survive a restart without becoming published capacity."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from qnu.domains.modelops.diagnostics import observations
from qnu.domains.modelops.resilience.execution import ManagedChatModel
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatRequest, ChatResponseError, ChatResult
from qnu.ports.provider_execution import ProviderExecution, ProviderFailure

ENDPOINT = "https://provider.example/v1"
IDENTITY = "a" * 64
NOW = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


class Provider:
    def __init__(self, config=None):
        self.id = "provider"
        self.extra_config = config


class Session:
    def __init__(self, provider):
        self.provider = provider

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, *_args, **_kwargs):
        return self.provider

    async def commit(self):
        return None


class Executor:
    async def call(self, capability, request, invoke):
        return await invoke(request)


class RejectingAdapter:
    def __init__(self, accept=4096):
        self.calls = []
        self.accept = accept

    async def complete(self, messages, request):
        self.calls.append(request.max_output_tokens)
        if request.max_output_tokens > self.accept:
            error = AppException("rejected", code="chat_provider_rejected")
            error.provider_failure = ProviderFailure(422)
            raw = json.dumps(
                {"error": {"code": "max_output_tokens_exceeded", "max_output_tokens": self.accept}}
            ).encode()
            raise ChatResponseError(error, raw, None)
        return ChatResult("ok", "fixture", request.model, 1, 1, "stop", 2)


def request(sessions=None, *, automatic=True):
    return ChatRequest(
        ENDPOINT,
        "model",
        8192,
        30,
        "fixture",
        execution=ProviderExecution("workspace", "provider", sessions=sessions),
        automatic_output_budget=automatic,
        budget_identity=IDENTITY,
    )


def record(provider, *, limit=4096, model="model", identity=IDENTITY, now=NOW):
    observations.record_observation(
        provider,
        endpoint=ENDPOINT,
        model_name=model,
        budget_identity=identity,
        limit=limit,
        now=now,
    )


def test_record_replaces_the_same_scope_and_keeps_newest_first():
    provider = Provider()
    record(provider, limit=4096)
    record(provider, limit=3000, now=NOW + timedelta(hours=1))
    rows = provider.extra_config[observations.OBSERVATIONS_KEY]
    assert [row["max_output_tokens"] for row in rows] == [3000]
    assert observations.matching_observation(
        provider,
        endpoint=ENDPOINT + "/",
        model_name="model",
        budget_identity=IDENTITY,
        now=NOW + timedelta(hours=2),
    ) == (3000, NOW + timedelta(seconds=observations.OBSERVATION_TTL_SECONDS, hours=1))


def test_history_is_capped_and_newest_wins():
    provider = Provider()
    for index in range(observations.MAX_OBSERVATIONS + 2):
        record(provider, model=f"model-{index}")
    rows = provider.extra_config[observations.OBSERVATIONS_KEY]
    assert len(rows) == observations.MAX_OBSERVATIONS
    assert rows[0]["model_name"] == f"model-{observations.MAX_OBSERVATIONS + 1}"


def test_expired_observation_and_other_scope_do_not_match():
    provider = Provider()
    record(provider)
    assert (
        observations.matching_observation(
            provider,
            endpoint=ENDPOINT,
            model_name="model",
            budget_identity=IDENTITY,
            now=NOW + timedelta(seconds=observations.OBSERVATION_TTL_SECONDS + 1),
        )
        is None
    )
    assert (
        observations.matching_observation(
            provider,
            endpoint=ENDPOINT,
            model_name="model",
            budget_identity="b" * 64,
            now=NOW,
        )
        is None
    )


def test_malformed_rows_are_ignored():
    provider = Provider(
        {observations.OBSERVATIONS_KEY: [{"endpoint": ENDPOINT, "max_output_tokens": True}, None]}
    )
    assert (
        observations.matching_observation(
            provider,
            endpoint=ENDPOINT,
            model_name="model",
            budget_identity=IDENTITY,
            now=NOW,
        )
        is None
    )


@pytest.mark.asyncio
async def test_remember_then_load_keeps_scope_and_remaining_ttl():
    provider = Provider()
    await observations.remember_limit(
        lambda: Session(provider),
        provider_id="provider",
        endpoint=ENDPOINT,
        model_name="model",
        budget_identity=IDENTITY,
        limit=4096,
    )
    loaded = await observations.load_limit(
        lambda: Session(provider),
        provider_id="provider",
        endpoint=ENDPOINT,
        model_name="model",
        budget_identity=IDENTITY,
    )
    assert loaded is not None
    limit, remaining = loaded
    assert limit == 4096
    assert 0 < remaining <= observations.OBSERVATION_TTL_SECONDS


@pytest.mark.asyncio
async def test_missing_session_or_identity_is_skipped():
    assert (
        await observations.load_limit(
            None,
            provider_id="provider",
            endpoint=ENDPOINT,
            model_name="model",
            budget_identity=IDENTITY,
        )
        is None
    )
    provider = Provider()
    await observations.remember_limit(
        lambda: Session(provider),
        provider_id="provider",
        endpoint=ENDPOINT,
        model_name="model",
        budget_identity=None,
        limit=4096,
    )
    assert provider.extra_config is None


@pytest.mark.asyncio
async def test_storage_failure_never_breaks_chat():
    def broken():
        raise RuntimeError("database unavailable")

    adapter = RejectingAdapter()
    managed = ManagedChatModel(adapter, Executor())
    result = await managed.complete([], request(broken))
    assert adapter.calls == [8192, 4096]
    assert result.budget_trace["output_limit_source"] == "observed_runtime"


@pytest.mark.asyncio
async def test_live_observation_is_stored_and_a_new_runtime_starts_from_it():
    provider = Provider()
    adapter = RejectingAdapter()

    def sessions():
        return Session(provider)

    first = await ManagedChatModel(adapter, Executor()).complete([], request(sessions))
    assert adapter.calls == [8192, 4096]
    assert first.budget_trace["output_limit_source"] == "observed_runtime"
    rows = provider.extra_config[observations.OBSERVATIONS_KEY]
    assert [(row["max_output_tokens"], row["budget_identity"]) for row in rows] == [
        (4096, IDENTITY)
    ]

    restarted_adapter = RejectingAdapter()
    second = await ManagedChatModel(restarted_adapter, Executor()).complete([], request(sessions))
    assert restarted_adapter.calls == [4096]
    assert second.budget_trace["output_limit_source"] == "observed_diagnostics"
    assert second.budget_trace["observed_output_limit"] == 4096


@pytest.mark.asyncio
async def test_absent_observation_is_read_once_before_reporting_capacity():
    provider = Provider()
    reads = []

    def sessions():
        reads.append(1)
        return Session(provider)

    adapter = RejectingAdapter(accept=8192)
    managed = ManagedChatModel(adapter, Executor())
    first = await managed.complete([], request(sessions))
    second = await managed.complete([], request(sessions))
    assert adapter.calls == [8192, 8192]
    assert len(reads) == 1
    assert first.budget_trace["output_limit_source"] == "capacity"
    assert second.budget_trace["output_limit_source"] == "capacity"


@pytest.mark.asyncio
async def test_explicit_budget_is_never_clamped_or_recorded():
    provider = Provider()
    record(provider)
    adapter = RejectingAdapter()
    managed = ManagedChatModel(adapter, Executor())
    with pytest.raises(ChatResponseError):
        await managed.complete([], request(lambda: Session(provider), automatic=False))
    assert adapter.calls == [8192]
    assert len(provider.extra_config[observations.OBSERVATIONS_KEY]) == 1
