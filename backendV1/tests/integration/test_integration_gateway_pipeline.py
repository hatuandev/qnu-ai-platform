"""Real gateway -> authorization -> hybrid RAG -> ModelOps with local fake model HTTP."""

import json
import os

import pytest
from redis.asyncio import from_url

from qnu.api.dependencies import get_actor
from qnu.domains.identity.service import resolve_actor
from qnu.domains.integration.gateway import get_redis_client
from qnu.main import app
from tests.integration.knowledge_support import API, PLATFORM, as_actor
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401


@pytest.mark.parametrize("output_budget", [128, None])
def test_external_key_calls_real_rag_and_preserves_assistant_config(client, ready, output_budget):  # noqa: F811
    ws = ready["workspace"]["id"]
    as_actor(PLATFORM)
    assistant = client.post(
        f"{API}/workspaces/{ws}/assistants",
        json={
            "name": "Integration pipeline fixture",
            "persona": "Synthetic gateway persona",
            "collection_id": ready["collection"]["id"],
            "chat_provider_id": ready["chat_provider"]["id"],
            "max_output_tokens": output_budget,
            "rag_policy": {"retrieval_mode": "hybrid", "context_window": 1},
        },
    )
    assert assistant.status_code == 201, assistant.text
    ast = assistant.json()["id"]
    app.dependency_overrides[resolve_actor] = lambda: PLATFORM
    created = client.post(
        f"{API}/workspaces/{ws}/integrations/keys",
        json={
            "app_name": "Pipeline synthetic app",
            "name": "Pipeline synthetic key",
            "allowed_assistant_ids": [ast],
        },
    )
    assert created.status_code == 201, created.text
    key = created.json()
    app.dependency_overrides.pop(get_actor, None)
    app.dependency_overrides.pop(resolve_actor, None)
    # Explicit isolated Redis endpoint; never the user's application Redis DB.
    redis = from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
    app.dependency_overrides[get_redis_client] = lambda: redis
    try:
        response = client.post(
            f"{API}/integrations/openai/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + key["secret_key"],
            },
            json={
                "model": ast,
                "messages": [
                    {"role": "user", "content": "Chỉ tiêu trúng tuyển năm 2024 là bao nhiêu?"}
                ],
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["qnu_extensions"]["status"] == "answered"
        assert "150" in body["choices"][0]["message"]["content"]
        assert body["qnu_extensions"]["sources"]
        assert body["qnu_extensions"]["statements"][0]["evidence_ids"][0].startswith("E")
        sent = ready["answer_chat"].requests[0]["body"]
        if output_budget is None:
            assert sent["max_tokens"] > 128
        else:
            assert sent["max_tokens"] == output_budget
        # Persona is deliberately data in the payload style field, never promoted to system policy.
        assert json.loads(sent["messages"][-1]["content"])["style"] == "Synthetic gateway persona"
        assert sent["model"] == "test-chat"
    finally:
        app.dependency_overrides.pop(get_redis_client, None)
        app.dependency_overrides.pop(resolve_actor, None)

        async def cleanup():
            keys = [k async for k in redis.scan_iter(match=f"*integrations:*:{key['id']}:*")]
            if keys:
                await redis.delete(*keys)
            await redis.aclose()

        client.portal.call(cleanup)
