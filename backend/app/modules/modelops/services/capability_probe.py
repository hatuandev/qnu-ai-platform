"""Capability-specific HTTP probes, selected by metadata rather than model spelling."""

import math
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import AppException
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.providers.chat_contract import safe_error_message


def classify_http_status(status: int) -> str:
    return {
        404: "unavailable",
        410: "deprecated",
        402: "payment_required",
        429: "rate_limited",
        503: "temporarily_overloaded",
        504: "temporarily_overloaded",
        529: "temporarily_overloaded",
    }.get(status, "error")


def valid_vector(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)
            for n in value
        )
    )


def embedding_vector(data: dict, provider_type: str) -> Any:
    result = data.get("result", data)
    if provider_type == "gemini":
        return result.get("embedding", {}).get("values")
    vectors = result.get("data", [])
    return (
        vectors[0].get("embedding")
        if vectors and isinstance(vectors[0], dict)
        else vectors[0]
        if vectors
        else None
    )


def validate_capability(data: Any, role: str, provider_type: str, model: str) -> None:
    if (
        not isinstance(data, dict)
        or data.get("error")
        or data.get("errors")
        or data.get("success") is False
    ):
        raise ValueError("Provider error body")
    result = data.get("result", data)
    if role == "embedding":
        vector = embedding_vector(data, provider_type)
        if valid_vector(vector):
            return
    elif role == "reranker":
        rows = (
            result
            if isinstance(result, list)
            else result.get("results", result.get("data", result.get("response", [])))
        )
        if (
            isinstance(rows, list)
            and len(rows) == 1
            and isinstance(rows[0], dict)
            and rows[0].get("index", rows[0].get("id")) == 0
        ):
            score = rows[0].get("relevance_score", rows[0].get("score"))
            if (
                isinstance(score, (int, float))
                and not isinstance(score, bool)
                and math.isfinite(score)
            ):
                return
    elif role == "ocr":
        ids = [
            row.get("id", row.get("name"))
            for row in result.get("data", result.get("models", []))
            if isinstance(row, dict)
        ]
        if model in ids:
            return
    raise ValueError("Invalid capability response")


async def probe_capability(
    provider_type: str,
    model: str,
    base_url: str | None,
    api_key: str | None,
    role: str,
    timeout_seconds: int,
    account_id: str | None = None,
) -> dict[str, Any]:
    result = {
        "model_name": model,
        "success": False,
        "status": "error",
        "latency_ms": 0,
        "tested_at": datetime.now(UTC).isoformat(),
        "probe_role": role,
        "verification_scope": "catalogue" if role == "ocr" else "inference",
    }
    start = time.perf_counter()
    try:
        adapter = get_llm_adapter(
            provider_type,
            model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            account_id=account_id,
        )
        if not api_key and provider_type != "ollama":
            raise AppException(
                "Provider chưa có khóa sử dụng được.",
                code="PROVIDER_CREDENTIALS_MISSING",
                status_code=401,
            )
        base = (adapter.base_url or "").rstrip("/")
        if provider_type == "claude":
            raise AppException(
                "Anthropic native hỗ trợ probe Chat; vai trò này cần provider tương ứng.",
                code="MODEL_PROBE_UNSUPPORTED",
                status_code=422,
            )
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        payload: dict[str, Any] = {"model": model, "input": ["ping"]}
        endpoint = base + "/embeddings"
        if role == "reranker":
            endpoint = base + "/rerank"
            payload = {"model": model, "query": "ping", "documents": ["ping"], "top_n": 1}
        if provider_type == "gemini":
            resource = model if model.startswith("models/") else f"models/{model}"
            headers = {"x-goog-api-key": api_key or ""}
            endpoint = f"{base}/{resource}:embedContent"
            payload = {"model": resource, "content": {"parts": [{"text": "ping"}]}}
            if role == "ocr":
                endpoint = f"{base}/{resource}"
            elif role != "embedding":
                raise AppException(
                    "Vai trò này chưa có probe trên Gemini.",
                    code="MODEL_PROBE_UNSUPPORTED",
                    status_code=422,
                )
        elif provider_type == "cloudflare":
            if not account_id:
                raise AppException(
                    "Thiếu Cloudflare Account ID.",
                    code="PROVIDER_CREDENTIALS_MISSING",
                    status_code=401,
                )
            base = base.replace("{account_id}", account_id)
            endpoint = f"{base}/{model}"
            payload = (
                {"text": ["ping"]}
                if role == "embedding"
                else {"query": "ping", "contexts": [{"text": "ping"}]}
            )
            if role == "ocr":
                raise AppException(
                    "Cloudflare OCR cần kiểm thử bóc tách; probe danh mục chưa hỗ trợ.",
                    code="MODEL_PROBE_UNSUPPORTED",
                    status_code=422,
                )
        if role == "ocr" and provider_type != "gemini":
            endpoint = base + "/models"
        async with httpx.AsyncClient(timeout=timeout_seconds, trust_env=False) as client:
            response = (
                await client.get(endpoint, headers=headers)
                if role == "ocr"
                else await client.post(endpoint, headers=headers, json=payload)
            )
        result["http_status"] = response.status_code
        if not response.is_success:
            result.update(
                status=classify_http_status(response.status_code),
                error_code="PROVIDER_HTTP_ERROR",
                message=safe_error_message(response, api_key),
            )
        else:
            data = response.json()
            if role == "ocr" and provider_type == "gemini" and data.get("name") == resource:
                data = {"models": [{"id": model}]}
            validate_capability(data, role, provider_type, model)
            if role == "embedding":
                result["embedding_dimension"] = len(embedding_vector(data, provider_type))
            result.update(
                success=True,
                status="available",
                message="Model có trong danh mục; chưa kiểm thử OCR."
                if role == "ocr"
                else f"Model trả kết quả {role} hợp lệ.",
            )
    except AppException as exc:
        result.update(error_code=exc.code, message=exc.message)
    except httpx.TimeoutException:
        result.update(
            error_code="PROVIDER_TIMEOUT", message=f"Hết thời gian kiểm tra ({timeout_seconds}s)."
        )
    except httpx.RequestError:
        result.update(
            error_code="PROVIDER_CONNECTION_ERROR", message="Không kết nối được provider."
        )
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, httpx.InvalidURL):
        result.update(
            error_code="MODEL_RESPONSE_PROTOCOL_ERROR",
            message=f"Provider không trả kết quả {role} đúng cấu trúc.",
        )
    result["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
    return result
