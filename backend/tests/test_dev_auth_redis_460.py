"""Opt-in real Redis integration; never touches application Redis or its data."""

import asyncio
import os
import subprocess
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from redis.exceptions import RedisError
from test_dev_auth_production_460 import ORIGIN, PASSWORD, production_settings
from test_dev_auth_production_460 import (
    auth_app as auth_app,  # noqa: PLC0414 -- pytest fixture re-export
)

from app.core.exceptions import AppException
from app.modules.auth import dev_access


@pytest.fixture
def isolated_redis_url() -> Iterator[str]:
    if os.environ.get("QNU_TEST_DEV_AUTH_REDIS") != "1":
        pytest.skip("Set QNU_TEST_DEV_AUTH_REDIS=1 for a disposable real Redis container")
    name = "qnu-auth460-" + uuid4().hex[:12]
    created = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--label",
            "qnu.test=auth460",
            "-p",
            "127.0.0.1::6379",
            "redis:7-alpine",
            "redis-server",
            "--save",
            "",
            "--appendonly",
            "no",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert created.stdout.strip()
    try:
        port = subprocess.run(
            ["docker", "port", name, "6379/tcp"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        yield "redis://" + port.stdout.strip() + "/0"
    finally:
        subprocess.run(
            ["docker", "stop", "--time", "1", name], capture_output=True, timeout=15, check=True
        )


@pytest.mark.asyncio
async def test_real_redis_shared_window_expiry_and_global_limit(
    isolated_redis_url: str, monkeypatch: pytest.MonkeyPatch, auth_app: FastAPI
) -> None:
    def new_client() -> Redis:
        return Redis.from_url(
            isolated_redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
        )

    async with new_client() as client:
        for attempt in range(30):
            try:
                await client.ping()
                break
            except (OSError, RedisError):
                if attempt == 29:
                    raise
                await asyncio.sleep(0.1)
        monkeypatch.setattr(dev_access, "get_redis_client", new_client)
        settings = production_settings()

        def request(peer: str) -> Request:
            return Request(
                {"type": "http", "method": "POST", "headers": [], "client": (peer, 1234)}
            )

        # Separate clients stand in for workers; atomic increment must admit exactly ten.
        results = await asyncio.gather(
            *[
                dev_access.enforce_login_rate_limit(request("127.0.0.9"), settings)
                for _ in range(20)
            ],
            return_exceptions=True,
        )
        assert sum(result is None for result in results) == 10
        assert (
            sum(
                isinstance(result, AppException) and result.status_code == 429 for result in results
            )
            == 10
        )
        keys = await client.keys("auth:dev:*")
        assert len(keys) == 2
        assert all([0 < await client.ttl(key) <= 300 for key in keys])
        # Expire only the isolated fixture's counters; no app Redis/FLUSHDB.
        for key in keys:
            await client.pexpire(key, 1)
        await asyncio.sleep(0.02)
        await dev_access.enforce_login_rate_limit(request("127.0.0.9"), settings)
        for index in range(99):
            await dev_access.enforce_login_rate_limit(request(f"test-peer-{index}"), settings)
        with pytest.raises(AppException) as error:
            await dev_access.enforce_login_rate_limit(request("new-peer"), settings)
        assert error.value.status_code == 429
        # Full HTTP -> real Redis -> signed cookie -> protected API, no throttle stub.
        async with AsyncClient(transport=ASGITransport(app=auth_app), base_url=ORIGIN) as browser:
            response = await browser.post(
                "/auth/login", json={"access_key": PASSWORD}, headers={"Origin": ORIGIN}
            )
            assert response.status_code == 200
            assert (await browser.get("/auth/me")).json()["authenticated"] is True
            assert (await browser.get("/protected")).status_code == 200
