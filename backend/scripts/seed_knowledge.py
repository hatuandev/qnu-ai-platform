"""Persist default official QNU knowledge collections, documents, and chunks into PostgreSQL."""

from __future__ import annotations

import asyncio

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.seeder import seed_default_knowledge


async def main() -> None:
    async with AsyncSessionFactory() as db:
        result = await seed_default_knowledge(db)
        print(f"Seeded knowledge result: {result}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
