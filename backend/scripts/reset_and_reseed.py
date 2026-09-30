"""Script to completely wipe SQL application tables, Qdrant vector collections, and re-seed all platform data with canonical module names."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure UTF-8 for Windows PowerShell output to prevent cp1252 crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Self-bootstrap: if not running inside backend/.venv, re-execute with backend/.venv Python
_backend_dir = Path(__file__).resolve().parent.parent
_venv_python = _backend_dir / ".venv" / "Scripts" / "python.exe"
if not _venv_python.exists():
    _venv_python = _backend_dir / ".venv" / "bin" / "python"

if _venv_python.exists() and Path(sys.executable).resolve() != _venv_python.resolve():
    print(f"[*] Đang chuyển hướng thực thi sang Python của môi trường ảo: {_venv_python}")
    sys.exit(subprocess.call([str(_venv_python), *sys.argv]))

# Ensure backend root is on sys.path
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

try:
    from qdrant_client import AsyncQdrantClient
except ImportError:
    AsyncQdrantClient = None

from sqlalchemy import inspect, select, text

from app.cli import run_db_seed, verify_core_seed_data
from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine
from app.modules.assistants.models import AssistantModel
from app.modules.knowledge.models import KnowledgeCollection, KnowledgeDocument, KnowledgeChunk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reset_and_reseed")


async def reset_sql_tables() -> None:
    """Truncate all public tables except alembic_version."""
    logger.info("=== STEP 1: TRUNCATING POSTGRESQL TABLES ===")
    async with engine.begin() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names(schema="public")
        )
        data_tables = [t for t in tables if t != "alembic_version"]
        logger.info("Found %d data tables to truncate: %s", len(data_tables), data_tables)

        if data_tables:
            quoted_tables = ", ".join(f'"{t}"' for t in data_tables)
            await conn.execute(text(f"TRUNCATE TABLE {quoted_tables} CASCADE;"))
            logger.info("Successfully truncated %d tables.", len(data_tables))


async def reset_qdrant() -> None:
    """Delete all collections in Qdrant Vector DB."""
    logger.info("=== STEP 2: DELETING QDRANT VECTOR COLLECTIONS ===")
    if AsyncQdrantClient is None:
        logger.warning("qdrant_client chưa sẵn sàng, bỏ qua dọn dẹp Qdrant.")
        return
    settings = get_settings()
    client = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    try:
        collections = await client.get_collections()
        existing = [c.name for c in collections.collections]
        logger.info("Found %d Qdrant collections: %s", len(existing), existing)
        for cname in existing:
            await client.delete_collection(cname)
            logger.info("Deleted Qdrant collection: %s", cname)
        logger.info("Qdrant Vector DB is completely empty.")
    except Exception as exc:
        logger.warning("Qdrant collection deletion error: %s", exc)
    finally:
        await client.close()


async def reseed_all() -> None:
    """Run full idempotent database seed."""
    logger.info("=== STEP 3: RUNNING FULL PLATFORM SEED ===")
    seed_result = await run_db_seed(seed_all=True)
    if seed_result != 0:
        logger.error("Platform seed failed with code %d", seed_result)
        raise RuntimeError("Seed failed")
    logger.info("Platform seed completed successfully.")


async def verify_results() -> None:
    """Verify and print new assistant and collection names."""
    logger.info("=== STEP 4: VERIFYING SEEDED ASSISTANTS & COLLECTIONS ===")
    verified = await verify_core_seed_data()
    logger.info("verify_core_seed_data passed: %s", verified)

    async with AsyncSessionFactory() as db:
        # Check Assistants
        assistants = list(
            (await db.execute(select(AssistantModel).order_by(AssistantModel.id))).scalars().all()
        )
        logger.info("--- 5 TRỢ LÝ AI (ASSISTANTS) ---")
        for ast in assistants:
            logger.info("  [%s] Code: %-15s | Name: %s", ast.id, ast.code, ast.name)

        # Check Collections
        collections = list(
            (await db.execute(select(KnowledgeCollection).order_by(KnowledgeCollection.id))).scalars().all()
        )
        logger.info("--- 5 KHO TRI THỨC (KNOWLEDGE COLLECTIONS) ---")
        for col in collections:
            docs_count = (await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.collection_id == col.id)
            )).scalars().all()
            chunks_count = (await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.collection_id == col.id)
            )).scalars().all()
            logger.info("  [%s] Code: %-15s | Docs: %d | Chunks: %d | Name: %s",
                        col.id, col.module_code, len(docs_count), len(chunks_count), col.name)

    # Check Qdrant points
    settings = get_settings()
    client = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    try:
        collections = await client.get_collections()
        logger.info("--- QDRANT VECTOR COLLECTIONS ---")
        for c in collections.collections:
            info = await client.get_collection(c.name)
            logger.info("  Qdrant collection: %s | points_count: %s", c.name, info.points_count)
    finally:
        await client.close()


async def main() -> None:
    await reset_sql_tables()
    await reset_qdrant()
    await reseed_all()
    await verify_results()
    logger.info("=== RESET AND RESEED COMPLETED SUCCESSFULLY! ===")


if __name__ == "__main__":
    asyncio.run(main())
