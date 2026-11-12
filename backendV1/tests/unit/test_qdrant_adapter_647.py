import json

import httpx
import pytest

from qnu.adapters.vector.qdrant import PAYLOAD_INDEX_FIELDS, QdrantVectorStore
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


def routed(existing: bool, index_status: str = "completed"):
    calls = []

    def handler(request):
        body = json.loads(request.content) if request.content else {}
        calls.append((request.method, request.url.path, body))
        if request.method == "GET":
            if not existing:
                return httpx.Response(404)
            return httpx.Response(
                200,
                json={
                    "result": {
                        "config": {"params": {"vectors": {"size": 1024, "distance": "Cosine"}}}
                    }
                },
            )
        if request.url.path.endswith("/index"):
            return httpx.Response(200, json={"result": {"status": index_status}})
        return httpx.Response(200, json={"result": {"status": "completed"}})

    return calls, httpx.MockTransport(handler)


@pytest.mark.parametrize("existing", [False, True])
async def test_ensure_collection_creates_keyword_payload_indexes(existing):
    calls, transport = routed(existing)
    store = QdrantVectorStore("http://localhost:6333", transport=transport)
    await store.ensure_collection(COLLECTION, 1024)
    indexed = [body for method, path, body in calls if path.endswith("/index")]
    assert [body["field_name"] for body in indexed] == list(PAYLOAD_INDEX_FIELDS)
    assert all(body["field_schema"] == "keyword" for body in indexed)


async def test_collection_mismatch_creates_no_payload_indexes():
    calls, transport = routed(existing=True)
    store = QdrantVectorStore("http://localhost:6333", transport=transport)
    with pytest.raises(AppException) as exc:
        await store.ensure_collection(COLLECTION, 768)
    assert exc.value.code == "vector_configuration_mismatch"
    assert not any(path.endswith("/index") for _, path, _ in calls)


async def test_unconfirmed_payload_index_is_not_success():
    _, transport = routed(existing=True, index_status="acknowledged")
    store = QdrantVectorStore("http://localhost:6333", transport=transport)
    with pytest.raises(AppException) as exc:
        await store.ensure_collection(COLLECTION, 1024)
    assert exc.value.code == "vector_unavailable"
