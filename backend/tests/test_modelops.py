"""Unit & Integration Tests for ModelOps, LLM Adapters, Circuit Breaker, Fallbacks & Quotas."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import AppException
from app.main import app
from app.modules.modelops.circuit_breaker import CircuitBreaker, CircuitBreakerState
from app.modules.modelops.models import LLMUsageLog, ModelProviderConfig, TenantQuota
from app.modules.modelops.providers import (
    CloudflareAdapter,
    GeminiAdapter,
    LocalVLLMAdapter,
    MistralAdapter,
    OpenAIAdapter,
    get_llm_adapter,
)
from app.modules.modelops.schemas import ChatMessage, LLMGenerateRequest
from app.modules.modelops.service import modelops_service


def test_circuit_breaker_lifecycle():
    """Verify Circuit Breaker trips from CLOSED to OPEN after reaching failure threshold."""
    cb = CircuitBreaker("test-provider", failure_threshold=3, recovery_timeout_seconds=2.0)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 1st failure
    cb.record_failure(ValueError("Connection timeout"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 2nd failure
    cb.record_failure(ValueError("500 Internal Error"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True

    # 3rd failure -> Trips to OPEN
    cb.record_failure(ValueError("Rate limit 429"))
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False

    # Simulate recovery timeout passing
    cb.last_failure_time -= 3.0  # simulate 3s passed
    assert cb.can_execute() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Success restores to CLOSED
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_llm_adapter_factory():
    """Verify Adapter Factory constructs corresponding provider instances."""
    adapter_openai = get_llm_adapter("openai", "gpt-4o-mini", api_key="mock")
    assert isinstance(adapter_openai, OpenAIAdapter)
    assert adapter_openai.provider_type == "openai"

    adapter_gemini = get_llm_adapter("gemini", "gemini-1.5-flash", api_key="mock")
    assert isinstance(adapter_gemini, GeminiAdapter)
    assert adapter_gemini.provider_type == "gemini"

    adapter_local = get_llm_adapter("local_vllm", "qwen2.5-7b-instruct")
    assert isinstance(adapter_local, LocalVLLMAdapter)
    assert adapter_local.provider_type == "local_vllm"

    adapter_mistral = get_llm_adapter("mistral", "mistral-large-latest", api_key="mock")
    assert isinstance(adapter_mistral, MistralAdapter)
    assert adapter_mistral.provider_type == "mistral"

    adapter_cloudflare = get_llm_adapter(
        "cloudflare", "@cf/meta/llama-3.3-70b-instruct", api_key="mock", account_id="acc-qnu-test"
    )
    assert isinstance(adapter_cloudflare, CloudflareAdapter)
    assert adapter_cloudflare.provider_type == "cloudflare"
    assert adapter_cloudflare.account_id == "acc-qnu-test"


@pytest.mark.asyncio
async def test_openai_adapter_mock_generation():
    """Verify OpenAI adapter returns valid LLMResponse in mock mode."""
    adapter = OpenAIAdapter(model_name="gpt-4o-mini", api_key="mock")
    messages = [
        ChatMessage(role="user", content="Điểm chuẩn ngành Công nghệ thông tin ĐH Quy Nhơn là gì?")
    ]
    resp = await adapter.generate(messages)
    assert resp.provider == "openai"
    assert resp.model == "gpt-4o-mini"
    assert len(resp.content) > 0
    assert resp.total_tokens > 0


@pytest.mark.asyncio
async def test_mistral_adapter_mock_generation():
    """Verify Mistral AI adapter returns valid LLMResponse in mock mode."""
    adapter = MistralAdapter(model_name="mistral-large-latest", api_key="mock")
    messages = [
        ChatMessage(role="user", content="Hãy giới thiệu về trường Đại học Quy Nhơn")
    ]
    resp = await adapter.generate(messages)
    assert resp.provider == "mistral"
    assert resp.model == "mistral-large-latest"
    assert "Mistral AI" in resp.content
    assert resp.total_tokens > 0


@pytest.mark.asyncio
async def test_cloudflare_adapter_mock_generation():
    """Verify Cloudflare Workers AI adapter returns valid LLMResponse in mock mode."""
    adapter = CloudflareAdapter(
        model_name="@cf/meta/llama-3.3-70b-instruct", api_key="mock", account_id="acc-qnu-test"
    )
    messages = [
        ChatMessage(role="user", content="Thông tin học phí ĐH Quy Nhơn")
    ]
    resp = await adapter.generate(messages)
    assert resp.provider == "cloudflare"
    assert resp.model == "@cf/meta/llama-3.3-70b-instruct"
    assert "Cloudflare Workers AI" in resp.content
    assert resp.total_tokens > 0



@pytest.mark.asyncio
async def test_dynamic_fallback_when_primary_fails():
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    req = LLMGenerateRequest(
        messages=[ChatMessage(role="user", content="Tư vấn tuyển sinh")],
        tenant_id="test-tenant",
    )

    # Patch quota check to return fresh quota
    mock_quota = TenantQuota(
        tenant_id="test-tenant",
        month_period="2026-09",
        monthly_token_limit=1_000_000,
        tokens_used=100,
    )

    mock_active = [
        {
            "id": "prov_openai",
            "name": "OpenAI Primary",
            "provider_type": "openai",
            "model_name": "gpt-4o",
            "models": ["gpt-4o"],
            "is_active": True,
            "priority": 1,
            "timeout_seconds": 15,
            "api_base_url": None,
            "api_key": "mock",
            "api_key_masked": "sk-mock",
            "keys_count": 1,
            "api_keys": [{"id": "k1", "api_key": "mock", "is_active": True, "status": "active"}],
        },
        {
            "id": "prov_gemini",
            "name": "Gemini Secondary",
            "provider_type": "gemini",
            "model_name": "gemini-1.5-flash",
            "models": ["gemini-1.5-flash"],
            "is_active": True,
            "priority": 2,
            "timeout_seconds": 15,
            "api_base_url": None,
            "api_key": "mock",
            "api_key_masked": "gem-mock",
            "keys_count": 1,
            "api_keys": [{"id": "k2", "api_key": "mock", "is_active": True, "status": "active"}],
        },
    ]

    with (
        patch.object(modelops_service, "check_quota_available", new_callable=AsyncMock) as mock_chk,
        patch.object(modelops_service, "get_active_providers", new_callable=AsyncMock) as mock_prov,
        patch(
            "app.modules.modelops.service.get_llm_adapter"
        ) as mock_factory,
    ):
        mock_chk.return_value = mock_quota
        mock_prov.return_value = mock_active

        # 1st call (Primary) fails, 2nd call (Secondary) succeeds
        primary_adapter = AsyncMock()
        primary_adapter.generate.side_effect = RuntimeError("OpenAI 503 Outage")

        secondary_adapter = AsyncMock()
        from app.modules.modelops.providers.base import LLMResponse

        secondary_adapter.generate.return_value = LLMResponse(
            content="Phản hồi từ mô hình dự phòng Gemini",
            provider="gemini",
            model="gemini-1.5-flash",
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50,
        )

        mock_factory.side_effect = [primary_adapter, secondary_adapter]

        res = await modelops_service.generate(mock_db, req)

    assert res.provider == "gemini"
    assert res.is_fallback is True
    assert "Gemini" in res.content


@pytest.mark.asyncio
async def test_quota_exceeded_blocking():
    """Verify Quota Manager halts execution with HTTP 429 when tenant exceeds monthly token cap."""
    mock_db = AsyncMock()
    mock_quota = TenantQuota(
        tenant_id="overlimit-tenant",
        month_period="2026-09",
        monthly_token_limit=10_000,
        tokens_used=10_000,
    )

    with patch.object(modelops_service, "get_or_create_quota", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_quota

        with pytest.raises(AppException) as exc_info:
            await modelops_service.check_quota_available(
                mock_db, tenant_id="overlimit-tenant", estimated_tokens=500
            )

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "QUOTA_EXCEEDED"


@pytest.mark.asyncio
async def test_api_list_providers():
    """Verify GET /platform/v1alpha1/modelops/providers returns active provider cascade."""
    mock_providers = [
        {
            "id": "prov_openai",
            "name": "OpenAI",
            "provider_type": "openai",
            "model_name": "gpt-4o-mini",
            "models": ["gpt-4o-mini"],
            "circuit_breaker_status": "CLOSED",
            "latency_ms": 110,
            "failure_rate": 0.0,
            "is_active": True,
            "api_base_url": "https://api.openai.com/v1",
            "timeout_seconds": 15,
            "priority": 1,
            "keys_count": 1,
            "api_keys": [],
        },
        {
            "id": "prov_gemini",
            "name": "Google Gemini",
            "provider_type": "gemini",
            "model_name": "gemini-1.5-flash",
            "models": ["gemini-1.5-flash"],
            "circuit_breaker_status": "CLOSED",
            "latency_ms": 110,
            "failure_rate": 0.0,
            "is_active": True,
            "api_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "timeout_seconds": 15,
            "priority": 2,
            "keys_count": 1,
            "api_keys": [],
        },
        {
            "id": "prov_mistral",
            "name": "Mistral AI",
            "provider_type": "mistral",
            "model_name": "mistral-large-latest",
            "models": ["mistral-large-latest"],
            "circuit_breaker_status": "CLOSED",
            "latency_ms": 110,
            "failure_rate": 0.0,
            "is_active": True,
            "api_base_url": "https://api.mistral.ai/v1",
            "timeout_seconds": 20,
            "priority": 3,
            "keys_count": 0,
            "api_keys": [],
        },
        {
            "id": "prov_cloudflare",
            "name": "Cloudflare Workers AI",
            "provider_type": "cloudflare",
            "model_name": "@cf/meta/llama-3.3-70b-instruct",
            "models": ["@cf/meta/llama-3.3-70b-instruct"],
            "circuit_breaker_status": "CLOSED",
            "latency_ms": 110,
            "failure_rate": 0.0,
            "is_active": True,
            "api_base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run",
            "timeout_seconds": 25,
            "priority": 4,
            "keys_count": 0,
            "api_keys": [],
        },
    ]

    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(modelops_service, "get_active_providers", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_providers
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.get("/platform/v1alpha1/modelops/providers")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    providers = response.json()
    assert len(providers) >= 4
    assert providers[0]["provider_type"] == "openai"
    assert providers[1]["provider_type"] == "gemini"
    assert providers[2]["provider_type"] == "mistral"
    assert providers[3]["provider_type"] == "cloudflare"


@pytest.mark.asyncio
async def test_api_seed_default_providers():
    """Verify POST /platform/v1alpha1/modelops/providers/seed-defaults seeds QNU standard presets."""
    mock_db = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(modelops_service, "seed_default_providers", new_callable=AsyncMock) as mock_seed:
            mock_seed.return_value = [{"id": "prov_mistral", "provider_type": "mistral"}]
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/platform/v1alpha1/modelops/providers/seed-defaults")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1



@pytest.mark.asyncio
async def test_api_modelops_generate():
    """Verify POST /platform/v1alpha1/modelops/generate invokes LLM successfully."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        mock_quota = TenantQuota(
            tenant_id="qnu-default",
            month_period="2026-09",
            monthly_token_limit=1_000_000,
            tokens_used=0,
        )
        mock_active = [
            {
                "id": "prov_openai",
                "name": "OpenAI",
                "provider_type": "openai",
                "model_name": "gpt-4o-mini",
                "models": ["gpt-4o-mini"],
                "circuit_breaker_status": "CLOSED",
                "latency_ms": 110,
                "failure_rate": 0.0,
                "is_active": True,
                "api_base_url": "https://api.openai.com/v1",
                "api_key": "mock",
                "timeout_seconds": 15,
                "priority": 1,
                "keys_count": 1,
                "api_keys": [{"id": "k1", "api_key": "mock", "is_active": True, "status": "active"}],
            }
        ]
        with (
            patch.object(modelops_service, "get_or_create_quota", new_callable=AsyncMock) as mock_q,
            patch.object(modelops_service, "get_active_providers", new_callable=AsyncMock) as mock_prov,
        ):
            mock_q.return_value = mock_quota
            mock_prov.return_value = mock_active

            payload = {
                "messages": [{"role": "user", "content": "Xin chào Trợ lý AI QNU!"}],
                "tenant_id": "qnu-default",
                "temperature": 0.2,
                "max_tokens": 500,
            }

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post("/platform/v1alpha1/modelops/generate", json=payload)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] in ("openai", "gemini", "local_vllm")
    assert len(data["content"]) > 0
    assert data["total_tokens"] > 0


@pytest.mark.asyncio
async def test_api_get_provider_presets():
    """Verify GET /platform/v1alpha1/modelops/presets returns provider templates."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/platform/v1alpha1/modelops/presets")

    assert response.status_code == 200
    presets = response.json()
    codes = [p["code"] for p in presets]
    assert "openai" in codes
    assert "gemini" in codes
    assert "deepseek" in codes
    assert "groq" in codes
    assert "cloudflare" in codes
    assert "nvidia" in codes
    assert "custom" in codes


@pytest.mark.asyncio
async def test_api_key_pool_crud_and_rotation():
    """Verify Key Pool management: list, add, update, test, and simulate 429 rotation."""
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. List keys for default provider
            res_list = await ac.get("/platform/v1alpha1/modelops/providers/prov_openai/keys")
            assert res_list.status_code == 200
            keys = res_list.json()
            assert len(keys) >= 2

            # 2. Add new key to pool
            new_key_payload = {
                "name": "Key Khoa CNTT Test",
                "api_key": "sk-proj-test-cntt-987654321",
                "priority": 3,
                "quota_limit": 5000000,
            }
            res_add = await ac.post(
                "/platform/v1alpha1/modelops/providers/prov_openai/keys",
                json=new_key_payload,
            )
            assert res_add.status_code == 201
            added_key = res_add.json()
            assert added_key["name"] == "Key Khoa CNTT Test"
            assert "sk-" in added_key["api_key_masked"]

            # 3. Test single key
            key_id = added_key["id"]
            res_test = await ac.post(
                f"/platform/v1alpha1/modelops/providers/prov_openai/keys/{key_id}/test"
            )
            assert res_test.status_code == 200
            assert res_test.json()["success"] is True

            # 4. Simulate Key Rotation on Rate Limit 429
            sim_payload = {
                "tokens_consumed": 2500,
                "trigger_rate_limit": True,
                "cooldown_seconds": 30,
            }
            res_sim = await ac.post(
                "/platform/v1alpha1/modelops/providers/prov_openai/keys/simulate-rotation",
                json=sim_payload,
            )
            assert res_sim.status_code == 200
            sim_data = res_sim.json()
            assert sim_data["success"] is True
            assert sim_data["rate_limit_triggered"] is True
            assert sim_data["rotated"] is True
            assert sim_data["next_key_id"] is not None
            assert "Rate Limit (429)" in sim_data["message"]

            # 5. Delete key
            res_del = await ac.delete(
                f"/platform/v1alpha1/modelops/providers/prov_openai/keys/{key_id}"
            )
            assert res_del.status_code == 200
            assert res_del.json()["success"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_system_model_defaults_api():
    """Test getting, updating, and setting system model routing defaults."""
    from app.core.database import get_db
    from app.main import create_app
    from app.modules.modelops.models import ModelProviderConfig

    app = create_app()
    mock_db = AsyncMock()

    cfg_record = ModelProviderConfig(
        id="system_model_defaults",
        name="Cấu Hình Mặc Định Hệ Thống",
        provider_type="system_routing",
        extra_config={
            "defaults": {
                "default_embedding_provider_id": "prov_cloudflare",
                "default_embedding_model": "@cf/baai/bge-m3",
                "default_reranker_provider_id": "prov_cloudflare",
                "default_reranker_model": "@cf/baai/bge-reranker-base",
                "default_ocr_provider_id": "prov_mistral",
                "default_ocr_model": "mistral-ocr-latest",
            }
        },
    )

    mock_res_cfg = MagicMock()
    mock_res_cfg.scalar_one_or_none.return_value = cfg_record

    mock_res_providers = MagicMock()
    mock_res_providers.scalars.return_value.all.return_value = [
        ModelProviderConfig(
            id="prov_cloudflare",
            name="Cloudflare Workers AI",
            provider_type="cloudflare",
            extra_config={"models": ["@cf/baai/bge-m3", "@cf/baai/bge-reranker-base"]},
        ),
        ModelProviderConfig(
            id="prov_sentence_transformers",
            name="Local SentenceTransformers",
            provider_type="sentence_transformers",
            extra_config={"models": ["BAAI/bge-m3"]},
        ),
    ]

    mock_db.execute.side_effect = [
        mock_res_cfg,
        mock_res_providers,
        mock_res_cfg,
        mock_res_providers,
        mock_res_cfg,
        mock_res_providers,
        mock_res_cfg,
        mock_res_providers,
    ]

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/platform/v1alpha1/modelops/defaults")
            assert res.status_code == 200
            data = res.json()
            assert data["defaults"]["default_embedding_provider_id"] == "prov_cloudflare"
            assert data["defaults"]["default_embedding_model"] == "@cf/baai/bge-m3"
            assert len(data["available_embeddings"]) >= 2
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_provider_models_test_all_success():
    """Verify endpoint tests all configured models of a provider and returns status."""
    mock_db = AsyncMock()
    cfg_record = ModelProviderConfig(
        id="prov_gemini",
        name="Google Gemini",
        provider_type="gemini",
        is_active=True,
        api_key_encrypted="mock_key",
        extra_config={"models": ["gemini-1.5-flash", "gemini-1.5-pro"]},
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = cfg_record
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/platform/v1alpha1/modelops/providers/prov_gemini/models/test")
            assert res.status_code == 200
            data = res.json()
            assert data["provider_id"] == "prov_gemini"
            assert data["total_models"] == 2
            assert data["available_models"] == 2
            assert data["unavailable_models"] == 0
            assert len(data["results"]) == 2
            assert data["results"][0]["model_name"] == "gemini-1.5-flash"
            assert data["results"][0]["status"] == "available"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_provider_models_test_single_model_and_invalid():
    """Verify endpoint tests a single model and correctly flags invalid/deprecated models."""
    mock_db = AsyncMock()
    cfg_record = ModelProviderConfig(
        id="prov_gemini",
        name="Google Gemini",
        provider_type="gemini",
        is_active=True,
        api_key_encrypted="mock_key",
        extra_config={"models": ["gemini-1.5-flash", "gemini-deprecated-404"]},
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = cfg_record
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Test single invalid model
            res = await ac.post(
                "/platform/v1alpha1/modelops/providers/prov_gemini/models/test",
                json={"model_name": "gemini-deprecated-404"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total_models"] == 1
            assert data["available_models"] == 0
            assert data["unavailable_models"] == 1
            assert data["results"][0]["status"] == "unavailable"
            assert data["results"][0]["success"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_api_get_quota_endpoints():
    """Verify both /quotas/{tenant_id} and /quota?tenant_id= query alias return TenantQuotaResponse."""
    mock_db = AsyncMock()
    mock_quota = TenantQuota(
        tenant_id="tenant_qnu",
        month_period="2026-09",
        monthly_token_limit=5_000_000,
        monthly_cost_limit_usd=100.0,
        tokens_used=125_000,
        cost_used_usd=2.50,
        is_blocked=False,
    )

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch.object(modelops_service, "get_or_create_quota", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_quota

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Path param standard endpoint
                res_path = await ac.get("/platform/v1alpha1/modelops/quotas/tenant_qnu")
                assert res_path.status_code == 200
                data_path = res_path.json()
                assert data_path["tenant_id"] == "tenant_qnu"
                assert data_path["tokens_used"] == 125_000
                assert data_path["monthly_token_limit"] == 5_000_000

                # 2. Query param backward-compatible alias endpoint
                res_query = await ac.get("/platform/v1alpha1/modelops/quota?tenant_id=tenant_qnu")
                assert res_query.status_code == 200
                data_query = res_query.json()
                assert data_query["tenant_id"] == "tenant_qnu"
                assert data_query["tokens_used"] == 125_000
                assert data_query["monthly_token_limit"] == 5_000_000
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_generate_stream_records_usage_and_deducts_quota():
    """Verify generate_stream accumulates token counts, updates tenant quota and records LLMUsageLog."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    mock_quota = TenantQuota(
        tenant_id="tenant_qnu",
        month_period="2026-09",
        monthly_token_limit=1_000_000,
        monthly_cost_limit_usd=50.0,
        tokens_used=1000,
        cost_used_usd=0.05,
        is_blocked=False,
    )

    mock_provider = {
        "id": "prov_openai",
        "name": "OpenAI",
        "provider_type": "openai",
        "model_name": "gpt-4o-mini",
        "api_key": "sk-proj-test",
        "api_base_url": "https://api.openai.com/v1",
        "timeout_seconds": 30,
        "is_active": True,
        "models": ["gpt-4o-mini"],
        "api_keys": [{"id": "k1", "api_key": "sk-proj-test", "is_active": True, "status": "active"}],
    }

    class FakeAdapter:
        async def stream(self, messages, temperature, max_tokens):
            for token in ["Trường ", "Đại học ", "Quy Nhơn"]:
                yield token

    req = LLMGenerateRequest(
        messages=[ChatMessage(role="user", content="Giới thiệu về trường QNU")],
        tenant_id="tenant_qnu",
        assistant_code="admissions",
        preferred_model_name="gpt-4o-mini",
    )

    with (
        patch.object(modelops_service, "check_quota_available", new_callable=AsyncMock) as mock_chk,
        patch.object(modelops_service, "get_active_providers", new_callable=AsyncMock) as mock_prov,
        patch("app.modules.modelops.service.get_llm_adapter", return_value=FakeAdapter()),
    ):
        mock_chk.return_value = mock_quota
        mock_prov.return_value = [mock_provider]

        chunks = []
        async for chunk in modelops_service.generate_stream(mock_db, req):
            chunks.append(chunk)

        assert chunks == ["Trường ", "Đại học ", "Quy Nhơn"]
        # Verify quota was updated
        assert mock_quota.tokens_used > 1000
        assert mock_quota.cost_used_usd >= 0.05
        # Verify LLMUsageLog was added to DB
        assert mock_db.add.called
        added_objs = [call[0][0] for call in mock_db.add.call_args_list]
        usage_logs = [obj for obj in added_objs if isinstance(obj, LLMUsageLog)]
        assert len(usage_logs) == 1
        assert usage_logs[0].tenant_id == "tenant_qnu"
        assert usage_logs[0].status == "success"
        assert usage_logs[0].total_tokens > 0


@pytest.mark.asyncio
async def test_generate_prioritizes_fallback_model_when_primary_unavailable():
    """Verify generate attempts fallback_model_name when primary model fails or is unavailable."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    mock_quota = TenantQuota(
        tenant_id="tenant_qnu",
        month_period="2026-09",
        monthly_token_limit=1_000_000,
        monthly_cost_limit_usd=50.0,
        tokens_used=0,
        cost_used_usd=0.0,
        is_blocked=False,
    )

    # Provider 1 has primary model but fails (HTTP 500)
    # Provider 2 has fallback model and succeeds
    p1 = {
        "id": "prov_openai",
        "name": "OpenAI Primary",
        "provider_type": "openai",
        "model_name": "gpt-4o",
        "api_key": "sk-proj-test",
        "api_base_url": "https://api.openai.com/v1",
        "timeout_seconds": 30,
        "is_active": True,
        "models": ["gpt-4o"],
        "api_keys": [{"id": "k1", "api_key": "sk-proj-test", "is_active": True, "status": "active"}],
    }
    p2 = {
        "id": "prov_gemini",
        "name": "Gemini Fallback",
        "provider_type": "gemini",
        "model_name": "gemini-1.5-flash",
        "api_key": "gemini-key",
        "api_base_url": None,
        "timeout_seconds": 30,
        "is_active": True,
        "models": ["gemini-1.5-flash"],
        "api_keys": [{"id": "k2", "api_key": "gemini-key", "is_active": True, "status": "active"}],
    }

    class FailingAdapter:
        async def generate(self, messages, temperature, max_tokens):
            raise RuntimeError("Provider 1 500 Server Error")

    class SuccessfulFallbackAdapter:
        async def generate(self, messages, temperature, max_tokens):
            from app.modules.modelops.providers.base import LLMResponse

            return LLMResponse(
                content="Câu trả lời từ Gemini Fallback",
                provider="gemini",
                model="gemini-1.5-flash",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                latency_ms=120.0,
            )

    def adapter_factory(provider_type, model_name, **kwargs):
        if provider_type == "openai":
            return FailingAdapter()
        return SuccessfulFallbackAdapter()

    req = LLMGenerateRequest(
        messages=[ChatMessage(role="user", content="Tra cứu quy chế")],
        tenant_id="tenant_qnu",
        assistant_code="regulations",
        preferred_model_name="gpt-4o",
        fallback_model_name="gemini-1.5-flash",
    )

    with (
        patch.object(modelops_service, "check_quota_available", new_callable=AsyncMock) as mock_chk,
        patch.object(modelops_service, "get_active_providers", new_callable=AsyncMock) as mock_prov,
        patch("app.modules.modelops.service.get_llm_adapter", side_effect=adapter_factory),
    ):
        mock_chk.return_value = mock_quota
        mock_prov.return_value = [p1, p2]

        response = await modelops_service.generate(mock_db, req)

        assert response.model == "gemini-1.5-flash"
        assert response.provider == "gemini"
        assert response.is_fallback is True
        assert "Gemini Fallback" in response.content





