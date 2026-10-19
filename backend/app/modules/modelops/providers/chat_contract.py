"""Model-agnostic OpenAI chat contract and bounded capability negotiation."""

from __future__ import annotations

import asyncio
import json
import re
import time
from hashlib import sha256
from typing import Any

import httpx

from app.core.exceptions import AppException
from app.modules.modelops.providers.context_budget import fit_rejected_context
from app.modules.modelops.services.inference_policy import (
    charge_chat_input,
    minimum_chat_output,
    retry_transient_response,
)

TOKEN_PARAMETERS = frozenset({"max_tokens", "max_completion_tokens", "max_output_tokens"})
MAX_NEGOTIATIONS = 3
PROBE_OUTPUT_BUDGET = 32
MAX_PROBE_OUTPUT_BUDGET = 256


def safe_error_message(response: httpx.Response, secret: str | None = None) -> str:
    """Only provider error text, never HTML/request headers or full URLs."""
    try:
        body = response.json()
        error = body.get("error", {}) if isinstance(body, dict) else {}
        text = error.get("message", "") if isinstance(error, dict) else str(error)
    except ValueError:
        text = ""
    text = str(text)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r'https?://[^\s"<>]+', "[URL]", text)
    text = re.sub(r"(?:Bearer\s+|sk-|AIza)[\w./+=-]+", "[REDACTED]", text)
    return text[:1200] or f"Upstream HTTP {response.status_code}"


def build_chat_payload(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
    stream: bool,
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    parameter = capabilities.get("token_parameter", "max_tokens")
    if parameter not in TOKEN_PARAMETERS:
        raise AppException(
            "Tham số giới hạn token không hợp lệ.",
            code="MODEL_REQUEST_CONFIG_INVALID",
            status_code=422,
        )
    minimum = int(capabilities.get("minimum_output_tokens", 1))
    if max_tokens < minimum:
        raise AppException(
            f"Model yêu cầu ít nhất {minimum} output tokens; đang cấu hình {max_tokens}.",
            code="MODEL_REQUEST_CONFIG_INVALID",
            status_code=422,
        )
    payload = {"model": model, "messages": messages, parameter: max_tokens, "stream": stream}
    if capabilities.get("temperature_supported", True):
        payload["temperature"] = temperature
    return payload


def adapt_rejected_payload(
    response: httpx.Response,
    payload: dict[str, Any],
    capabilities: dict[str, Any],
    *,
    probe: bool = False,
) -> bool:
    """Only explicit HTTP400 parameter evidence permits one scoped change.

    Never alter model/endpoint/messages/auth, infer from model names, or raise a
    runtime token budget. Probe budgets alone may rise up to a fixed cost cap.
    """
    if response.status_code != 400:
        return False
    message = safe_error_message(response).replace('\\"', '"').replace("\\u003e", ">")
    unsupported = re.search(
        r"Unsupported (?:parameter|value):\s*['\"]([a-z_]+)['\"]", message, re.IGNORECASE
    )
    if unsupported and unsupported[1] == "temperature" and "temperature" in payload:
        payload.pop("temperature")
        capabilities["temperature_supported"] = False
        return True
    token_key = next((key for key in TOKEN_PARAMETERS if key in payload), None)
    minimum = re.search(
        r"Invalid\s+['\"](?:max_output_tokens|max_completion_tokens|max_tokens)['\"].*?Expected.*?>=\s*(\d+)",
        message,
        re.IGNORECASE | re.DOTALL,
    )
    if minimum and token_key:
        bound = int(minimum[1])
        capabilities["minimum_output_tokens"] = bound
        if probe and payload[token_key] < bound <= MAX_PROBE_OUTPUT_BUDGET:
            payload[token_key] = bound
            return True
    replacement = re.search(
        r"(?:use|with)\s+['\"](max_completion_tokens|max_output_tokens|max_tokens)['\"]",
        message,
        re.IGNORECASE,
    )
    if unsupported and unsupported[1] == token_key and replacement and replacement[1] != token_key:
        payload[replacement[1]] = payload.pop(token_key)
        capabilities["token_parameter"] = replacement[1]
        return True
    return False


async def post_chat(
    client: httpx.AsyncClient,
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    capabilities: dict[str, Any],
    *,
    probe: bool = False,
    output_contract: dict | None = None,
    trace: list | None = None,
) -> httpx.Response:
    timeout = client.timeout.read
    deadline = time.monotonic() + timeout if isinstance(timeout, (int, float)) else float("inf")
    try:
        async with asyncio.timeout_at(deadline):
            return await _post_chat(client, endpoint, headers, payload, capabilities, probe=probe, deadline=deadline,
                output_contract=output_contract, trace=trace)
    except TimeoutError as exc:
        raise httpx.ReadTimeout("Chat transport deadline exceeded") from exc


async def _post_chat(
    client: httpx.AsyncClient, endpoint: str, headers: dict[str, str],
    payload: dict[str, Any], capabilities: dict[str, Any], *, probe: bool, deadline: float,
    output_contract: dict | None = None, trace: list | None = None,
) -> httpx.Response:
    budget_retried = False
    context_retried = False
    for attempt in range(MAX_NEGOTIATIONS + 1):
        async def send():
            if output_contract is not None:
                request = client.build_request("POST", endpoint, headers=headers, json=payload)
                charge_chat_input(len(request.content))
                response = await client.send(request)
            else:
                response = await client.post(endpoint, headers=headers, json=payload)
            if trace is not None:
                trace.append({"http_status": response.status_code, "body_sha256": sha256(response.content).hexdigest(),
                    "request_bytes": len(response.request.content), "payload_sha256": sha256(response.request.content).hexdigest()})
            return response
        response = await send()
        if not probe and await retry_transient_response(response, deadline):
            response = await send()
        if attempt < MAX_NEGOTIATIONS and adapt_rejected_payload(
            response, payload, capabilities, probe=probe
        ):
            continue
        requested_output = next((payload[k] for k in TOKEN_PARAMETERS if k in payload), 1)
        minimum_output = minimum_chat_output(requested_output, int(capabilities.get("minimum_output_tokens", 1)))
        if (output_contract is None and attempt < MAX_NEGOTIATIONS and not context_retried and not probe and minimum_output < requested_output
                and await fit_rejected_context(client, endpoint, headers, payload, response,
                                               minimum_output)):
            context_retried = True
            continue
        if output_contract is not None and response.status_code == 400:
            from app.modules.modelops.services.key_rotation import (
                classify_key_failure,
                is_context_overflow_error,
            )
            request_error = httpx.HTTPStatusError("Upstream request rejected", request=response.request, response=response)
            if is_context_overflow_error(request_error) or classify_key_failure(request_error).state is not None:
                raise request_error
            try:
                error = response.json().get("error", {})
            except (ValueError, AttributeError):
                error = {}
            unsupported = isinstance(error, dict) and error.get("code") in {"unsupported_parameter", "unsupported_value"} and error.get("param") == "response_format"
            raise AppException("Provider từ chối hợp đồng request; không quay vòng key.",
                code="MODEL_OUTPUT_CONTRACT_UNSUPPORTED" if unsupported else "MODEL_OUTPUT_REQUEST_INVALID",
                status_code=422, details={"stage": "capability" if unsupported else "provider", "http_status": 400})
        response.raise_for_status()
        if (
            probe
            and not budget_retried
            and attempt < MAX_NEGOTIATIONS
            and completion_is_truncated(response)
        ):
            parameter = next((key for key in TOKEN_PARAMETERS if key in payload), None)
            if parameter and payload[parameter] < MAX_PROBE_OUTPUT_BUDGET:
                payload[parameter] = MAX_PROBE_OUTPUT_BUDGET
                budget_retried = True
                continue
        return response
    raise AssertionError("Bounded chat negotiation exhausted")


def completion_is_truncated(response: httpx.Response) -> bool:
    if "text/event-stream" in response.headers.get("content-type", ""):
        return False
    try:
        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        return (
            not data.get("error")
            and choice.get("finish_reason") == "length"
            and message.get("content") in (None, "")
        )
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return False


def decode_completion(response: httpx.Response, *, output_contract: dict | None = None) -> tuple[str, dict[str, Any], str | None]:
    if "text/event-stream" in response.headers.get("content-type", ""):
        raise AppException(
            "Provider trả streaming cho yêu cầu stream=false.",
            code="MODEL_RESPONSE_PROTOCOL_ERROR",
            status_code=502,
        )
    try:
        data = response.json()
        if output_contract is not None and len(data["choices"]) != 1:
            raise ValueError("Contract requires exactly one choice")
        choice = data["choices"][0]
        if output_contract is None and choice.get("finish_reason") == "length":
            raise AppException(
                "Model đã hết ngân sách đầu ra; câu trả lời chưa hoàn tất.",
                code="MODEL_OUTPUT_BUDGET_EXHAUSTED", status_code=502,
            )
        content = choice["message"].get("content")
        if output_contract is not None and content is None:
            content = ""
        if not isinstance(content, str) or (output_contract is None and not content.strip()) or data.get("error"):
            raise ValueError("No answer content")
        usage = data.get("usage") or {}
        if not isinstance(usage, dict):
            raise TypeError("Invalid usage")
        return content, usage, data.get("model")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise AppException(
            "Provider không trả JSON completion có nội dung hợp lệ.",
            code="MODEL_RESPONSE_PROTOCOL_ERROR",
            status_code=502,
        ) from exc


def completion_metadata(response: httpx.Response) -> dict:
    data = response.json()
    choices = data.get("choices", [])
    choice = choices[0]
    finish = choice.get("finish_reason")
    if finish is not None and finish not in ("stop", "length", "content_filter", "tool_calls", "function_call"):
        raise AppException("Provider trả finish metadata không hợp lệ.", code="MODEL_RESPONSE_PROTOCOL_ERROR", status_code=502)
    return {"finish_reason": finish, "refusal": choice.get("message", {}).get("refusal"),
        "response_metadata": {"request_id_sha256": sha256(response.headers["x-request-id"].encode()).hexdigest() if response.headers.get("x-request-id") else None,
            "response_id_sha256": sha256(str(data["id"]).encode()).hexdigest() if data.get("id") else None,
            "body_sha256": sha256(response.content).hexdigest(), "choice_count": len(choices),
            "content_parts": 1, "finish_reason_known": choice.get("finish_reason") is not None}}


def decode_stream_event(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    text = line[5:].strip()
    if text == "[DONE]":
        return {"done": True}
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("error"):
            raise ValueError("Invalid stream event")
        return data
    except ValueError as exc:
        raise AppException(
            "Provider trả SSE không hợp lệ.", code="MODEL_RESPONSE_PROTOCOL_ERROR", status_code=502
        ) from exc
