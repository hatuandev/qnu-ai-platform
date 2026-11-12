"""Publication drives indexing without a second browser action."""

import asyncio

import pytest
from sqlalchemy import select

from tests.integration.index_support import FakeEmbedding, execute_index, published_input
from tests.integration.knowledge_support import (
    EDITOR,
    MEMBER,
    OUTSIDER,
    PLATFORM,
    add_member,
    as_actor,
)
from tests.integration.ocr_support import FakeJobQueue
from tests.integration.test_index_api_647 import embedding_provider, withdraw


def test_publish_records_durable_search_update(client):
    data = published_input(client)
    response = client.get(data["base"] + "/search-readiness")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["revision"] == 1
    assert client.get(data["base"] + "/indexing-runs").json() == []


def test_replaying_publication_does_not_increment_sync_revision(client, source):
    from qnu.domains.knowledge.publication.models import PublicationDecision, PublicationPreview
    from qnu.platform.database import AsyncSessionFactory

    async def original_request():
        async with AsyncSessionFactory() as db:
            decision = await db.scalar(
                select(PublicationDecision).where(PublicationDecision.action == "publish")
            )
            preview = await db.get(PublicationPreview, decision.preview_id)
            return {"preview_id": preview.id, "preview_sha256": preview.preview_sha256}

    as_actor(PLATFORM)
    replay = client.post(
        source["version_url"] + "/decisions",
        json=client.portal.call(original_request),
        headers={"Idempotency-Key": "publish"},
    )
    assert replay.status_code == 200, replay.text
    assert client.get(source["base"] + "/search-readiness").json()["revision"] == 1


def test_publication_and_outbox_roll_back_together(client, source, monkeypatch):
    from qnu.domains.knowledge.index import sync
    from qnu.platform.errors import Conflict

    original = sync.mark_pending

    async def fail_after_mark(*args):
        await original(*args)
        raise Conflict("Synthetic transaction interruption.", code="synthetic_rollback")

    monkeypatch.setattr(sync, "mark_pending", fail_after_mark)
    as_actor(PLATFORM)
    preview = client.post(
        source["version_url"] + "/decision-preview",
        json={"action": "withdraw", "reason": "Synthetic rollback test."},
    ).json()
    response = client.post(
        source["version_url"] + "/decisions",
        json={"preview_id": preview["id"], "preview_sha256": preview["preview_sha256"]},
        headers={"Idempotency-Key": "withdraw-rollback"},
    )
    assert response.status_code == 409, response.text
    assert client.get(source["document_url"] + "/published").status_code == 200
    assert client.get(source["base"] + "/search-readiness").json()["revision"] == 1


def test_several_publications_coalesce_to_the_current_snapshot(client, source):
    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        withdraw(client, source)
        as_actor(PLATFORM)
        version = client.get(source["version_url"]).json()
        for action in ("approve", "publish"):
            payload = {"action": action, "reason": "Synthetic current publication."}
            if action == "approve":
                payload["review_skip"] = {
                    "confirmed_skip": True,
                    "version_id": version["id"],
                    "bundle_sha256": version["bundle_sha256"],
                    "retrieval_metadata_sha256": version["retrieval_metadata_sha256"],
                }
            preview = client.post(source["version_url"] + "/decision-preview", json=payload)
            assert preview.status_code == 200, preview.text
            body = preview.json()
            result = client.post(
                source["version_url"] + "/decisions",
                json={"preview_id": body["id"], "preview_sha256": body["preview_sha256"]},
                headers={"Idempotency-Key": "again-" + action},
            )
            assert result.status_code == 200, result.text
        assert client.get(source["base"] + "/search-readiness").json()["revision"] == 3
        assert sync_now(client, source) == "building"
        rows = client.get(source["base"] + "/indexing-runs").json()
        assert len(rows) == 1
        assert execute_index(client, rows[0]["id"]) == "completed"
        assert sync_now(client, source) == "ready"
        assert len(fake.requests) == 1


def sync_now(client, data):
    from qnu.domains.knowledge.index.sync import synchronize
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def execute():
        async with AsyncSessionFactory() as db:
            return await synchronize(db, app.state.container, data["collection"]["id"])

    return client.portal.call(execute)


@pytest.fixture
def source(client):
    data = published_input(client)
    # Workers re-resolve current DB membership; a queue payload cannot grant admin roles.
    add_member(client, data["workspace"]["id"], PLATFORM.actor_id, "admin")
    as_actor(EDITOR)
    yield data
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def cleanup():
        async with AsyncSessionFactory() as db:
            names = list((await db.scalars(select(IndexRun.vector_collection))).all())
        for name in names:
            await app.state.container.vector_store.delete_collection(name)

    client.portal.call(cleanup)


def test_automatic_build_activates_and_queue_loss_is_recoverable(client, source):
    from qnu.main import app

    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        old_queue = app.state.container.job_queue
        app.state.container.job_queue = FakeJobQueue(failing=True)
        try:
            assert sync_now(client, source) == "building"
            rows = client.get(source["base"] + "/indexing-runs").json()
            assert len(rows) == 1 and rows[0]["dispatched_at"] is None
            assert sync_now(client, source) == "building"
            assert len(client.get(source["base"] + "/indexing-runs").json()) == 1
            assert execute_index(client, rows[0]["id"]) == "completed"
            assert sync_now(client, source) == "ready"
            assert len(fake.requests) == 1
            ready = client.get(source["document_url"] + "/index-readiness").json()
            assert ready["status"] == "ready"
            assert ready["version_id"] == source["compiled"]["version"]["id"]
        finally:
            app.state.container.job_queue = old_queue


def test_missing_provider_does_not_undo_publication_and_retry_is_idempotent(client, source):
    assert sync_now(client, source) == "failed"
    assert client.get(source["document_url"] + "/published").status_code == 200
    url = source["base"] + "/search-readiness/retry"
    as_actor(MEMBER)
    assert client.post(url, json={}, headers={"Idempotency-Key": "repair"}).status_code == 403
    as_actor(OUTSIDER)
    assert client.get(source["base"] + "/search-readiness").status_code == 404
    as_actor(EDITOR)
    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        first = client.post(url, json={}, headers={"Idempotency-Key": "repair"})
        assert first.status_code == 202, first.text
        replay = client.post(url, json={}, headers={"Idempotency-Key": "repair"})
        assert replay.status_code == 202 and replay.json()["revision"] == first.json()["revision"]
        assert sync_now(client, source) == "building"


def test_uncertain_embedding_is_not_automatically_sent_again(client, source):
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.platform.database import AsyncSessionFactory

    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        assert sync_now(client, source) == "building"
        run_id = client.get(source["base"] + "/indexing-runs").json()[0]["id"]

        async def interrupt():
            async with AsyncSessionFactory() as db:
                run = await db.get(IndexRun, run_id)
                run.status, run.error_code = "uncertain", "embedding_uncertain"
                await db.commit()

        client.portal.call(interrupt)
        assert sync_now(client, source) == "uncertain"
        assert sync_now(client, source) == "not_pending"
        assert not fake.requests
        assert len(client.get(source["base"] + "/indexing-runs").json()) == 1


def test_concurrent_delivery_prepares_only_one_run(client, source):
    from qnu.domains.knowledge.index.sync import synchronize
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def deliver():
        async def one():
            async with AsyncSessionFactory() as db:
                return await synchronize(db, app.state.container, source["collection"]["id"])

        return await asyncio.gather(one(), one())

    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        assert client.portal.call(deliver) == ["building", "building"]
        assert len(client.get(source["base"] + "/indexing-runs").json()) == 1
        assert not fake.requests


def test_withdrawal_while_building_keeps_newer_intent_and_never_activates_stale_content(
    client, source
):
    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        assert sync_now(client, source) == "building"
        run_id = client.get(source["base"] + "/indexing-runs").json()[0]["id"]
        withdraw(client, source)
        assert client.get(source["base"] + "/search-readiness").json()["revision"] == 2
        assert sync_now(client, source) == "building"
        assert execute_index(client, run_id) == "failed"
        assert sync_now(client, source) == "empty"
        assert not fake.requests
        assert all(not r["is_active"] for r in client.get(source["base"] + "/indexing-runs").json())


def test_retirement_preserves_citations_and_never_removes_active_or_recent_index(
    client, source, monkeypatch
):
    from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
    from qnu.domains.knowledge.index.retirement import retire_vectors, retirement_candidates
    from qnu.main import app
    from qnu.platform.config import get_settings
    from qnu.platform.database import AsyncSessionFactory

    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        for key in ("old", "recent", "active"):
            result = client.post(
                source["base"] + "/indexing-runs", json={}, headers={"Idempotency-Key": key}
            )
            assert result.status_code == 201, result.text
            assert execute_index(client, result.json()["run"]["id"]) == "completed"
        rows = client.get(source["base"] + "/indexing-runs").json()

        async def clean_and_check():
            async with AsyncSessionFactory() as db:
                assert not await retire_vectors(db, app.state.container.vector_store, rows[0]["id"])
                assert not await retire_vectors(db, app.state.container.vector_store, rows[1]["id"])
                assert not await retire_vectors(db, app.state.container.vector_store, rows[2]["id"])
                assert await retirement_candidates(db, app.state.container.vector_store) == []
                monkeypatch.setattr(get_settings(), "INDEX_RETIRE_AFTER_SECONDS", 0)
                assert await retirement_candidates(db, app.state.container.vector_store) == [
                    rows[2]["id"]
                ]
                assert await retire_vectors(db, app.state.container.vector_store, rows[2]["id"])
                assert not await retire_vectors(db, app.state.container.vector_store, rows[2]["id"])
                run = await db.get(IndexRun, rows[2]["id"])
                chunks = list(
                    (await db.scalars(select(IndexChunk).where(IndexChunk.run_id == run.id))).all()
                )
                assert chunks and all(c.vector is None and c.text and c.citations for c in chunks)
                assert await app.state.container.blob_store.get_bytes(run.manifest_key)
                assert not await app.state.container.vector_store.collection_exists(
                    run.vector_collection
                )

        client.portal.call(clean_and_check)


def test_maintenance_recovers_committed_publication_without_browser(client, source, monkeypatch):
    from qnu.main import app
    from qnu.workers.tasks.indexing import index_maintenance, index_run, index_sync

    queue = FakeJobQueue()
    monkeypatch.setattr(app.state.container, "job_queue", queue)
    ctx = {"container": app.state.container, "worker_id": "sync-test"}
    with FakeEmbedding() as fake:
        embedding_provider(client, source, fake.base_url)
        assert client.portal.call(index_maintenance, ctx) == 1
        job = next(j for j in queue.jobs if j["function"] == "index_sync")
        assert client.portal.call(index_sync, ctx, *job["args"]) == "building"
        run = next(j for j in queue.jobs if j["function"] == "index_run")
        assert client.portal.call(index_run, ctx, *run["args"]) == "completed"
        assert client.portal.call(index_sync, ctx, *job["args"]) == "ready"
        assert len(fake.requests) == 1


class FlakyUpsert:
    """A transient vector outage on the first write, then the real target."""

    def __init__(self, inner, failures=1):
        self._inner = inner
        self.failures = failures
        self.attempts = 0

    def __getattr__(self, name):
        return getattr(self._inner, name)

    async def upsert(self, collection, points):
        from qnu.platform.errors import DependencyUnavailable

        self.attempts += 1
        if self.failures:
            self.failures -= 1
            raise DependencyUnavailable(
                "Qdrant tạm thời không nhận vector.", code="vector_unavailable"
            )
        await self._inner.upsert(collection, points)


def test_transient_vector_failure_is_redispatched_without_waiting_for_reconcile(
    client, source, monkeypatch
):
    from qnu.main import app
    from qnu.workers.tasks.indexing import index_run

    with FakeEmbedding() as fake:
        queue = FakeJobQueue()
        monkeypatch.setattr(app.state.container, "job_queue", queue)
        embedding_provider(client, source, fake.base_url)
        assert sync_now(client, source) == "building"
        run_id = client.get(source["base"] + "/indexing-runs").json()[0]["id"]
        flaky = FlakyUpsert(app.state.container.vector_store)
        monkeypatch.setattr(app.state.container, "vector_store", flaky)
        ctx = {"container": app.state.container, "worker_id": "retry-test"}

        assert client.portal.call(index_run, ctx, run_id) == "queued"
        rows = client.get(source["base"] + "/indexing-runs").json()
        assert rows[0]["status"] == "queued" and rows[0]["dispatched_at"] is not None
        deliveries = [
            job for job in queue.jobs if job["function"] == "index_run" and job["args"] == (run_id,)
        ]
        assert deliveries[-1]["job_id"] == f"qnu:v1:index:{run_id}:2"
        assert client.portal.call(index_run, ctx, run_id) == "completed"
        assert flaky.attempts == 2
        assert len(fake.requests) == 1
