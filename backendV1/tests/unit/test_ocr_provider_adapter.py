"""Provider adapter behaviour: URL normalisation, payload shape and error mapping.

The mapping matters because the run row stores the code: config, permission, quota,
timeout, transport and malformed-response failures must stay distinguishable.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from qnu.adapters.providers.nemotron import (
    NemotronOcrEngine,
    build_payload,
    completions_url,
)
from qnu.domains.ocr.errors import is_uncertain
from qnu.platform.errors import AppException
from qnu.ports.ocr_engine import OcrRequest

REQUEST = OcrRequest(
    endpoint="http://127.0.0.1:9",
    model="nemotron-parse",
    prompt="</s><s><predict_bbox>",
    max_tokens=8192,
    timeout_seconds=1.0,
    api_key="secret-key-value",
)
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def stub_http(monkeypatch):
    """Install a stub transport so no socket is opened, and return a bound engine."""

    def install(handler) -> NemotronOcrEngine:
        original = httpx.AsyncClient

        def factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return original(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", factory)
        return NemotronOcrEngine()

    return install


def _answer(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def _ok(text: str, *, finish_reason: str = "stop", total_tokens: int | None = 140) -> dict:
    payload: dict = {
        "choices": [{"message": {"content": text}, "finish_reason": finish_reason}],
    }
    if total_tokens is not None:
        payload["usage"] = {"total_tokens": total_tokens}
    return payload


def test_base_url_is_normalised_to_chat_completions() -> None:
    assert completions_url("https://ocr.example.vn") == "https://ocr.example.vn/v1/chat/completions"
    assert completions_url("https://ocr.example.vn/") == "https://ocr.example.vn/v1/chat/completions"
    assert completions_url("https://ocr.example.vn/v1") == "https://ocr.example.vn/v1/chat/completions"
    assert (
        completions_url("https://ocr.example.vn/v1/chat/completions")
        == "https://ocr.example.vn/v1/chat/completions"
    )


def test_payload_sends_the_image_as_a_data_uri_without_a_storage_path() -> None:
    payload = build_payload(REQUEST, PNG)
    image = payload["messages"][0]["content"][1]["image_url"]["url"]
    assert image.startswith("data:image/png;base64,")
    assert base64.b64decode(image.split(",", 1)[1]) == PNG
    assert payload["model"] == "nemotron-parse"
    assert payload["max_tokens"] == 8192
    assert payload["temperature"] == 0
    assert payload["skip_special_tokens"] is False


async def test_successful_call_returns_text_and_measured_tokens(stub_http) -> None:
    engine = stub_http(lambda request: _answer(_ok("<x_0.1><y_0.1>A<x_0.9><y_0.2><class_Text>")))
    response = await engine.extract_page(PNG, REQUEST)
    assert "class_Text" in response.text
    assert response.usage_tokens == 140
    assert response.raw["choices"][0]["finish_reason"] == "stop"


async def test_missing_usage_is_null_not_zero(stub_http) -> None:
    engine = stub_http(lambda request: _answer(_ok("A", total_tokens=None)))
    assert (await engine.extract_page(PNG, REQUEST)).usage_tokens is None


async def test_the_credential_is_sent_as_a_bearer_header(stub_http) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("Authorization", "")
        seen["url"] = str(request.url)
        return _answer(_ok("A"))

    await stub_http(handler).extract_page(PNG, REQUEST)
    assert seen["authorization"] == "Bearer secret-key-value"
    assert seen["url"].endswith("/v1/chat/completions")


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "ocr_provider_auth_failed"),
        (403, "ocr_provider_auth_failed"),
        (429, "ocr_provider_rate_limited"),
        (500, "ocr_provider_unavailable"),
        (503, "ocr_provider_unavailable"),
        (400, "ocr_provider_rejected"),
    ],
)
async def test_http_status_maps_to_a_distinct_code(stub_http, status: int, code: str) -> None:
    engine = stub_http(lambda request: _answer({"error": "nope"}, status=status))
    with pytest.raises(AppException) as caught:
        await engine.extract_page(PNG, REQUEST)
    assert caught.value.code == code


async def test_timeout_is_uncertain_and_not_retried_blindly(stub_http) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(AppException) as caught:
        await stub_http(handler).extract_page(PNG, REQUEST)
    assert caught.value.code == "ocr_provider_timeout"
    assert is_uncertain(caught.value.code) is True


async def test_transport_failure_is_unreachable(stub_http) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(AppException) as caught:
        await stub_http(handler).extract_page(PNG, REQUEST)
    assert caught.value.code == "ocr_provider_unreachable"
    assert is_uncertain(caught.value.code) is False


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        json.dumps({"choices": []}),
        json.dumps({"choices": [{"message": {}}]}),
        json.dumps({"choices": ["nope"]}),
        json.dumps([1, 2, 3]),
    ],
)
async def test_malformed_bodies_are_invalid_responses(stub_http, body: str) -> None:
    engine = stub_http(lambda request: httpx.Response(200, text=body))
    with pytest.raises(AppException) as caught:
        await engine.extract_page(PNG, REQUEST)
    assert caught.value.code == "ocr_response_invalid"


async def test_truncated_output_is_refused_instead_of_partial_text(stub_http) -> None:
    engine = stub_http(lambda request: _answer(_ok("một nửa", finish_reason="length")))
    with pytest.raises(AppException) as caught:
        await engine.extract_page(PNG, REQUEST)
    assert caught.value.code == "ocr_output_truncated"


async def test_empty_content_is_refused(stub_http) -> None:
    engine = stub_http(lambda request: _answer(_ok("   ")))
    with pytest.raises(AppException) as caught:
        await engine.extract_page(PNG, REQUEST)
    assert caught.value.code == "ocr_response_empty"


async def test_missing_credential_is_a_configuration_error() -> None:
    anonymous = OcrRequest(
        endpoint=REQUEST.endpoint,
        model=REQUEST.model,
        prompt=REQUEST.prompt,
        max_tokens=REQUEST.max_tokens,
        timeout_seconds=REQUEST.timeout_seconds,
        api_key=None,
    )
    with pytest.raises(AppException) as caught:
        await NemotronOcrEngine().extract_page(PNG, anonymous)
    assert caught.value.code == "ocr_credentials_missing"
    assert caught.value.status_code == 503


async def test_empty_image_is_refused_before_any_call() -> None:
    with pytest.raises(AppException) as caught:
        await NemotronOcrEngine().extract_page(b"", REQUEST)
    assert caught.value.code == "ocr_input_empty"


async def test_logs_never_contain_the_credential_or_the_image(stub_http, capsys) -> None:
    # The application logger writes structured lines to stdout, so capture that stream.
    engine = stub_http(lambda request: _answer(_ok("A")))
    await engine.extract_page(PNG, REQUEST)
    combined = capsys.readouterr().out
    assert "ocr_page_called" in combined
    assert "secret-key-value" not in combined
    assert "data:image/png;base64" not in combined
    assert base64.b64encode(PNG).decode("ascii") not in combined
