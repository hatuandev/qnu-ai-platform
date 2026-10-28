"""Strict dense OpenAI-compatible embedding transport; one call, no implicit retry."""

from __future__ import annotations

import math
import time

import httpx

from qnu.adapters.providers.failures import tag_failure
from qnu.platform.config import get_settings
from qnu.platform.errors import AppException
from qnu.platform.logging import get_logger
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.embedding_model import EmbeddingRequest, EmbeddingResult

logger = get_logger(__name__)


def embeddings_url(endpoint: str) -> str:
    base = endpoint.strip().rstrip("/")
    if base.endswith("/embeddings"):
        return base
    return base + ("/embeddings" if base.endswith(("/v1", "/openai")) else "/v1/embeddings")


def _error(code: str, detail: str, status: int = 502) -> AppException:
    return AppException(detail, code=code, status_code=status, title="Embedding lỗi")


def decode_embeddings(
    data: object, count: int, request: EmbeddingRequest
) -> tuple[list[list[float]], int | None]:
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise _error("embedding_response_invalid", "Phản hồi embedding sai cấu trúc.")
    if data.get("model") not in (None, request.model):
        raise _error("embedding_model_mismatch", "Provider trả model khác yêu cầu.")
    rows = data["data"]
    if len(rows) != count:
        raise _error("embedding_count_mismatch", "Thiếu hoặc thừa vector.")
    vectors = {}
    dimension = request.expected_dimension
    for row in rows:
        if not isinstance(row, dict) or type(row.get("index")) is not int:
            raise _error("embedding_response_invalid", "Embedding thiếu index hợp lệ.")
        index, vector = row["index"], row.get("embedding")
        if index in vectors or not 0 <= index < count or not isinstance(vector, list) or not vector:
            raise _error("embedding_response_invalid", "Vector/index không hợp lệ.")
        dimension = dimension or len(vector)
        if len(vector) != dimension:
            raise _error("embedding_dimension_mismatch", "Số chiều vector không khớp cấu hình.")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
            raise _error("embedding_vector_invalid", "Vector phải gồm các số hữu hạn.")
        if not any(v != 0 for v in vector):
            raise _error("embedding_vector_invalid", "Không chấp nhận vector toàn 0.")
        vectors[index] = [float(v) for v in vector]
    usage = data.get("usage")
    tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
    tokens = tokens if type(tokens) is int and tokens >= 0 else None
    return [vectors[i] for i in range(count)], tokens


class ModelOpsEmbeddingModel:
    name = "embedding"

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def embed(self, texts: list[str], request: EmbeddingRequest) -> EmbeddingResult:
        if not texts or any(not isinstance(t, str) or not t.strip() for t in texts):
            raise _error("embedding_input_invalid", "Đầu vào embedding không được rỗng.", 422)
        if not request.api_key:
            raise _error("embedding_credentials_missing", "Thiếu credential embedding.", 503)
        url = embeddings_url(request.endpoint)
        assert_allowed_endpoint(url, allow_private=not get_settings().is_production)
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=request.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    url,
                    headers={"Authorization": "Bearer " + request.api_key},
                    json={"model": request.model, "input": texts, "encoding_format": "float"},
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            raise _error("embedding_unreachable", "Không kết nối được provider embedding.") from exc
        except httpx.RequestError as exc:
            raise _error(
                "embedding_uncertain", "Chưa xác định kết quả embedding; không tự gửi lại.", 504
            ) from exc
        if response.status_code in (401, 403):
            raise tag_failure(
                _error("embedding_auth_failed", "Provider từ chối credential."), response
            )
        if response.status_code == 429:
            raise tag_failure(
                _error("embedding_rate_limited", "Provider giới hạn tần suất.", 503), response
            )
        if response.status_code >= 500:
            raise tag_failure(
                _error("embedding_unavailable", "Provider embedding không sẵn sàng.", 503), response
            )
        if response.status_code != 200:
            raise tag_failure(
                _error("embedding_rejected", "Provider từ chối yêu cầu embedding."), response
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise _error(
                "embedding_response_invalid", "Phản hồi embedding không phải JSON."
            ) from exc
        vectors, tokens = decode_embeddings(data, len(texts), request)
        logger.info(
            "embedding_completed",
            model=request.model,
            items=len(vectors),
            dimension=len(vectors[0]),
            total_tokens=tokens,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return EmbeddingResult(vectors, len(vectors[0]), tokens, response.content)
