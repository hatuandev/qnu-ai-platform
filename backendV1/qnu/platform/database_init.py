"""Create the configured PostgreSQL database when missing (deployment bootstrap)."""

from __future__ import annotations

import asyncio
import sys

from asyncpg.exceptions import InvalidCatalogNameError
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from qnu.platform.config import get_settings


async def ensure_database_exists() -> int:
    settings = get_settings()
    url = make_url(settings.DATABASE_URL)
    target_db = url.database

    if not target_db or target_db in {"postgres", "template1"}:
        print(f"database-init: target database is default ({target_db}); ready")
        return 0

    # 1. Probe target database directly
    try:
        engine = create_async_engine(url, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        print(f"database-init: database ready ({target_db})")
        return 0
    except Exception as exc:
        # Check if the failure is because the database does not exist
        orig = getattr(exc, "orig", exc)
        is_missing = isinstance(orig, InvalidCatalogNameError) or "does not exist" in str(exc).lower()
        if not is_missing:
            print(f"database-init: database connection probe failed ({type(exc).__name__}: {exc})", file=sys.stderr)
            return 1

    # 2. Connect to maintenance db (postgres) and create the target database
    print(f"database-init: database '{target_db}' does not exist, creating...")
    for maint_db in ("postgres", "template1"):
        try:
            maint_url = url.set(database=maint_db)
            maint_engine = create_async_engine(maint_url, isolation_level="AUTOCOMMIT")
            async with maint_engine.connect() as conn:
                res = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": target_db},
                )
                if res.scalar() is None:
                    # Escape double quotes in database name to prevent SQL injection
                    safe_name = target_db.replace('"', '""')
                    await conn.execute(text(f'CREATE DATABASE "{safe_name}"'))
                    print(f"database-init: database created successfully ({target_db})")
                else:
                    print(f"database-init: database already exists in pg_database ({target_db})")
            await maint_engine.dispose()
            return 0
        except Exception as maint_exc:
            print(f"database-init: attempt via '{maint_db}' failed ({type(maint_exc).__name__}: {maint_exc})", file=sys.stderr)

    return 1


def main() -> int:
    return asyncio.run(ensure_database_exists())


if __name__ == "__main__":
    raise SystemExit(main())
