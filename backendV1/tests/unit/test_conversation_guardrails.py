"""Verify the guardrail contract stays off by default and validates model output."""

import pytest
from pydantic import ValidationError

from qnu.domains.assistants.guardrail_policy import GuardrailPolicy
from qnu.domains.conversations import guardrails
from qnu.domains.conversations.routing import (
    BASE_ROUTES,
    RoutedTurn,
    routed_turn_schema,
)


def test_policy_is_disabled_by_default():
    policy = GuardrailPolicy()
    assert policy.enabled is False and policy.categories == []


def test_enabled_policy_requires_a_category():
    with pytest.raises(ValidationError):
        GuardrailPolicy(enabled=True)


def test_categories_are_unique_and_known():
    policy = GuardrailPolicy(enabled=True, categories=["privacy", "privacy"])
    assert policy.categories == ["privacy"]
    with pytest.raises(ValidationError):
        GuardrailPolicy(enabled=True, categories=["spam"])


def test_categories_are_read_from_the_assistant_snapshot():
    config = {
        "rag_policy": {
            "guardrail_policy": {"enabled": True, "categories": ["privacy", "spam"]}
        }
    }
    assert guardrails.categories(config) == ["privacy"]
    assert guardrails.categories({"rag_policy": {}}) == []
    assert guardrails.categories({}) == []


@pytest.mark.parametrize(
    ("answer", "found"),
    [
        ("Mình không thể chia sẻ thông tin cá nhân.", []),
        ("Bạn A có số 0912345678.", ["figures", "contact"]),
        ("Xem tại https://example.com để biết thêm.", ["contact"]),
        ("Liên hệ a@example.com nhé.", ["contact"]),
        ("Điểm của bạn ấy là 27.", ["figures"]),
    ],
)
def test_output_checks(answer, found):
    assert guardrails.violations(answer) == found


def test_retry_note_names_only_the_failed_checks():
    single = guardrails.retry_note(["figures"])
    assert "chữ số" in single and "email" not in single
    both = guardrails.retry_note(["figures", "contact"])
    assert "chữ số" in both and "email" in both


def test_fallback_refusal_passes_its_own_checks():
    assert guardrails.violations(guardrails.FALLBACK) == []


def test_schema_hides_guardrail_fields_when_policy_is_off():
    schema = routed_turn_schema(guardrail=False)
    assert tuple(schema["properties"]["route"]["enum"]) == BASE_ROUTES
    assert "guardrail_category" not in schema["properties"]
    assert "guardrail_category" not in schema.get("required", [])


def test_schema_requires_the_category_when_policy_is_on():
    schema = routed_turn_schema(guardrail=True)
    assert "guardrail" in schema["properties"]["route"]["enum"]
    assert "guardrail_category" in schema["required"]


def _turn(**overrides):
    value = {
        "route": "guardrail",
        "answer": "Mình không thể hỗ trợ nội dung này.",
        "standalone_question": "Cho mình xin điểm của bạn A.",
        "needs_clarification": False,
        "guardrail_category": "privacy",
    }
    value.update(overrides)
    return value


def test_guardrail_turn_requires_an_answer_and_category():
    assert RoutedTurn.model_validate(_turn()).guardrail_category == "privacy"
    with pytest.raises(ValidationError):
        RoutedTurn.model_validate(_turn(answer=None))
    with pytest.raises(ValidationError):
        RoutedTurn.model_validate(_turn(guardrail_category=None))


def test_other_routes_reject_a_guardrail_category():
    with pytest.raises(ValidationError):
        RoutedTurn.model_validate(_turn(route="knowledge", answer=None))
    with pytest.raises(ValidationError):
        RoutedTurn.model_validate(_turn(route="greeting", guardrail_category="other_school"))
