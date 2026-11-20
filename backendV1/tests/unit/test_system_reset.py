"""Unit tests for the system reset and seed operations endpoint and service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from qnu.domains.identity.actor import AuthActor
from qnu.domains.operations.reset import (
    TABLES_TO_TRUNCATE,
    delete_qdrant_collections,
    perform_system_reset_and_seed,
    purge_storage_objects,
)
from qnu.domains.operations.schemas import SystemResetRequest, SystemResetResponse
from qnu.platform.config import Settings
from qnu.platform.errors import Conflict, Forbidden


def test_system_reset_request_validation():
    # Valid
    req = SystemResetRequest(confirm_phrase="RESET_AND_SEED")
    assert req.confirm_phrase == "RESET_AND_SEED"
    assert req.seed_workspace is True
    assert req.seed_modelops is True
    assert req.seed_assistant is True

    # Missing confirm_phrase
    with pytest.raises(ValidationError):
        SystemResetRequest()


def test_tables_to_truncate_contains_core_domains():
    assert "workspaces" in TABLES_TO_TRUNCATE
    assert "workspace_members" in TABLES_TO_TRUNCATE
    assert "chat_assistants" in TABLES_TO_TRUNCATE
    assert "chat_conversations" in TABLES_TO_TRUNCATE
    assert "chat_turns" in TABLES_TO_TRUNCATE
    assert "kb_collections" in TABLES_TO_TRUNCATE
    assert "kb_sources" in TABLES_TO_TRUNCATE
    assert "kb_index_runs" in TABLES_TO_TRUNCATE
    assert "kb_index_chunks" in TABLES_TO_TRUNCATE
    assert "ocr_processing_runs" in TABLES_TO_TRUNCATE
    # Critical migration table must NEVER be truncated
    assert "alembic_version_backendv1" not in TABLES_TO_TRUNCATE
    assert "ocr_spelling_defaults" not in TABLES_TO_TRUNCATE


@pytest.mark.asyncio
async def test_system_reset_refuses_in_production_without_flag():
    actor = AuthActor(
        actor_id="usr_admin",
        username="admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
    )
    req = SystemResetRequest(confirm_phrase="RESET_AND_SEED")
    db = AsyncMock()

    custom_settings = Settings(
        ENVIRONMENT="production",
        ALLOW_SYSTEM_RESET=False,
    )

    with patch("qnu.domains.operations.reset.get_settings", return_value=custom_settings):
        with pytest.raises(Forbidden) as exc:
            await perform_system_reset_and_seed(db, actor, None, None, req)
        assert exc.value.code == "reset_forbidden_in_production"


@pytest.mark.asyncio
async def test_system_reset_refuses_invalid_confirm_phrase():
    actor = AuthActor(
        actor_id="usr_admin",
        username="admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
    )
    req = SystemResetRequest(confirm_phrase="WRONG_PHRASE")
    db = AsyncMock()

    custom_settings = Settings(
        ENVIRONMENT="development",
        ALLOW_SYSTEM_RESET=True,
    )

    with patch("qnu.domains.operations.reset.get_settings", return_value=custom_settings):
        with pytest.raises(Conflict) as exc:
            await perform_system_reset_and_seed(db, actor, None, None, req)
        assert exc.value.code == "invalid_confirm_phrase"


@pytest.mark.asyncio
async def test_delete_qdrant_collections_filters_prefix():
    mock_vectors = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "collections": [
                {"name": "qnu_v1_idx_abcd1234abcd1234abcd1234abcd1234"},
                {"name": "unrelated_collection_test"},
                {"name": "qnu_v1_idx_5678efgh5678efgh5678efgh5678efgh"},
            ]
        }
    }
    mock_vectors._request = AsyncMock(return_value=mock_response)
    mock_vectors.delete_collection = AsyncMock()

    deleted = await delete_qdrant_collections(mock_vectors)

    assert deleted == [
        "qnu_v1_idx_abcd1234abcd1234abcd1234abcd1234",
        "qnu_v1_idx_5678efgh5678efgh5678efgh5678efgh",
    ]
    assert mock_vectors.delete_collection.call_count == 2


@pytest.mark.asyncio
async def test_purge_storage_objects():
    mock_blob = MagicMock()
    mock_obj1 = MagicMock(key="uploads/doc1.pdf")
    mock_obj2 = MagicMock(key="parsed/doc1.json")
    mock_blob.list_objects = AsyncMock(return_value=[mock_obj1, mock_obj2])
    mock_blob.purge = AsyncMock()

    purged = await purge_storage_objects(mock_blob)
    assert purged == 2
    assert mock_blob.purge.call_count == 2


@pytest.mark.asyncio
async def test_perform_system_reset_and_seed_success():
    actor = AuthActor(
        actor_id="usr_admin",
        username="admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
    )
    req = SystemResetRequest(confirm_phrase="RESET_AND_SEED", seed_workspace=True, seed_modelops=True, seed_assistant=True)
    db = AsyncMock()
    mock_blob = MagicMock()
    mock_blob.list_objects = AsyncMock(return_value=[])
    mock_vectors = MagicMock()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {"result": {"collections": []}}
    mock_vectors._request = AsyncMock(return_value=mock_response)

    custom_settings = Settings(
        ENVIRONMENT="development",
        ALLOW_SYSTEM_RESET=True,
    )

    with (
        patch("qnu.domains.operations.reset.get_settings", return_value=custom_settings),
        patch("qnu.domains.operations.reset.truncate_database_tables", new_callable=AsyncMock) as mock_trunc,
        patch("qnu.domains.operations.reset.clear_redis_cache_and_queues", new_callable=AsyncMock) as mock_redis,
        patch("qnu.domains.operations.reset.seed_shl_workspace", new_callable=AsyncMock) as mock_ws,
        patch("qnu.domains.operations.reset.seed_modelops_defaults", new_callable=AsyncMock) as mock_modelops,
        patch("qnu.domains.operations.reset.seed_pilot_assistant_and_collection", new_callable=AsyncMock) as mock_asst,
    ):
        mock_trunc.return_value = ["workspaces", "chat_assistants"]
        mock_redis.return_value = 5
        mock_ws_obj = MagicMock(id="ws_shl_123", code="shl", name="Trung tâm Số & Học liệu")
        mock_ws.return_value = mock_ws_obj
        mock_modelops.return_value = {"chat_provider_id": "prov_chat_123"}
        mock_asst.return_value = ("col_123", "asst_123")

        res: SystemResetResponse = await perform_system_reset_and_seed(db, actor, mock_blob, mock_vectors, req)

        assert res.success is True
        assert res.workspace_id == "ws_shl_123"
        assert res.assistant_id == "asst_123"
        assert res.stats["tables_truncated"] == 2
        assert res.stats["redis_keys_cleared"] == 5
        assert res.stats["publication_slug"] == "tuyen-sinh-qnu-2026"
        assert db.commit.called


def test_system_reset_endpoint_requires_auth():
    from fastapi.testclient import TestClient

    from qnu.main import app

    with TestClient(app) as client:
        res = client.post(
            "/platform/v1alpha1/operations/system-reset-and-seed",
            json={"confirm_phrase": "RESET_AND_SEED"},
        )
        # Without auth header, it should be 401
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_key_service_add_key_handles_provider_without_parent_id():
    from unittest.mock import MagicMock, patch

    from qnu.domains.modelops.keys.service import key_service
    from qnu.domains.modelops.schemas import KeyCreateRequest

    actor = AuthActor(
        actor_id="usr_admin",
        username="admin",
        roles=["AI.Admin"],
        permissions=["ai.access.admin"],
    )
    req = KeyCreateRequest(name="Test Key", secret="test_secret_123")

    # Object without parent_id attribute
    provider_mock = MagicMock(spec=["id"])
    provider_mock.id = "conn_12345"

    db = AsyncMock()
    owner_mock = MagicMock(id="conn_12345")

    with patch("qnu.domains.modelops.keys.service.credential_owner", new_callable=AsyncMock) as mock_owner:
        mock_owner.return_value = owner_mock
        key = await key_service.add_key(db, provider_mock, req, actor)
        assert key.provider_id == "conn_12345"
        assert key.model_ids is None


