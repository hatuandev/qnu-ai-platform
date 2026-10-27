"""Concurrent uploads and the database guarantees that make them safe.

The service pre-checks are best-effort; the unique constraints are the real guard.
These tests run inside the TestClient portal so both coroutines share the same
event loop (and therefore the same asyncpg pool) as the application.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from qnu.api.wiring import build_container
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.models import KBSource, KBSourceRevision, KBUploadRequest
from qnu.domains.knowledge.sources.service import UploadOutcome, source_service
from qnu.domains.workspaces.models import Workspace
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory
from qnu.platform.errors import Conflict
from tests.integration.knowledge_support import (
    API,
    EDITOR,
    as_actor,
    create_collection,
    pdf_bytes,
    workspace_with_editor,
)


def _two_uploads(
    client: TestClient,
    workspace_id: str,
    collection_id: str,
    *,
    payload: bytes,
    keys: tuple[str | None, str | None],
    actor: AuthActor = EDITOR,
) -> list[object]:
    async def scenario() -> list[object]:
        store = build_container(get_settings()).blob_store

        async def one(key: str | None) -> object:
            async with AsyncSessionFactory() as session:
                workspace = await session.get(Workspace, workspace_id)
                assert workspace is not None
                return await source_service.upload(
                    session,
                    store,
                    workspace,
                    collection_id,
                    file_name="de-an.pdf",
                    title=None,
                    payload=payload,
                    max_bytes=10_000,
                    actor=actor,
                    idempotency_key=key,
                )

        return list(await asyncio.gather(one(keys[0]), one(keys[1]), return_exceptions=True))

    return client.portal.call(scenario)


def _count_sources(client: TestClient, collection_id: str) -> int:
    async def scenario() -> int:
        from sqlalchemy import func, select

        async with AsyncSessionFactory() as session:
            return int(
                (
                    await session.execute(
                        select(func.count(KBSource.id)).where(
                            KBSource.collection_id == collection_id
                        )
                    )
                ).scalar_one()
            )

    return client.portal.call(scenario)


def test_same_idempotency_key_concurrently_creates_one_source(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Đồng thời cùng key")
    payload = pdf_bytes("race-key")

    results = _two_uploads(
        client,
        workspace["id"],
        collection["id"],
        payload=payload,
        keys=("race-key-1", "race-key-1"),
    )
    outcomes = [item for item in results if isinstance(item, UploadOutcome)]
    conflicts = [item for item in results if isinstance(item, Conflict)]
    assert len(outcomes) + len(conflicts) == 2, results
    assert len({outcome.source.id for outcome in outcomes}) <= 1
    assert _count_sources(client, collection["id"]) == 1


def test_same_content_different_keys_concurrently_creates_one_source(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Đồng thời khác key")
    payload = pdf_bytes("race-content")

    results = _two_uploads(
        client,
        workspace["id"],
        collection["id"],
        payload=payload,
        keys=("race-a-1", "race-b-2"),
    )
    outcomes = [item for item in results if isinstance(item, UploadOutcome)]
    conflicts = [item for item in results if isinstance(item, Conflict)]
    assert len(outcomes) == 1, results
    assert len(conflicts) == 1, results
    assert conflicts[0].code == "duplicate_content"
    assert _count_sources(client, collection["id"]) == 1


def test_database_rejects_duplicate_content_without_the_service(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Ràng buộc DB")
    payload = pdf_bytes("constraint")
    uploaded = client.post(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources",
        files={"file": ("de-an.pdf", payload, "application/pdf")},
    ).json()
    sha256 = uploaded["revision"]["sha256"]

    async def scenario() -> str:
        async with AsyncSessionFactory() as session:
            session.add(
                KBSource(
                    id="src_manual_1",
                    workspace_id=workspace["id"],
                    collection_id=collection["id"],
                    title="Chèn tay",
                    status="stored",
                    latest_revision_no=1,
                    created_by=EDITOR.actor_id,
                )
            )
            await session.flush()
            session.add(
                KBSourceRevision(
                    id="rev_manual_1",
                    workspace_id=workspace["id"],
                    collection_id=collection["id"],
                    source_id="src_manual_1",
                    revision_no=1,
                    file_name="khac.pdf",
                    content_type="application/pdf",
                    size_bytes=len(payload),
                    sha256=sha256,
                    storage_key="v1/manual/other-key",
                    created_by=EDITOR.actor_id,
                )
            )
            try:
                await session.flush()
            except IntegrityError as exc:
                await session.rollback()
                return type(exc).__name__
            return "inserted"

    assert client.portal.call(scenario) == "IntegrityError"
    assert _count_sources(client, collection["id"]) == 1


def test_database_rejects_a_reused_idempotency_key(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Ràng buộc key")
    client.post(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources",
        files={"file": ("de-an.pdf", pdf_bytes("ledger"), "application/pdf")},
        headers={"Idempotency-Key": "ledger-key-1"},
    )

    async def scenario() -> str:
        async with AsyncSessionFactory() as session:
            session.add(
                KBUploadRequest(
                    id="upl_manual_1",
                    workspace_id=workspace["id"],
                    collection_id=collection["id"],
                    actor_ref=EDITOR.actor_id,
                    idempotency_key="ledger-key-1",
                    request_hash="0" * 64,
                    source_id="src_manual_2",
                    revision_id="rev_manual_2",
                )
            )
            try:
                await session.flush()
            except IntegrityError as exc:
                await session.rollback()
                return type(exc).__name__
            return "inserted"

    assert client.portal.call(scenario) == "IntegrityError"


def test_unknown_workspace_is_not_reachable_from_the_service(client: TestClient) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    create_collection(client, workspace["id"], "Sai workspace")

    async def scenario() -> str:
        store = build_container(get_settings()).blob_store
        async with AsyncSessionFactory() as session:
            workspace_row = await session.get(Workspace, workspace["id"])
            assert workspace_row is not None
            try:
                await source_service.upload(
                    session,
                    store,
                    workspace_row,
                    "col_khong_ton_tai",
                    file_name="de-an.pdf",
                    title=None,
                    payload=pdf_bytes("ghost"),
                    max_bytes=10_000,
                    actor=EDITOR,
                )
            except Exception as exc:
                return getattr(exc, "code", type(exc).__name__)
            return "created"

    assert client.portal.call(scenario) == "collection_not_found"


@pytest.mark.parametrize("bad_key", ["short", "x" * 129])
def test_idempotency_key_length_is_enforced(client: TestClient, bad_key: str) -> None:
    workspace = workspace_with_editor(client)
    as_actor(EDITOR)
    collection = create_collection(client, workspace["id"], "Key sai")
    response = client.post(
        f"{API}/workspaces/{workspace['id']}/collections/{collection['id']}/sources",
        files={"file": ("de-an.pdf", pdf_bytes("bad-key"), "application/pdf")},
        headers={"Idempotency-Key": bad_key},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_invalid"
