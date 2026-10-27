"""Exercise ownership fencing, raw retention and real runtime budget boundaries."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select, update

from qnu.domains.ocr.execution import claim_run
from qnu.domains.ocr.lease import LeaseLost, commit_owned, heartbeat, renew_claim
from qnu.domains.ocr.models import OcrProcessingRun, OcrRunArtifact, utcnow
from qnu.main import app
from qnu.platform.database import AsyncSessionFactory
from qnu.workers.tasks.ocr import ocr_reconcile_queued
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import (
    FakeJobQueue,
    FakeNemotron,
    execute_now,
    request_run,
    set_quota,
)
from tests.integration.test_ocr_regressions_643 import setup


def test_expired_owner_cannot_commit_after_another_worker_claims(client):
    with FakeNemotron() as fake:
        _provider, run, _url = setup(client, fake, "fenced-writer")

        async def scenario():
            async with AsyncSessionFactory() as old:
                first = await claim_run(old, run["id"], "old-token", 60)
                assert await renew_claim(run["id"], "old-token", 60)
                async with AsyncSessionFactory() as new:
                    await new.execute(
                        update(OcrProcessingRun)
                        .where(OcrProcessingRun.id == run["id"])
                        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
                    )
                    await new.commit()
                    assert not await renew_claim(run["id"], "old-token", 60)
                    claimed = await claim_run(new, run["id"], "new-token", 60)
                    assert claimed is not None
                first.status = "completed"
                try:
                    await commit_owned(old, first)
                    fenced = False
                except LeaseLost:
                    fenced = True
                    await old.rollback()
            async with AsyncSessionFactory() as check:
                current = await check.get(OcrProcessingRun, run["id"])
                return fenced, current.status, current.worker_id

        assert client.portal.call(scenario) == (True, "running", "new-token")


def test_heartbeat_renews_a_live_claim(client):
    with FakeNemotron() as fake:
        _provider, run, _url = setup(client, fake, "heartbeat-live")

        async def scenario():
            async with AsyncSessionFactory() as db:
                current = await claim_run(db, run["id"], "heartbeat-token", 1)
                before = current.lease_expires_at
                async with heartbeat(current, 1):
                    await asyncio.sleep(1.1)
                    async with AsyncSessionFactory() as check:
                        after = (await check.get(OcrProcessingRun, run["id"])).lease_expires_at
                        stolen = await claim_run(check, run["id"], "other-worker", 60)
                return after > before and stolen is None

        assert client.portal.call(scenario)


def test_lost_claim_does_not_publish_a_provider_result(client):
    with FakeNemotron() as fake:
        _provider, run, url = setup(client, fake, "fence-after-http")
        delegate = app.state.container.ocr_engine

        class StolenClaim:
            async def extract_page(self, image, request):
                response = await delegate.extract_page(image, request)
                async with AsyncSessionFactory() as db:
                    await db.execute(
                        update(OcrProcessingRun)
                        .where(OcrProcessingRun.id == run["id"])
                        .values(
                            worker_id="replacement-token",
                            lease_expires_at=utcnow() + timedelta(seconds=60),
                        )
                    )
                    await db.commit()
                return response

        outcome = execute_now(client, run["id"], engine=StolenClaim())
        assert outcome.reason == "worker_lease_lost"
        assert client.get(url).json()["status"] == "running"
        assert len(fake.requests) == 1


@pytest.mark.parametrize("mode", ["truncated", "malformed", "http_error"])
def test_every_received_error_keeps_raw_bytes(client, mode):
    with FakeNemotron() as fake:
        fake.mode = mode
        _provider, run, _url = setup(client, fake, f"keep-raw-{mode}")
        assert execute_now(client, run["id"]).status == "failed"

        async def raw_record():
            async with AsyncSessionFactory() as db:
                return await db.scalar(
                    select(OcrRunArtifact).where(
                        OcrRunArtifact.run_id == run["id"], OcrRunArtifact.kind == "raw_response"
                    )
                )

        record = client.portal.call(raw_record)
        assert record is not None and record.size_bytes > 0


def test_unknown_multimodal_input_is_blocked_before_http(client):
    with FakeNemotron() as fake:
        provider, run, _url = setup(client, fake, "unknown-image-budget")
        as_actor(PLATFORM)
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}",
                json={
                    "token_limits": {"context_window_tokens": 1000000, "max_output_tokens": 65536}
                },
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        result = execute_now(client, run["id"])
        assert result.reason == "model_input_budget_unknown" and not fake.requests


def test_quota_covers_image_input_and_output_instead_of_a_fixed_output_number(client):
    with FakeNemotron() as fake:
        _provider, run, url = setup(client, fake, "full-request-quota")
        workspace_id = client.get(url).json()["workspace_id"]
        # Input bound8192 + requested output8192 needs16384, even though the old
        # OCR_PAGE_TOKEN_BUDGET8192 would have allowed this request.
        assert set_quota(client, workspace_id, 10000).status_code == 200
        outcome = execute_now(client, run["id"])
        assert outcome.reason == "quota_exceeded" and not fake.requests


def test_reconcile_recovers_old_delivery_without_replaying_a_live_worker(client):
    with FakeNemotron() as fake:
        _provider, run, _url = setup(client, fake, "stale-delivery")
        queue = FakeJobQueue()

        async def scenario():
            async with AsyncSessionFactory() as db:
                await db.execute(
                    update(OcrProcessingRun)
                    .where(OcrProcessingRun.id == run["id"])
                    .values(dispatched_at=utcnow() - timedelta(hours=1))
                )
                await db.commit()
            assert await ocr_reconcile_queued({"container": SimpleNamespace(job_queue=queue)}) == 1
            async with AsyncSessionFactory() as db:
                assert await claim_run(db, run["id"], "healthy-token", 60) is not None
            return await ocr_reconcile_queued({"container": SimpleNamespace(job_queue=queue)})

        assert client.portal.call(scenario) == 0


def test_capacity_change_creates_new_generation_instead_of_reusing_old_result(client):
    with FakeNemotron() as fake:
        provider, run, url = setup(client, fake, "reuse-config-change")
        assert execute_now(client, run["id"]).status == "completed"
        identity = client.get(url).json()
        as_actor(PLATFORM)
        limits = dict(provider["token_limits"], max_output_tokens=65536)
        assert (
            client.patch(
                f"{API}/modelops/providers/{provider['id']}", json={"token_limits": limits}
            ).status_code
            == 200
        )
        as_actor(EDITOR)
        second = request_run(
            client,
            identity["workspace_id"],
            identity["collection_id"],
            identity["source_id"],
            identity["revision_id"],
        ).json()
        assert second["created"] and second["run"]["generation"] == 2
        assert len(fake.requests) == 1
