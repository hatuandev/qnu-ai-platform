"""Verification shares the authorized answer reasoning contract and detects drift."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.modelops.reasoning import ReasoningPolicy
from qnu.domains.rag.answer import verification
from qnu.domains.rag.answer.schemas import AnswerRequest, EvidenceSource, Statement
from qnu.platform.errors import Conflict
from qnu.ports.chat_model import ChatRequest
from tests.unit.test_rag_modelops_budgets_767 import runtime
from tests.unit.test_table_grounding_770 import source as table_source


def test_judge_receives_exact_quote_units_not_synthetic_rendered_rows():
    source = table_source([["Device", "Cost"], ["Marine sensor", "12\nmillion"]])
    payload = verification.verification_evidence(source)
    assert payload["id"] == "E1"
    assert payload["rows"] == [["Device", "Cost"], ["Marine sensor", "12\nmillion"]]
    assert all(
        text in verification.evidence_texts(source) for row in payload["rows"] for text in row
    )
    assert "text" not in payload


@pytest.mark.asyncio
@pytest.mark.parametrize("verified", [False, True])
async def test_verifier_uses_answer_policy_only_when_declared_and_verified(monkeypatch, verified):
    target = replace(
        runtime(),
        reasoning_policy=ReasoningPolicy(
            mode="chat_template_kwarg",
            parameter="enable_thinking",
            off_value=False,
            tasks={"off": ["answer"]},
            verified=verified,
        ),
    )
    prepared = []

    async def prepare(*args, **kwargs):
        prepared.append(kwargs)
        return (
            target,
            ChatRequest(
                endpoint=target.base_url,
                model=target.model_name,
                max_output_tokens=8192,
                timeout_seconds=5,
                api_key="test-only",
                reasoning=target.reasoning_directive(kwargs.get("reasoning_task", "chat")),
            ),
            SimpleNamespace(total_reserved_tokens=8192),
        )

    monkeypatch.setattr(verification, "prepare_chat_request", prepare)
    monkeypatch.setattr(verification, "resolve_chat_runtime", AsyncMock(return_value=target))
    monkeypatch.setattr(
        verification.usage_service, "reserve", AsyncMock(return_value=SimpleNamespace(id="usage"))
    )
    monkeypatch.setattr(verification.usage_service, "settle", AsyncMock())
    source = EvidenceSource(
        evidence_id="E1",
        chunk_id="chunk",
        document_id="doc",
        version_id="v",
        publication_decision_id="decision",
        kind="paragraph",
        score=1,
        text="Source rule.",
        citations={},
        structure=None,
    )
    response = SimpleNamespace(
        content=json.dumps(
            {
                "findings": [
                    {
                        "statement_index": 0,
                        "status": "supported",
                        "reason": "Exact rule",
                        "quotes": [{"evidence_id": "E1", "quote": "Source rule."}],
                    }
                ]
            }
        ),
        total_tokens=20,
        prompt_tokens=12,
        completion_tokens=8,
        budget_trace={},
    )
    chat = SimpleNamespace(complete=AsyncMock(return_value=response))
    report = await verification.verify(
        SimpleNamespace(commit=AsyncMock()),
        chat,
        None,
        "ws",
        "answer",
        AnswerRequest(question="Which rule?", verification_mode="enforce"),
        [Statement(text="Source rule.", evidence_ids=["E1"])],
        [source],
        AsyncMock(),
    )
    assert prepared[0]["reasoning_task"] == "answer"
    directive = chat.complete.await_args.args[1].reasoning
    assert (directive is not None) is verified
    assert report["reasoning"]["applied"] is verified
    assert report["inference_configuration_hash"] == target.inference_configuration_hash("answer")
    assert chat.complete.await_count == 1


@pytest.mark.asyncio
async def test_reasoning_drift_before_verification_releases_unsent_usage(monkeypatch):
    target = runtime()
    changed = replace(
        target,
        reasoning_policy=ReasoningPolicy(
            mode="chat_template_kwarg",
            parameter="enable_thinking",
            off_value=False,
            tasks={"off": ["answer"]},
            verified=True,
        ),
    )
    request = ChatRequest(
        endpoint=target.base_url,
        model=target.model_name,
        max_output_tokens=8192,
        timeout_seconds=5,
        api_key="test-only",
    )
    monkeypatch.setattr(
        verification,
        "prepare_chat_request",
        AsyncMock(return_value=(target, request, SimpleNamespace(total_reserved_tokens=8192))),
    )
    monkeypatch.setattr(verification, "resolve_chat_runtime", AsyncMock(return_value=changed))
    monkeypatch.setattr(
        verification.usage_service, "reserve", AsyncMock(return_value=SimpleNamespace(id="usage"))
    )
    settle = AsyncMock()
    monkeypatch.setattr(verification.usage_service, "settle", settle)
    chat = SimpleNamespace(complete=AsyncMock())
    with pytest.raises(Conflict) as caught:
        await verification.verify(
            SimpleNamespace(commit=AsyncMock()),
            chat,
            None,
            "ws",
            "answer",
            AnswerRequest(question="Which rule?"),
            [],
            [],
            AsyncMock(),
        )
    assert caught.value.code == "answer_verification_provider_changed"
    assert not chat.complete.called
    assert settle.await_args.kwargs == {"total_tokens": 0, "failed": True}
