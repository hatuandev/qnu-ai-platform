"""Non-secret OCR configuration participates in parse cache identity."""

import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modelops.models import ModelProviderConfig


async def ocr_configuration_fingerprint(db: AsyncSession) -> str:
    config = await db.get(ModelProviderConfig, "system_model_defaults")
    defaults = (config.extra_config or {}).get("defaults", {}) if isinstance(config, ModelProviderConfig) else {}
    routing = {key: value for key, value in defaults.items() if key.startswith("default_ocr_") or key == "ocr_combo_chain"}
    provider_ids = {routing.get("default_ocr_provider_id")}
    provider_ids.update(item.get("provider_id") for item in routing.get("ocr_combo_chain", []) if isinstance(item, dict))
    providers = []
    for provider_id in sorted(str(value) for value in provider_ids if value):
        provider = await db.get(ModelProviderConfig, provider_id)
        if isinstance(provider, ModelProviderConfig):
            providers.append({"id": provider.id, "model": provider.model_name, "timeout": provider.timeout_seconds,
                              "endpoint": (provider.extra_config or {}).get("api_base_url"),
                              "updated_at": str(provider.updated_at)})
    return hashlib.sha256(json.dumps({"routing": routing, "providers": providers}, sort_keys=True).encode()).hexdigest()
