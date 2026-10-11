"""Local credential bootstrap must not leak, overwrite or enter production."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.crypto import encrypt_secret
from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig


@pytest.mark.asyncio
async def test_local_seed_restores_primary_and_authoritative_pool(tmp_path):
    from app.modules.modelops.services import local_seed_credentials as seed
    token = encrypt_secret("fixture-only-secret")
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"vllm_api_key_encrypted": token}), encoding="utf-8")
    db = AsyncMock()
    config = ModelProviderConfig(id="prov_rtx5090_vllm", provider_type="vllm", extra_config={})
    with patch.object(seed, "LOCAL_SEED_CREDENTIALS_PATH", path):
        await seed.apply_local_seed_credentials(db, config)
    assert config.api_key_encrypted == token
    assert config.extra_config["api_keys"][0]["api_key"] == token
    assert db.add.call_args.args[0].api_key_encrypted == token


@pytest.mark.asyncio
async def test_existing_key_is_never_overwritten():
    from app.modules.modelops.services import local_seed_credentials as seed
    config = ModelProviderConfig(id="prov_rtx5090_vllm", provider_type="vllm", api_key_encrypted="existing")
    await seed.apply_local_seed_credentials(AsyncMock(), config)
    assert config.api_key_encrypted == "existing"


@pytest.mark.asyncio
async def test_plaintext_bootstrap_is_rejected(tmp_path):
    from app.modules.modelops.services import local_seed_credentials as seed
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"vllm_api_key_encrypted": "fixture-plaintext"}), encoding="utf-8")
    config = ModelProviderConfig(id="prov_rtx5090_vllm", provider_type="vllm", extra_config={})
    with patch.object(seed, "LOCAL_SEED_CREDENTIALS_PATH", path), pytest.raises(AppException):
        await seed.apply_local_seed_credentials(AsyncMock(), config)


@pytest.mark.asyncio
async def test_production_does_not_use_local_seed(tmp_path):
    from app.modules.modelops.services import local_seed_credentials as seed
    config = ModelProviderConfig(id="prov_rtx5090_vllm", provider_type="vllm", extra_config={})
    with patch.object(seed.settings, "ENVIRONMENT", "production"):
        await seed.apply_local_seed_credentials(AsyncMock(), config)
    assert not config.api_key_encrypted


@pytest.mark.asyncio
async def test_empty_database_seed_restores_key_and_preserves_it_on_reseed(tmp_path):
    from app.modules.modelops.models import ProviderApiKey
    from app.modules.modelops.services import local_seed_credentials as seed
    from app.modules.modelops.services.provider_service import ProviderService
    token = encrypt_secret("fixture-bootstrap-secret")
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"vllm_api_key_encrypted": token}), encoding="utf-8")
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    with patch.object(seed, "LOCAL_SEED_CREDENTIALS_PATH", path), patch(
        "app.modules.modelops.services.model_catalog_service.model_catalog_service.seed_system_model_defaults", AsyncMock()
    ):
        await ProviderService().seed_default_providers(db)
        added = [call.args[0] for call in db.add.call_args_list]
        provider = next(row for row in added if isinstance(row, ModelProviderConfig) and row.id == "prov_rtx5090_vllm")
        assert provider.api_key_encrypted == token
        assert any(isinstance(row, ProviderApiKey) and row.provider_id == provider.id for row in added)
        result.scalars.return_value.all.return_value = [row for row in added if isinstance(row, ModelProviderConfig)]
        db.add.reset_mock()
        await ProviderService().seed_default_providers(db)
        db.add.assert_not_called()
        assert provider.api_key_encrypted == token
