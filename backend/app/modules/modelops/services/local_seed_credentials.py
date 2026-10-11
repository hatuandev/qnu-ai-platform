"""Optional encrypted, Git-ignored bootstrap for local database resets only."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_secret, is_encrypted, mask_secret
from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey

LOCAL_SEED_CREDENTIALS_PATH = (
    Path(__file__).resolve().parents[4] / "storage" / "modelops-bootstrap" / "credentials.json"
)


def _load_encrypted_key() -> str | None:
    if not LOCAL_SEED_CREDENTIALS_PATH.exists():
        return None
    try:
        payload = json.loads(LOCAL_SEED_CREDENTIALS_PATH.read_text(encoding="utf-8"))
        token = payload.get("vllm_api_key_encrypted")
        if not isinstance(token, str) or not is_encrypted(token) or not decrypt_secret(token):
            raise ValueError("Invalid encrypted credential")
        return token
    except (OSError, ValueError, AttributeError) as exc:
        raise AppException(
            "Không đọc được khóa seed mã hóa. Kiểm tra tệp bootstrap và khóa mã hóa của ứng dụng.",
            code="LOCAL_SEED_CREDENTIAL_INVALID", status_code=400,
        ) from exc


async def apply_local_seed_credentials(db: AsyncSession, config: ModelProviderConfig) -> None:
    """Called only for newly created presets; never overrides managed credentials."""
    if settings.ENVIRONMENT not in {"development", "dev", "local", "test", "testing"}:
        return
    if config.id != "prov_rtx5090_vllm" or config.provider_type != "vllm":
        return
    extra = dict(config.extra_config or {})
    if config.api_key_encrypted or extra.get("api_keys"):
        return
    token = await asyncio.to_thread(_load_encrypted_key)
    if token is None:
        return
    key_id = f"primary_{config.id}"
    masked = mask_secret(decrypt_secret(token)) or "••••••••"
    config.api_key_encrypted = token
    extra["api_keys"] = [{
        "id": key_id, "name": "vLLM local seed", "api_key": token,
        "api_key_masked": masked, "priority": 1, "is_active": True, "status": "active",
    }]
    config.extra_config = extra
    db.add(ProviderApiKey(
        id=key_id, provider_id=config.id, name="vLLM local seed", api_key_encrypted=token,
        api_key_masked=masked, priority=1, is_active=True, status="active", usage_tokens=0,
    ))
