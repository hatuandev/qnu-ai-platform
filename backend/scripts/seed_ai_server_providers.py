"""Install only missing AI-server providers; never reset credentials or defaults."""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionFactory
from app.modules.modelops.models import ModelProviderConfig
from app.modules.modelops.services.local_seed_credentials import apply_local_seed_credentials
from app.modules.modelops.services.provider_service import STANDARD_QNU_PROVIDERS


async def seed_ai_server_providers() -> None:
    async with AsyncSessionFactory() as db:
        for preset in STANDARD_QNU_PROVIDERS:
            if preset["id"] not in {"prov_paddleocr_vl", "prov_rtx5090_vllm"}:
                continue
            existing = await db.get(ModelProviderConfig, preset["id"])
            if existing is not None:
                print(f"Preserved provider: {existing.id}")
                continue
            config = ModelProviderConfig(
                id=preset["id"], name=preset["name"], provider_type=preset["provider_type"],
                model_name=preset["model_name"], api_base_url=preset["api_base_url"],
                api_key_encrypted=None, priority=preset["priority"],
                is_active=preset["is_active"], timeout_seconds=preset["timeout_seconds"],
                extra_config=dict(preset["extra_config"]),
            )
            db.add(config)
            await apply_local_seed_credentials(db, config)
            print(f"Installed provider: {preset['id']}")
        await db.commit()
    print("PaddleOCR needs no key. vLLM restores local encrypted bootstrap for new presets if present.")


if __name__ == "__main__":
    asyncio.run(seed_ai_server_providers())
