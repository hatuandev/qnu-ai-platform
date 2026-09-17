"""Seed the Platform document taxonomy from the versioned Core manifest."""

from __future__ import annotations

import asyncio
import sys

from app.core.database import AsyncSessionFactory
from app.modules.document_types.service import document_types_service


async def seed_document_types() -> None:
    """Idempotently import the qnu-ai-core taxonomy into PostgreSQL."""
    async with AsyncSessionFactory() as db:
        result = await document_types_service.sync_from_catalog(db)
    print(
        f"Seeded taxonomy {result.taxonomy_version}: "
        f"total={result.total}, added={result.added}, updated={result.updated}, "
        f"deactivated={result.deactivated}, skipped={result.skipped}"
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(seed_document_types())
