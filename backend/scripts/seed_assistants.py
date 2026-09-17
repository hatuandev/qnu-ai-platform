"""Persist the official QNU assistant and workflow templates."""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionFactory, engine
from app.modules.assistants.seeder import seed_standard_assistants


async def main() -> None:
    async with AsyncSessionFactory() as db:
        result = await seed_standard_assistants(db)
        print(result.model_dump_json(indent=2))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
