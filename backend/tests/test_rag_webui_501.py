"""WebUI model policy and nested structured output regressions; no live egress."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AppException
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest, LLMGenerateResponse
from app.modules.modelops.service import modelops_service
from app.modules.modelops.services.chat_routes import plan_chat_routes
from app.modules.modelops.services.inference_policy import (
    filter_chat_routes,
    load_rag_provider_ids,
    rag_chat_scope,
)
from app.modules.rag.evidence_contracts import data_field_guide, validate_data_instance
from app.modules.rag.evidence_indexed_audit import audit_contract
from app.modules.rag.evidence_model import structured_call
from app.modules.rag.response_audit import VisibleAnswerAudit
from app.modules.rag.schemas import AskRequest


@pytest.mark.asyncio
async def test_server_modelops_mode_restores_explicit_provider_selection(tmp_path):
    (tmp_path / "rag_inference_policy.json").write_text('{"chat_provider_mode":"modelops"}', encoding="utf-8")
    with patch("app.modules.modelops.services.inference_policy.get_configs_dir", return_value=tmp_path):
        assert await load_rag_provider_ids() is None
        async with rag_chat_scope():
            providers = [{"id": name, "model_name": "m", "models": ["m"]}
                         for name in ("primary", "fallback", "not-selected")]
            req = LLMGenerateRequest(messages=[ChatMessage(role="user", content="test")],
                preferred_provider_id="primary", preferred_model_name="m",
                fallback_provider_id="fallback", fallback_model_name="m")
            assert [(p["id"], m) for p, m in filter_chat_routes(plan_chat_routes(providers, req))] == [
                ("primary", "m"), ("fallback", "m")]


@pytest.mark.asyncio
@pytest.mark.parametrize("config", [{"chat_provider_mode":"typo"}, [], {},
    {"chat_provider_mode":"modelops", "allowed_chat_provider_ids":["internal"]}])
async def test_invalid_or_conflicting_server_policy_stays_fail_closed(tmp_path, config):
    (tmp_path / "rag_inference_policy.json").write_text(json.dumps(config), encoding="utf-8")
    with (patch("app.modules.modelops.services.inference_policy.get_configs_dir", return_value=tmp_path),
          pytest.raises(AppException) as error):
        await load_rag_provider_ids()
    assert error.value.code == "RAG_INFERENCE_POLICY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_nested_modelops_scope_uses_frozen_policy_and_resets_after_error():
    with patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids",
               AsyncMock(return_value=None)) as load:
        with pytest.raises(RuntimeError):
            async with rag_chat_scope():
                async with rag_chat_scope():
                    raise RuntimeError("request cancelled by fixture")
        assert load.await_count == 1
        async with rag_chat_scope():
            assert load.await_count == 2


def test_nested_audit_guide_keeps_root_fields_distinct_from_claim_fields():
    contract = audit_contract([{"id":"c"}], {"e1":None})
    guide = data_field_guide(contract)
    assert "$.claims[].claim_id" in guide
    assert "$.essential_conditions" in guide and "$.complete" in guide
    assert "$.claims[].essential_conditions" not in guide


@pytest.mark.asyncio
async def test_nested_fields_repair_keeps_negative_check_and_requires_root_complete():
    contract = audit_contract([{"id":"c"}], {"e1":None})
    bad = {"claims":[{"claim_id":"c", "all_assertions_supported":False, "essential_conditions":[]}]}
    good = {"claims":[{"claim_id":"c", "all_assertions_supported":False}], "complete":False}
    responses = [SimpleNamespace(content=json.dumps(body), provider="fake", model="fake") for body in (bad, good)]
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(side_effect=responses)) as generate:
        output = await structured_call(None, AskRequest(question="test", collection_id="c"),
            contract, "Audit", {"claims":[{"id":"c"}]}, max_tokens=500)
    assert not output.complete and not output.claims[0].all_assertions_supported
    prompt = generate.call_args_list[0].args[1].messages[0].content
    assert "$.complete" in prompt and "$.claims[].claim_id" in prompt


def test_root_path_keys_are_format_only_and_keep_all_negative_verdicts():
    raw = {"$.all_assertions_supported":False, "$.answers_original_question":True,
        "$.essential_conditions_retained":False, "$.conflict":False,
        "$.evidence_ids":[], "$.assertions":[], "$.missing_constraints":["Missing scope"]}
    output = validate_data_instance(VisibleAnswerAudit, json.dumps(raw))
    assert not output.all_assertions_supported and not output.essential_conditions_retained
    assert output.missing_constraints == ["Missing scope"]


@pytest.mark.parametrize("patch_data", [
    {"all_assertions_supported": True},
    {"$.claims[].complete": True},
    {"$.assertions": [{"$.evidence_id":"e1"}]},
])
def test_root_aliases_do_not_override_or_move_unrecognized_fields(patch_data):
    raw = {"$.all_assertions_supported":False, "$.answers_original_question":True,
        "$.essential_conditions_retained":False, "$.conflict":False}
    with pytest.raises(ValueError):
        validate_data_instance(VisibleAnswerAudit, json.dumps({**raw, **patch_data}))


@pytest.mark.asyncio
async def test_live_observed_root_path_shape_is_validated_without_another_model_call():
    body = {"$.all_assertions_supported":False, "$.answers_original_question":True,
        "$.essential_conditions_retained":False, "$.conflict":False}
    with patch("app.modules.rag.evidence_model.modelops_service.generate", AsyncMock(return_value=
        SimpleNamespace(content=json.dumps(body),provider="fake",model="fake"))) as generate:
        output = await structured_call(None, AskRequest(question="test",collection_id="c"),
                                       VisibleAnswerAudit, "Audit", {}, max_tokens=500)
    assert not output.all_assertions_supported and generate.await_count == 1


@pytest.mark.asyncio
async def test_modelops_boundary_accepts_selected_non_internal_provider():
    provider = {"id":"configured-cloud", "name":"configured-cloud", "provider_type":"custom",
        "model_name":"selected-model", "api_key":"fixture", "models":["selected-model"],
        "api_base_url":"https://fake.invalid/v1", "timeout_seconds":1}
    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    response = LLMGenerateResponse(content="ok", provider="custom", model="selected-model",
                               prompt_tokens=1, completion_tokens=1, total_tokens=2)
    adapter = SimpleNamespace(generate=AsyncMock(return_value=response))
    with (patch("app.modules.modelops.services.inference_policy.load_rag_provider_ids", AsyncMock(return_value=None)),
          patch.object(modelops_service, "check_quota_available", AsyncMock()),
          patch.object(modelops_service, "get_active_providers", AsyncMock(return_value=[provider])),
          patch.object(modelops_service, "record_usage_log", AsyncMock()),
          patch("app.modules.modelops.service.get_llm_adapter", return_value=adapter) as factory,
          patch("app.modules.modelops.services.inference_service.circuit_breaker_registry") as breakers,
          patch("app.modules.modelops.services.provider_key_rotation_service.provider_key_rotation_service.acquire",
                AsyncMock(return_value=SimpleNamespace(managed=False, lease=None)))):
        breakers.get.return_value.can_execute.return_value = True
        async with rag_chat_scope():
            output = await modelops_service.generate(db, LLMGenerateRequest(
                messages=[ChatMessage(role="user",content="synthetic")],
                preferred_provider_id="configured-cloud", preferred_model_name="selected-model"))
    assert output.content == "ok"
    assert factory.call_args.kwargs["base_url"] == provider["api_base_url"]
