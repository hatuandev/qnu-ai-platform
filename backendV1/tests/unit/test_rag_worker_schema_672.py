"""A migrated DB does not make an old worker binary compatible."""

import json

import pytest

from qnu.adapters.queue.arq_queue import ArqJobQueue
from qnu.platform.schema import SCHEMA_HEAD


@pytest.mark.parametrize(
    "schema,code,ready",
    [
        (SCHEMA_HEAD, SCHEMA_HEAD, True),
        (SCHEMA_HEAD, "0002_operational_readiness", False),
        ("0002_operational_readiness", SCHEMA_HEAD, False),
        (SCHEMA_HEAD, None, False),
    ],
)
async def test_worker_requires_matching_database_and_code_schema(monkeypatch, schema, code, ready):
    class Pool:
        async def ping(self):
            return True

        async def scan_iter(self, **kwargs):
            yield "own-worker"

        async def get(self, key):
            return json.dumps({"schema_head": schema, "code_head": code})

    async def pool(self):
        return Pool()

    monkeypatch.setattr(ArqJobQueue, "_get_pool", pool)
    queue = ArqJobQueue("redis://127.0.0.1:6379/3", "test-schema")
    result = await queue.health()
    assert result["worker_schema_head"] == (SCHEMA_HEAD if ready else None)
