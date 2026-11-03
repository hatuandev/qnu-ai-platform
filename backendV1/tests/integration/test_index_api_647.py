"""Index requests must be durable and idempotent for published source snapshots."""

import pytest

from tests.integration.index_support import FakeEmbedding, execute_index, published_input
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue


def embedding_provider(client, data, endpoint="http://127.0.0.1:20128/v1", dimension=4):
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "embedding",
            "provider_type": "openai_compatible",
            "base_url": endpoint,
            "model_name": "test-embedding",
            "capabilities": ["embedding"],
            "embedding_dimension": dimension,
            "token_limits": {"max_input_tokens": 32768},
            "timeout_seconds": 5,
        },
    )
    assert response.status_code == 201, response.text
    provider = response.json()
    assert (
        client.post(
            f"{API}/modelops/providers/{provider['id']}/keys",
            json={"name": "test", "secret": "embedding-test-secret"},
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
            json={
                "provider_ids": [data["ocr_provider"]["id"], provider["id"]],
                "defaults": {"embedding": provider["id"], "ocr": data["ocr_provider"]["id"]},
            },
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    return provider


def test_index_request_is_durable_and_idempotent(client):
    data = published_input(client)
    embedding_provider(client, data)
    use_queue(FakeJobQueue(failing=True))
    url = data["base"] + "/indexing-runs"
    response = client.post(url, headers={"Idempotency-Key": "index-one"}, json={})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["created"] and not body["dispatched"]
    assert body["run"]["status"] == "queued"
    replay = client.post(url, headers={"Idempotency-Key": "index-one"}, json={})
    assert replay.status_code == 200
    assert replay.json()["run"]["id"] == body["run"]["id"]


@pytest.fixture
def indexed(client):
    data = published_input(client)
    with FakeEmbedding() as fake:
        provider = embedding_provider(client, data, fake.base_url)
        use_queue(FakeJobQueue())
        response = client.post(
            data["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": "index-one"}
        )
        assert response.status_code == 201, response.text
        data.update(index_run=response.json()["run"], embedding_provider=provider, embedding=fake)
        try:
            yield data
        finally:
            from sqlalchemy import select

            from qnu.domains.knowledge.index.models import IndexRun
            from qnu.main import app
            from qnu.platform.database import AsyncSessionFactory

            async def cleanup():
                async with AsyncSessionFactory() as db:
                    names = list((await db.scalars(select(IndexRun.vector_collection))).all())
                for name in names:
                    await app.state.container.vector_store.delete_collection(name)

            client.portal.call(cleanup)


def test_real_qdrant_index_and_search_return_pinned_sources(client, indexed):
    data = indexed
    run = data["index_run"]["id"]
    assert execute_index(client, run) == "completed"
    assert execute_index(client, run) == "not_claimed"
    before = len(data["embedding"].requests)
    url = data["base"] + "/indexing-runs/" + run
    status = client.get(url).json()
    assert status["is_active"] and status["chunks_total"] >= 2 and status["dimension"] == 4
    manifest = client.get(url + "/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["config"]["provider"]["model_name"] == "test-embedding"
    response = client.post(
        data["base"] + "/search", json={"query": "Chỉ tiêu tuyển sinh", "top_k": 5}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "results" and body["hits"]
    assert response.headers["cache-control"] == "private, no-store"
    for hit in body["hits"]:
        assert hit["version_id"] == data["compiled"]["version"]["id"]
        assert hit["citations"]
        assert all(
            ref["revision_id"] == data["revision"]["id"] for ref in hit["citations"].values()
        )
    assert len(data["embedding"].requests) == before + 1


def withdraw(client, data):
    as_actor(PLATFORM)
    response = client.post(
        data["version_url"] + "/decision-preview",
        json={"action": "withdraw", "reason": "Synthetic withdrawal."},
    )
    assert response.status_code == 200, response.text
    p = response.json()
    result = client.post(
        data["version_url"] + "/decisions",
        headers={"Idempotency-Key": "withdraw"},
        json={"preview_id": p["id"], "preview_sha256": p["preview_sha256"]},
    )
    assert result.status_code == 200, result.text
    as_actor(EDITOR)


def test_withdrawn_content_is_excluded_before_query_embedding(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    before = len(indexed["embedding"].requests)
    withdraw(client, indexed)
    response = client.post(indexed["base"] + "/search", json={"query": "Chỉ tiêu"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "no_eligible_content" and not response.json()["hits"]
    assert len(indexed["embedding"].requests) == before


@pytest.mark.parametrize(
    "mode,code",
    [
        ("wrong_dimension", "embedding_dimension_mismatch"),
        ("malformed", "embedding_count_mismatch"),
        ("auth_error", "embedding_auth_failed"),
    ],
)
def test_bad_embedding_cannot_activate_generation(client, indexed, mode, code):
    indexed["embedding"].mode = mode
    assert execute_index(client, indexed["index_run"]["id"]) == "failed"
    status = client.get(indexed["base"] + "/indexing-runs/" + indexed["index_run"]["id"]).json()
    assert status["error_code"] == code and not status["is_active"]
    assert client.post(indexed["base"] + "/search", json={"query": "x"}).status_code == 409


def test_index_and_search_require_server_membership_and_roles(client, indexed):
    from tests.integration.knowledge_support import MEMBER, OUTSIDER

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    as_actor(MEMBER)
    assert (
        client.post(
            indexed["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": "member"}
        ).status_code
        == 403
    )
    assert client.post(indexed["base"] + "/search", json={"query": "x"}).status_code == 200
    as_actor(OUTSIDER)
    assert client.post(indexed["base"] + "/search", json={"query": "x"}).status_code == 404
    as_actor(None)
    assert client.post(indexed["base"] + "/search", json={"query": "x"}).status_code == 401


def test_model_identity_change_stops_old_generation(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    as_actor(PLATFORM)
    provider = indexed["embedding_provider"]["id"]
    assert (
        client.patch(
            f"{API}/modelops/providers/{provider}", json={"model_name": "changed-model"}
        ).status_code
        == 200
    )
    as_actor(EDITOR)
    response = client.post(indexed["base"] + "/search", json={"query": "x"})
    assert response.status_code == 409
    assert response.json()["code"] == "embedding_dimension_stale"


def test_source_revision_change_excludes_content_without_model_call(client, indexed):
    from tests.integration.knowledge_support import add_revision
    from tests.integration.ocr_support import real_pdf

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    count = len(indexed["embedding"].requests)
    result = add_revision(
        client,
        indexed["workspace"]["id"],
        indexed["collection"]["id"],
        indexed["source"]["id"],
        payload=real_pdf(["new source"]),
    )
    assert result.status_code == 201, result.text
    response = client.post(indexed["base"] + "/search", json={"query": "x"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "no_eligible_content"
    assert response.json()["skipped_documents"][0]["reason"] == "publication_source_stale"
    assert len(indexed["embedding"].requests) == count


def test_out_of_scope_document_filter_is_not_widened(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    response = client.post(
        indexed["base"] + "/search", json={"query": "x", "document_ids": ["other-document"]}
    )
    assert response.status_code == 404


def test_provider_error_during_query_is_not_no_match(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    indexed["embedding"].mode = "http_error"
    response = client.post(indexed["base"] + "/search", json={"query": "x"})
    assert response.status_code == 503
    assert response.json()["code"] == "embedding_unavailable"


def test_retired_monthly_limit_does_not_block_indexing(client, indexed):
    from tests.integration.ocr_support import set_quota

    assert set_quota(client, indexed["workspace"]["id"], 0).status_code == 200
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    assert indexed["embedding"].requests


def test_publication_change_before_worker_is_not_indexed(client, indexed):
    withdraw(client, indexed)
    assert execute_index(client, indexed["index_run"]["id"]) == "failed"
    assert not indexed["embedding"].requests


def test_expired_embedding_marker_becomes_uncertain_without_resend(client, indexed):
    from datetime import timedelta

    from qnu.domains.knowledge.compilation.models import utcnow
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.modelops.usage.service import usage_service
    from qnu.platform.database import AsyncSessionFactory

    async def mark():
        async with AsyncSessionFactory() as db:
            usage = await usage_service.reserve(
                db,
                EDITOR,
                indexed["workspace"]["id"],
                "embedding",
                "interrupted-index",
                "1" * 64,
                1000,
                indexed["embedding_provider"]["id"],
            )
            row = await db.get(IndexRun, indexed["index_run"]["id"])
            row.pending_batch = {"usage_id": usage.id, "start": 0, "chunk_ids": []}
            row.status = "running"
            row.worker_id = "dead-worker"
            row.lease_expires_at = utcnow() - timedelta(seconds=5)
            await db.commit()

    client.portal.call(mark)
    assert execute_index(client, indexed["index_run"]["id"]) == "uncertain"
    assert not indexed["embedding"].requests


def test_cross_scope_vector_payload_is_error_and_filter_precedes_topk(client, indexed, monkeypatch):
    from qnu.main import app

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    store = app.state.container.vector_store
    original = store.search

    async def inject(collection, vector, limit, scope):
        assert scope["workspace_id"] == indexed["workspace"]["id"]
        assert scope["collection_id"] == indexed["collection"]["id"]
        assert scope["version_id"] == [indexed["compiled"]["version"]["id"]]
        hits = await original(collection, vector, limit, scope)
        hits[0].payload["workspace_id"] = "foreign-workspace"
        return hits

    monkeypatch.setattr(store, "search", inject)
    response = client.post(indexed["base"] + "/search", json={"query": "x"})
    assert response.status_code == 503
    assert response.json()["code"] == "vector_response_invalid"


def test_failed_replacement_generation_keeps_previous_active(client, indexed):
    first = indexed["index_run"]["id"]
    assert execute_index(client, first) == "completed"
    response = client.post(
        indexed["base"] + "/indexing-runs", headers={"Idempotency-Key": "index-two"}, json={}
    )
    assert response.status_code == 201, response.text
    indexed["embedding"].mode = "wrong_dimension"
    assert execute_index(client, response.json()["run"]["id"]) == "failed"
    assert client.get(indexed["base"] + "/indexing-runs/" + first).json()["is_active"]
    indexed["embedding"].mode = "ok"
    assert (
        client.post(indexed["base"] + "/search", json={"query": "x"}).json()["index_run_id"]
        == first
    )


def test_withdrawal_during_query_embedding_is_rechecked(client, indexed, monkeypatch):
    from qnu.domains.knowledge.publication.decisions import commit_decision, create_preview
    from qnu.domains.knowledge.publication.schemas import CommitRequest, PreviewRequest
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    original = app.state.container.embedding_model

    class WithdrawDuringEmbedding:
        async def embed(self, texts, request):
            result = await original.embed(texts, request)
            async with AsyncSessionFactory() as db:
                p = await create_preview(
                    db,
                    app.state.container.blob_store,
                    PLATFORM,
                    indexed["workspace"]["id"],
                    indexed["collection"]["id"],
                    indexed["compiled"]["document"]["id"],
                    indexed["compiled"]["version"]["id"],
                    PreviewRequest(action="withdraw", reason="Synthetic race check."),
                )
                await commit_decision(
                    db,
                    app.state.container.blob_store,
                    PLATFORM,
                    indexed["workspace"]["id"],
                    indexed["collection"]["id"],
                    indexed["compiled"]["document"]["id"],
                    indexed["compiled"]["version"]["id"],
                    CommitRequest(preview_id=p.id, preview_sha256=p.preview_sha256),
                    "withdraw-race",
                )
            return result

    monkeypatch.setattr(app.state.container, "embedding_model", WithdrawDuringEmbedding())
    response = client.post(indexed["base"] + "/search", json={"query": "x"})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "no_eligible_content" and not response.json()["hits"]


def test_provider_disabled_during_embedding_is_rechecked(client, indexed, monkeypatch):
    from qnu.domains.modelops.models import Provider
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    original = app.state.container.embedding_model

    class DisableDuringEmbedding:
        async def embed(self, texts, request):
            result = await original.embed(texts, request)
            async with AsyncSessionFactory() as db:
                provider = await db.get(Provider, indexed["embedding_provider"]["id"])
                provider.is_active = False
                await db.commit()
            return result

    monkeypatch.setattr(app.state.container, "embedding_model", DisableDuringEmbedding())
    response = client.post(indexed["base"] + "/search", json={"query": "x"})
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "provider_inactive"


def test_table_structure_tampering_is_rejected(client, indexed):
    from sqlalchemy import select

    from qnu.domains.knowledge.index.models import IndexChunk
    from qnu.platform.database import AsyncSessionFactory

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"

    async def tamper():
        async with AsyncSessionFactory() as db:
            row = await db.scalar(select(IndexChunk).where(IndexChunk.kind == "table"))
            row.structure = {"altered": True}
            await db.commit()

    client.portal.call(tamper)
    response = client.post(indexed["base"] + "/search", json={"query": "x", "top_k": 50})
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "vector_response_invalid"
