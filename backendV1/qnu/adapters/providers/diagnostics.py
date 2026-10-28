"""Diagnostics share runtime URL builders, payloads, validators and egress policy.

No retries, redirects, environment proxies, raw upstream errors or response persistence.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx

from qnu.adapters.providers.embedding import decode_embeddings, embeddings_url
from qnu.adapters.providers.nemotron import (
    _decode_response as decode_ocr,
)
from qnu.adapters.providers.nemotron import (
    build_payload,
)
from qnu.adapters.providers.nemotron import (
    completions_url as ocr_url,
)
from qnu.adapters.providers.openai_compatible import _decode as decode_chat
from qnu.adapters.providers.openai_compatible import completions_url
from qnu.adapters.providers.reranker import decode as decode_rerank
from qnu.domains.ocr.public_api import OCR_PROMPT, validate_located_text
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.chat_model import ChatRequest
from qnu.ports.embedding_model import EmbeddingRequest
from qnu.ports.ocr_engine import OcrRequest
from qnu.ports.provider_diagnostics import DiagnosticKind, DiagnosticResult, DiagnosticTarget


def models_url(endpoint: str) -> str:
    base = endpoint.strip().rstrip("/")
    for suffix in ("/chat/completions", "/embeddings", "/rerank", "/models"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base + ("/models" if base.endswith("/v1") else "/v1/models")


def sample_page() -> bytes:
    import fitz

    with fitz.open() as document:
        page = document.new_page(width=420, height=120)
        page.insert_text((20, 65), "QNU TEST 123", fontsize=28)
        return page.get_pixmap(dpi=100).tobytes("png")


def retry_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.strip().isdigit():
            return datetime.now(UTC) + timedelta(seconds=min(int(value), 604800))
        date = parsedate_to_datetime(value)
        return date.replace(tzinfo=UTC) if date.tzinfo is None else date.astimezone(UTC)
    except (ValueError, TypeError, OverflowError):
        return None


def failed(code: str, detail: str, **kwargs) -> DiagnosticResult:
    return DiagnosticResult("failed", code, detail, **kwargs)


async def payload(kind: DiagnosticKind, target: DiagnosticTarget) -> tuple[str, dict | None]:
    if kind == "discovery":
        return models_url(target.endpoint), None
    if kind == "embedding":
        return embeddings_url(target.endpoint), {
            "model": target.model,
            "input": ["QNU connection test"],
            "encoding_format": "float",
        }
    if kind == "rerank":
        base = target.endpoint.rstrip("/")
        url = (
            base
            if base.endswith("/rerank")
            else base + ("/rerank" if base.endswith("/v1") else "/v1/rerank")
        )
        return url, {
            "model": target.model,
            "query": "QNU",
            "documents": ["QNU test", "Sample"],
            "top_n": 2,
        }
    if kind == "ocr":
        request = OcrRequest(
            target.endpoint,
            target.model,
            OCR_PROMPT,
            target.max_output_tokens,
            target.timeout_seconds,
            target.api_key,
        )
        return ocr_url(target.endpoint), build_payload(
            request, await asyncio.to_thread(sample_page)
        )
    return completions_url(target.endpoint), {
        "model": target.model,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "max_tokens": target.max_output_tokens,
        "stream": False,
    }


def validate(
    kind: DiagnosticKind, target: DiagnosticTarget, response: httpx.Response
) -> DiagnosticResult:
    data = response.json()
    if isinstance(data, dict) and data.get("error") is not None:
        raise ValueError("Upstream error envelope")
    result = DiagnosticResult("ok", "diagnostic_ok", "Yêu cầu thử trả kết quả hợp lệ.")
    observed = data.get("model") if isinstance(data, dict) else None
    if (
        isinstance(observed, str)
        and 0 < len(observed) <= 200
        and observed.isprintable()
        and not (target.api_key and target.api_key in observed)
    ):
        result.observed_model = observed
    if kind == "discovery":
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValueError("Invalid model catalog")
        ids = []
        for row in rows:
            model = row.get("id") if isinstance(row, dict) else None
            if not isinstance(model, str) or not 0 < len(model) <= 200 or not model.isprintable():
                raise ValueError("Invalid model ID")
            if target.api_key and target.api_key in model:
                raise ValueError("Credential reflected by upstream")
            ids.append(model)
        result.models = sorted(set(ids))
        result.detail = "Đã lấy danh sách; các model chưa được kiểm tra inference."
    elif kind == "embedding":
        vectors, result.total_tokens = decode_embeddings(
            data,
            1,
            EmbeddingRequest(
                target.endpoint,
                target.model,
                target.timeout_seconds,
                target.api_key,
                target.expected_dimension,
            ),
        )
        result.observed_dimension = len(vectors[0])
    elif kind == "rerank":
        result.total_tokens = decode_rerank(data, 2, 2, target.model).total_tokens
    elif kind == "ocr":
        text, _ = decode_ocr(response)
        validate_located_text(text)
        result.detail = "OCR trả khối có tọa độ hợp lệ; chưa đo chất lượng tài liệu thực tế."
    else:
        decoded = decode_chat(
            response,
            ChatRequest(
                endpoint=target.endpoint,
                model=target.model,
                max_output_tokens=target.max_output_tokens,
                timeout_seconds=target.timeout_seconds,
                api_key=target.api_key,
            ),
        )
        result.total_tokens = decoded.total_tokens
        result.detail = "Chat cơ bản hợp lệ; chưa kiểm định chất lượng hoặc strict JSON."
    return result


class HttpProviderDiagnosticClient:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def check(self, kind: DiagnosticKind, target: DiagnosticTarget) -> DiagnosticResult:
        supported = target.provider_type in {"openai_compatible", "local"} or (
            target.provider_type == "nemotron" and kind in {"discovery", "ocr"}
        )
        if not supported:
            return DiagnosticResult(
                "unsupported",
                "diagnostic_unsupported",
                "Chưa có adapter kiểm tra cho loại provider/chức năng này.",
            )
        if not target.api_key and not target.auth_optional:
            return failed("credentials_missing", "Chưa có khóa đang hoạt động.")
        started = time.monotonic()
        sent = False
        try:
            # Validate before building an OCR image or attaching any credential header.
            assert_allowed_endpoint(target.endpoint, allow_private=not get_settings().is_production)
            async with asyncio.timeout(target.timeout_seconds):
                url, body = await payload(kind, target)
                assert_allowed_endpoint(url, allow_private=not get_settings().is_production)
                async with httpx.AsyncClient(
                    timeout=target.timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self.transport,
                ) as client:
                    sent = True
                    response = await client.request(
                        "GET" if kind == "discovery" else "POST",
                        url,
                        headers={"Authorization": "Bearer " + target.api_key}
                        if target.api_key
                        else {},
                        json=body,
                    )
            result = self.decode(kind, target, response)
        except AppException:
            result = failed("endpoint_blocked", "Endpoint bị chặn bởi chính sách mạng.")
        except httpx.InvalidURL:
            result = failed("endpoint_invalid", "Địa chỉ server không hợp lệ.")
        except (httpx.TimeoutException, TimeoutError):
            result = failed(
                "provider_timeout", "Hết thời gian chờ; chưa xác định kết quả upstream."
            )
        except httpx.RequestError:
            result = failed("provider_unreachable", "Không kết nối được server model.")
        result.latency_ms = int((time.monotonic() - started) * 1000) if sent else None
        return result

    @staticmethod
    def decode(kind: DiagnosticKind, target: DiagnosticTarget, response: httpx.Response):
        status = response.status_code
        reason = None
        if status in (401, 403):
            reason = ("provider_auth_failed", "Server từ chối khóa hoặc quyền truy cập.")
        elif status == 429:
            reason = ("provider_rate_limited", "Server giới hạn tần suất; chờ trước khi thử lại.")
        elif status >= 500:
            reason = ("provider_unavailable", "Server model đang gặp lỗi.")
        elif status != 200:
            reason = (
                "provider_rejected",
                "Server từ chối yêu cầu thử hoặc endpoint không phù hợp.",
            )
        if reason:
            return failed(
                *reason,
                http_status=status,
                retry_after=retry_time(response.headers.get("retry-after")),
            )
        try:
            result = validate(kind, target, response)
        except AppException as exc:
            result = failed(exc.code, "Phản hồi không đúng hợp đồng của chức năng.")
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            result = failed(
                "provider_response_invalid", "Phản hồi không đúng hợp đồng của chức năng."
            )
        result.http_status = status
        return result
