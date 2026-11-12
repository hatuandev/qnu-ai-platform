"""Local runtime native context discovery (Ollama, llama.cpp): bounded, opt-in, never invented."""

from dataclasses import replace

import httpx
import pytest

from qnu.adapters.providers.diagnostics import (
    HttpProviderDiagnosticClient,
    models_url,
    native_root,
)
from qnu.ports.provider_diagnostics import DiagnosticTarget

TARGET = DiagnosticTarget(
    "http://127.0.0.1:11434/v1",
    "configured-model",
    "local",
    5,
    api_key="fixture-secret",
)
LLAMA_TARGET = replace(TARGET, endpoint="http://127.0.0.1:8080/v1")


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:11434",
        "http://127.0.0.1:11434/",
        "http://127.0.0.1:11434/v1",
        "http://127.0.0.1:11434/v1/",
        "http://127.0.0.1:11434/v1/models",
        "http://127.0.0.1:11434/api/chat",
        "http://127.0.0.1:11434/api/tags",
    ],
)
def test_native_root_is_derived_from_configured_runtime_paths(endpoint):
    assert native_root(endpoint) == "http://127.0.0.1:11434"


async def run(handler, *, target=TARGET):
    requests = []

    def upstream(request):
        requests.append(request)
        return handler(request)

    result = await HttpProviderDiagnosticClient(transport=httpx.MockTransport(upstream)).check(
        "discovery", target
    )
    return result, requests


@pytest.mark.asyncio
async def test_native_context_enriches_only_the_unlabeled_snapshot():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}, {"id": "bge-m3:latest"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": "qwen3:8b"}, {"name": "bge-m3:latest"}]}
            )
        if b"qwen3" in request.content:
            return httpx.Response(
                200,
                json={
                    "model_info": {"general.architecture": "qwen3", "qwen3.context_length": 40960}
                },
            )
        return httpx.Response(200, json={"model_info": {"bert.context_length": 8192}})

    result, requests = await run(respond)
    assert result.outcome == "ok"
    assert [(row.id, row.context_window_tokens) for row in result.model_metadata] == [
        ("qwen3:8b", 40960),
        ("bge-m3:latest", 8192),
    ]
    assert all(row.max_output_tokens is None for row in result.model_metadata)
    assert all(row.embedding_dimension is None for row in result.model_metadata)
    assert [request.method for request in requests] == ["GET", "GET", "POST", "POST"]
    assert [request.url.path for request in requests] == [
        "/v1/models",
        "/api/tags",
        "/api/show",
        "/api/show",
    ]
    assert "server" in result.detail


@pytest.mark.asyncio
async def test_catalog_with_declared_context_is_not_probed():
    def respond(request):
        return httpx.Response(200, json={"data": [{"id": "listed", "max_model_len": 131072}]})

    result, requests = await run(respond)
    assert result.model_metadata[0].context_window_tokens == 131072
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_large_catalog_is_not_probed():
    ids = [{"id": f"model-{index}"} for index in range(33)]

    def respond(request):
        return httpx.Response(200, json={"data": ids})

    result, requests = await run(respond)
    assert len(result.models) == 33
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("native_status", [404, 500])
async def test_native_failure_keeps_the_openai_snapshot(native_status):
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "unlisted"}]})
        return httpx.Response(native_status, json={"error": "unavailable"})

    result, requests = await run(respond)
    assert result.outcome == "ok"
    assert result.model_metadata[0].context_window_tokens is None
    assert result.detail == "Đã lấy danh sách; các model chưa được kiểm tra inference."
    # Both native families are attempted; neither may change the snapshot.
    assert [request.url.path for request in requests] == ["/v1/models", "/api/tags", "/props"]


@pytest.mark.asyncio
async def test_one_failed_show_does_not_hide_another_model():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "a"}, {"name": "b"}]})
        if b'"a"' in request.content:
            return httpx.Response(500, json={"error": "broken"})
        return httpx.Response(200, json={"model_info": {"x.context_length": 32768}})

    result, requests = await run(respond)
    assert [(row.id, row.context_window_tokens) for row in result.model_metadata] == [
        ("a", None),
        ("b", 32768),
    ]
    assert len(requests) == 4


@pytest.mark.asyncio
async def test_invalid_context_values_are_not_recorded():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "a"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "a"}]})
        return httpx.Response(
            200,
            json={"model_info": {"general.architecture": "a", "a.context_length": True}},
        )

    result, _ = await run(respond)
    assert result.model_metadata[0].context_window_tokens is None


@pytest.mark.asyncio
async def test_native_probe_is_skipped_when_the_catalog_url_is_not_derivable():
    target = replace(TARGET, endpoint="https://gateway.example/team/ollama/v1")
    assert models_url(target.endpoint) == "https://gateway.example/team/ollama/v1/models"
    # A gateway path cannot be reduced to a local runtime host without guessing.
    assert native_root(target.endpoint) is None

    def respond(request):
        return httpx.Response(200, json={"data": [{"id": "gateway/model"}]})

    result, requests = await run(respond, target=target)
    assert result.outcome == "ok" and len(requests) == 1


@pytest.mark.asyncio
async def test_declared_ollama_type_enriches_via_tags():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "gpt-oss:120b"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gpt-oss:120b"}]})
        return httpx.Response(
            200,
            json={
                "model_info": {
                    "general.architecture": "gptoss",
                    "gptoss.context_length": 131072,
                }
            },
        )

    target = replace(TARGET, provider_type="ollama")
    result, requests = await run(respond, target=target)
    assert result.model_metadata[0].context_window_tokens == 131072
    assert [request.url.path for request in requests] == ["/v1/models", "/api/tags", "/api/show"]


@pytest.mark.asyncio
async def test_declared_llamacpp_type_probes_props_before_ollama_tags():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3.8-27b-q4"}]})
        return httpx.Response(
            200,
            json={
                "default_generation_settings": {"n_ctx": 65536},
                "model_path": "/models/qwen3.8-27b-q4.gguf",
            },
        )

    target = replace(LLAMA_TARGET, provider_type="llamacpp")
    result, requests = await run(respond, target=target)
    assert result.model_metadata[0].context_window_tokens == 65536
    assert [request.url.path for request in requests] == ["/v1/models", "/props"]


@pytest.mark.asyncio
async def test_llamacpp_props_context_enriches_the_single_served_model():
    model = "../models/Qwen3-8B-Q4_K_M.gguf"

    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": model}]})
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(
            200,
            json={
                "default_generation_settings": {"n_ctx": 32768},
                "total_slots": 4,
                "model_path": model,
            },
        )

    result, requests = await run(respond, target=LLAMA_TARGET)
    assert result.outcome == "ok"
    assert [(row.id, row.context_window_tokens) for row in result.model_metadata] == [
        (model, 32768)
    ]
    # n_ctx is per slot; total_slots must not multiply it into 131072.
    assert [request.url.path for request in requests] == [
        "/v1/models",
        "/api/tags",
        "/props",
    ]
    assert all(row.max_output_tokens is None for row in result.model_metadata)
    assert all(row.embedding_dimension is None for row in result.model_metadata)
    assert "server" in result.detail


@pytest.mark.asyncio
async def test_llamacpp_props_matches_the_served_file_among_many_models():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(
                200, json={"data": [{"id": "other-model"}, {"id": "Qwen3-8B-Q4_K_M"}]}
            )
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(
            200,
            json={
                "default_generation_settings": {"n_ctx": 16384},
                "model_path": "/opt/models/Qwen3-8B-Q4_K_M.gguf",
            },
        )

    result, _ = await run(respond, target=LLAMA_TARGET)
    assert [(row.id, row.context_window_tokens) for row in result.model_metadata] == [
        ("other-model", None),
        ("Qwen3-8B-Q4_K_M", 16384),
    ]


@pytest.mark.asyncio
async def test_llamacpp_ambiguous_catalog_stays_unknown():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(
            200,
            json={
                "default_generation_settings": {"n_ctx": 16384},
                "model_path": "/opt/models/unlisted.gguf",
            },
        )

    result, requests = await run(respond, target=LLAMA_TARGET)
    assert [row.context_window_tokens for row in result.model_metadata] == [None, None]
    assert result.detail == "Đã lấy danh sách; các model chưa được kiểm tra inference."
    assert len(requests) == 3


@pytest.mark.asyncio
async def test_llamacpp_does_not_overwrite_a_declared_context():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(
                200, json={"data": [{"id": "a.gguf", "max_model_len": 65536}, {"id": "b"}]}
            )
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(
            200,
            json={
                "default_generation_settings": {"n_ctx": 8192},
                "model_path": "/models/a.gguf",
            },
        )

    result, _ = await run(respond, target=LLAMA_TARGET)
    assert [(row.id, row.context_window_tokens) for row in result.model_metadata] == [
        ("a.gguf", 65536),
        ("b", None),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("declared", [True, 0, -1, 1.5, "32768"])
async def test_llamacpp_invalid_context_values_are_not_recorded(declared):
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "a"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(
            200,
            json={"default_generation_settings": {"n_ctx": declared}, "model_path": "a.gguf"},
        )

    result, _ = await run(respond, target=LLAMA_TARGET)
    assert result.model_metadata[0].context_window_tokens is None


@pytest.mark.asyncio
async def test_llamacpp_without_generation_settings_is_not_enriched():
    def respond(request):
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "a"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json={"total_slots": 1})

    result, _ = await run(respond, target=LLAMA_TARGET)
    assert result.model_metadata[0].context_window_tokens is None
