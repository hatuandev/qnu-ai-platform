"""Output boundary regressions: HTTP transport and real selector/binding/stage."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import tests.test_semantic_lifecycle as lifecycle
from app.core.exceptions import AppException
from app.modules.knowledge.services.qnu_serving import verify_revision_pair
from app.modules.knowledge.services.semantic_modelops import generate_bound_semantics
from app.modules.knowledge.services.semantic_selector import parse_selector
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.services.output_contract import (
    OutputContract,
    contract_schemas,
    resolve_contract,
)
from tests.test_semantic_context_binding import note_payload

storage = lifecycle.storage
pair = lifecycle.pair


def complete_selector(packet, contract="qnu_semantic_selector_v1"):
    result = note_payload(packet)
    if contract == "qnu_semantic_selector_v2":
        for category in ("notes", "cells", "limitations"):
            for item in result[category]:
                item.pop("source_unit_id")
    result.update(cells=[], limitations=[], needs_context=[], unresolved=[], context_followups=[])
    return result


def response(content, **metadata):
    return SimpleNamespace(content=content, provider="TEST", model="TEST", is_fallback=False,
        prompt_tokens=1, completion_tokens=1, cost_usd=0, **metadata)


@pytest.mark.asyncio
@pytest.mark.parametrize("malformation", ["missing", "duplicate", "extra_data"])
async def test_whole_response_rejects_missing_duplicate_and_extra_data(pair, malformation):
    artifact = lifecycle.artifact_of(pair)
    before = copy.deepcopy(artifact)

    async def generate(_db, request):
        packet = json.loads(request.messages[1].content)
        data = complete_selector(packet, request.output_contract.name)
        if malformation == "missing":
            data.pop("unresolved")
        content = json.dumps(data)
        if malformation == "duplicate":
            content = content[:-1] + ', "context_id": ' + json.dumps(data["context_id"]) + '}'
        if malformation == "extra_data":
            content += ' explanation'
        return response(content)

    with patch("app.modules.modelops.service.modelops_service.generate", side_effect=generate), pytest.raises(AppException) as failure:
        await generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=await verify_revision_pair(pair))
    assert failure.value.code == "SEMANTIC_OUTPUT_INVALID"
    assert artifact == before


def test_compiled_schema_matches_every_business_field_and_nested_selector():
    business, wire = contract_schemas()
    def check(before, after):
        if isinstance(before, dict):
            assert before.keys() - {"default", "required", "additionalProperties"} <= after.keys()
            if before.get("type") == "object":
                assert set(after["required"]) == set(before["properties"])
                assert after["additionalProperties"] is False
            for key in before.keys() - {"default", "required", "additionalProperties"}:
                check(before[key], after[key])
        elif isinstance(before, list):
            assert len(before) == len(after)
            for left, right in zip(before, after, strict=True): check(left, right)
        else: assert before == after
    check(business, wire)
    assert "unresolved" in wire["required"] and "context_followups" in wire["required"]


@pytest.mark.parametrize("content,mode,stage", [
    ('{} {}', "json_object", "json_syntax"),
    ('{} trailing', "prompt_only", "json_syntax"),
    ('{"context_id":"a","context_id":"b"}', "prompt_only", "json_syntax"),
    ('{"value":NaN}', "prompt_only", "json_syntax"),
    ('{"value":Infinity}', "prompt_only", "json_syntax"),
    ('[]', "prompt_only", "selector_schema"),
    ('{}', "prompt_only", "selector_schema"),
    ('```json\n{}\n```', "json_schema", "json_syntax"),
    ('```json\n{}\n``` extra', "prompt_only", "json_syntax"),
    ('```json\n{}', "prompt_only", "json_syntax"),
])
def test_strict_parser_rejects_without_repair(content, mode, stage):
    with pytest.raises(AppException) as failure:
        parse_selector(response(content), mode)
    assert failure.value.details["stage"] == stage
    assert "content" not in failure.value.details


@pytest.mark.parametrize("fence", [False, True])
def test_valid_unicode_escaped_text_and_brackets(fence):
    data = {"context_id": "test", "notes": [], "cells": [], "limitations": [], "needs_context": [],
        "unresolved": [{"unit_ids": [], "reason": 'Dòng tiếng Việt\n"{nội dung}"'}], "context_followups": []}
    content = json.dumps(data, ensure_ascii=False)
    if fence: content = '```json\n' + content + '\n```'
    wire, trace = parse_selector(response(content), "prompt_only")
    assert wire.unresolved[0].reason == data["unresolved"][0]["reason"]
    assert trace["normalization"] == ("single_whole_json_fence" if fence else "none")


@pytest.mark.parametrize("metadata,stage", [({"finish_reason": "length"}, "response_incomplete"),
    ({"finish_reason": "content_filter"}, "refusal"), ({"refusal": "denied"}, "refusal")])
def test_finish_and_refusal_precede_syntax(metadata, stage):
    with pytest.raises(AppException) as failure: parse_selector(response('{}', **metadata), "prompt_only")
    assert failure.value.details["stage"] == stage


@pytest.mark.parametrize("mutation", ["extra", "null", "missing_nested", "enum", "coerce"])
def test_selector_shape_is_never_filled_coerced_or_dropped(mutation):
    data = {"context_id": "test", "notes": [], "cells": [], "limitations": [], "needs_context": [], "unresolved": [], "context_followups": []}
    if mutation == "extra": data["extra"] = 1
    if mutation == "null": data["unresolved"] = None
    if mutation == "coerce": data["context_id"] = 123
    if mutation == "missing_nested": data["unresolved"] = [{"reason": "Missing unit list"}]
    if mutation == "enum": data["notes"] = [{"source_unit_id": "a", "evidence_id": "b", "reason": "Test reason", "table_id": "t", "scope": "invalid", "row_unit_ids": [], "column_ids": []}]
    with pytest.raises(AppException) as failure: parse_selector(response(json.dumps(data)), "prompt_only")
    assert failure.value.details["stage"] == "selector_schema"


def install_http(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handler), timeout=kw.get("timeout", 15)))


def inference_boundary(monkeypatch, capabilities):
    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.services import inference_service as module
    from app.modules.modelops.services.inference_service import InferenceService
    providers, configs = [], {}
    for index, caps in enumerate(capabilities):
        identity = "contract-test-" + str(index)
        endpoint = "http://provider" + str(index) + "/v1"
        model = "alias" + str(index)
        providers.append({"id": identity, "name": identity, "provider_type": "custom", "model_name": model, "models": [model],
            "api_base_url": endpoint, "timeout_seconds": 3, "priority": index, "api_key": "fixture-only-credential", "is_active": True})
        configs[identity] = ModelProviderConfig(id=identity, api_base_url=endpoint, extra_config={"chat_request_contracts": {model: {"endpoint": endpoint, "capabilities": caps}}})
    facade = SimpleNamespace(check_quota_available=AsyncMock(), get_active_providers=AsyncMock(return_value=providers), record_usage_log=AsyncMock())
    service = InferenceService(facade)
    service._record_key_success = AsyncMock()
    service._record_key_failure = AsyncMock()
    monkeypatch.setattr(module, "save_chat_capabilities", AsyncMock())
    monkeypatch.setattr(module.provider_key_rotation_service, "acquire", AsyncMock(return_value=SimpleNamespace(managed=False, lease=None)))
    db = AsyncMock()
    def execute(query):
        result = MagicMock()
        result.scalar_one_or_none.return_value = configs[query.compile().params["id_1"]]
        return result
    db.execute.side_effect = execute
    return service, db


@pytest.mark.asyncio
@pytest.mark.parametrize("contract,capabilities,expected", [
    (None, {}, None),
    (OutputContract(), {"json_schema_supported": True}, "json_schema"),
    (OutputContract(allowed_weaker_modes=("json_object",)), {"json_object_supported": True}, "json_object"),
    (OutputContract(allowed_weaker_modes=("prompt_only",)), {}, None),
])
async def test_request_service_adapter_http_preserves_contract(monkeypatch, contract, capabilities, expected):
    requests = []
    def server(req):
        requests.append(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]})
    install_http(monkeypatch, server)
    service, db = inference_boundary(monkeypatch, [capabilities])
    result = await service.generate(db, LLMGenerateRequest(messages=[ChatMessage(role="user", content="JSON test")],
        preferred_provider_id="contract-test-0", preferred_model_name="alias0", output_contract=contract))
    assert requests[0].get("response_format", {}).get("type") == expected
    if expected == "json_schema":
        assert requests[0]["response_format"]["json_schema"]["schema"] == contract_schemas()[1]
    assert result.finish_reason == "stop" and len(result.attempt_trace) == 1
    assert len(result.attempt_trace[0]["transport_attempts"]) == (1 if contract else 0)


@pytest.mark.asyncio
async def test_fallback_rechecks_capability_and_strict_never_silently_downgrades(monkeypatch):
    calls = []
    install_http(monkeypatch, lambda req: (calls.append(req), httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]}))[1])
    service, db = inference_boundary(monkeypatch, [{}, {"json_schema_supported": True}])
    request = LLMGenerateRequest(messages=[ChatMessage(role="user", content="JSON")], preferred_provider_id="contract-test-0", preferred_model_name="alias0",
        fallback_provider_id="contract-test-1", fallback_model_name="alias1", output_contract=OutputContract())
    result = await service.generate(db, request)
    assert len(calls) == 1 and calls[0].url.host == "provider1"
    assert result.is_fallback and result.output_contract["effective_mode"] == "json_schema"
    assert result.attempt_trace[0]["code"] == "MODEL_OUTPUT_CONTRACT_UNSUPPORTED"
    service._record_key_failure.assert_not_awaited()
    service, db = inference_boundary(monkeypatch, [{}])
    with pytest.raises(AppException) as failure:
        await service.generate(db, request.model_copy(update={"fallback_provider_id": None, "fallback_model_name": None}))
    assert failure.value.code == "MODEL_OUTPUT_CONTRACT_UNSUPPORTED" and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("error,code", [({"code": "invalid_json_schema", "param": "response_format"}, "MODEL_OUTPUT_REQUEST_INVALID"),
    ({"code": "unsupported_parameter", "param": "response_format"}, "MODEL_OUTPUT_CONTRACT_UNSUPPORTED"),
    ({"code": "context_length_exceeded"}, "MODEL_CONTEXT_EXCEEDED")])
async def test_bad_request_is_not_key_failure_or_context_cropping(monkeypatch, error, code):
    calls = []
    install_http(monkeypatch, lambda req: (calls.append(req), httpx.Response(400, json={"error": error}))[1])
    service, db = inference_boundary(monkeypatch, [{"json_schema_supported": True}])
    with pytest.raises(AppException) as failure:
        await service.generate(db, LLMGenerateRequest(messages=[ChatMessage(role="user", content="JSON")], preferred_provider_id="contract-test-0",
            preferred_model_name="alias0", output_contract=OutputContract()))
    assert failure.value.code == code and len(calls) == 1
    service._record_key_failure.assert_not_awaited()


@pytest.mark.asyncio
async def test_old_adapter_signature_without_thinking_budget_preserves_contract(monkeypatch):
    from app.modules.modelops.providers.base import LLMResponse
    service, db = inference_boundary(monkeypatch, [{}])
    calls = []
    class Legacy:
        supports_output_contract = True
        request_capabilities = {"json_object_supported": True}
        async def generate(self, messages, temperature, max_tokens, output_contract):
            calls.append(output_contract)
            return LLMResponse("{}", "TEST", "alias0", 1, 1, 2)
    monkeypatch.setattr(service, "_get_adapter_factory", lambda: lambda **kw: Legacy())
    result = await service.generate(db, LLMGenerateRequest(messages=[ChatMessage(role="user", content="JSON")], preferred_model_name="alias0",
        output_contract=OutputContract(requested_mode="json_object")))
    assert len(calls) == 1 and result.output_contract["effective_mode"] == "json_object"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,expected_calls", [("success", 2), ("fail", 2), ("evidence", 1), ("refusal", 1), ("length", 1), ("schema", 1)])
async def test_retry_same_packet_real_binding_atomic_stage(pair, kind, expected_calls):
    artifact = lifecycle.artifact_of(pair)
    before = copy.deepcopy(artifact)
    requests = []
    async def generate(_db, request):
        packet = json.loads(request.messages[1].content)
        requests.append(request)
        data = complete_selector(packet, request.output_contract.name)
        if kind == "evidence": data["notes"][0]["evidence_id"] = "wrong-evidence"
        if kind == "schema": data.pop("needs_context")
        text = json.dumps(data)
        if kind == "fail" or kind == "success" and len(requests) == 1: text += '"}'
        return response(text, finish_reason="length" if kind == "length" else "stop", refusal="denied" if kind == "refusal" else None)
    with patch("app.modules.modelops.service.modelops_service.generate", side_effect=generate):
        if kind == "success":
            pending = await generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=await verify_revision_pair(pair))
            assert pending["status"] == "proposed" and len(pending["annotations"]["notes"]) == 1
            assert pending["model"]["metrics"]["format_retries"] == 1
            assert requests[0].messages[1] == requests[1].messages[1]
            assert requests[0].output_contract == requests[1].output_contract
            assert not artifact.get("semantic_effective")
        else:
            with pytest.raises(AppException):
                await generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=await verify_revision_pair(pair))
            assert artifact == before
    assert len(requests) == expected_calls


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_retry_keeps_deadline_and_cancellation_without_mutation(pair, cancel):
    artifact = lifecycle.artifact_of(pair)
    before = copy.deepcopy(artifact)
    calls = []
    async def generate(_db, request):
        calls.append(request)
        if len(calls) == 1: return response('{} trailing')
        await asyncio.sleep(1)
    with patch("app.modules.modelops.service.modelops_service.generate", side_effect=generate):
        task = asyncio.create_task(generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=await verify_revision_pair(pair),
            context_policy={"run_seconds": 0.2}))
        if cancel:
            while len(calls) < 2: await asyncio.sleep(0.005)
            task.cancel()
            with pytest.raises(asyncio.CancelledError): await task
        else:
            with pytest.raises(AppException) as failure: await task
            assert failure.value.code == "SEMANTIC_RUN_DEADLINE"
    assert len(calls) == 2 and artifact == before


@pytest.mark.asyncio
async def test_http_through_modelops_and_real_binder_stages_only_valid_retry(monkeypatch, pair):
    requests = []
    def server(request):
        payload = json.loads(request.content)
        requests.append(payload)
        packet = json.loads(payload["messages"][1]["content"])
        content = json.dumps(complete_selector(packet, payload["response_format"]["json_schema"]["name"])) + ('"}' if len(requests) == 1 else '')
        return httpx.Response(200, json={"id": "TEST-response", "model": "alias0", "choices": [{"message": {"content": content}, "finish_reason": "stop"}]})
    install_http(monkeypatch, server)
    service, db = inference_boundary(monkeypatch, [{"json_schema_supported": True}])
    monkeypatch.setattr("app.modules.modelops.service.modelops_service.generate", service.generate)
    artifact = lifecycle.artifact_of(pair)
    pending = await generate_bound_semantics(db, artifact, "TEST", "alias0", "contract-test-0", document=await verify_revision_pair(pair))
    assert pending["status"] == "proposed" and len(pending["annotations"]["notes"]) == 1
    assert requests[0]["response_format"] == requests[1]["response_format"]
    assert requests[0]["messages"][1] == requests[1]["messages"][1]
    assert pending["model"]["metrics"]["transport_attempts"] == 2
    assert pending["model"]["metrics"]["provider_attempts"] == 2
    assert not artifact.get("semantic_effective")


@pytest.mark.asyncio
async def test_packet_two_fails_after_retry_never_stages_first_packet(pair):
    from app.modules.knowledge.services.semantic_annotations import stage_semantic_annotations
    from app.modules.knowledge.services.semantic_binding import bind_model_proposals
    from app.modules.knowledge.services.semantic_context import ContextBuilder
    artifact = lifecycle.artifact_of(pair)
    document = await verify_revision_pair(pair)
    before = copy.deepcopy(artifact)
    packet = ContextBuilder(artifact, document).packets()[0]
    calls = []
    async def generate(_db, request):
        calls.append(request)
        return response(json.dumps(complete_selector(packet, request.output_contract.name)) if len(calls) == 1 else '{} trailing')
    with patch.object(ContextBuilder, "packets", return_value=[packet, packet]), \
         patch("app.modules.modelops.service.modelops_service.generate", side_effect=generate), \
         patch("app.modules.knowledge.services.semantic_modelops.bind_model_proposals", wraps=bind_model_proposals) as binder, \
         patch("app.modules.knowledge.services.semantic_annotations.stage_semantic_annotations", wraps=stage_semantic_annotations) as stage, \
         pytest.raises(AppException) as failure:
        await generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=document)
    assert failure.value.details["stage"] == "json_syntax"
    assert len(calls) == 3 and binder.call_count == 1 and stage.call_count == 0
    assert artifact == before


@pytest.mark.asyncio
async def test_expansion_does_not_reset_format_retry_limit(pair):
    from app.modules.knowledge.services.semantic_context import ContextBuilder
    artifact = lifecycle.artifact_of(pair)
    document = await verify_revision_pair(pair)
    before = copy.deepcopy(artifact)
    calls = []
    async def generate(_db, request):
        packet = json.loads(request.messages[1].content)
        calls.append(request)
        if len(calls) != 2: return response('{} trailing')
        data = complete_selector(packet, request.output_contract.name)
        data["needs_context"] = ["qnu:n"]
        return response(json.dumps(data))
    def expand(_self, packet, _requested):
        return copy.deepcopy(packet)  # Expansion boundary only; parser/binder/retry remain real.
    with patch.object(ContextBuilder, "expand", expand), patch("app.modules.modelops.service.modelops_service.generate", side_effect=generate), pytest.raises(AppException) as failure:
        await generate_bound_semantics(None, artifact, "TEST", "TEST", "TEST", document=document)
    assert failure.value.details["stage"] == "json_syntax" and len(calls) == 3
    assert failure.value.details["metrics"]["format_retries"] == 1
    assert artifact == before


@pytest.mark.asyncio
async def test_semantic_contract_rejects_stream_and_ambiguous_choices(monkeypatch):
    from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
    contract = resolve_contract(OutputContract(), {"json_schema_supported": True}, supports_chat_schema=True)
    adapter = OpenAIAdapter("alias0", "fixture-only-credential", "http://provider0/v1")
    install_http(monkeypatch, lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}, {"message": {"content": "{}"}}]}))
    with pytest.raises(AppException) as failure:
        await adapter.generate([ChatMessage(role="user", content="JSON")], output_contract=contract)
    assert failure.value.code == "MODEL_RESPONSE_PROTOCOL_ERROR"
    with pytest.raises(AppException) as failure:
        async for _ in adapter.stream([ChatMessage(role="user", content="JSON")], output_contract=contract): pass
    assert failure.value.code == "MODEL_OUTPUT_STREAM_UNSUPPORTED"


@pytest.mark.asyncio
async def test_transport_retry_shares_byte_budget_and_preserves_schema(monkeypatch):
    from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
    from app.modules.modelops.services.inference_policy import transient_retry_scope
    calls = []
    def server(request):
        calls.append(json.loads(request.content))
        return httpx.Response(503 if len(calls) == 1 else 200,
            json={"error": {"message": "service temporarily unavailable"}} if len(calls) == 1 else {"choices": [{"message": {"content": "{}"}}]})
    install_http(monkeypatch, server)
    contract = resolve_contract(OutputContract(), {"json_schema_supported": True}, supports_chat_schema=True)
    adapter = OpenAIAdapter("alias0", "fixture-only-credential", "http://provider0/v1")
    with transient_retry_scope(max_input_bytes=100000):
        result = await adapter.generate([ChatMessage(role="user", content="JSON")], output_contract=contract)
    assert len(calls) == 2 and len(result.attempt_trace) == 2 and calls[0] == calls[1]
    size = result.attempt_trace[0]["request_bytes"]
    calls.clear()
    with transient_retry_scope(max_input_bytes=size + 1), pytest.raises(AppException) as failure:
        await adapter.generate([ChatMessage(role="user", content="JSON")], output_contract=contract)
    assert failure.value.code == "SEMANTIC_CONTEXT_INCOMPLETE" and len(calls) == 1


@pytest.mark.asyncio
async def test_parameter_negotiation_cannot_remove_output_format(monkeypatch):
    from app.modules.modelops.providers.openai_adapter import OpenAIAdapter
    calls = []
    def server(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if "temperature" in payload:
            return httpx.Response(400, json={"error": {"message": "Unsupported parameter: 'temperature'"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    install_http(monkeypatch, server)
    contract = resolve_contract(OutputContract(), {"json_schema_supported": True}, supports_chat_schema=True)
    await OpenAIAdapter("alias0", "fixture-only-credential", "http://provider0/v1").generate([ChatMessage(role="user", content="JSON")], output_contract=contract)
    assert len(calls) == 2 and calls[0]["response_format"] == calls[1]["response_format"]
