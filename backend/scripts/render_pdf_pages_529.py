"""Render selected PDF pages to PNG for visual verification; local pymupdf only, no model calls."""

import argparse
import asyncio
import json
from pathlib import Path

import pymupdf

from app.core.database import AsyncSessionFactory, engine
from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeSourceRevision

OUT = Path("storage/qnu529/pages")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--page", action="append", type=int, required=True)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionFactory() as db:
        revision = await db.get(KnowledgeSourceRevision, args.revision)
        snapshot = revision.snapshot_storage_path
    content = await storage_service.get(snapshot)
    document = pymupdf.open(stream=content, filetype="pdf")
    matrix = pymupdf.Matrix(args.dpi / 72, args.dpi / 72)
    for number in args.page:
        page = document[number - 1]
        path = OUT / f"{args.revision}_p{number:02d}.png"
        path.write_bytes(page.get_pixmap(matrix=matrix).tobytes("png"))
        print(json.dumps({"page": number, "png": str(path), "size": path.stat().st_size}))
    document.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
