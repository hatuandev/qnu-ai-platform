"""New index generations size source chunks from the authorized embedding model."""

import pytest

from qnu.domains.knowledge.index.models import IndexChunk, IndexRun
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from tests.integration.index_support import published_input
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeJobQueue, use_queue
from tests.integration.test_index_api_647 import embedding_provider


@pytest.mark.parametrize(
    "override,input_tokens,context_tokens,expected,contextual",
    [
        (None, 8192, None, 8160, False),
        (None, 4096, 8192, 4064, False),
        (2000, 8192, None, 2000, False),
        (None, 8192, None, 8160, True),
    ],
)
def test_index_pins_model_budget_and_respects_explicit_override(
    client, monkeypatch, override, input_tokens, context_tokens, expected, contextual
):
    from sqlalchemy import select

    monkeypatch.setattr(get_settings(), "INDEX_CHUNK_MAX_BYTES", override)
    data = published_input(client)
    provider = embedding_provider(client, data)
    as_actor(PLATFORM)
    response = client.patch(
        f"{API}/modelops/providers/{provider['id']}",
        json={
            "token_limits": {
                "max_input_tokens": input_tokens,
                "context_window_tokens": context_tokens,
            }
        },
    )
    assert response.status_code == 200, response.text
    as_actor(EDITOR)
    use_queue(FakeJobQueue())
    response = client.post(
        data["base"] + "/indexing-runs",
        json={"contextual_search": contextual},
        headers={"Idempotency-Key": "model-budget"},
    )
    assert response.status_code == 201, response.text
    run_id = response.json()["run"]["id"]

    async def check_pinned_chunks():
        async with AsyncSessionFactory() as db:
            run = await db.get(IndexRun, run_id)
            assert run.config["chunk_max_bytes"] == expected
            chunks = list(await db.scalars(select(IndexChunk).where(IndexChunk.run_id == run_id)))
            assert chunks
            assert all(len(chunk.text.encode("utf-8")) <= expected for chunk in chunks)
            assert all(chunk.citations for chunk in chunks)

    client.portal.call(check_pinned_chunks)
