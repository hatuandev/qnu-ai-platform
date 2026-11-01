"""Operational defaults are bounded policy, never invented model capacity."""

import pytest

from qnu.domains.modelops.capacity.automatic import operational_budget
from qnu.domains.modelops.capacity.policy import plan_token_budget
from qnu.domains.modelops.capacity.schemas import ModelCapacity, ModelTokenLimits


def declared(**limits):
    return ModelCapacity(
        status="configured", basis="server_reported", token_limits=ModelTokenLimits(**limits)
    )


def test_unknown_chat_can_plan_without_claiming_server_capacity():
    state = ModelCapacity(status="unknown")
    effective = operational_budget(state, "chat")
    assert state.token_limits is None and state.status == "unknown"
    assert effective.status == "provisional"
    assert effective.sources == {
        "context_window_tokens": "application_default",
        "max_output_tokens": "application_default",
    }
    budget = plan_token_budget(effective.token_limits, input_tokens=2000)
    assert budget.max_output_tokens == 4096
    assert budget.total_reserved_tokens == 6096


def test_known_large_model_is_not_capped_by_application_defaults():
    state = declared(context_window_tokens=163840, max_output_tokens=32768)
    effective = operational_budget(state, "chat")
    assert effective.status == "declared" and effective.token_limits == state.token_limits
    assert set(effective.sources.values()) == {"server_reported"}
    assert plan_token_budget(effective.token_limits, input_tokens=100000).max_output_tokens == 32768


@pytest.mark.parametrize("capability", ["embedding", "rerank"])
def test_unknown_text_only_models_have_finite_per_input_budgets(capability):
    effective = operational_budget(ModelCapacity(status="unknown"), capability)
    assert effective.status == "provisional"
    assert effective.token_limits.max_input_tokens == 2048
    assert effective.token_limits.context_window_tokens is None
    assert effective.token_limits.max_output_tokens is None


def test_partial_capacity_fills_only_missing_limits():
    effective = operational_budget(declared(context_window_tokens=1000), "chat")
    assert effective.token_limits.context_window_tokens == 1000
    assert effective.token_limits.max_output_tokens == 250
    assert effective.sources["context_window_tokens"] == "server_reported"
    assert effective.sources["max_output_tokens"] == "application_default"
    independent = operational_budget(declared(max_input_tokens=500), "chat")
    assert independent.token_limits.context_window_tokens is None
    assert independent.token_limits.max_input_tokens == 500
    assert independent.token_limits.max_output_tokens == 4096


def test_output_only_large_model_does_not_get_a_fake_shared_context():
    effective = operational_budget(declared(max_output_tokens=100000), "chat")
    assert effective.token_limits.context_window_tokens is None
    assert effective.token_limits.max_input_tokens == 28672
    assert effective.token_limits.max_output_tokens == 100000


def test_stale_configuration_never_falls_back_to_defaults():
    effective = operational_budget(ModelCapacity(status="stale"), "chat")
    assert effective.status == "blocked" and effective.token_limits is None
    assert effective.reason_code == "model_token_limits_stale"


def test_no_image_token_budget_is_invented_for_ocr():
    effective = operational_budget(ModelCapacity(status="unknown"), "ocr")
    assert effective.status == "blocked" and effective.token_limits is None
    assert effective.reason_code == "model_input_budget_unknown"


def test_complete_independent_limits_remain_independent():
    state = declared(max_input_tokens=200000, max_output_tokens=50000)
    assert operational_budget(state, "chat").token_limits == state.token_limits


def test_operational_defaults_do_not_silently_clamp_an_explicit_output_request():
    from qnu.platform.errors import AppException

    effective = operational_budget(ModelCapacity(status="unknown"), "chat")
    with pytest.raises(AppException, match="Ngân sách") as caught:
        plan_token_budget(effective.token_limits, input_tokens=100, requested_output_tokens=8192)
    assert caught.value.code == "model_output_limit_exceeded"
