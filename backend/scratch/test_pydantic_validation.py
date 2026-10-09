import asyncio
import sys

from app.core.database import AsyncSessionFactory
from app.modules.modelops.schemas import ProviderKeyItem
from app.modules.modelops.services.provider_service import provider_service

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def test_validation():
    async with AsyncSessionFactory() as db:
        keys = await provider_service.get_provider_keys(db, "prov_gemini")
        print("Validating with Pydantic ProviderKeyItem:")
        for k in keys:
            item = ProviderKeyItem.model_validate(k)
            print("  Validated OK:", item.model_dump())

if __name__ == "__main__":
    asyncio.run(test_validation())
