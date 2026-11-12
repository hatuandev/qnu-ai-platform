"""Read-only V1 startup probes. Never calls models, migrates or seeds data."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backendV1"))
sys.path.insert(0, str(ROOT / "scripts"))

from v1_storage import check_storage

if TYPE_CHECKING:
    from qnu.platform.config import Settings


async def check_redis(url: str) -> tuple[bool, str]:
    client = Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    try:
        ok = await asyncio.wait_for(client.ping(), timeout=3)
        return bool(ok), "Redis PING" if ok else "Redis did not return PONG"
    except (RedisError, OSError, TimeoutError, ValueError):
        return (
            False,
            "Redis unavailable; check REDIS_URL and start the configured Redis service",
        )
    finally:
        await client.aclose()


async def check_database(url: str, head: str) -> tuple[bool, str]:
    engine = create_async_engine(url, connect_args={"timeout": 2, "command_timeout": 2})
    try:
        async with engine.connect() as connection:
            version_exists = await connection.scalar(
                text(
                    "SELECT to_regclass('public.alembic_version_backendv1') IS NOT NULL"
                )
            )
            if not version_exists:
                return (
                    False,
                    "PostgreSQL connected; V1 schema not initialized. Run make v1-migrate to create V1 tables",
                )
            current = await connection.scalar(
                text("SELECT version_num FROM alembic_version_backendv1")
            )
        if current != head:
            return (
                False,
                (
                    f"V1 schema revision {current} differs from this build's {head}; "
                    "check v1-db-check, then run v1-migrate if the database is behind "
                    "or update SCHEMA_HEAD if the database is ahead"
                ),
            )
        return True, "PostgreSQL connected and V1 schema current"
    except (SQLAlchemyError, OSError, TimeoutError):
        return (
            False,
            "PostgreSQL or V1 schema unavailable; check DATABASE_URL and v1-db-check",
        )
    finally:
        await engine.dispose()


async def check_qdrant(url: str) -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
            response = await client.get(url.rstrip("/") + "/collections")
        return response.status_code == 200, "Qdrant GET /collections"
    except (httpx.HTTPError, httpx.InvalidURL, OSError, ValueError):
        return (
            False,
            "Qdrant unavailable; check QDRANT_URL and the configured vector service",
        )


async def inspect(
    settings: Settings, root: Path, head: str, frontend: str = "frontendV1"
) -> dict[str, tuple[bool, str]]:
    checks = await asyncio.gather(
        check_redis(settings.REDIS_URL),
        check_database(settings.DATABASE_URL, head),
        check_qdrant(settings.QDRANT_URL),
        check_storage(settings),
    )
    results = dict(
        zip(("redis", "postgresql", "qdrant", "storage"), checks, strict=True)
    )
    vite_present = (root / frontend / "node_modules/vite/bin/vite.js").is_file()
    install = (
        "make v1-install-fe" if frontend == "frontendV1" else "npm ci in frontendV2"
    )
    results["frontend"] = (
        vite_present,
        f"Vite installed in {frontend}" if vite_present else f"Run {install} first",
    )
    return results


def main(frontend: str = "frontendV1") -> int:
    try:
        from qnu.domains.operations.recovery.service import HEAD
        from qnu.platform.config import get_settings

        results = asyncio.run(inspect(get_settings(), ROOT, HEAD, frontend))
    except (
        SQLAlchemyError,
        RedisError,
        httpx.HTTPError,
        OSError,
        TimeoutError,
        ValueError,
        TypeError,
        ImportError,
    ):
        # Do not print exceptions: URLs, credentials or provider data may be embedded.
        print("V1 startup check failed; verify the selected .env configuration.")
        return 1
    for name, (ok, detail) in results.items():
        print(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")
    if not all(ok for ok, _ in results.values()):
        print(
            "No API/worker/FE started. Resolve the failed checks above before retrying."
        )
        if not results["redis"][0] or not results["qdrant"][0]:
            print(
                "For local Docker services: open Docker Desktop, then make v1-infra-up."
            )
        if not results.get("storage", (True, ""))[0]:
            print(
                "Storage: run make v1-infra-up for local MinIO; "
                "for remote S3, verify the configured service and bucket permissions."
            )
        print(
            "Remote infrastructure: check the selected configuration. No model inference was checked."
        )
        return 1
    print("Dependency checks passed. This is not a live model or answer-quality check.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend", choices=("frontendV1", "frontendV2"), default="frontendV1"
    )
    raise SystemExit(main(parser.parse_args().frontend))
