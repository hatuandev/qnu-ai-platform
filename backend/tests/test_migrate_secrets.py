"""Unit tests for Provider Secrets Migration Tool and Key Rotation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.crypto import (
    _derive_fernet,
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
    reencrypt_secret,
)
from app.modules.modelops.models import ModelProviderConfig
from scripts.migrate_provider_secrets import (
    KeyStats,
    inspect_secrets,
    run_apply,
    run_dry_run,
    run_verify,
)


@pytest.mark.asyncio
async def test_crypto_key_rotation() -> None:
    """Verify that tokens encrypted with older keys can be decrypted via key rotation and re-encrypted."""
    old_key = "old-legacy-secret-key-2025"
    new_key = "new-active-secret-key-2026"

    # Encrypt using old key directly
    old_fernet = _derive_fernet(old_key)
    raw_secret = "sk-test-secret-value-12345"
    old_token = f"enc:v1:{old_fernet.encrypt(raw_secret.encode('utf-8')).decode('ascii')}"

    # With only new_key active and old_key in rotation:
    with patch("app.core.crypto.settings.PROVIDER_ENCRYPTION_KEY", new_key), patch(
        "app.core.crypto.settings.OLD_PROVIDER_ENCRYPTION_KEYS", [old_key]
    ):
        # 1. Decrypt should succeed via fallback fernet
        decrypted = decrypt_secret(old_token)
        assert decrypted == raw_secret

        # 2. Re-encrypt should upgrade token to new active key
        new_token = reencrypt_secret(old_token)
        assert new_token != old_token
        assert is_encrypted(new_token)

        # 3. New token should decrypt using active key directly
        assert decrypt_secret(new_token) == raw_secret


@pytest.mark.asyncio
async def test_inspect_secrets_classification() -> None:
    """Test inspect_secrets correctly categorizes encrypted, plaintext, and empty keys."""
    prov_plain = ModelProviderConfig(
        id="prov_1",
        name="Plain Provider",
        provider_type="openai",
        api_key_encrypted="sk-raw-plaintext-key",
        extra_config={
            "api_keys": [
                {"id": "k1", "api_key": "sk-pool-plaintext"},
                {"id": "k2", "api_key": encrypt_secret("sk-pool-encrypted")},
            ]
        },
    )
    prov_enc = ModelProviderConfig(
        id="prov_2",
        name="Enc Provider",
        provider_type="gemini",
        api_key_encrypted=encrypt_secret("sk-already-encrypted"),
        extra_config={"api_keys": []},
    )
    prov_empty = ModelProviderConfig(
        id="prov_3",
        name="Empty Provider",
        provider_type="local_vllm",
        api_key_encrypted=None,
        extra_config={"api_keys": [{"id": "k3", "api_key": None}]},
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prov_plain, prov_enc, prov_empty]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("scripts.migrate_provider_secrets.AsyncSessionFactory", return_value=mock_db):
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        stats, _details = await inspect_secrets()

        assert stats.total_providers == 3
        assert stats.primary_plaintext == 1
        assert stats.primary_encrypted == 1
        assert stats.primary_empty == 1

        assert stats.pool_keys_total == 3
        assert stats.pool_keys_plaintext == 1
        assert stats.pool_keys_encrypted == 1
        assert stats.pool_keys_empty == 1


@pytest.mark.asyncio
async def test_migrate_apply_encrypts_and_commits() -> None:
    """Test run_apply encrypts plaintext secrets and commits transaction."""
    prov = ModelProviderConfig(
        id="prov_test",
        name="Test Provider",
        provider_type="openai",
        api_key_encrypted="sk-plaintext-key-to-encrypt",
        extra_config={"api_keys": [{"id": "k1", "api_key": "sk-pool-plaintext"}]},
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prov]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("scripts.migrate_provider_secrets.AsyncSessionFactory", return_value=mock_db):
        mock_db.__aenter__.return_value = mock_db
        mock_db.__aexit__.return_value = None

        code = await run_apply()
        assert code == 0

        # Verify in-memory mutation
        assert is_encrypted(prov.api_key_encrypted)
        assert decrypt_secret(prov.api_key_encrypted) == "sk-plaintext-key-to-encrypt"

        pool_key = prov.extra_config["api_keys"][0]
        assert is_encrypted(pool_key["api_key"])
        assert decrypt_secret(pool_key["api_key"]) == "sk-pool-plaintext"

        # Verify db.commit was called
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_migrate_verify_passes_when_all_encrypted() -> None:
    """Test run_verify succeeds when zero plaintext secrets remain."""
    mock_stats = KeyStats(
        total_providers=2,
        primary_encrypted=2,
        primary_plaintext=0,
        primary_empty=0,
        pool_keys_total=2,
        pool_keys_encrypted=2,
        pool_keys_plaintext=0,
        pool_keys_empty=0,
    )
    mock_details = [
        {"id": "prov_1", "name": "P1", "primary_status": "encrypted", "pool_keys": []},
        {"id": "prov_2", "name": "P2", "primary_status": "encrypted", "pool_keys": []},
    ]

    with patch(
        "scripts.migrate_provider_secrets.inspect_secrets",
        new_callable=AsyncMock,
        return_value=(mock_stats, mock_details),
    ):
        code = await run_verify()
        assert code == 0


@pytest.mark.asyncio
async def test_migrate_verify_fails_when_plaintext_found() -> None:
    """Test run_verify fails (returns 1) when plaintext secrets exist."""
    mock_stats = KeyStats(
        total_providers=1,
        primary_encrypted=0,
        primary_plaintext=1,
        primary_empty=0,
    )
    mock_details = [
        {"id": "prov_1", "name": "P1", "primary_status": "plaintext", "pool_keys": []},
    ]

    with patch(
        "scripts.migrate_provider_secrets.inspect_secrets",
        new_callable=AsyncMock,
        return_value=(mock_stats, mock_details),
    ):
        code = await run_verify()
        assert code == 1


@pytest.mark.asyncio
async def test_migrate_dry_run_executes() -> None:
    """Test run_dry_run executes cleanly without throwing."""
    mock_stats = KeyStats(total_providers=1, primary_encrypted=1)
    mock_details = [{"id": "p1", "name": "P1", "provider_type": "openai", "primary_status": "encrypted", "pool_keys": []}]

    with patch(
        "scripts.migrate_provider_secrets.inspect_secrets",
        new_callable=AsyncMock,
        return_value=(mock_stats, mock_details),
    ):
        code = await run_dry_run()
        assert code == 0
