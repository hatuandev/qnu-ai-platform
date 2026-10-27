"""Embedding transport and response integrity, independent from index orchestration."""

import json

import httpx
import pytest

from qnu.adapters.providers.embedding import (
    ModelOpsEmbeddingModel,
    decode_embeddings,
    embeddings_url,
)
from qnu.platform.errors import AppException
from qnu.ports.embedding_model import EmbeddingRequest


def request(dimension=2):
    return EmbeddingRequest(
        "http://127.0.0.1:1234/v1", "sample-model", 5, "unit-only-secret", dimension
    )


@pytest.mark.parametrize("base", ["http://host", "http://host/v1", "http://host/v1/embeddings"])
def test_endpoint_suffix_once(base):
    assert embeddings_url(base) == "http://host/v1/embeddings"


def test_embedding_order_is_index_order_and_missing_usage_is_unknown():
    vectors, tokens = decode_embeddings(
        {
            "model": "sample-model",
            "data": [
                {"index": 1, "embedding": [0.5, 0.3]},
                {"index": 0, "embedding": [1.0, -0.2]},
            ],
        },
        2,
        request(),
    )
    assert vectors == [[1.0, -0.2], [0.5, 0.3]] and tokens is None
    assert "unit-only-secret" not in repr(request())


@pytest.mark.parametrize(
    "rows,code",
    [
        ([], "embedding_count_mismatch"),
        ([{"index": 0, "embedding": [1, 2, 3]}], "embedding_dimension_mismatch"),
        ([{"index": 0, "embedding": [0, 0]}], "embedding_vector_invalid"),
        ([{"index": 0, "embedding": [float("nan"), 1]}], "embedding_vector_invalid"),
        ([{"index": 0, "embedding": [True, 1]}], "embedding_vector_invalid"),
        ([{"index": "0", "embedding": [1, 2]}], "embedding_response_invalid"),
        ([{"index": 2, "embedding": [1, 2]}], "embedding_response_invalid"),
    ],
)
def test_bad_embedding_vectors_are_not_accepted(rows, code):
    with pytest.raises(AppException) as exc:
        decode_embeddings({"data": rows}, 1, request())
    assert exc.value.code == code


@pytest.mark.asyncio
async def test_adapter_uses_bearer_model_and_float_protocol_once():
    calls = []

    def handle(r):
        calls.append(r)
        assert r.headers["authorization"] == "Bearer unit-only-secret"
        assert json.loads(r.content) == {
            "model": "sample-model",
            "input": ["synthetic"],
            "encoding_format": "float",
        }
        return httpx.Response(
            200, json={"data": [{"index": 0, "embedding": [1, 2]}], "usage": {"total_tokens": 7}}
        )

    result = await ModelOpsEmbeddingModel(transport=httpx.MockTransport(handle)).embed(
        ["synthetic"], request()
    )
    assert result.dimension == 2 and result.total_tokens == 7 and len(calls) == 1


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "embedding_auth_failed"),
        (429, "embedding_rate_limited"),
        (503, "embedding_unavailable"),
        (302, "embedding_rejected"),
    ],
)
@pytest.mark.asyncio
async def test_http_error_is_not_empty_vectors_or_retry(status, code):
    calls = []

    def handle(r):
        calls.append(r)
        return httpx.Response(
            status,
            json={"error": "private upstream detail"},
            headers={"location": "http://untrusted.invalid"},
        )

    with pytest.raises(AppException) as exc:
        await ModelOpsEmbeddingModel(transport=httpx.MockTransport(handle)).embed(
            ["synthetic"], request()
        )
    assert exc.value.code == code and len(calls) == 1
    assert "private upstream detail" not in exc.value.detail


@pytest.mark.asyncio
async def test_read_timeout_is_uncertain_without_provider_details():
    def handle(r):
        raise httpx.ReadTimeout("private detail", request=r)

    with pytest.raises(AppException) as exc:
        await ModelOpsEmbeddingModel(transport=httpx.MockTransport(handle)).embed(
            ["synthetic"], request()
        )
    assert exc.value.code == "embedding_uncertain" and "private detail" not in exc.value.detail
