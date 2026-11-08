"""Assistant readiness combines published scope and the active index generation."""

from tests.integration.index_support import FakeEmbedding, execute_index, published_input
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    PLATFORM,
    as_actor,
    create_collection,
)
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_index_api_647 import embedding_provider


def create_assistant(client, data, *, collection_id=None):
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/workspaces/{data['workspace']['id']}/assistants",
        json={
            "name": "Trợ lý kiểm tra phạm vi",
            "collection_id": collection_id or data["collection"]["id"],
        },
    )
    assert response.status_code == 201, response.text
    as_actor(EDITOR)
    return response.json()


def readiness(client, data, assistant):
    response = client.get(
        f"{API}/workspaces/{data['workspace']['id']}/assistants/{assistant['id']}/readiness"
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_collection_without_published_documents_is_empty(client):
    data = published_input(client)
    as_actor(EDITOR)
    empty = create_collection(client, data["workspace"]["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, data, collection_id=empty["id"])
    body = readiness(client, data, assistant)
    assert body["status"] == "empty"
    assert body["published_document_count"] == 0
    assert body["served_document_count"] == 0
    assert body["index_run_id"] is None
    assert body["collection_name"] == "Bộ sưu tập trống"


def test_published_but_unindexed_is_not_ready(client):
    data = published_input(client)
    assistant = create_assistant(client, data)
    body = readiness(client, data, assistant)
    # Publication queues an outbox row; without an active generation the
    # assistant must report that content is still being prepared.
    assert body["status"] == "syncing"
    assert body["published_document_count"] == 1
    assert body["served_document_count"] == 0
    assert body["sync_status"] in {"pending", "building"}


def test_completed_index_reports_ready_and_served(client):
    data = published_input(client)
    assistant = create_assistant(client, data)
    with FakeEmbedding() as fake:
        embedding_provider(client, data, fake.base_url)
        use_queue(FakeJobQueue())
        as_actor(EDITOR)
        created = client.post(
            data["base"] + "/indexing-runs",
            json={},
            headers={"Idempotency-Key": "assistant-readiness"},
        )
        assert created.status_code == 201, created.text
        run = created.json()["run"]
        assert execute_index(client, run["id"]) == "completed"
        body = readiness(client, data, assistant)
        assert body["status"] == "ready"
        assert body["published_document_count"] == 1
        assert body["served_document_count"] == 1
        assert body["index_run_id"] == run["id"]
        assert body["index_generation"] >= 1
