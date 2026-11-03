"""Local Qwen seed preserves ModelOps policy while opting into completion waits."""

from unittest.mock import AsyncMock

import pytest

from qnu.domains.modelops.models import Provider
from qnu.domains.modelops.resilience.schemas import ResiliencePolicy
from qnu.domains.modelops.resilience.service import POLICY_KEY, effective_policy, identity
from scripts import seed_local_modelops as seed


def model(**overrides):
    return Provider(
        id="seed-qwen",
        base_url=seed.QNU_GATEWAY + "/v1",
        model_name=seed.QWEN_MODEL,
        provider_type="openai_compatible",
        capabilities=["chat"],
        extra_config={seed.EXTRA_CONFIG_KEY: seed.QWEN_REASONING.model_dump(mode="json")},
        **overrides,
    )


@pytest.mark.asyncio
async def test_seed_enables_wait_preserving_other_policy(monkeypatch):
    row = model()
    policy = ResiliencePolicy(retry_owner="gateway", rate_cooldown_seconds=75)
    row.extra_config[POLICY_KEY] = {"identity": identity(row), "policy": policy.model_dump()}
    save = AsyncMock()
    monkeypatch.setattr(seed, "save_policy", save)
    await seed.configure_qwen_runtime(None, None, row)
    saved = save.call_args.args[3]
    assert saved.wait_for_completion is True
    assert saved.retry_owner == "gateway"
    assert saved.rate_cooldown_seconds == 75
    assert row.extra_config[seed.EXTRA_CONFIG_KEY]["verified"] is True
    save.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_is_idempotent_when_wait_already_set(monkeypatch):
    row = model()
    row.extra_config[POLICY_KEY] = {
        "identity": identity(row),
        "policy": ResiliencePolicy(wait_for_completion=True).model_dump(),
    }
    save = AsyncMock()
    reasoning = AsyncMock()
    monkeypatch.setattr(seed, "save_policy", save)
    monkeypatch.setattr(seed.provider_service, "set_reasoning", reasoning)
    await seed.configure_qwen_runtime(None, None, row)
    save.assert_not_awaited()
    reasoning.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("base_url", "http://other/v1"), ("model_name", "other")])
async def test_seed_does_not_change_another_endpoint_or_model(monkeypatch, field, value):
    row = model()
    setattr(row, field, value)
    save = AsyncMock()
    reasoning = AsyncMock()
    monkeypatch.setattr(seed, "save_policy", save)
    monkeypatch.setattr(seed.provider_service, "set_reasoning", reasoning)
    await seed.configure_qwen_runtime(None, None, row)
    save.assert_not_awaited()
    reasoning.assert_not_awaited()
    assert not effective_policy(row).wait_for_completion
