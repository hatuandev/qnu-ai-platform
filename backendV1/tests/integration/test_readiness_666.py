"""Readiness reports observed workers/dependencies, not invented inference success."""
# ruff: noqa: F811

import asyncio
import os
import uuid

from arq import create_pool
from arq.connections import RedisSettings

from qnu.adapters.queue.arq_queue import ArqJobQueue
from qnu.platform.config import get_settings
from qnu.workers import heartbeat
from tests.integration.compiler_support import processed_input
from tests.integration.knowledge_support import API, EDITOR, OUTSIDER, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401


def test_readiness_reports_missing_configuration_and_does_not_claim_live_inference(client):
    data = processed_input(client, code="readiness-666")
    as_actor(PLATFORM)
    url = f"{API}/workspaces/{data['workspace']['id']}/operations/readiness"
    response = client.get(url)
    assert response.status_code == 200, response.text
    body = response.json()
    assert not body["ready"] and not body["live_inference_verified"]
    assert body["checks"]["storage"]["ok"]
    assert not body["checks"]["chat"]["ok"] and not body["checks"]["embedding"]["ok"]
    assert not body["production_auth_configured"]
    as_actor(EDITOR)
    assert client.get(url).status_code == 403
    as_actor(OUTSIDER)
    assert client.get(url).status_code == 404


def test_worker_heartbeat_is_queue_scoped_and_removed_on_shutdown(client, monkeypatch):
    queue_name = "qnu:v1:test:readiness:" + uuid.uuid4().hex
    settings = get_settings()
    monkeypatch.setattr(settings, "QUEUE_NAME", queue_name)
    redis_url = os.environ["TEST_REDIS_URL"]
    queue = ArqJobQueue(redis_url, queue_name)
    other = ArqJobQueue(redis_url, queue_name + "-other")

    async def check():
        pool = await create_pool(RedisSettings.from_dsn(redis_url), default_queue_name=queue_name)
        ctx = {"redis": pool, "worker_id": uuid.uuid4().hex}
        try:
            assert (await queue.health())["worker_schema_head"] is None
            await heartbeat.start(ctx)
            for _ in range(50):
                if (await queue.health())["worker_schema_head"]:
                    break
                await asyncio.sleep(0.02)
            assert (await queue.health())["worker_schema_head"] == "0003_rag_policy_metadata"
            assert (await other.health())["worker_schema_head"] is None
            await heartbeat.stop(ctx)
            assert (await queue.health())["worker_schema_head"] is None
        finally:
            await heartbeat.stop(ctx)
            await queue.close()
            await other.close()
            await pool.aclose()

    client.portal.call(check)


def test_readiness_distinguishes_missing_zero_unlimited_and_blocked_quota(
    client, ready, monkeypatch
):
    from sqlalchemy import delete

    from qnu.domains.modelops.models import WorkspaceQuota
    from qnu.main import app
    from qnu.platform.database import AsyncSessionFactory

    async def worker_healthy():
        return {"ok": True, "worker_schema_head": "0003_rag_policy_metadata"}

    monkeypatch.setattr(app.state.container.job_queue, "health", worker_healthy)
    as_actor(PLATFORM)
    base = f"{API}/workspaces/{ready['workspace']['id']}"
    providers = {
        "ocr": ready["ocr_provider"]["id"],
        "chat": ready["chat_provider"]["id"],
        "embedding": ready["embedding_provider"]["id"],
    }
    granted = client.put(
        base + "/allowed-providers",
        json={"provider_ids": list(providers.values()), "defaults": providers},
    )
    assert granted.status_code == 200, granted.text
    url = base + "/operations/readiness"
    before = client.get(url)
    assert before.status_code == 200 and before.json()["ready"], before.text

    async def unconfigure():
        async with AsyncSessionFactory() as db:
            await db.execute(
                delete(WorkspaceQuota).where(
                    WorkspaceQuota.workspace_id == ready["workspace"]["id"]
                )
            )
            await db.commit()

    client.portal.call(unconfigure)
    missing = client.get(url).json()
    assert not missing["ready"]
    assert not missing["checks"]["quota"]["configured"]
    for limit, blocked, expected in [(0, False, False), (None, False, True), (None, True, False)]:
        configured = client.put(
            base + "/quota", json={"monthly_token_limit": limit, "is_blocked": blocked}
        )
        assert configured.status_code == 200, configured.text
        report = client.get(url).json()
        assert report["checks"]["quota"]["configured"]
        assert report["checks"]["quota"]["ok"] == expected and report["ready"] == expected
