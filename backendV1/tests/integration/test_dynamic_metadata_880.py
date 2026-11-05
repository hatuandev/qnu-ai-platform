import copy

import pytest
from sqlalchemy import select

from qnu.domains.knowledge.index.models import IndexChunk
from qnu.platform.database import AsyncSessionFactory
from tests.integration import rag_support_672
from tests.integration.knowledge_support import EDITOR, OUTSIDER, PLATFORM, as_actor
from tests.integration.rag_support_672 import metadata_index as metadata_index_fixture
from tests.integration.test_answers_api_648 import ready  # noqa: F401
from tests.integration.test_conversations_649 import chat_session  # noqa: F401
from tests.integration.test_index_api_647 import indexed  # noqa: F401

metadata_index = metadata_index_fixture


@pytest.fixture
def custom_metadata(monkeypatch):
    original = rag_support_672.prepared

    def prepared(client):
        data = original(client)
        draft = client.get(f"{data['url']}/{data['run']}/draft").json()
        citation = next(ref for ref in draft["citations"] if ref.endswith("ev_p001_b001"))
        data["annotations"][0]["values"]["attributes"] = {"PHỤ LỤC": "01"}
        data["annotations"][0]["evidence"].append({"citation": citation, "quote": "PHỤ LỤC 01"})
        return data

    monkeypatch.setattr(rag_support_672, "prepared", prepared)


@pytest.mark.usefixtures("custom_metadata")
def test_dynamic_filters_before_dense_and_fts_topk_and_facets_after_withdrawal(
    client, metadata_index
):
    data = metadata_index
    url = data["base"] + "/search-facets"
    facets = client.get(url)
    assert facets.status_code == 200, facets.text
    assert facets.headers["cache-control"] == "private, no-store"
    assert facets.json() == {"ready": True, "attributes": {"PHỤ LỤC": ["01"]}, "truncated": False}
    unknown_doc = client.get(url, params={"document_ids": "missing"})
    assert unknown_doc.status_code == 404, unknown_doc.text

    outcomes = []
    for mode in ("dense", "hybrid"):
        for automatic in (False, True):
            response = client.post(
                data["base"] + "/search",
                json={
                    "query": "PHỤ LỤC: 01",
                    "mode": mode,
                    "top_k": 1,
                    "scope_resolution": "catalog" if automatic else "explicit",
                    "metadata_filter": {} if automatic else {"attributes": {"PHỤ LỤC": "01"}},
                },
            )
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["trace"]["metadata_eligible_chunks"] == 1
            assert len(result["hits"]) == 1
            assert result["hits"][0]["structure"]["retrieval_metadata"][0]["values"][
                "attributes"
            ] == {
                "PHỤ LỤC": "01",
            }
            outcomes.append([hit["chunk_id"] for hit in result["hits"]])
    assert all(result == outcomes[0] for result in outcomes)

    count = len(data["embedding"].requests)
    missing = client.post(
        data["base"] + "/search",
        json={
            "query": "Tổng quan",
            "metadata_filter": {"attributes": {"PHỤ LỤC": "99"}},
        },
    )
    assert missing.status_code == 200 and missing.json()["hits"] == []
    assert len(data["embedding"].requests) == count
    conflict = client.post(
        data["base"] + "/search",
        json={
            "query": "PHỤ LỤC: 99",
            "scope_resolution": "catalog",
            "metadata_filter": {"attributes": {"PHỤ LỤC": "01"}},
        },
    )
    assert conflict.status_code == 409, conflict.text
    assert len(data["embedding"].requests) == count

    as_actor(OUTSIDER)
    denied = client.get(url)
    assert denied.status_code in (403, 404)
    as_actor(PLATFORM)
    preview = client.post(
        data["version_url"] + "/decision-preview",
        json={
            "action": "withdraw",
            "reason": "Dynamic metadata withdrawal regression.",
        },
    )
    assert preview.status_code == 200, preview.text
    withdrawn = client.post(
        data["version_url"] + "/decisions",
        headers={"Idempotency-Key": "withdraw-facets"},
        json={
            "preview_id": preview.json()["id"],
            "preview_sha256": preview.json()["preview_sha256"],
        },
    )
    assert withdrawn.status_code == 200, withdrawn.text
    as_actor(EDITOR)
    after = client.get(url)
    assert after.status_code == 200 and after.json()["attributes"] == {}
    assert len(data["embedding"].requests) == count


def test_legacy_index_facets_and_manifest_tampering(client, metadata_index):
    data = metadata_index
    url = data["base"] + "/search-facets"
    before = client.get(url)
    assert before.status_code == 200 and before.json()["attributes"] == {}

    async def mutate():
        async with AsyncSessionFactory() as db:
            row = await db.scalar(
                select(IndexChunk).where(IndexChunk.run_id == data["index_run_id"])
            )
            structure = copy.deepcopy(row.structure)
            structure["retrieval_metadata"] = [{"values": {"attributes": {"Giả": "mới"}}}]
            row.structure = structure
            await db.commit()

    client.portal.call(mutate)
    invalid = client.get(url)
    assert invalid.status_code == 409, invalid.text
    assert invalid.json()["code"] == "index_metadata_changed"


def test_no_index_does_not_expose_unconfirmed_compiler_proposals(client):
    data = rag_support_672.prepared(client)
    response = client.get(data["base"] + "/search-facets")
    assert response.status_code == 200, response.text
    assert response.json() == {"ready": False, "attributes": {}, "truncated": False}


def test_chat_keeps_fixed_and_previous_custom_scopes_and_rejects_conflict(client, chat_session):  # noqa: F811
    data = chat_session
    assistant = data["assistant"]
    as_actor(PLATFORM)
    url = f"/platform/v1alpha1/workspaces/{data['workspace']['id']}"
    updated = client.put(
        url + "/assistants/" + assistant["id"],
        json={
            "name": assistant["name"],
            "collection_id": data["collection"]["id"],
            "chat_provider_id": assistant["chat_provider_id"],
            "expected_revision": assistant["revision"],
            "rag_policy": {"metadata_filter": {"attributes": {"Cơ sở": "A"}}},
        },
    )
    assert updated.status_code == 200, updated.text
    as_actor(EDITOR)
    created = client.post(url + "/conversations", json={"assistant_id": assistant["id"]})
    assert created.status_code == 201, created.text
    turns = url + "/conversations/" + created.json()["id"] + "/turns"
    data["answer_chat"].intent_route = "greeting"
    for sequence, attributes in enumerate(({"Hệ": "Chính quy"}, {"Đợt": "B"})):
        response = client.post(
            turns,
            headers={"Idempotency-Key": f"scope-{sequence}"},
            json={
                "question": "Chào bạn",
                "expected_turn_no": sequence,
                "metadata_filter": {"attributes": attributes},
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "completed", response.text
    assert response.json()["metadata_filter"]["attributes"] == {
        "Cơ sở": "A",
        "Hệ": "Chính quy",
        "Đợt": "B",
    }
    blocked = client.post(
        turns,
        headers={"Idempotency-Key": "scope-conflict"},
        json={
            "question": "Chào bạn",
            "expected_turn_no": 2,
            "metadata_filter": {"attributes": {"Cơ sở": "B"}},
        },
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["code"] == "conversation_scope_conflict"
    assert client.get(turns.removesuffix("/turns")).json()["last_turn_no"] == 2
