"""Unit tests for Wave 1 fixes: semantic cache isolation/LRU/TTL, collection-less public chat, and system backup verify."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qnu.domains.operations.system_backup import inspect_and_restore_system_backup
from qnu.domains.publications.public_service import turn as public_turn
from qnu.domains.publications.schemas import PublicTurnRequest, PublicTurnResponse
from qnu.domains.rag.answer import semantic_cache
from qnu.platform.errors import Conflict


def test_semantic_cache_key_isolates_all_scope_dimensions():
    base = semantic_cache.semantic_cache_key(
        "ws_1",
        "col_1",
        "idx_1",
        "diem chuan cntt 2025",
        collection_ids=["col_1"],
        document_ids=["doc_1"],
        metadata_filter={"data_year": 2025},
        scope_resolution="catalog",
        persona="Tro ly tuyen sinh",
        provider_id="prov_1",
        model_name="qwen-27b",
        prompt_version="qnu.rag.answer/v42",
    )
    assert base != semantic_cache.semantic_cache_key(
        "ws_1", "col_1", "idx_1", "diem chuan cntt 2025",
        collection_ids=["col_1", "col_2"],
        document_ids=["doc_1"],
        metadata_filter={"data_year": 2025},
        scope_resolution="catalog",
        persona="Tro ly tuyen sinh",
        provider_id="prov_1",
        model_name="qwen-27b",
        prompt_version="qnu.rag.answer/v42",
    )
    assert base != semantic_cache.semantic_cache_key(
        "ws_1", "col_1", "idx_1", "diem chuan cntt 2025",
        collection_ids=["col_1"],
        document_ids=["doc_2"],
        metadata_filter={"data_year": 2025},
        scope_resolution="catalog",
        persona="Tro ly tuyen sinh",
        provider_id="prov_1",
        model_name="qwen-27b",
        prompt_version="qnu.rag.answer/v42",
    )
    assert base != semantic_cache.semantic_cache_key(
        "ws_1", "col_1", "idx_1", "diem chuan cntt 2025",
        collection_ids=["col_1"],
        document_ids=["doc_1"],
        metadata_filter={"data_year": 2024},
        scope_resolution="catalog",
        persona="Tro ly tuyen sinh",
        provider_id="prov_1",
        model_name="qwen-27b",
        prompt_version="qnu.rag.answer/v42",
    )
    assert base != semantic_cache.semantic_cache_key(
        "ws_1", "col_1", "idx_1", "diem chuan cntt 2025",
        collection_ids=["col_1"],
        document_ids=["doc_1"],
        metadata_filter={"data_year": 2025},
        scope_resolution="catalog",
        persona="Tro ly khac",
        provider_id="prov_1",
        model_name="qwen-27b",
        prompt_version="qnu.rag.answer/v42",
    )
    assert base != semantic_cache.semantic_cache_key(
        "ws_1", "col_1", "idx_1", "diem chuan cntt 2025",
        collection_ids=["col_1"],
        document_ids=["doc_1"],
        metadata_filter={"data_year": 2025},
        scope_resolution="catalog",
        persona="Tro ly tuyen sinh",
        provider_id="prov_1",
        model_name="qwen-27b",
        prompt_version="qnu.rag.answer/v43",
    )


@pytest.mark.asyncio
async def test_local_semantic_cache_enforces_lru_bound_ttl_and_discards_corrupt():
    semantic_cache._LOCAL_SEMANTIC_CACHE.clear()
    try:
        with patch.object(semantic_cache, "LOCAL_CACHE_MAX_ENTRIES", 2):
            for idx in range(3):
                entry = semantic_cache.SemanticCacheEntry(
                    workspace_id="ws_1",
                    collection_id="col_1",
                    index_run_id="idx_1",
                    normalized_query=f"q{idx}",
                    raw_answer=f"ans{idx}",
                )
                with patch("qnu.domains.rag.answer.semantic_cache.cache.set_json", AsyncMock()):
                    await semantic_cache.store_semantic_cache(f"k{idx}", entry, ttl_seconds=60)
            assert list(semantic_cache._LOCAL_SEMANTIC_CACHE.keys()) == ["k1", "k2"]

        # Expired entry is evicted on read
        semantic_cache._LOCAL_SEMANTIC_CACHE["expired"] = (
            time.monotonic() - 1.0,
            {"workspace_id": "ws_1"},
        )
        with patch("qnu.domains.rag.answer.semantic_cache.cache.get_json", AsyncMock(return_value=None)):
            assert await semantic_cache.get_semantic_cache("expired") is None
        assert "expired" not in semantic_cache._LOCAL_SEMANTIC_CACHE

        # Corrupt entry triggers discard
        semantic_cache._LOCAL_SEMANTIC_CACHE["corrupt"] = (
            time.monotonic() + 60.0,
            {"broken": True},
        )
        with patch("qnu.domains.rag.answer.semantic_cache.discard_semantic_cache", AsyncMock()) as mock_discard:
            assert await semantic_cache.get_semantic_cache("corrupt") is None
            mock_discard.assert_awaited_once_with("corrupt")
    finally:
        semantic_cache._LOCAL_SEMANTIC_CACHE.clear()


@pytest.mark.asyncio
async def test_public_turn_without_collections_returns_valid_response_and_accounts_usage():
    mock_pub = SimpleNamespace(
        id="pub_1",
        workspace_id="ws_1",
        assistant_id="ast_1",
        max_turns_per_session=10,
        daily_token_budget=5000,
    )
    mock_assistant = SimpleNamespace(
        id="ast_1",
        is_active=True,
        collection_id=None,
        collection_ids=[],
        persona="Trợ lý QNU",
        chat_provider_id="prov_1",
        max_output_tokens=256,
    )
    mock_runtime = SimpleNamespace(
        provider_id="prov_1",
        inference_configuration_hash=lambda task: "cfg_hash",
    )
    mock_budget = SimpleNamespace(total_reserved_tokens=300)
    mock_usage = SimpleNamespace(id="usg_1")
    mock_chat = MagicMock()
    mock_chat.complete = AsyncMock(
        return_value=SimpleNamespace(content="Xin chào, mình có thể giúp gì cho bạn?", total_tokens=42)
    )
    db = AsyncMock()
    req = PublicTurnRequest(session_id="sess_" + "a" * 20, question="Xin chào")

    with (
        patch("qnu.domains.publications.public_service._publication", AsyncMock(return_value=(mock_pub, True))),
        patch(
            "qnu.domains.publications.public_service.get_json",
            AsyncMock(return_value={"publication_id": "pub_1", "turns": 0, "created_at": time.time() - 2.0}),
        ),
        patch("qnu.domains.publications.public_service._rate_limit", AsyncMock()),
        patch("qnu.domains.publications.public_service.DailyBudget.check", AsyncMock()),
        patch("qnu.domains.publications.public_service._readiness", AsyncMock(return_value="ready")),
        patch("qnu.domains.publications.public_service._reserve_turn", AsyncMock(return_value=9)),
        patch("qnu.domains.publications.public_service.get_assistant", AsyncMock(return_value=mock_assistant)),
        patch(
            "qnu.domains.publications.public_service.prepare_chat_request",
            AsyncMock(return_value=(mock_runtime, SimpleNamespace(), mock_budget)),
        ),
        patch("qnu.domains.publications.public_service.bind_usage", side_effect=lambda r, u: r),
        patch("qnu.domains.publications.public_service.usage_service.reserve", AsyncMock(return_value=mock_usage)) as mock_reserve,
        patch("qnu.domains.publications.public_service.usage_service.settle", AsyncMock()) as mock_settle,
        patch("qnu.domains.publications.public_service._bump_stats", AsyncMock()) as mock_bump,
    ):
        resp = await public_turn(
            db=db,
            blob=MagicMock(),
            embedding=MagicMock(),
            vectors=MagicMock(),
            chat=mock_chat,
            reranker=None,
            slug="qnu-helper",
            req=req,
            requester="ip_hash",
        )

    assert isinstance(resp, PublicTurnResponse)
    assert resp.status == "answered"
    assert resp.turns_remaining == 9
    assert "Xin chào" in (resp.answer or "")
    mock_reserve.assert_awaited_once()
    mock_settle.assert_awaited_once_with(db, "usg_1", total_tokens=42)
    mock_bump.assert_awaited_once()


@pytest.mark.asyncio
async def test_system_backup_inspect_verifies_bundle_and_rejects_tampered_sha():
    # Build an in-memory system backup bundle (.tar.gz)
    pg_buf = io.BytesIO()
    with tarfile.open(fileobj=pg_buf, mode="w:gz") as pg_tar:
        meta = json.dumps({"table_count": 1, "total_rows": 2, "table_stats": {"t1": 2}}).encode("utf-8")
        mi = tarfile.TarInfo("schema_metadata.json")
        mi.size = len(meta)
        pg_tar.addfile(mi, io.BytesIO(meta))
        csv_b = b"id\n1\n2\n"
        ci = tarfile.TarInfo("tables/t1.csv")
        ci.size = len(csv_b)
        pg_tar.addfile(ci, io.BytesIO(csv_b))
    pg_bytes = pg_buf.getvalue()

    manifest = {
        "schema_version": "qnu.system-backup/v1",
        "backup_id": "backup_test_01",
        "created_at": "2026-11-23T00:00:00+00:00",
        "target": "postgres",
        "alembic_head": "0035",
        "items": [
            {
                "kind": "postgres",
                "path": "postgres/database_dump.tar.gz",
                "tool": "asyncpg_native",
                "format": "tar_gz",
                "size_bytes": len(pg_bytes),
                "sha256": hashlib.sha256(pg_bytes).hexdigest(),
                "table_count": 1,
                "total_rows": 2,
            }
        ],
    }

    bundle_buf = io.BytesIO()
    with tarfile.open(fileobj=bundle_buf, mode="w:gz") as bundle_tar:
        m_bytes = json.dumps(manifest).encode("utf-8")
        mi = tarfile.TarInfo("manifest.json")
        mi.size = len(m_bytes)
        bundle_tar.addfile(mi, io.BytesIO(m_bytes))
        pi = tarfile.TarInfo("postgres/database_dump.tar.gz")
        pi.size = len(pg_bytes)
        bundle_tar.addfile(pi, io.BytesIO(pg_bytes))

    report = await inspect_and_restore_system_backup(
        bundle_buf.getvalue(), "qnu-system-backup.tar.gz", confirm=False
    )
    assert report["status"] == "verified"
    assert report["format"] == "system_bundle_tar_gz"
    assert report["postgres_tables"] == 1
    assert report["postgres_rows"] == 2

    # Tampered manifest sha256 must be rejected with Conflict
    manifest["items"][0]["sha256"] = "0" * 64
    bad_buf = io.BytesIO()
    with tarfile.open(fileobj=bad_buf, mode="w:gz") as bundle_tar:
        m_bytes = json.dumps(manifest).encode("utf-8")
        mi = tarfile.TarInfo("manifest.json")
        mi.size = len(m_bytes)
        bundle_tar.addfile(mi, io.BytesIO(m_bytes))
        pi = tarfile.TarInfo("postgres/database_dump.tar.gz")
        pi.size = len(pg_bytes)
        bundle_tar.addfile(pi, io.BytesIO(pg_bytes))

    with pytest.raises(Conflict) as exc_info:
        await inspect_and_restore_system_backup(bad_buf.getvalue(), "bad.tar.gz", confirm=False)
    assert exc_info.value.code == "backup_integrity_failed"
