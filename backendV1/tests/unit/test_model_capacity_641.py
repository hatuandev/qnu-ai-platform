"""Declared model limits constrain a request, without a global context/output cap."""

import pytest
from pydantic import ValidationError

from qnu.domains.modelops.capacity.policy import plan_token_budget
from qnu.domains.modelops.capacity.schemas import ModelTokenLimits
from qnu.platform.errors import AppException


def test_ocr_workflow_configuration_accepts_output_above_32768():
    from qnu.platform.config import Settings

    assert Settings(OCR_MAX_OUTPUT_TOKENS=65536).OCR_MAX_OUTPUT_TOKENS == 65536


def test_large_context_and_output_do_not_inherit_a_small_global_cap():
    limits = ModelTokenLimits(context_window_tokens=2097152, max_output_tokens=131072)
    budget = plan_token_budget(limits, input_tokens=1500000, reserve_tokens=1024)
    assert budget.max_output_tokens == 131072
    assert budget.total_reserved_tokens == 1632096


def test_output_uses_remaining_shared_context_and_exact_boundary():
    limits = ModelTokenLimits(context_window_tokens=10000, max_output_tokens=6000)
    budget = plan_token_budget(limits, input_tokens=7000, reserve_tokens=100)
    assert budget.max_output_tokens == 2900 and budget.total_reserved_tokens == 10000
    assert plan_token_budget(limits, input_tokens=9999).max_output_tokens == 1


def test_independent_input_output_limits_are_not_added_into_a_fake_shared_context():
    limits = ModelTokenLimits(max_input_tokens=1000, max_output_tokens=2000)
    budget = plan_token_budget(limits, input_tokens=950, reserve_tokens=50)
    assert budget.max_output_tokens == 2000
    assert budget.total_reserved_tokens == 3000


def test_explicit_lower_workflow_output_budget_is_respected():
    limits = ModelTokenLimits(context_window_tokens=1000000, max_output_tokens=65536)
    assert (
        plan_token_budget(limits, input_tokens=100, requested_output_tokens=2000).max_output_tokens
        == 2000
    )


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"context_window_tokens": 0},
        {"context_window_tokens": -1},
        {"context_window_tokens": True},
        {"context_window_tokens": "32768"},
        {"context_window_tokens": 1024.5},
        {"context_window_tokens": 1024, "max_output_tokens": 1025},
        {"context_window_tokens": 1024, "max_input_tokens": 1025},
        {"context_window_tokens": 32768, "basis": "provider_reported"},
    ],
)
def test_invalid_or_forged_capacity_declarations_are_rejected(raw):
    with pytest.raises(ValidationError):
        ModelTokenLimits.model_validate(raw)


@pytest.mark.parametrize(
    "limits,options,code",
    [
        ({"context_window_tokens": 1000}, {"input_tokens": None}, "model_input_budget_unknown"),
        ({"max_output_tokens": 1000}, {"input_tokens": 10}, "model_capacity_required"),
        ({"max_input_tokens": 1000}, {"input_tokens": 10}, "model_output_capacity_required"),
        (
            {"max_input_tokens": 1000, "max_output_tokens": 100},
            {"input_tokens": 1001},
            "model_input_limit_exceeded",
        ),
        ({"context_window_tokens": 1000}, {"input_tokens": 1000}, "model_context_limit_exceeded"),
        (
            {"context_window_tokens": 1000},
            {"input_tokens": 950, "requested_output_tokens": 51},
            "model_output_limit_exceeded",
        ),
        ({"context_window_tokens": 1000}, {"input_tokens": True}, "model_token_budget_invalid"),
        (
            {"context_window_tokens": 1000},
            {"input_tokens": 10, "reserve_tokens": -1},
            "model_token_budget_invalid",
        ),
        (
            {"context_window_tokens": 1000},
            {"input_tokens": 10, "requested_output_tokens": 1, "minimum_output_tokens": 2},
            "model_output_limit_exceeded",
        ),
    ],
)
def test_unsafe_budget_fails_without_cropping_or_silent_clamping(limits, options, code):
    with pytest.raises(AppException) as error:
        plan_token_budget(ModelTokenLimits(**limits), **options)
    assert error.value.code == code
