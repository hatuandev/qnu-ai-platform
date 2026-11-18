"""Reasoning is a declared, verified parameter; never inferred from a model name."""

import pytest

from qnu.adapters.providers.openai_compatible import build_payload
from qnu.domains.modelops.reasoning import (
    ReasoningDirective,
    ReasoningPolicy,
    parse_policy,
    resolve_directive,
    trace_for,
)
from qnu.platform.errors import AppException
from qnu.ports.chat_model import ChatMessage, ChatRequest

MESSAGES = [ChatMessage("system", "s"), ChatMessage("user", "u")]


def request(**kwargs) -> ChatRequest:
    return ChatRequest(
        endpoint="http://localhost:8000/v1",
        model="qwen",
        max_output_tokens=8192,
        timeout_seconds=30,
        api_key="secret",
        **kwargs,
    )


def test_server_default_sends_no_parameter_and_says_so():
    policy = ReasoningPolicy()
    assert resolve_directive(policy) is None
    payload = build_payload(MESSAGES, request())
    assert "reasoning_effort" not in payload
    assert "enable_thinking" not in payload
    assert "chat_template_kwargs" not in payload
    trace = trace_for(policy)
    assert trace["applied"] is False
    assert trace["reason"] == "provider_keeps_server_default"


def test_unverified_capability_is_not_applied():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        level="off",
        verified=False,
    )
    assert resolve_directive(policy) is None
    assert trace_for(policy)["reason"] == "capability_not_verified"
    assert policy.status == "unverified"


def test_verified_toggle_adds_only_the_declared_body_parameter():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        level="off",
        verified=True,
    )
    directive = resolve_directive(policy)
    assert directive is not None and directive.level == "off"
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["enable_thinking"] is False
    assert "chat_template_kwargs" not in payload
    assert payload["max_tokens"] == 8192


def test_chat_template_kwarg_location_is_explicit_and_model_wide():
    policy = ReasoningPolicy(
        mode="chat_template_kwarg",
        parameter="thinking",
        low_value=True,
        level="low",
        verified=True,
    )
    directive = resolve_directive(policy)
    assert directive is not None and directive.level == "low"
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["chat_template_kwargs"] == {"thinking": True}
    assert "thinking" not in payload


def test_effort_value_is_sent_under_the_declared_name():
    policy = ReasoningPolicy(
        mode="effort",
        parameter="reasoning_effort",
        low_value="low",
        level="low",
        verified=True,
    )
    directive = resolve_directive(policy)
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["reasoning_effort"] == "low"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "toggle", "off_value": False, "level": "off"},
        {"mode": "server_default", "parameter": "enable_thinking"},
        {"mode": "toggle", "parameter": "enable_thinking", "level": "off"},
        {"mode": "toggle", "parameter": "enable_thinking", "level": "low"},
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "level": "low",
        },
        {"mode": "effort", "parameter": "bad.name", "low_value": "low"},
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "tasks": {"off": ["compiler"]},
        },
    ],
)
def test_invalid_policy_is_rejected(kwargs):
    with pytest.raises(ValueError):
        ReasoningPolicy(**kwargs)


def test_declared_without_a_level_keeps_the_server_default():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        level=None,
        verified=True,
    )
    assert resolve_directive(policy) is None
    assert trace_for(policy)["reason"] == "level_not_set"


def test_legacy_task_map_with_one_level_keeps_that_level():
    policy = parse_policy(
        {
            "mode": "chat_template_kwarg",
            "parameter": "enable_thinking",
            "off_value": False,
            "tasks": {"off": ["compiler", "compiler_review", "answer", "ocr_review"]},
            "verified": True,
        }
    )
    assert policy is not None and policy.level == "off"
    directive = resolve_directive(policy)
    assert directive is not None
    assert build_payload(MESSAGES, request(reasoning=directive))[
        "chat_template_kwargs"
    ] == {"enable_thinking": False}
    assert "tasks" not in policy.model_dump()


def test_legacy_task_map_with_mixed_levels_reads_as_off():
    policy = parse_policy(
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "low_value": True,
            "tasks": {"off": ["compiler"], "low": ["compiler_review"]},
            "verified": True,
        }
    )
    assert policy is not None and policy.level == "off"
    directive = resolve_directive(policy)
    assert directive is not None and directive.value is False


def test_legacy_task_map_without_entries_keeps_the_server_default():
    policy = parse_policy(
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "tasks": {"off": [], "low": []},
            "verified": True,
        }
    )
    assert policy is not None and policy.level is None
    assert resolve_directive(policy) is None
    assert trace_for(policy)["reason"] == "level_not_set"


def test_directive_round_trip_and_corrupt_record():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        level="off",
        verified=True,
    )
    directive = resolve_directive(policy)
    restored = ReasoningDirective.from_public_dict(directive.public_dict())
    assert restored == directive
    assert ReasoningDirective.from_public_dict(None) is None
    with pytest.raises(AppException) as error:
        ReasoningDirective.from_public_dict({"mode": "toggle"})
    assert error.value.code == "modelops_reasoning_policy_invalid"


def test_invalid_stored_json_is_never_applied():
    assert parse_policy({"mode": "toggle"}) is None
    assert parse_policy("not-a-dict") is None
    assert parse_policy(None) is None
    assert parse_policy({"mode": "toggle", "parameter": "x", "level": "high"}) is None


def test_one_level_serves_every_task_this_model_handles():
    policy = ReasoningPolicy(
        mode="chat_template_kwarg",
        parameter="enable_thinking",
        off_value=False,
        level="off",
        verified=True,
    )
    directive = resolve_directive(policy)
    assert directive is not None and directive.level == "off"
    assert build_payload(MESSAGES, request(reasoning=directive))["chat_template_kwargs"] == {
        "enable_thinking": False,
    }
    assert resolve_directive(policy.model_copy(update={"verified": False})) is None
