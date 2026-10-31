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
    assert resolve_directive(policy, "compiler") is None
    payload = build_payload(MESSAGES, request())
    assert "reasoning_effort" not in payload
    assert "enable_thinking" not in payload
    assert "chat_template_kwargs" not in payload
    trace = trace_for(policy, "compiler")
    assert trace["applied"] is False
    assert trace["reason"] == "provider_keeps_server_default"


def test_unverified_capability_is_not_applied():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        tasks={"off": ["compiler"]},
        verified=False,
    )
    assert resolve_directive(policy, "compiler") is None
    assert trace_for(policy, "compiler")["reason"] == "capability_not_verified"
    assert policy.status == "unverified"


def test_verified_toggle_adds_only_the_declared_body_parameter():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        tasks={"off": ["compiler"]},
        verified=True,
    )
    directive = resolve_directive(policy, "compiler")
    assert directive is not None and directive.level == "off"
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["enable_thinking"] is False
    assert "chat_template_kwargs" not in payload
    assert payload["max_tokens"] == 8192


def test_chat_template_kwarg_location_is_explicit_and_task_scoped():
    policy = ReasoningPolicy(
        mode="chat_template_kwarg",
        parameter="thinking",
        low_value=True,
        tasks={"low": ["compiler_review"]},
        verified=True,
    )
    assert resolve_directive(policy, "compiler") is None
    directive = resolve_directive(policy, "compiler_review")
    assert directive is not None
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["chat_template_kwargs"] == {"thinking": True}
    assert "thinking" not in payload


def test_effort_value_is_sent_under_the_declared_name():
    policy = ReasoningPolicy(
        mode="effort",
        parameter="reasoning_effort",
        low_value="low",
        tasks={"low": ["compiler"]},
        verified=True,
    )
    directive = resolve_directive(policy, "compiler")
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["reasoning_effort"] == "low"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mode": "toggle", "off_value": False, "tasks": {"off": ["compiler"]}},
        {"mode": "server_default", "parameter": "enable_thinking"},
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "tasks": {"off": ["chat"]},
            "verified": True,
        },
        {"mode": "toggle", "parameter": "enable_thinking", "tasks": {"off": ["compiler"]}},
        {"mode": "effort", "parameter": "bad.name", "low_value": "low", "verified": True},
        # A task may only be declared at one level; a level must name a task.
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "low_value": True,
            "tasks": {"off": ["compiler"], "low": ["compiler"]},
            "verified": True,
        },
        {
            "mode": "toggle",
            "parameter": "enable_thinking",
            "off_value": False,
            "tasks": {"off": []},
            "verified": True,
        },
    ],
)
def test_invalid_policy_is_rejected(kwargs):
    with pytest.raises(ValueError):
        ReasoningPolicy(**kwargs)


def test_tasks_map_level_to_task_not_task_to_level():
    """The dict is keyed by level; the compiler task alone gets the off value."""
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        tasks={"off": ["compiler"]},
        verified=True,
    )
    assert policy.level_for("compiler") == "off"
    assert policy.level_for("compiler_review") is None
    assert resolve_directive(policy, "compiler_review") is None
    assert trace_for(policy, "compiler_review")["reason"] == "task_not_configured"


def test_answer_task_supports_reasoning_policy():
    policy = ReasoningPolicy(
        mode="chat_template_kwarg",
        parameter="enable_thinking",
        off_value=False,
        tasks={"off": ["answer"]},
        verified=True,
    )
    directive = resolve_directive(policy, "answer")
    assert directive is not None
    assert directive.level == "off"
    payload = build_payload(MESSAGES, request(reasoning=directive))
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}


def test_directive_round_trip_and_corrupt_record():
    policy = ReasoningPolicy(
        mode="toggle",
        parameter="enable_thinking",
        off_value=False,
        tasks={"off": ["compiler"]},
        verified=True,
    )
    directive = resolve_directive(policy, "compiler")
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
