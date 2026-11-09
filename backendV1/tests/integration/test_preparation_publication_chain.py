"""G3: a prepared draft completed the review, publication and serving chain.

The chain starts from a real PreparationIntent, so registration only accepts
the pinned compilation the preparation produced. Nothing is served before
publication, and withdrawal hides old content without waiting for a rebuild.
"""

from tests.integration.compiler_support import FakeChat, chat_provider, execute_compile
from tests.integration.index_support import FakeEmbedding, execute_index
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    PLATFORM,
    REVIEWER,
    add_member,
    as_actor,
)
from tests.integration.ocr_support import FakeJobQueue, FakeNemotron, execute_now
from tests.integration.test_index_api_647 import embedding_provider
from tests.integration.test_preparation_intents import (
    _status_url,
    advance,
    create_intent,
    prepared_workspace,
)
from tests.integration.test_publication_646 import decision
from tests.integration.test_review_handoff import inbox, submit


def sync_now(client, collection_id: str) -> str:
    from qnu.domains.knowledge.index.sync import synchronize
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def execute():
        async with AsyncSessionFactory() as db:
            return await synchronize(db, app.state.container, collection_id)

    return client.portal.call(execute)


def test_prepared_draft_runs_the_full_publication_lifecycle(client):
    with FakeNemotron() as ocr_api, FakeChat() as chat_api:
        data = prepared_workspace(client, "prep-publish", ocr_api)
        # Workers re-resolve current DB membership; the publisher must be one.
        add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
        as_actor(EDITOR)
        chat_provider(client, data, chat_api.base_url)
        queue = FakeJobQueue()
        created = create_intent(client, data, key="prep-publish", mode="auto", queue=queue)
        assert created.status_code == 201, created.text
        intent_id = created.json()["intent"]["id"]

        assert advance(client, intent_id, queue) == "waiting_ocr"
        ocr_run_id = client.get(_status_url(data, intent_id)).json()["ocr_run_id"]
        assert execute_now(client, ocr_run_id).status == "completed"
        assert advance(client, intent_id, queue) == "compiling"
        compilation_id = client.get(_status_url(data, intent_id)).json()["compilation_run_id"]
        assert execute_compile(client, compilation_id) == "completed"
        assert advance(client, intent_id, queue) == "ready"

        as_actor(EDITOR)
        collection_base = (
            f"{API}/workspaces/{data['workspace']['id']}/collections/{data['collection']['id']}"
        )
        base = collection_base + "/compiled-documents"
        registered = client.post(
            base,
            headers={"Idempotency-Key": "prep-register"},
            json={
                "document_key": "de-an",
                "title": "Đề án",
                "compilation_run_id": compilation_id,
            },
        )
        assert registered.status_code == 201, registered.text
        document, version = registered.json()["document"], registered.json()["version"]
        doc_url = base + "/" + document["id"]
        version_url = doc_url + "/versions/" + version["id"]
        assert version["status"] == "draft"
        assert client.get(doc_url + "/published").status_code == 404
        assert client.get(collection_base + "/search-readiness").json()["status"] != "ready"

        submission = submit(client, data, document["id"], version["id"], key="prep-submit")
        assert submission["status"] == "pending"
        as_actor(REVIEWER)
        pending = inbox(client, data).json()["items"]
        assert [item["kind"] for item in pending] == ["review_pending"]
        assert pending[0]["submission_id"] == submission["id"]

        approved = decision(client, version_url, "approve", key="prep-approve")
        assert approved.status_code == 200, approved.text
        assert client.get(doc_url + "/published").status_code == 404
        assert client.get(collection_base + "/search-readiness").json()["status"] != "ready"

        as_actor(PLATFORM)
        published = decision(client, version_url, "publish", key="prep-publish-decision")
        assert published.status_code == 200, published.text
        served = client.get(doc_url + "/published")
        assert served.status_code == 200, served.text
        assert served.json()["version"]["id"] == version["id"]
        assert client.get(collection_base + "/search-readiness").json()["status"] == "pending"

        with FakeEmbedding() as fake:
            embedding_provider(client, data, fake.base_url)
            assert sync_now(client, data["collection"]["id"]) == "building"
            runs = client.get(collection_base + "/indexing-runs").json()
            assert len(runs) == 1
            assert execute_index(client, runs[0]["id"]) == "completed"
            assert sync_now(client, data["collection"]["id"]) == "ready"

            search = client.post(collection_base + "/search", json={"query": "PHỤ LỤC"})
            assert search.status_code == 200, search.text
            body = search.json()
            assert body["status"] == "results" and body["hits"]
            for hit in body["hits"]:
                assert hit["version_id"] == version["id"]
                assert all(
                    ref["revision_id"] == data["revision"]["id"]
                    for ref in hit["citations"].values()
                )

            as_actor(PLATFORM)
            withdrawn = decision(client, version_url, "withdraw", key="prep-withdraw")
            assert withdrawn.status_code == 200, withdrawn.text
            assert client.get(doc_url + "/published").status_code == 404
            assert client.get(collection_base + "/search-readiness").json()["status"] != "ready"

            after = client.post(collection_base + "/search", json={"query": "PHỤ LỤC"})
            assert after.status_code == 200, after.text
            assert after.json()["status"] == "no_eligible_content"
            assert after.json()["hits"] == []
