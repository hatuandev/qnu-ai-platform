"""Local operator read-only inventory; no model call, reset, backup password or publication."""

import argparse
import asyncio
import json
from uuid import uuid4

from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.core.storage import storage_service
from app.modules.knowledge.services.migration_inventory import build_inventory


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--save-report", action="store_true")
    args = parser.parse_args()
    try:
        async with asyncio.timeout(45), AsyncSessionFactory() as db:
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            report = await build_inventory(db, args.collection)
        if args.save_report:
            path = f"snapshots/migration-inventory/{uuid4().hex}.json"
            data = json.dumps(report, ensure_ascii=False, sort_keys=True).encode()
            await storage_service.save(path, data)
            if await storage_service.get(path) != data:
                raise ValueError("Inventory readback failed")
            print(json.dumps({"report_path": path, "collection_id": args.collection,
                "bindings": len(report["bindings"]), "revisions": len(report["revisions"]),
                "source_format_counts": report["source_format_counts"], "busy_jobs": len(report["busy_jobs"]),
                "backup_verified": False, "purge_authorized": False}, ensure_ascii=True))
        else:
            print(json.dumps(report, ensure_ascii=True))
    except Exception as error:
        print(json.dumps({"status": "failed", "code": getattr(error, "code", type(error).__name__)}))
        raise SystemExit(1) from None
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
