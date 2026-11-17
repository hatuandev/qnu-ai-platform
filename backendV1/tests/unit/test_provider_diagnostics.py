"""Real HTTP adapter contract with scripted responses; never calls a model server."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from qnu.adapters.providers.diagnostics import HttpProviderDiagnosticClient, models_url
from qnu.ports.provider_diagnostics import DiagnosticTarget

TARGET = DiagnosticTarget(
    "https://provider.example/v1",
    "test-model",
    "openai_compatible",
    5,
    api_key="sk-test-private-value",
)


@pytest.mark.parametrize("suffix", ["", "/", "/models", "/embeddings", "/chat/completions"])
def test_discovery_uses_the_configured_runtime_origin(suffix):
    assert models_url(TARGET.endpoint + suffix) == "https://provider.example/v1/models"


async def call(kind, body, status=200, headers=None, target=TARGET):
    requests = []

    def upstream(request):
        requests.append(request)
        return httpx.Response(status, json=body, headers=headers)

    result = await HttpProviderDiagnosticClient(transport=httpx.MockTransport(upstream)).check(
        kind, target
    )
    return result, requests


async def test_discovery_is_not_inference_and_does_not_reflect_secret():
    result, requests = await call("discovery", {"data": [{"id": "a"}, {"id": "b"}]})
    assert result.models == ["a", "b"] and result.outcome == "ok"
    assert requests[0].method == "GET"
    assert requests[0].headers["authorization"] == "Bearer " + TARGET.api_key
    bad, _ = await call("discovery", {"data": [{"id": TARGET.api_key}]})
    assert bad.outcome == "failed" and TARGET.api_key not in repr(bad)


async def test_anthropic_discovery_uses_its_declared_auth_scheme():
    result, requests = await call(
        "discovery",
        {"data": [{"id": "a"}]},
        target=replace(TARGET, auth_scheme="anthropic"),
    )
    assert result.outcome == "ok"
    assert requests[0].headers["x-api-key"] == TARGET.api_key
    assert requests[0].headers["anthropic-version"] == "2023-06-01"
    assert "authorization" not in requests[0].headers


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "provider_auth_failed"),
        (403, "provider_auth_failed"),
        (429, "provider_rate_limited"),
        (503, "provider_unavailable"),
        (307, "provider_rejected"),
        (404, "provider_rejected"),
    ],
)
async def test_upstream_errors_are_safe_and_do_not_retry(status, code):
    result, requests = await call(
        "chat",
        {"error": {"message": TARGET.api_key}},
        status,
        {"Retry-After": "5", "Location": "https://other.example"},
    )
    assert len(requests) == 1 and result.code == code
    assert result.http_status == status and TARGET.api_key not in repr(result)
    assert result.retry_after is not None


async def test_chat_uses_runtime_shape_and_rejects_empty_content():
    body = {
        "model": "upstream-model",
        "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 9},
    }
    result, requests = await call("chat", body)
    assert result.outcome == "ok" and result.observed_model == "upstream-model"
    assert result.total_tokens == 9
    assert json.loads(requests[0].content)["stream"] is False
    body["choices"][0]["message"]["content"] = ""
    result, _ = await call("chat", body)
    assert result.code == "chat_response_empty"


@pytest.mark.parametrize("vector", [[0, 0], [1, float("inf")], [True, 1], []])
async def test_bad_embedding_does_not_become_verified(vector):
    # Infinity deliberately uses a raw JSON response to exercise decoder validation.
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            content=json.dumps({"data": [{"index": 0, "embedding": vector}]}),
            headers={"content-type": "application/json"},
        )
    )
    result = await HttpProviderDiagnosticClient(transport=transport).check("embedding", TARGET)
    assert result.outcome == "failed"


async def test_dimension_is_observed_and_configured_dimension_is_enforced():
    body = {"data": [{"index": 0, "embedding": [1.0, 2.0]}]}
    result, _ = await call("embedding", body)
    assert result.observed_dimension == 2
    mismatch, _ = await call("embedding", body, target=replace(TARGET, expected_dimension=3))
    assert mismatch.code == "embedding_dimension_mismatch"


async def test_rerank_requires_valid_unique_indexes():
    result, _ = await call(
        "rerank",
        {
            "results": [
                {"index": 0, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.3},
            ]
        },
    )
    assert result.code == "rerank_response_invalid"


async def test_ocr_requires_located_layout_and_uses_a_generated_page():
    result, requests = await call(
        "ocr",
        {
            "choices": [
                {
                    "message": {"content": "<x_0.1><y_0.1>QNU TEST 123<x_0.9><y_0.8><class_Text>"},
                    "finish_reason": "stop",
                }
            ]
        },
        target=replace(TARGET, provider_type="openai_compatible"),
    )
    assert result.outcome == "ok"
    message = json.loads(requests[0].content)["messages"][0]["content"]
    assert message[1]["image_url"]["url"].startswith("data:image/png;base64,")
    bad, _ = await call("ocr", {"choices": [{"message": {"content": "plain text"}}]})
    assert bad.outcome == "failed"


async def test_policy_and_missing_credentials_do_not_send_http():
    def forbidden(_):
        pytest.fail("HTTP must not be called")

    client = HttpProviderDiagnosticClient(transport=httpx.MockTransport(forbidden))
    blocked = await client.check("chat", replace(TARGET, endpoint="http://169.254.169.254/v1"))
    assert blocked.code == "endpoint_blocked"
    missing = await client.check("chat", replace(TARGET, api_key=None))
    assert missing.code == "credentials_missing"
    unsupported = await client.check("chat", replace(TARGET, provider_type="gemini"))
    assert unsupported.outcome == "unsupported"


async def test_timeout_is_unknown_not_an_empty_success():
    def timeout(request):
        raise httpx.ReadTimeout("unsafe private body", request=request)

    result = await HttpProviderDiagnosticClient(transport=httpx.MockTransport(timeout)).check(
        "chat", TARGET
    )
    assert result.code == "provider_timeout" and result.outcome == "failed"
    assert "unsafe" not in repr(result)


async def test_total_deadline_bounds_a_slow_upstream():
    async def slow(_):
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={"data": []})

    result = await HttpProviderDiagnosticClient(transport=httpx.MockTransport(slow)).check(
        "discovery", replace(TARGET, timeout_seconds=0.01)
    )
    assert result.code == "provider_timeout" and result.outcome == "failed"


async def test_http_200_error_is_not_an_empty_model_list():
    result, _ = await call("discovery", {"error": {"message": TARGET.api_key}, "data": []})
    assert result.outcome == "failed" and TARGET.api_key not in repr(result)


async def test_discovery_keeps_only_validated_capacity_fields():
    result, _ = await call(
        "discovery",
        {
            "data": [
                {
                    "id": "server-model",
                    "max_model_len": 131072,
                    "max_output_tokens": 16384,
                    "embedding_dimension": 1024,
                    "secret": TARGET.api_key,
                    "root": TARGET.api_key,
                }
            ]
        },
    )
    assert result.model_metadata[0].model_dump() == {
        "id": "server-model",
        "context_window_tokens": 131072,
        "max_output_tokens": 16384,
        "embedding_dimension": 1024,
    }
    assert TARGET.api_key not in repr(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_model_len", True),
        ("max_model_len", "8192"),
        ("max_model_len", 0),
        ("max_model_len", -1),
        ("max_model_len", 3.5),
        ("context_length", True),
        ("context_length", "8192"),
        ("max_completion_tokens", 3.5),
        ("embedding_dimension", 65537),
        ("max_output_tokens", 8193),
    ],
)
async def test_discovery_rejects_invalid_metadata_without_leaking_raw(field, value):
    result, _ = await call(
        "discovery", {"data": [{"id": "a", "max_model_len": 8192, field: value}]}
    )
    assert result.code == "provider_response_invalid"
    assert result.models == [] and result.model_metadata == []


async def test_discovery_reads_openai_catalog_limit_aliases():
    result, _ = await call(
        "discovery",
        {
            "data": [
                {
                    "id": "cx/gpt-6-luna",
                    "context_length": 200000,
                    "max_completion_tokens": 64000,
                    "capabilities": {"contextWindow": 200000, "maxOutput": 64000},
                }
            ]
        },
    )
    assert result.model_metadata[0].model_dump() == {
        "id": "cx/gpt-6-luna",
        "context_window_tokens": 200000,
        "max_output_tokens": 64000,
        "embedding_dimension": None,
    }


async def test_discovery_rejects_conflicting_limit_aliases():
    result, _ = await call(
        "discovery",
        {"data": [{"id": "a", "max_model_len": 8192, "context_length": 16384}]},
    )
    assert result.code == "provider_response_invalid"
    assert result.models == [] and result.model_metadata == []


async def test_discovery_rejects_ambiguous_duplicate_ids():
    result, _ = await call(
        "discovery",
        {"data": [{"id": "a", "max_model_len": 1024}, {"id": "a", "max_model_len": 8192}]},
    )
    assert result.outcome == "failed" and result.model_metadata == []


@pytest.mark.parametrize("count", [638, 5000])
async def test_gateway_catalog_preserves_models_beyond_the_first_500(count):
    rows = [{"id": f"gateway/model-{index}"} for index in range(count)]
    rows[-1] = {"id": "ollama/gpt-oss:120b"}
    result, requests = await call("discovery", {"object": "list", "data": rows})
    assert result.outcome == "ok" and result.http_status == 200
    assert len(result.models) == len(result.model_metadata) == count
    assert "ollama/gpt-oss:120b" in result.models
    assert len(requests) == 1


async def test_gateway_catalog_over_limit_is_explicit_not_silently_truncated():
    result, _ = await call(
        "discovery", {"data": [{"id": f"model-{index}"} for index in range(5001)]}
    )
    assert result.code == "provider_catalog_too_large" and result.http_status == 200
    assert result.models == [] and result.model_metadata == []


@pytest.mark.parametrize("tail", [{"id": "model-0"}, {"id": TARGET.api_key}, {"id": 123}])
async def test_large_catalog_still_validates_every_row(tail):
    rows = [{"id": f"model-{index}"} for index in range(637)] + [tail]
    result, _ = await call("discovery", {"data": rows})
    assert result.code == "provider_response_invalid"
    assert result.models == [] and result.model_metadata == []
    assert TARGET.api_key not in repr(result)
