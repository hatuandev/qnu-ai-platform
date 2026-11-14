"""Exact answer cache: identical inputs reuse a generation; everything else regenerates."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index.schemas import SearchHit, SearchResponse
from qnu.domains.knowledge.metadata import MetadataFilter
from qnu.domains.rag.answer import cache as answer_cache
from qnu.domains.rag.answer import service
from qnu.domains.rag.answer.cells import catalog
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.platform import cache as platform_cache
from qnu.ports.chat_model import ChatMessage, ChatResult
from tests.unit.test_table_grounding_770 import selected, source

GENERATED = selected("E1:r1:k1")
ABSTAINED = json.dumps({"status": "insufficient_evidence", "statements": [], "lookups": []})


class FakeDB:
    async def commit(self):
        return None


class Runtime:
    provider_id = "prov"
    model_name = "model-a"
    routing_trace = [{"provider_id": "prov"}]

    def __init__(self, configuration_hash="cfg-a"):
        self.configuration_hash = configuration_hash

    def inference_configuration_hash(self, task):
        return "inference:" + self.configuration_hash

    def reasoning_trace(self, task):
        return {"mode": "provider_default", "task": task}


class Usage:
    def __init__(self):
        self.settled = []

    async def reserve(self, *args, **kwargs):
        return SimpleNamespace(id="usage-1")

    async def settle(self, *args, **kwargs):
        self.settled.append((args, kwargs))


class Harness:
    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch
        self.store = {}
        self.ttls = []
        self.read_error = None
        self.write_error = None
        self.table = source([["Item", "Rate"], ["Valve", "8"]])
        self.content = GENERATED
        self.runtime = Runtime()
        self.proof = "proof-1"
        self.generation = 1
        self.index_run_id = "idx-1"
        self.manifest = "manifest-1"
        self.ttl = 300
        self.db = FakeDB()
        self.usage = Usage()
        self.chat = AsyncMock()
        self.chat.complete.return_value = ChatResult(
            content=self.content,
            provider="prov",
            model="model-a",
            prompt_tokens=10,
            completion_tokens=5,
            finish_reason="stop",
            total_tokens=15,
        )
        self._install()

    def _install(self):
        set_ = self.monkeypatch.setattr
        set_(service, "search", self._search)
        set_(service, "expand_context", self._expand)
        set_(
            service,
            "select_hits",
            lambda hits, context, question, resolved_question=None: (hits, {}),
        )
        set_(service, "sources_for", lambda _: [self.table])
        set_(service, "attach_source_text", AsyncMock())
        set_(service, "_pack_messages", self._pack)
        set_(service, "validate_results", self._validate)
        set_(service, "prepare_chat_request", self._prepare)
        set_(service, "resolve_chat_runtime", self._resolve)
        set_(
            service,
            "verify",
            AsyncMock(
                return_value={
                    "mode": "observe",
                    "status": "supported",
                    "version": "test",
                    "ms": 0.1,
                }
            ),
        )
        set_(service, "usage_service", self.usage)
        set_(answer_cache, "ttl_seconds", lambda: self.ttl)
        set_(platform_cache, "get_json", self._get_json)
        set_(platform_cache, "set_json", self._set_json)

    async def _search(self, *args, **kwargs):
        hit = SearchHit.model_validate(self.table.model_dump(exclude={"evidence_id"}))
        return SearchResponse(
            index_run_id=self.index_run_id,
            generation=self.generation,
            status="results",
            eligible_documents=1,
            hits=[hit],
            trace={"manifest_sha256": self.manifest},
        )

    async def _expand(self, *args, **kwargs):
        return await self._search(), {}

    def _pack(self, req, sources, context, *, resolved_question, persona, metadata_filter):
        user = {
            "question": req.question,
            "resolved": resolved_question,
            "style": persona,
            "scope": metadata_filter,
            "evidence": [s.evidence_id for s in sources],
        }
        return (
            [ChatMessage("system", "system prompt"), ChatMessage("user", json.dumps(user))],
            catalog(list(sources)),
            {},
            128,
            [],
        )

    async def _validate(self, *args, **kwargs):
        return self.proof

    async def _prepare(self, *args, **kwargs):
        request = SimpleNamespace(execution=None, max_output_tokens=64)
        budget = SimpleNamespace(total_reserved_tokens=64)
        return self.runtime, request, budget

    async def _resolve(self, *args, **kwargs):
        return self.runtime

    async def _get_json(self, key):
        if self.read_error is not None:
            raise self.read_error
        return self.store.get(key)

    async def _set_json(self, key, value, ttl_seconds):
        if self.write_error is not None:
            raise self.write_error
        self.ttls.append(ttl_seconds)
        self.store[key] = value

    async def run(
        self, *, question="Học phí bao nhiêu?", workspace="ws-1", collection="col-1", **overrides
    ):
        req = AnswerRequest(question=question, **overrides)
        return await service.answer(
            self.db, None, None, None, self.chat, None, workspace, collection, req
        )

    def entry(self):
        (key,) = self.store
        return key, self.store[key]


def test_cache_key_is_stable_and_sensitive_to_every_material():
    base = {"question": "q", "scope": {"data_year": 2024}, "hits": ["a"]}
    same = {"hits": ["a"], "scope": {"data_year": 2024}, "question": "q"}
    assert answer_cache.key(base) == answer_cache.key(same)
    assert answer_cache.key(base) != answer_cache.key({**base, "question": "other"})
    assert answer_cache.key(base) != answer_cache.key({**base, "scope": {"data_year": 2025}})


@pytest.mark.asyncio
async def test_identical_request_reuses_the_cached_generation(monkeypatch):
    h = Harness(monkeypatch)
    first = await h.run()
    assert first.status == "answered"
    assert h.chat.complete.await_count == 1
    assert h.ttls == [300]
    key, entry = h.entry()
    assert entry["version"] == answer_cache.VERSION
    assert entry["content"] == GENERATED

    second = await h.run()
    assert h.chat.complete.await_count == 1
    assert second.status == "answered"
    assert second.answer == first.answer
    assert second.id != first.id
    assert second.trace.cache["status"] == "hit"
    assert second.trace.cache["key"] == key
    assert "origin_usage_id" not in second.trace.cache
    assert second.trace.usage_id is None
    assert second.trace.prompt_tokens is None
    assert second.trace.evidence_sha256 == "proof-1"
    assert second.trace.contract == first.trace.contract


@pytest.mark.parametrize(
    "change",
    [
        {"workspace": "ws-2"},
        {"collection": "col-2"},
        {"question": "Chỉ tiêu năm nay?"},
        {"metadata_filter": MetadataFilter(data_year=2024)},
        {"document_ids": ["doc-2"]},
    ],
)
@pytest.mark.asyncio
async def test_changed_scope_or_question_never_reuses_an_answer(monkeypatch, change):
    h = Harness(monkeypatch)
    await h.run()
    await h.run(**change)
    assert h.chat.complete.await_count == 2
    assert h.ttls == [300, 300]


@pytest.mark.asyncio
async def test_changed_index_generation_or_evidence_never_reuses_an_answer(monkeypatch):
    h = Harness(monkeypatch)
    await h.run()
    h.generation = 2
    await h.run()
    h.generation = 2
    h.proof = "proof-2"
    await h.run()
    assert h.chat.complete.await_count == 3


@pytest.mark.asyncio
async def test_changed_chat_runtime_never_reuses_an_answer(monkeypatch):
    h = Harness(monkeypatch)
    await h.run()
    h.runtime = Runtime("cfg-b")
    await h.run()
    assert h.chat.complete.await_count == 2


@pytest.mark.asyncio
async def test_abstained_generation_is_not_cached(monkeypatch):
    h = Harness(monkeypatch)
    h.content = ABSTAINED
    h.chat.complete.return_value = ChatResult(
        content=ABSTAINED,
        provider="prov",
        model="model-a",
        prompt_tokens=10,
        completion_tokens=1,
        finish_reason="stop",
        total_tokens=11,
    )
    first = await h.run()
    await h.run()
    assert first.status == "insufficient_evidence"
    assert first.reason == "model_abstained"
    assert h.store == {}
    # Each request has an initial draft and one re-evaluation of the same evidence.
    assert h.chat.complete.await_count == 4


@pytest.mark.asyncio
async def test_unsupported_observed_answer_is_not_cached(monkeypatch):
    h = Harness(monkeypatch)
    service.verify = AsyncMock(
        return_value={
            "mode": "observe",
            "status": "unsupported",
            "version": "test",
            "ms": 0.1,
        }
    )
    first = await h.run(verification_mode="observe")
    await h.run(verification_mode="observe")
    assert first.status == "answered"
    assert first.trace.verification["status"] == "unsupported"
    assert h.store == {}
    assert h.chat.complete.await_count == 2


@pytest.mark.asyncio
async def test_cache_disabled_or_unavailable_never_blocks_an_answer(monkeypatch):
    h = Harness(monkeypatch)
    h.ttl = 0
    first = await h.run()
    second = await h.run()
    assert first.status == second.status == "answered"
    assert h.store == {}
    assert h.chat.complete.await_count == 2

    h = Harness(monkeypatch)
    h.ttl = 300
    h.read_error = RuntimeError("redis down")
    h.write_error = RuntimeError("redis down")
    answer = await h.run()
    assert answer.status == "answered"


@pytest.mark.asyncio
async def test_corrupt_cached_generation_falls_back_to_the_model(monkeypatch):
    h = Harness(monkeypatch)
    await h.run()
    key, entry = h.entry()
    h.store[key] = {**entry, "content": "{not json"}
    discard = AsyncMock()
    monkeypatch.setattr(answer_cache, "discard", discard)
    answer = await h.run()
    assert answer.status == "answered"
    assert h.chat.complete.await_count == 2
    discard.assert_awaited_once_with(key)
