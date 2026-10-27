"""Resolve Nemotron credentials only from its selected active ModelOps provider."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.core.exceptions import AppException
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.model_runtime_resolver import ModelRuntimeConfig
from app.modules.modelops.services.probe_credentials import select_probe_credential
from app.modules.modelops.services.provider_key_rotation_service import (
    provider_key_rotation_service,
)
from app.modules.modelops.services.runtime_key_lease import renew_runtime_key
from app.modules.ocr.adapters.nemotron_adapter import NemotronParseAdapter


async def extract_nemotron(db: AsyncSession, provider: ModelProviderConfig,
                          model: str, content: bytes, filename: str) -> dict[str, Any]:
    """Keep lease/cancellation semantics and report measured tokens, without retry."""
    extra = provider.extra_config or {}
    models = set(extra.get('models') or []) | {provider.model_name}
    if not provider.is_active or model not in models:
        raise AppException('Model Nemotron chưa được bật cho provider đã chọn.',
                           code='OCR_PROVIDER_UNAVAILABLE', status_code=503)
    acquired = await provider_key_rotation_service.acquire(db, provider.id,
        lease_seconds=max(180, provider.timeout_seconds + 60))
    lease = acquired.lease
    if acquired.managed and lease is None:
        raise AppException('Provider Nemotron chưa có khóa khả dụng.',
                           code='OCR_PROVIDER_KEYS_UNAVAILABLE', status_code=503)
    settled = False
    try:
        encrypted = None if lease else (await select_probe_credential(db, provider))[0]
        api_key = lease.api_key if lease else decrypt_secret(encrypted) if encrypted else None
        if not api_key and not extra.get('ocr_auth_optional', False):
            raise AppException('Thiếu API key Nemotron trong ModelOps.',
                               code='OCR_PROVIDER_CREDENTIALS_MISSING', status_code=503)
        runtime = ModelRuntimeConfig(provider.id, provider.provider_type, model,
            provider.api_base_url, api_key, None, provider.timeout_seconds,
            key_id=lease.id if lease else None, lease_token=lease.lease_token if lease else None)
        adapter = NemotronParseAdapter(base_url=runtime.api_base_url, api_key=api_key,
            model_name=model, timeout=runtime.timeout_seconds,
            max_tokens=int(extra.get('ocr_max_output_tokens', 8192)))
        async with renew_runtime_key(runtime):
            result = await adapter.extract(content, filename)
        tokens = sum(int((page['response'].get('usage') or {}).get('total_tokens') or 0)
                     for page in result['raw_payload']['pages'])
        if lease:
            settled = await provider_key_rotation_service.complete_success(db, lease, total_tokens=tokens)
            if not settled:
                raise AppException('Quyền sử dụng khóa Nemotron đã hết hiệu lực.',
                                   code='MODEL_KEY_LEASE_LOST', status_code=503)
        return result
    except Exception as exc:
        if lease:
            await provider_key_rotation_service.complete_failure(db, lease, exc)
            settled = True
        raise
    finally:
        if lease and not settled:
            await provider_key_rotation_service.release(db, lease)
