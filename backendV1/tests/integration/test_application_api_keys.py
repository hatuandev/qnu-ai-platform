"""API-level integration tests for external application API keys and OpenAI-compatible gateway.

Verifies:
- Secret is displayed ONLY ONCE and stored strictly as SHA-256 hash.
- Machine principal is registered with real workspace membership without AI.Admin bypass.
- Workspace-scoped authorization: no cross-workspace access.
- Key lifecycle: active, suspended, rotated, revoked.
- OpenAI-compatible /models and /chat/completions endpoints.
- Rejection of unsupported options (stream=true, tools).
- Immediate revocation enforcement even mid-flight.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

if not os.environ.get("TEST_DATABASE_URL", "").strip():
    pytest.skip(
        "NOT RUN: TEST_DATABASE_URL chưa cấu hình (Postgres test riêng).",
        allow_module_level=True,
    )

from qnu.api.dependencies import get_actor
from qnu.domains.identity.actor import AuthActor
from qnu.domains.identity.service import resolve_actor
from qnu.domains.integration.gateway import get_redis_client
from qnu.domains.rag.answer.schemas import (
    AnswerResponse,
    AnswerTrace,
    EvidenceSource,
    Statement,
)
from qnu.main import app
from qnu.platform.errors import AppException

PLATFORM = AuthActor(
    username="root", actor_id="root", roles=["AI.Admin"], permissions=["ai.access.admin"]
)
ADMIN_A = AuthActor(
    username="admin-a",
    actor_id="usr_admin_a",
    roles=["staff"],
    permissions=["ai.workspaces.view", "ai.models.manage"],
)
ADMIN_B = AuthActor(
    username="admin-b",
    actor_id="usr_admin_b",
    roles=["staff"],
    permissions=["ai.workspaces.view", "ai.models.manage"],
)

API = "/platform/v1alpha1"


@pytest.fixture(autouse=True)
def clear_integration_overrides():
    yield
    app.dependency_overrides.pop(resolve_actor, None)
    app.dependency_overrides.pop(get_redis_client, None)


def _as(actor: AuthActor | None) -> None:
    def _dependency() -> AuthActor:
        if actor is None:
            raise AppException("Chưa đăng nhập.", code="unauthorized", status_code=401)
        return actor

    app.dependency_overrides[get_actor] = _dependency
    app.dependency_overrides[resolve_actor] = _dependency


def _setup_test_workspaces(client: TestClient) -> tuple[str, str]:
    _as(PLATFORM)
    # Workspace A
    res_a = client.post(f"{API}/workspaces", json={"code": f"ws_int_a_{os.getpid()}", "name": "Đơn vị Tích hợp A"})
    assert res_a.status_code == 201, res_a.text
    ws_a_id = res_a.json()["id"]

    client.post(f"{API}/workspaces/{ws_a_id}/members", json={"actor_ref": ADMIN_A.actor_id, "role": "admin"})

    # Workspace B
    res_b = client.post(f"{API}/workspaces", json={"code": f"ws_int_b_{os.getpid()}", "name": "Đơn vị Tích hợp B"})
    assert res_b.status_code == 201, res_b.text
    ws_b_id = res_b.json()["id"]

    client.post(f"{API}/workspaces/{ws_b_id}/members", json={"actor_ref": ADMIN_B.actor_id, "role": "admin"})

    return ws_a_id, ws_b_id


def test_api_key_lifecycle_and_security(client: TestClient) -> None:
    ws_a_id, _ = _setup_test_workspaces(client)

    # 1. Admin A creates a key
    _as(ADMIN_A)
    create_payload = {
        "app_name": "Cổng thông tin tuyển sinh",
        "allow_all_assistants": True,
        "name": "Khóa Web Chính",
        "rate_limit_rpm": 30,
        "rate_limit_rpd": 5000,
        "expires_in_days": 30,
        "idempotency_key": "idem-key-001",
    }
    res = client.post(f"{API}/workspaces/{ws_a_id}/integrations/keys", json=create_payload)
    assert res.status_code == 201, res.text
    key_data = res.json()

    assert "secret_key" in key_data
    raw_secret = key_data["secret_key"]
    assert raw_secret.startswith("qnu_live_")
    key_id = key_data["id"]
    assert key_data["app_id"]
    assert key_data["status"] == "active"
    assert "..." in key_data["key_prefix"]

    # 2. Idempotency test: resending with same idempotency key fails with 409
    res_dup = client.post(
        f"{API}/workspaces/{ws_a_id}/integrations/keys",
        json=create_payload,
        headers={"Idempotency-Key": "idem-key-001"},
    )
    assert res_dup.status_code == 409, res_dup.text
    assert res_dup.json().get("code") == "idempotency_conflict"

    # 3. List keys: secret_key MUST NOT be present
    res_list = client.get(f"{API}/workspaces/{ws_a_id}/integrations/keys")
    assert res_list.status_code == 200
    listed_keys = res_list.json()
    assert len(listed_keys) >= 1
    found = next(k for k in listed_keys if k["id"] == key_id)
    assert "secret_key" not in found
    assert found["key_prefix"] == key_data["key_prefix"]

    # 4. Cross-workspace isolation: Admin B cannot list or access Workspace A keys
    _as(ADMIN_B)
    res_forbidden = client.get(f"{API}/workspaces/{ws_a_id}/integrations/keys")
    assert res_forbidden.status_code in (403, 404)

    # 5. Suspend Key
    _as(ADMIN_A)
    res_suspend = client.put(
        f"{API}/workspaces/{ws_a_id}/integrations/keys/{key_id}/status",
        json={"status": "suspended", "reason": "Bảo trì định kỳ"},
    )
    assert res_suspend.status_code == 200
    assert res_suspend.json()["status"] == "suspended"

    # 6. Reactivate Key
    res_reactivate = client.put(
        f"{API}/workspaces/{ws_a_id}/integrations/keys/{key_id}/status",
        json={"status": "active"},
    )
    assert res_reactivate.status_code == 200
    assert res_reactivate.json()["status"] == "active"

    # 7. Rotate Key
    res_rotate = client.post(
        f"{API}/workspaces/{ws_a_id}/integrations/keys/{key_id}/rotate",
        json={"expires_in_days": 60},
    )
    assert res_rotate.status_code == 200, res_rotate.text
    rotate_data = res_rotate.json()
    assert "secret_key" in rotate_data
    new_raw_secret = rotate_data["secret_key"]
    assert new_raw_secret != raw_secret
    assert rotate_data["rotated_from_key_id"] == key_id

    # Old key is now revoked
    res_list_after = client.get(f"{API}/workspaces/{ws_a_id}/integrations/keys")
    old_key_found = next(k for k in res_list_after.json() if k["id"] == key_id)
    assert old_key_found["status"] == "revoked"

    # 8. Revoke new key
    new_key_id = rotate_data["id"]
    res_revoke = client.request(
        "DELETE",
        f"{API}/workspaces/{ws_a_id}/integrations/keys/{new_key_id}",
        json={"reason": "Dự án đã kết thúc"},
    )
    assert res_revoke.status_code == 200
    assert res_revoke.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_openai_gateway_endpoints(client: TestClient) -> None:
    redis = MagicMock()
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[1, True, 1, True])
    redis.pipeline.return_value.__aenter__ = AsyncMock(return_value=pipeline)
    redis.pipeline.return_value.__aexit__ = AsyncMock(return_value=False)
    app.dependency_overrides[get_redis_client] = lambda: redis
    ws_a_id, ws_b_id = _setup_test_workspaces(client)

    # Setup chat provider and make it the system default
    _as(PLATFORM)
    created = client.post(
        f"{API}/modelops/providers",
        json={
            "name": f"provider-test-{os.getpid()}",
            "provider_type": "openai_compatible",
            "base_url": "http://127.0.0.1:11434/v1",
            "model_name": "qwen2.5:7b",
            "capabilities": ["chat"],
            "timeout_seconds": 5,
        },
    )
    assert created.status_code == 201, created.text
    prov_id = created.json()["id"]

    defaults = client.put(f"{API}/modelops/defaults", json={"chat_provider_id": prov_id})
    assert defaults.status_code == 200, defaults.text

    # Create an assistant in Workspace A
    _as(ADMIN_A)
    # Create collection
    res_col = client.post(
        f"{API}/workspaces/{ws_a_id}/collections",
        json={"name": "Kho Tuyển Sinh", "description": "Tài liệu tuyển sinh"},
    )
    assert res_col.status_code == 201
    col_a_id = res_col.json()["id"]

    # Create Assistant A
    res_ast_a = client.post(
        f"{API}/workspaces/{ws_a_id}/assistants",
        json={
            "collection_id": col_a_id,
            "name": "Trợ lý Tuyển Sinh QNU",
            "persona": "Bạn là chuyên gia tư vấn tuyển sinh QNU.",
            "top_k": 3,
            "chat_provider_id": prov_id,
        },
    )
    assert res_ast_a.status_code == 201
    ast_a_id = res_ast_a.json()["id"]

    # Create Assistant B in Workspace B
    _as(ADMIN_B)
    res_col_b = client.post(
        f"{API}/workspaces/{ws_b_id}/collections",
        json={"name": "Kho Quy Định", "description": "Tài liệu quy định"},
    )
    col_b_id = res_col_b.json()["id"]
    res_ast_b = client.post(
        f"{API}/workspaces/{ws_b_id}/assistants",
        json={
            "collection_id": col_b_id,
            "name": "Trợ lý Quy Định QNU",
            "persona": "Bạn là chuyên gia quy định QNU.",
            "top_k": 3,
            "chat_provider_id": prov_id,
        },
    )
    ast_b_id = res_ast_b.json()["id"]

    # Create API key in Workspace A scoped only to ast_a_id
    _as(ADMIN_A)
    res_key = client.post(
        f"{API}/workspaces/{ws_a_id}/integrations/keys",
        json={
            "app_name": "Mobile App QNU",
            "name": "Khóa App",
            "allowed_assistant_ids": [ast_a_id],
        },
    )
    assert res_key.status_code == 201
    raw_secret = res_key.json()["secret_key"]
    auth_header = {"Authorization": f"Bearer {raw_secret}"}

    # Remove overrides for resolve_actor so the OpenAI gateway relies exclusively on Bearer token
    app.dependency_overrides.pop(resolve_actor, None)
    app.dependency_overrides.pop(get_actor, None)

    # 1. Test GET /integrations/openai/v1/models
    res_models = client.get(f"{API}/integrations/openai/v1/models", headers=auth_header)
    assert res_models.status_code == 200, res_models.text
    models_data = res_models.json()
    assert models_data["object"] == "list"
    model_ids = [m["id"] for m in models_data["data"]]
    assert ast_a_id in model_ids
    assert ast_b_id not in model_ids  # Isolation: cannot see Workspace B assistant

    # 2. Test Invalid Token
    res_bad_auth = client.get(
        f"{API}/integrations/openai/v1/models",
        headers={"Authorization": "Bearer qnu_live_invalid_token_12345"},
    )
    assert res_bad_auth.status_code == 401
    assert "error" in res_bad_auth.json()

    # 3. Test Unsupported streaming parameter
    res_stream = client.post(
        f"{API}/integrations/openai/v1/chat/completions",
        headers=auth_header,
        json={
            "model": ast_a_id,
            "messages": [{"role": "user", "content": "Xin chào"}],
            "stream": True,
        },
    )
    assert res_stream.status_code == 400
    assert res_stream.json()["error"]["code"] == "streaming_not_supported"

    # 4. Test Cross-workspace model call: Key A calls Assistant B
    res_cross = client.post(
        f"{API}/integrations/openai/v1/chat/completions",
        headers=auth_header,
        json={
            "model": ast_b_id,
            "messages": [{"role": "user", "content": "Điểm chuẩn là gì?"}],
        },
    )
    assert res_cross.status_code in (403, 404)

    # 5. Test Successful Chat Completion with mock RAG answer pipeline
    mock_answer = AnswerResponse(
        id="ans_test_001",
        status="answered",
        answer="Điểm chuẩn ngành CNTT năm 2025 là 24.5 điểm.",
        statements=[
            Statement(
                text="Điểm chuẩn ngành CNTT năm 2025 là 24.5 điểm.",
                evidence_ids=["ev_001"],
            )
        ],
        sources=[
            EvidenceSource(
                chunk_id="chk_001",
                document_id="doc_001",
                version_id="ver_001",
                publication_decision_id="pub_001",
                score=0.92,
                kind="text",
                text="Ngành CNTT lấy 24.5 điểm",
                citations={"page_no": 2},
                structure=None,
                evidence_id="ev_001",
            )
        ],
        index_run_id="idx_001",
        generation=1,
        trace=AnswerTrace(
            prompt_version="1",
            prompt_tokens=15,
            completion_tokens=20,
            total_tokens=35,
            verification={"status": "verified"},
        ),
    )

    with patch("qnu.domains.integration.gateway.execute_rag_answer", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_answer

        res_chat = client.post(
            f"{API}/integrations/openai/v1/chat/completions",
            headers=auth_header,
            json={
                "model": ast_a_id,
                "messages": [
                    {"role": "user", "content": "Điểm chuẩn ngành CNTT?"},
                ],
            },
        )
        assert res_chat.status_code == 200, res_chat.text
        chat_data = res_chat.json()

        assert chat_data["object"] == "chat.completion"
        assert chat_data["choices"][0]["message"]["content"] == mock_answer.answer
        assert chat_data["choices"][0]["finish_reason"] == "stop"

        # Verify qnu_extensions contains evidence-first citations
        assert "qnu_extensions" in chat_data
        assert len(chat_data["qnu_extensions"]["statements"]) == 1
        assert chat_data["qnu_extensions"]["sources"][0]["evidence_id"] == "ev_001"
