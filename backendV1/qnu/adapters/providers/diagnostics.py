"""Diagnostics share runtime URL builders, payloads, validators and egress policy.

No retries, redirects, environment proxies, raw upstream errors or response persistence.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

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
from qnu.ports.provider_diagnostics import (
    DiagnosticKind,
    DiagnosticResult,
    DiagnosticTarget,
    DiscoveredModel,
)

# Gateways aggregate many providers; bound the snapshot without truncating it.
MAX_DISCOVERED_MODELS = 5000
# Native context probes stay opt-in, small, and bounded inside the discovery deadline.
MAX_NATIVE_CONTEXT_MODELS = 32
NATIVE_PROBE_SECONDS = 5.0
MAX_CONTEXT_TOKENS = 2147483647
# Types that normally expose a direct OpenAI-compatible host; a runtime is still confirmed by probe.
NATIVE_DISCOVERY_TYPES = ("local", "openai_compatible", "ollama", "llamacpp")


def published_limit(row: dict, *keys: str) -> int | None:
    """Read one catalog limit; aliases must agree so contradictory data fails closed."""
    present = {key: row[key] for key in keys if key in row}
    if not present:
        return None
    values = set(present.values())
    if len(values) != 1 or type(next(iter(values))) is not int:
        raise ValueError("Invalid declared limit")
    return next(iter(values))


def models_url(endpoint: str) -> str:
    base = endpoint.strip().rstrip("/")
    for suffix in ("/chat/completions", "/embeddings", "/rerank", "/models"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base + ("/models" if base.endswith(("/v1", "/openai")) else "/v1/models")


def native_root(endpoint: str) -> str | None:
    """Only a direct host path can host a local runtime; a gateway path is not guessed."""
    base = endpoint.strip().rstrip("/")
    for suffix in (
        "/chat/completions",
        "/embeddings",
        "/rerank",
        "/models",
        "/api/tags",
        "/api/show",
        "/api/chat",
    ):
        if base.endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
    for suffix in ("/v1", "/api"):
        if base.endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
    return base if base and urlsplit(base).path in ("", "/") else None


def auth_headers(target: DiagnosticTarget) -> dict[str, str]:
    if not target.api_key:
        return {}
    if target.auth_scheme == "anthropic":
        return {"x-api-key": target.api_key, "anthropic-version": "2023-06-01"}
    return {"Authorization": "Bearer " + target.api_key}


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
        if not isinstance(rows, list):
            raise ValueError("Invalid model catalog")
        if len(rows) > MAX_DISCOVERED_MODELS:
            return failed(
                "provider_catalog_too_large",
                f"Danh sách vượt giới hạn {MAX_DISCOVERED_MODELS} model; chưa nhập danh sách.",
            )
        ids: set[str] = set()
        for row in rows:
            model = row.get("id") if isinstance(row, dict) else None
            if not isinstance(model, str) or not 0 < len(model) <= 200 or not model.isprintable():
                raise ValueError("Invalid model ID")
            if target.api_key and target.api_key in model:
                raise ValueError("Credential reflected by upstream")
            if model in ids:
                raise ValueError("Duplicate model ID")
            ids.add(model)
            result.model_metadata.append(
                DiscoveredModel(
                    id=model,
                    context_window_tokens=published_limit(row, "max_model_len", "context_length"),
                    max_output_tokens=published_limit(
                        row, "max_output_tokens", "max_completion_tokens"
                    ),
                    embedding_dimension=row.get("embedding_dimension"),
                )
            )
        result.models = sorted(ids)
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


def tag_names(data: object) -> dict[str, str]:
    """Map installed tags to the exact name and, as a fallback, the untagged name."""
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise TypeError("Invalid tags")
    names: dict[str, str] = {}
    for row in models:
        name = row.get("name") if isinstance(row, dict) else None
        if not isinstance(name, str) or not 0 < len(name) <= 200 or not name.isprintable():
            continue
        names.setdefault(name, name)
        if ":" in name:
            names.setdefault(name.split(":", 1)[0], name)
    return names


def server_context(data: object) -> int | None:
    """Accept one strict positive integer declared under ``*.context_length``; never invent."""
    info = data.get("model_info") if isinstance(data, dict) else None
    if not isinstance(info, dict):
        return None
    arch = info.get("general.architecture")
    if isinstance(arch, str) and arch:
        value = info.get(f"{arch}.context_length")
    else:
        declared = [
            item
            for key, item in info.items()
            if isinstance(key, str) and key.endswith(".context_length")
        ]
        value = declared[0] if len(declared) == 1 else None
    return value if type(value) is int and 0 < value <= MAX_CONTEXT_TOKENS else None


def generation_context(data: object) -> int | None:
    """llama.cpp declares one per-slot runtime context; slots never multiply it."""
    settings = data.get("default_generation_settings") if isinstance(data, dict) else None
    if not isinstance(settings, dict):
        return None
    value = settings.get("n_ctx")
    return value if type(value) is int and 0 < value <= MAX_CONTEXT_TOKENS else None


def loaded_identity(data: object) -> tuple[str, ...]:
    """Ordered exact identities for the loaded GGUF: path, file name, then stem."""
    path = data.get("model_path") if isinstance(data, dict) else None
    if not isinstance(path, str) or not 0 < len(path) <= 4096 or not path.isprintable():
        return ()
    name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = name[:-5] if name.lower().endswith(".gguf") else name
    return tuple(dict.fromkeys((path, name, stem)))


def context_detail(enriched: int) -> str:
    return (
        f"Đã lấy danh sách; {enriched} model có cửa sổ ngữ cảnh do server công bố; "
        "các model chưa được kiểm tra inference."
    )


async def apply_ollama_context(
    client: httpx.AsyncClient,
    target: DiagnosticTarget,
    result: DiagnosticResult,
    root: str,
) -> bool:
    """Recognize an Ollama host and record its declared per-model context."""
    tags = await client.get(root + "/api/tags", headers=auth_headers(target))
    if tags.status_code != 200:
        return False
    try:
        names = tag_names(tags.json())
    except (ValueError, TypeError):
        return False
    enriched = 0
    for index, row in enumerate(result.model_metadata):
        if row.context_window_tokens is not None:
            continue
        name = names.get(row.id) or names.get(row.id.split(":", 1)[0])
        if name is None:
            continue
        shown = await client.post(
            root + "/api/show", headers=auth_headers(target), json={"name": name}
        )
        if shown.status_code != 200:
            continue
        try:
            limit = server_context(shown.json())
        except ValueError:
            continue
        if limit is None:
            continue
        result.model_metadata[index] = row.model_copy(update={"context_window_tokens": limit})
        enriched += 1
    if enriched:
        result.detail = context_detail(enriched)
    return True


async def apply_llamacpp_context(
    client: httpx.AsyncClient,
    target: DiagnosticTarget,
    result: DiagnosticResult,
    root: str,
) -> bool:
    """Recognize a llama.cpp host and record ``/props`` context for the loaded model."""
    props = await client.get(root + "/props", headers=auth_headers(target))
    if props.status_code != 200:
        return False
    try:
        data = props.json()
    except ValueError:
        return False
    if not isinstance(data, dict) or not isinstance(data.get("default_generation_settings"), dict):
        return False
    limit = generation_context(data)
    if limit is None:
        return True
    unknowns = [
        index
        for index, row in enumerate(result.model_metadata)
        if row.context_window_tokens is None
    ]
    matched: list[int] = []
    for candidate in loaded_identity(data):
        matched = [index for index in unknowns if result.model_metadata[index].id == candidate]
        if matched:
            break
    if not matched and len(result.model_metadata) == 1:
        # A llama.cpp host serves exactly one model, so the only row is the loaded one.
        matched = unknowns
    for index in matched:
        result.model_metadata[index] = result.model_metadata[index].model_copy(
            update={"context_window_tokens": limit}
        )
    if matched:
        result.detail = context_detail(len(matched))
    return True


async def enrich_native_context(
    client: httpx.AsyncClient,
    target: DiagnosticTarget,
    result: DiagnosticResult,
    *,
    deadline: float,
) -> None:
    """Best-effort native context; failures keep the OpenAI-compatible snapshot."""
    root = native_root(target.endpoint)
    if (
        root is None
        or not result.model_metadata
        or len(result.model_metadata) > MAX_NATIVE_CONTEXT_MODELS
        or all(row.context_window_tokens is not None for row in result.model_metadata)
    ):
        return
    budget = min(NATIVE_PROBE_SECONDS, deadline - asyncio.get_running_loop().time() - 0.25)
    if budget <= 0.05:
        return
    try:
        async with asyncio.timeout(budget):
            probes = (
                (apply_llamacpp_context, apply_ollama_context)
                if target.provider_type == "llamacpp"
                else (apply_ollama_context, apply_llamacpp_context)
            )
            for probe in probes:
                if await probe(client, target, result, root):
                    break
    except (TimeoutError, httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
        return


class HttpProviderDiagnosticClient:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def check(self, kind: DiagnosticKind, target: DiagnosticTarget) -> DiagnosticResult:
        from qnu.domains.modelops.registry import transport_for

        metadata = transport_for(target.provider_type)
        supported = metadata.discovery if kind == "discovery" else kind in metadata.protocols
        if not supported:
            return DiagnosticResult(
                "unsupported",
                "diagnostic_unsupported",
                "Chưa có adapter kiểm tra cho loại provider/chức năng này.",
            )
        if not target.api_key and not target.auth_optional:
            return failed("credentials_missing", "Chưa có khóa đang hoạt động.")
        if target.provider_type == "mineru":
            from qnu.adapters.providers.mineru_diagnostic import check_mineru

            return await check_mineru(target, self.transport)
        started = time.monotonic()
        deadline = started + target.timeout_seconds
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
                        headers=auth_headers(target),
                        json=body,
                    )
                    result = self.decode(kind, target, response)
                    if (
                        kind == "discovery"
                        and result.outcome == "ok"
                        and target.provider_type in NATIVE_DISCOVERY_TYPES
                    ):
                        await enrich_native_context(client, target, result, deadline=deadline)
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
