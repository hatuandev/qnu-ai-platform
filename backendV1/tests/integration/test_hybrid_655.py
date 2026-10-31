"""Hybrid retrieval keeps publication filtering and citations before and after rerank HTTP."""

import json

import pytest

from tests.integration.index_support import execute_index
from tests.integration.knowledge_support import API, EDITOR, PLATFORM, as_actor
from tests.integration.ocr_support import FakeNemotron
from tests.integration.test_index_api_647 import indexed as indexed_fixture
from tests.integration.test_index_api_647 import withdraw

indexed = indexed_fixture


class FakeRerank(FakeNemotron):
    def _respond(self, index):
        req = self.requests[index]["body"]
        n = len(req["documents"])
        results = [{"index": i, "relevance_score": float(i + 1) / n} for i in reversed(range(n))][
            : req["top_n"]
        ]
        if self.mode == "duplicate":
            results = [results[0]] * len(results)
        elif self.mode == "foreign":
            results[0]["index"] = n
        elif self.mode == "missing":
            results = []
        elif self.mode == "auth":
            return 401, b"{}"
        return 200, json.dumps({"results": results, "usage": {"total_tokens": 57}}).encode()


def setup_rerank(client, data, endpoint):
    as_actor(PLATFORM)
    result = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "rerank-test",
            "provider_type": "openai_compatible",
            "base_url": endpoint,
            "model_name": "test-rerank",
            "capabilities": ["rerank"],
            "timeout_seconds": 5,
            "token_limits": {"max_input_tokens": 32768},
        },
    )
    assert result.status_code == 201, result.text
    provider = result.json()["id"]
    assert (
        client.post(
            f"{API}/modelops/providers/{provider}/keys",
            json={"name": "test", "secret": "rerank-test-secret"},
        ).status_code
        == 201
    )
    result = client.put(
        f"{API}/workspaces/{data['workspace']['id']}/allowed-providers",
        json={
            "provider_ids": [
                data["ocr_provider"]["id"],
                data["embedding_provider"]["id"],
                provider,
            ],
            "defaults": {
                "ocr": data["ocr_provider"]["id"],
                "embedding": data["embedding_provider"]["id"],
                "rerank": provider,
            },
        },
    )
    assert result.status_code == 200, result.text
    as_actor(EDITOR)
    return provider


def test_hybrid_uses_same_index_and_scoped_lexical_candidates(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    response = client.post(
        indexed["base"] + "/search",
        json={"query": "Chỉ tiêu tuyển sinh", "mode": "hybrid", "candidate_k": 10},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["hits"] and result["trace"]["lexical_count"] > 0
    assert (
        result["trace"]["fusion"] == "rrf" and result["trace"]["lexical"] == "postgres_simple_fts"
    )
    assert all(h["version_id"] == indexed["compiled"]["version"]["id"] for h in result["hits"])
    assert len({h["chunk_id"] for h in result["hits"]}) == len(result["hits"])
    response = client.post(
        indexed["base"] + "/search",
        json={"query": "Chỉ tiêu", "mode": "hybrid", "document_ids": ["foreign"]},
    )
    assert response.status_code == 404


@pytest.mark.parametrize("tokens", [0, 37, None])
def test_rerank_rejection_settles_measured_usage_without_retry(client, indexed, tokens):
    from sqlalchemy import select

    from qnu.domains.modelops.models import ModelUsageRecord, WorkspaceQuota
    from qnu.domains.modelops.usage.service import month_start
    from qnu.platform.database import AsyncSessionFactory

    class RejectedRerank(FakeRerank):
        def _respond(self, index):
            payload = {"error": "rate limit"}
            if tokens is not None:
                payload["usage"] = {"total_tokens": tokens}
            return 429, json.dumps(payload).encode()

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    with RejectedRerank() as fake:
        setup_rerank(client, indexed, fake.base_url)
        response = client.post(
            indexed["base"] + "/search",
            json={"query": "Chỉ tiêu", "mode": "hybrid_rerank", "candidate_k": 10},
        )
        assert response.status_code == 503, response.text
        assert response.json()["code"] == "rerank_unavailable"
        assert len(fake.requests) == 1

    async def ledger():
        async with AsyncSessionFactory() as db:
            record = (
                await db.scalars(
                    select(ModelUsageRecord).where(
                        ModelUsageRecord.workspace_id == indexed["workspace"]["id"],
                        ModelUsageRecord.capability == "rerank",
                    )
                )
            ).one()
            quota = await db.get(WorkspaceQuota, (indexed["workspace"]["id"], month_start()))
            return record.total_tokens, record.status, quota.tokens_reserved, record.reserved_tokens

    used, status, held, reserved = client.portal.call(ledger)
    assert used == tokens
    assert status == ("unknown" if tokens is None else "failed")
    assert held == (reserved if tokens is None else 0)


@pytest.mark.parametrize("mode", ["normal", "duplicate", "foreign", "missing", "auth"])
def test_rerank_protocol_is_strict_and_citations_stay_server_bound(client, indexed, mode):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    with FakeRerank() as fake:
        setup_rerank(client, indexed, fake.base_url)
        fake.mode = mode
        response = client.post(
            indexed["base"] + "/search",
            json={"query": "Chỉ tiêu", "mode": "hybrid_rerank", "candidate_k": 10},
        )
        assert len(fake.requests) == 1
        if mode != "normal":
            assert response.status_code == 502, response.text
            assert response.json()["code"] in {"rerank_response_invalid", "rerank_auth_failed"}
        else:
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["trace"]["rerank_tokens"] == 57
            assert body["trace"]["rerank_presentation"] == "qnu.evidence-reading/v1"
            assert all("\n" not in text for text in fake.requests[0]["body"]["documents"])
            assert all(h["citations"] for h in body["hits"])
            assert fake.requests[0]["path"].endswith("/v1/rerank")


def test_withdrawal_excludes_both_branches_before_rerank(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    with FakeRerank() as fake:
        setup_rerank(client, indexed, fake.base_url)
        withdraw(client, indexed)
        result = client.post(
            indexed["base"] + "/search", json={"query": "Chỉ tiêu", "mode": "hybrid_rerank"}
        )
        assert result.status_code == 200 and result.json()["status"] == "no_eligible_content"
        assert not fake.requests


def test_withdrawal_during_rerank_never_returns_stale_text(client, indexed):
    assert execute_index(client, indexed["index_run"]["id"]) == "completed"

    class WithdrawingRerank(FakeRerank):
        def _respond(self, index):
            withdraw(client, indexed)
            return super()._respond(index)

    with WithdrawingRerank() as fake:
        setup_rerank(client, indexed, fake.base_url)
        response = client.post(
            indexed["base"] + "/search", json={"query": "Chỉ tiêu", "mode": "hybrid_rerank"}
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "answer_evidence_changed"
        assert "hits" not in response.json() and len(fake.requests) == 1


def test_withdrawal_after_quota_commit_blocks_rerank_egress(client, indexed, monkeypatch):
    import asyncio

    from qnu.domains.modelops.usage.service import usage_service

    assert execute_index(client, indexed["index_run"]["id"]) == "completed"
    reserve = usage_service.reserve

    async def revoke_after_reserve(*args, **kwargs):
        row = await reserve(*args, **kwargs)
        if args[3] == "rerank":
            await asyncio.to_thread(withdraw, client, indexed)
        return row

    monkeypatch.setattr(usage_service, "reserve", revoke_after_reserve)
    with FakeRerank() as fake:
        setup_rerank(client, indexed, fake.base_url)
        response = client.post(
            indexed["base"] + "/search", json={"query": "Chỉ tiêu", "mode": "hybrid_rerank"}
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "answer_evidence_changed"
        assert not fake.requests
