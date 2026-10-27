import httpx
import pytest

from qnu.adapters.vector.qdrant import QdrantVectorStore
from qnu.platform.errors import AppException

COLLECTION = "qnu_v1_idx_" + "a" * 32


async def test_unconfirmed_vector_write_is_not_success():
    store = QdrantVectorStore(
        "http://localhost:6333",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"result": {"status": "acknowledged"}})
        ),
    )
    with pytest.raises(AppException) as exc:
        await store.upsert(COLLECTION, [])
    assert exc.value.code == "vector_unavailable"


async def test_vector_infrastructure_error_is_not_missing_collection():
    store = QdrantVectorStore(
        "http://localhost:6333",
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )
    with pytest.raises(AppException) as exc:
        await store.collection_exists(COLLECTION)
    assert exc.value.code == "vector_unavailable"


async def test_legacy_vector_collection_cannot_be_written():
    store = QdrantVectorStore("http://localhost:6333")
    with pytest.raises(AppException) as exc:
        await store.upsert("qnu_documents", [])
    assert exc.value.code == "vector_collection_forbidden"
