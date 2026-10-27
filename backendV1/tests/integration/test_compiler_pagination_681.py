"""Offset paging exercises the real handler/database and preserves authorization."""

from sqlalchemy import select

from tests.integration.compiler_support import chat_provider, processed_input, request_compile
from tests.integration.knowledge_support import EDITOR, OUTSIDER, as_actor, create_collection


def seed_runs(client, count=105):
    from qnu.domains.knowledge.compilation.models import CompilationRun
    from qnu.platform.database import AsyncSessionFactory

    data = processed_input(client, code="paging-681")
    chat_provider(client, data, "http://127.0.0.1:20128/v1")  # Configuration only; no chat call.
    response = request_compile(client, data)
    assert response.status_code == 201, response.text
    original_id = response.json()["run"]["id"]
    other = create_collection(client, data["workspace"]["id"], "Other collection")

    async def insert():
        async with AsyncSessionFactory() as db:
            original = await db.scalar(
                select(CompilationRun).where(CompilationRun.id == original_id)
            )
            for generation in range(2, count + 1):
                db.add(
                    CompilationRun(
                        id=f"paging-{generation}",
                        workspace_id=original.workspace_id,
                        collection_id=original.collection_id,
                        generation=generation,
                        topic="Synthetic pagination",
                        status="failed",
                        requested_by=original.requested_by,
                        idempotency_key=f"paging-{generation}",
                        request_hash="0" * 64,
                        input_sha256="0" * 64,
                        provider_id=original.provider_id,
                        config=original.config,
                    )
                )
            db.add(
                CompilationRun(
                    id="paging-foreign",
                    workspace_id=original.workspace_id,
                    collection_id=other["id"],
                    generation=999,
                    topic="Other collection",
                    status="failed",
                    requested_by=original.requested_by,
                    idempotency_key="paging-foreign",
                    request_hash="0" * 64,
                    input_sha256="0" * 64,
                    provider_id=original.provider_id,
                    config=original.config,
                )
            )
            await db.commit()

    client.portal.call(insert)
    return data


def test_compiler_offset_reaches_beyond_first_hundred_without_duplicates(client):
    data = seed_runs(client)
    first = client.get(data["url"], params={"limit": 100, "offset": 0})
    second = client.get(data["url"], params={"limit": 100, "offset": 100})
    assert first.status_code == second.status_code == 200
    assert [r["generation"] for r in first.json()] == list(range(105, 5, -1))
    assert [r["generation"] for r in second.json()] == [5, 4, 3, 2, 1]
    assert not ({r["id"] for r in first.json()} & {r["id"] for r in second.json()})
    assert client.get(data["url"], params={"offset": 105}).json() == []
    default = client.get(data["url"])
    assert default.status_code == 200 and len(default.json()) == 20
    assert all(row["collection_id"] == data["collection"]["id"] for row in first.json())


def test_compiler_offset_keeps_workspace_membership_and_collection_scope(client):
    data = seed_runs(client, count=2)
    as_actor(OUTSIDER)
    denied = client.get(data["url"], params={"offset": 1})
    assert denied.status_code == 404  # Non-members must not learn that the workspace exists.
    assert denied.json()["code"] == "workspace_not_found"
    as_actor(EDITOR)
    result = client.get(data["url"], params={"offset": 1, "limit": 1})
    assert result.status_code == 200 and result.json()[0]["generation"] == 1
    assert result.json()[0]["collection_id"] == data["collection"]["id"]


def test_compiler_offset_rejects_negative_and_out_of_budget_requests(client):
    data = seed_runs(client, count=1)
    assert client.get(data["url"], params={"offset": -1}).status_code == 422
    assert client.get(data["url"], params={"limit": 101}).status_code == 422
