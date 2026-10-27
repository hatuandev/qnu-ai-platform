"""Adapters must fail loudly instead of fabricating provider data."""

from __future__ import annotations

import httpx
import pytest

from qnu.adapters.providers.reranker import ModelOpsReranker
from qnu.platform.errors import AppException
from qnu.ports.reranker import RerankRequest


@pytest.mark.asyncio
async def test_unimplemented_provider_raises() -> None:
    """An unavailable upstream must fail; implementing the adapter never enables fake ranking."""
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(503, json={"error": "not_implemented"})

    with pytest.raises(AppException) as caught:
        await ModelOpsReranker(transport=httpx.MockTransport(handle)).rerank(
            "query",
            ["source"],
            1,
            RerankRequest("http://127.0.0.1:8000/v1", "test", 5, "synthetic-key"),
        )
    assert caught.value.code == "rerank_unavailable"
    assert len(calls) == 1
