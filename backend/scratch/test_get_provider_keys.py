import asyncio
import sys
from app.core.database import AsyncSessionFactory
from app.modules.modelops.services.provider_service import provider_service

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def test_get_keys():
    async with AsyncSessionFactory() as db:
        keys = await provider_service.get_provider_keys(db, "prov_gemini")
        print("Keys returned by get_provider_keys('prov_gemini'):")
        print(f"Total keys: {len(keys)}")
        for k in keys:
            print("  Key:", k)

if __name__ == "__main__":
    asyncio.run(test_get_keys())
