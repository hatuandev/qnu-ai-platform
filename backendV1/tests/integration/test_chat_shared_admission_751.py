"""Real Redis Lua admission, multiple concurrent callers in the isolated test namespace."""

import asyncio
import uuid
from types import SimpleNamespace

from qnu.domains.modelops.resilience import admission


def test_real_redis_enforces_shared_limit_and_releases_own_leases(client, monkeypatch):
    settings = admission.get_settings()
    assert settings.CACHE_NAMESPACE.startswith("qnu:test:")
    monkeypatch.setattr(settings, "MODEL_CHAT_CONCURRENCY", 2)
    request = SimpleNamespace(
        endpoint="https://test.invalid/v1", model=uuid.uuid4().hex, timeout_seconds=2
    )

    async def exercise():
        active, peak = 0, 0

        async def caller():
            nonlocal active, peak
            async with admission.chat_slot(request):
                active += 1
                peak = max(active, peak)
                await asyncio.sleep(0.03)
                active -= 1

        await asyncio.gather(*(caller() for _ in range(8)))
        assert peak == 2
        assert (
            await admission.get_redis().zcard(
                admission.resource_key(request.endpoint, request.model)
            )
            == 0
        )

    client.portal.call(exercise)
