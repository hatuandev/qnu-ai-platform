"""Public chatbot channel: config safety, anonymous limits and honest stats."""

from __future__ import annotations

import json

from qnu.domains.identity.actor import AuthActor
from tests.integration.index_support import FakeEmbedding, execute_index, published_input
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    PLATFORM,
    add_member,
    as_actor,
    create_collection,
    workspace_with_editor,
)
from tests.integration.ocr_support import FakeJobQueue, use_queue

PUB = f"{API}/public/chatbots"
ADMIN = AuthActor(username="admin", actor_id="cb_admin", permissions=["ai.knowledge.view"])


def ensure_chat_default(client):
    """Assistant creation resolves the system chat default; seed one per test."""
    as_actor(PLATFORM)
    created = client.post(
        f"{API}/modelops/providers",
        json={
            "name": "chat-default",
            "provider_type": "openai_compatible",
            "base_url": "https://provider.example.test/v1",
            "model_name": "chat-default",
            "capabilities": ["chat"],
        },
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    key = client.post(
        f"{API}/modelops/providers/{provider['id']}/keys",
        json={"name": "key-1", "secret": "sk-test-secret-12345"},
    )
    assert key.status_code == 201, key.text
    granted = client.put(f"{API}/modelops/defaults", json={"chat_provider_id": provider["id"]})
    assert granted.status_code == 200, granted.text


def workspace_with_admin(client, code="khoa-cntt"):
    workspace = workspace_with_editor(client, code)
    add_member(client, workspace["id"], ADMIN.actor_id, "admin")
    ensure_chat_default(client)
    as_actor(ADMIN)
    return workspace


def publication_url(workspace_id: str, assistant_id: str) -> str:
    return f"{API}/workspaces/{workspace_id}/assistants/{assistant_id}/publication"


def create_assistant(client, workspace_id, collection_id, name="Trợ lý công khai"):
    as_actor(PLATFORM)
    response = client.post(
        f"{API}/workspaces/{workspace_id}/assistants",
        json={"name": name, "collection_id": collection_id},
    )
    assert response.status_code == 201, response.text
    as_actor(EDITOR)
    return response.json()


def payload(**overrides):
    body = {
        "slug": "tuyen-sinh-2026",
        "display_name": "Tuyển sinh 2026",
        "welcome_message": "Chào bạn, tôi có thể giúp gì?",
        "starter_prompts": ["Học phí ngành CNTT?"],
        "max_turns_per_session": 5,
        "daily_token_budget": None,
        "enabled": False,
        "expected_revision": None,
    }
    body.update(overrides)
    return body


def insert_publication(client, workspace_id, assistant_id, **overrides):
    """Stage an enabled release directly; admin enablement itself is tested separately."""
    from qnu.domains.ocr.ids import new_id
    from qnu.domains.publications.models import AssistantPublication
    from qnu.platform.database import AsyncSessionFactory

    fields = {
        "slug": "kenh-thu-nghiem",
        "display_name": "Kênh thử nghiệm",
        "welcome_message": "Chào bạn",
        "starter_prompts": [],
        "max_turns_per_session": 5,
        "daily_token_budget": None,
        "enabled": True,
        "revision": 1,
        "updated_by": "test",
    }
    fields.update(overrides)

    async def run():
        async with AsyncSessionFactory() as db:
            row = AssistantPublication(
                id=new_id("pub"),
                assistant_id=assistant_id,
                workspace_id=workspace_id,
                **fields,
            )
            db.add(row)
            await db.commit()
            return row.id

    return client.portal.call(run)


def seed_session(client, session_id, publication_id, turns):
    from qnu.platform.cache import get_redis, namespaced

    async def run():
        await get_redis().set(
            namespaced(f"pubchat:session:{session_id}"),
            json.dumps({"publication_id": publication_id, "turns": turns}),
            ex=600,
        )

    client.portal.call(run)


def seed_budget(client, publication_id, tokens):
    from qnu.domains.publications.public_service import _day_key
    from qnu.platform.cache import get_redis, namespaced

    async def run():
        await get_redis().set(namespaced(_day_key(publication_id)), tokens)

    client.portal.call(run)


def test_concurrent_public_turns_respect_session_limit(client, monkeypatch):
    import asyncio

    from qnu.domains.publications import public_service
    from qnu.domains.publications.schemas import PublicTurnRequest
    from qnu.domains.rag.answer.schemas import AnswerResponse, AnswerTrace
    from qnu.platform.database import AsyncSessionFactory
    from qnu.platform.errors import AppException

    workspace = workspace_with_admin(client)
    collection = create_collection(client, workspace["id"], "Kho thử đồng thời")
    assistant = create_assistant(client, workspace["id"], collection["id"])
    publication = insert_publication(
        client, workspace["id"], assistant["id"], max_turns_per_session=1
    )
    seed_session(client, "concurrent-turns-fixture", publication, 0)

    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0

        async def ready(*args):
            return "ready"

        async def answer(db, *args, **kwargs):
            nonlocal calls
            calls += 1
            await db.commit()
            started.set()
            await release.wait()
            return AnswerResponse(
                id="answer-test",
                status="answered",
                answer="Kết quả thử.",
                index_run_id="idx-test",
                generation=1,
                trace=AnswerTrace(prompt_version="test"),
            )

        async def send():
            async with AsyncSessionFactory() as db:
                try:
                    result = await public_service.turn(
                        db,
                        None,
                        None,
                        None,
                        None,
                        None,
                        "kenh-thu-nghiem",
                        PublicTurnRequest(
                            session_id="concurrent-turns-fixture", question="Câu hỏi thử?"
                        ),
                        "concurrency-test",
                    )
                    return result.turns_remaining
                except AppException as exc:
                    return exc.code

        monkeypatch.setattr(public_service, "_readiness", ready)
        monkeypatch.setattr(public_service, "answer", answer)
        first = asyncio.create_task(send())
        second = None
        try:
            await asyncio.wait_for(started.wait(), 5)
            second = asyncio.create_task(send())
            await asyncio.wait_for(asyncio.shield(second), 3)
        except TimeoutError:
            pass
        finally:
            release.set()
            results = await asyncio.gather(first, *([second] if second is not None else []))
        assert results == [0, "public_chat_session_limit"]
        assert calls == 1

    client.portal.call(run)


def test_public_budget_counts_each_modelops_stage_and_refunds_denied_turn(client, monkeypatch):
    import hashlib

    from qnu.domains.modelops.usage.service import usage_service
    from qnu.domains.publications import public_service
    from qnu.domains.rag.answer.schemas import AnswerResponse, AnswerTrace

    workspace = workspace_with_admin(client)
    collection = create_collection(client, workspace["id"], "Kho thử ngân sách")
    assistant = create_assistant(client, workspace["id"], collection["id"])
    publication = insert_publication(
        client, workspace["id"], assistant["id"], daily_token_budget=1000
    )
    session = client.post(f"{PUB}/kenh-thu-nghiem/sessions").json()["session_id"]
    calls = []

    async def ready(*args):
        return "ready"

    async def fake_answer(db, blob, embedding, vectors, chat, actor, workspace_id, *args, **kwargs):
        for stage, reserve, measured in [("generation", 600, 400), ("verification", 500, 120)]:
            key = f"public-{stage}-{len(calls)}"
            record = await usage_service.reserve(
                db,
                actor,
                workspace_id,
                "chat",
                key,
                hashlib.sha256(key.encode()).hexdigest(),
                reserve,
            )
            calls.append(stage)
            await usage_service.settle(db, record.id, total_tokens=measured)
        return AnswerResponse(
            id="answer-test",
            status="answered",
            answer="Kết quả thử.",
            index_run_id="idx-test",
            generation=1,
            trace=AnswerTrace(prompt_version="test", total_tokens=400),
        )

    monkeypatch.setattr(public_service, "_readiness", ready)
    monkeypatch.setattr(public_service, "answer", fake_answer)
    url = f"{PUB}/kenh-thu-nghiem/turns"
    body = {"session_id": session, "question": "Câu hỏi thử?"}
    first = client.post(url, json=body)
    assert first.status_code == 200, first.text
    assert first.json()["turns_remaining"] == 4
    second = client.post(url, json=body)
    assert second.status_code == 429, second.text
    assert second.json()["code"] == "public_chat_budget_exhausted"
    assert calls == ["generation", "verification"]
    as_actor(ADMIN)
    stats = client.get(publication_url(workspace["id"], assistant["id"]) + "/stats").json()
    assert stats["budget_used_today"] == stats["totals"]["tokens"] == 520
    assert stats["totals"]["turns"] == 1
    assert stats["totals"]["error_turns"] == 1

    async def cached_session():
        from qnu.platform.cache import get_json

        return await get_json(f"pubchat:session:{session}")

    assert client.portal.call(cached_session) == {"publication_id": publication, "turns": 1}


def test_daily_budget_reservation_is_atomic_across_sessions(client):
    import asyncio

    from qnu.domains.publications.limits import DailyBudget
    from qnu.platform.cache import namespaced
    from qnu.platform.errors import AppException

    async def run():
        key = namespaced("quota-concurrency-fixture")
        first, second = DailyBudget(key, 1000), DailyBudget(key, 1000)

        async def claim(budget, usage_id):
            try:
                await budget.reserve(usage_id, 700)
            except AppException as exc:
                return exc.code
            return usage_id

        results = await asyncio.gather(claim(first, "a"), claim(second, "b"))
        assert results.count("public_chat_budget_exhausted") == 1
        winner, loser = (first, second) if results[0] == "a" else (second, first)
        usage_id = "a" if winner is first else "b"
        await winner.settle(usage_id, None)
        assert await claim(loser, "c") == "public_chat_budget_exhausted"
        await winner.settle(usage_id, 200)
        await winner.settle(usage_id, 200)
        assert winner.observed_tokens == 200
        assert await claim(loser, "c") == "c"

    client.portal.call(run)


def test_save_disabled_publication_and_view(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, workspace["id"], collection["id"])

    url = publication_url(workspace["id"], assistant["id"])
    as_actor(ADMIN)
    saved = client.put(url, json=payload(slug="  Tuyen-Sinh-2026 "))
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["configured"] is True
    assert body["enabled"] is False
    assert body["slug"] == "tuyen-sinh-2026"
    assert body["public_path"] == "/chatbot/tuyen-sinh-2026"
    assert body["revision"] == 1
    assert body["daily_token_budget"] is None
    assert body["readiness"] == "empty"
    assert body["system_enabled"] is True

    viewed = client.get(url)
    assert viewed.status_code == 200, viewed.text
    assert viewed.json()["slug"] == "tuyen-sinh-2026"


def test_invalid_slug_is_rejected(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, workspace["id"], collection["id"])
    as_actor(ADMIN)
    denied = client.put(
        publication_url(workspace["id"], assistant["id"]), json=payload(slug="Tuyển Sinh!")
    )
    assert denied.status_code == 422, denied.text


def test_enable_requires_ready_assistant(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, workspace["id"], collection["id"])

    as_actor(EDITOR)
    forbidden = client.put(
        publication_url(workspace["id"], assistant["id"]), json=payload(enabled=True)
    )
    assert forbidden.status_code == 403, forbidden.text
    assert forbidden.json()["code"] == "workspace_forbidden"

    as_actor(ADMIN)
    denied = client.put(
        publication_url(workspace["id"], assistant["id"]), json=payload(enabled=True)
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["code"] == "publication_not_ready"


def test_slug_taken_between_assistants(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    first = create_assistant(client, workspace["id"], collection["id"], name="Trợ lý một")
    second = create_assistant(client, workspace["id"], collection["id"], name="Trợ lý hai")

    as_actor(ADMIN)
    saved = client.put(publication_url(workspace["id"], first["id"]), json=payload())
    assert saved.status_code == 200, saved.text
    denied = client.put(publication_url(workspace["id"], second["id"]), json=payload())
    assert denied.status_code == 409, denied.text
    assert denied.json()["code"] == "publication_slug_taken"


def test_revision_conflict_contract(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, workspace["id"], collection["id"])
    url = publication_url(workspace["id"], assistant["id"])

    as_actor(ADMIN)
    created = client.put(url, json=payload())
    assert created.status_code == 200, created.text
    assert created.json()["revision"] == 1

    stale = client.put(url, json=payload(expected_revision=None))
    assert stale.status_code == 409, stale.text
    assert stale.json()["code"] == "publication_revision_conflict"

    updated = client.put(url, json=payload(expected_revision=1, display_name="Tuyển sinh QNU"))
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    assert updated.json()["display_name"] == "Tuyển sinh QNU"

    replay = client.put(url, json=payload(expected_revision=1))
    assert replay.status_code == 409, replay.text
    assert replay.json()["code"] == "publication_revision_conflict"


def test_public_info_sessions_and_kill_switch(client, monkeypatch):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, workspace["id"], collection["id"])
    publication_id = insert_publication(client, workspace["id"], assistant["id"], slug="kenh-thu")

    missing = client.get(f"{PUB}/khong-ton-tai")
    assert missing.status_code == 404, missing.text
    assert missing.json()["code"] == "public_chatbot_not_found"

    info = client.get(f"{PUB}/kenh-thu")
    assert info.status_code == 200, info.text
    body = info.json()
    assert body["available"] is False
    assert body["unavailable_reason"]
    assert body["max_turns_per_session"] == 5

    session = client.post(f"{PUB}/kenh-thu/sessions")
    assert session.status_code == 201, session.text
    created = session.json()
    assert created["max_turns"] == 5
    assert created["turns_remaining"] == 5

    as_actor(EDITOR)
    stats = client.get(publication_url(workspace["id"], assistant["id"]) + "/stats")
    assert stats.status_code == 200, stats.text
    assert stats.json()["totals"]["sessions"] == 1
    assert publication_id

    from qnu.platform.config import get_settings

    monkeypatch.setattr(get_settings(), "PUBLIC_CHATBOTS_ENABLED", False)
    blocked = client.get(f"{PUB}/kenh-thu")
    assert blocked.status_code == 404, blocked.text
    assert blocked.json()["code"] == "public_chatbot_not_found"
    blocked_session = client.post(f"{PUB}/kenh-thu/sessions")
    assert blocked_session.status_code == 404, blocked_session.text


def test_turn_guards_and_unlimited_budget(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    open_assistant = create_assistant(client, workspace["id"], collection["id"], name="Trợ lý mở")
    capped_assistant = create_assistant(
        client, workspace["id"], collection["id"], name="Trợ lý có hạn mức"
    )
    open_pub = insert_publication(
        client, workspace["id"], open_assistant["id"], slug="kenh-mo", max_turns_per_session=2
    )
    capped_pub = insert_publication(
        client,
        workspace["id"],
        capped_assistant["id"],
        slug="kenh-co-han",
        daily_token_budget=1000,
    )

    expired = client.post(
        f"{PUB}/kenh-mo/turns", json={"session_id": "x" * 24, "question": "Học phí?"}
    )
    assert expired.status_code == 410, expired.text
    assert expired.json()["code"] == "public_chat_session_expired"

    session = client.post(f"{PUB}/kenh-mo/sessions").json()
    seed_session(client, session["session_id"], open_pub, turns=2)
    limited = client.post(
        f"{PUB}/kenh-mo/turns",
        json={"session_id": session["session_id"], "question": "Học phí?"},
    )
    assert limited.status_code == 429, limited.text
    assert limited.json()["code"] == "public_chat_session_limit"

    capped_session = client.post(f"{PUB}/kenh-co-han/sessions").json()
    seed_budget(client, capped_pub, tokens=5000)
    exhausted = client.post(
        f"{PUB}/kenh-co-han/turns",
        json={"session_id": capped_session["session_id"], "question": "Học phí?"},
    )
    assert exhausted.status_code == 429, exhausted.text
    assert exhausted.json()["code"] == "public_chat_budget_exhausted"

    open_session = client.post(f"{PUB}/kenh-mo/sessions").json()
    seed_budget(client, open_pub, tokens=10_000_000)
    past_the_cap = client.post(
        f"{PUB}/kenh-mo/turns",
        json={"session_id": open_session["session_id"], "question": "Học phí?"},
    )
    assert past_the_cap.status_code == 409, past_the_cap.text
    assert past_the_cap.json()["code"] == "public_chatbot_unavailable"


def test_stats_zero_fill_and_parameters(client):
    workspace = workspace_with_admin(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Bộ sưu tập trống")
    assistant = create_assistant(client, workspace["id"], collection["id"])
    url = publication_url(workspace["id"], assistant["id"])

    unconfigured = client.get(url + "/stats")
    assert unconfigured.status_code == 200, unconfigured.text
    assert unconfigured.json()["configured"] is False
    assert unconfigured.json()["daily"] == []

    as_actor(ADMIN)
    saved = client.put(url, json=payload(daily_token_budget=200000))
    assert saved.status_code == 200, saved.text

    weekly = client.get(url + "/stats")
    assert weekly.status_code == 200, weekly.text
    body = weekly.json()
    assert body["configured"] is True
    assert body["days"] == 7
    assert len(body["daily"]) == 7
    assert body["totals"] == {
        "sessions": 0,
        "turns": 0,
        "insufficient_turns": 0,
        "error_turns": 0,
        "tokens": 0,
    }
    assert body["budget_limit"] == 200000
    assert body["budget_used_today"] == 0
    assert body["top_questions"] == []

    from qnu.domains.publications.public_service import business_day

    assert body["daily"][-1]["day"] == business_day().isoformat()

    monthly = client.get(url + "/stats?days=30")
    assert monthly.status_code == 200, monthly.text
    assert len(monthly.json()["daily"]) == 30

    too_short = client.get(url + "/stats?days=3")
    assert too_short.status_code == 422, too_short.text


def test_ready_assistant_can_enable_and_serve(client, monkeypatch):
    from qnu.domains.assistants.schemas import AssistantConfig
    from qnu.domains.publications import public_service
    from qnu.domains.rag.answer.schemas import AnswerResponse, AnswerTrace

    data = published_input(client)
    add_member(client, data["workspace"]["id"], ADMIN.actor_id, "admin")
    assistant = create_assistant(client, data["workspace"]["id"], data["collection"]["id"])
    with FakeEmbedding() as fake:
        from tests.integration.test_index_api_647 import embedding_provider

        embedding_provider(client, data, fake.base_url)
        use_queue(FakeJobQueue())
        as_actor(EDITOR)
        created = client.post(
            data["base"] + "/indexing-runs",
            json={},
            headers={"Idempotency-Key": "publication-channel"},
        )
        assert created.status_code == 201, created.text
        run = created.json()["run"]
        assert execute_index(client, run["id"]) == "completed"

    as_actor(ADMIN)
    saved = client.put(
        publication_url(data["workspace"]["id"], assistant["id"]),
        json=payload(enabled=True),
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["enabled"] is True
    assert body["readiness"] == "ready"

    info = client.get(f"{PUB}/tuyen-sinh-2026")
    assert info.status_code == 200, info.text
    assert info.json()["available"] is True
    assert info.json()["unavailable_reason"] is None

    session = client.post(f"{PUB}/tuyen-sinh-2026/sessions")
    assert session.status_code == 201, session.text

    calls = 0

    async def fake_answer(*args, **kwargs):
        nonlocal calls
        calls += 1
        return AnswerResponse(
            id="test-answer",
            status="answered",
            answer="Kết quả thử.",
            index_run_id=run["id"],
            generation=1,
            trace=AnswerTrace(prompt_version="test"),
        )

    monkeypatch.setattr(public_service, "answer", fake_answer)

    async def unexpected_snapshot_read(*args, **kwargs):
        raise AssertionError("The directory must not read published bundles")

    with monkeypatch.context() as patch:
        patch.setattr(public_service, "_readiness", unexpected_snapshot_read)
        assert client.get(PUB).json()["chatbots"][0]["available"] is True

    update_url = f"{API}/workspaces/{data['workspace']['id']}/assistants/{assistant['id']}"
    update = {key: assistant[key] for key in AssistantConfig.model_fields}
    update["expected_revision"] = assistant["revision"]
    paused = client.put(update_url, json={**update, "is_active": False})
    assert paused.status_code == 200, paused.text

    body = {"session_id": session.json()["session_id"], "question": "Chỉ tiêu tuyển sinh?"}
    rejected = client.post(f"{PUB}/tuyen-sinh-2026/turns", json=body)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["code"] == "public_chatbot_unavailable"
    assert calls == 0
    assert client.get(f"{PUB}/tuyen-sinh-2026").json()["available"] is False
    assert client.get(PUB).json()["chatbots"][0]["available"] is False
    assert client.post(f"{PUB}/tuyen-sinh-2026/sessions").status_code == 409

    update["expected_revision"] = paused.json()["revision"]
    resumed = client.put(update_url, json={**update, "is_active": True})
    assert resumed.status_code == 200, resumed.text
    assert client.get(f"{PUB}/tuyen-sinh-2026").json()["available"] is True
    assert client.get(PUB).json()["chatbots"][0]["available"] is True
    reply = client.post(f"{PUB}/tuyen-sinh-2026/turns", json=body)
    assert reply.status_code == 200, reply.text
    assert reply.json()["turns_remaining"] == 4
    assert calls == 1

    from tests.integration.test_index_api_647 import withdraw

    withdraw(client, data)
    assert client.get(PUB).json()["chatbots"][0]["available"] is False
