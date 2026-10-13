"""Health probes call the same transport as real chat, without failover."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.exceptions import AppException
from app.modules.modelops.providers import get_llm_adapter
from app.modules.modelops.providers.chat_contract import PROBE_OUTPUT_BUDGET, safe_error_message
from app.modules.modelops.schemas import ChatMessage
from app.modules.modelops.services.capability_probe import classify_http_status


async def probe_chat(
    provider_type: str,
    model_name: str,
    base_url: str | None,
    api_key: str | None,
    capabilities: dict[str, Any] | None = None,
    timeout_seconds: int = 15,
    account_id: str | None = None,
) -> dict[str, Any]:
    result = {
        "model_name": model_name,
        "success": False,
        "status": "error",
        "latency_ms": 0.0,
        "tested_at": datetime.now(UTC).isoformat(),
    }
    started = time.perf_counter()
    try:
        adapter = get_llm_adapter(
            provider_type,
            model_name,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            account_id=account_id,
            request_capabilities=capabilities,
        )
        budget = max(PROBE_OUTPUT_BUDGET, int((capabilities or {}).get("minimum_output_tokens", 1)))
        if budget > 256:
            raise AppException(
                "Hạn mức tối thiểu vượt ngân sách probe; cần kiểm tra có chủ đích.",
                code="MODEL_REQUEST_CONFIG_INVALID",
                status_code=422,
            )
        async with asyncio.timeout(timeout_seconds):
            answer = await adapter.generate(
                [ChatMessage(role="user", content="Reply OK.")],
                temperature=0.2,
                max_tokens=budget,
                probe=True,
            )
        if not isinstance(answer.content, str) or not answer.content.strip():
            raise AppException(
                "Model không trả nội dung trả lời.",
                code="MODEL_RESPONSE_PROTOCOL_ERROR",
                status_code=502,
            )
        result.update(
            success=True,
            http_status=200,
            status="available",
            latency_ms=answer.latency_ms,
            served_model=answer.model,
            request_capabilities=getattr(adapter, "request_capabilities", {}),
            message=f"Model '{model_name}' trả nội dung hợp lệ; model phục vụ: {answer.model}.",
        )
        if getattr(adapter, "request_capabilities", {}).get("temperature_supported") is False:
            result["message"] += " Model không hỗ trợ temperature; request đã bỏ tham số này."
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        result.update(
            http_status=status,
            error_code="MODEL_REQUEST_REJECTED" if status == 400 else "PROVIDER_HTTP_ERROR",
            status=classify_http_status(status),
            message=f"{'Request kiểm tra bị từ chối' if status == 400 else 'Provider phản hồi lỗi'} (HTTP {status}): "
            + safe_error_message(exc.response, api_key),
        )
    except AppException as exc:
        result.update(
            error_code=exc.code,
            message=exc.message,
            http_status=200
            if exc.code in {"MODEL_OUTPUT_BUDGET_EXHAUSTED", "MODEL_RESPONSE_PROTOCOL_ERROR"}
            else None,
        )
    except (TimeoutError, httpx.TimeoutException):
        result.update(
            error_code="PROVIDER_TIMEOUT",
            message=f"Hết thời gian kiểm tra ({timeout_seconds}s); chưa xác minh được model.",
        )
    except httpx.RequestError as exc:
        result.update(
            error_code="PROVIDER_CONNECTION_ERROR",
            message=f"Không thể kết nối provider ({type(exc).__name__}).",
        )
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, httpx.InvalidURL):
        result.update(
            error_code="MODEL_RESPONSE_PROTOCOL_ERROR",
            message="Provider hoặc dữ liệu phản hồi không đúng giao thức đã cấu hình.",
        )
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return result
