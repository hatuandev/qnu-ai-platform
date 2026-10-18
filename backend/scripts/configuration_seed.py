"""Capture/preview/restore encrypted config; no reset, seed, or network model calls.

Run from backend: python -m scripts.configuration_seed --help
Restore into migrated, empty configuration tables BEFORE db seed/bootstrap.
"""

import argparse
import asyncio
import json

from app.core.database import engine
from app.core.storage import storage_service
from app.modules.backups.configuration_seed import capture, load, restore


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "restore"])
    parser.add_argument("--actor", required=True)
    parser.add_argument("--path")
    parser.add_argument("--sha256")
    parser.add_argument("--apply", action="store_true", help="Restore only into empty config tables; default is preview")
    args = parser.parse_args()
    if args.action == "capture" and (args.apply or args.path or args.sha256):
        parser.error("capture does not accept restore options")
    if args.action == "restore" and (not args.path or not args.sha256):
        parser.error("restore requires --path and --sha256")
    try:
        async with asyncio.timeout(90):
            if args.action == "capture":
                result = await capture(engine, storage_service, args.actor)
            else:
                payload = await load(storage_service, args.path, args.sha256)
                result = await restore(engine, payload, actor=args.actor, apply=args.apply)
            print(json.dumps(result, ensure_ascii=True))
    except Exception as error:
        # Never print SQL/connection strings/row data or encrypted secrets.
        print(json.dumps({"error": getattr(error, "code", type(error).__name__)}, ensure_ascii=True))
        raise SystemExit(1) from None
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
