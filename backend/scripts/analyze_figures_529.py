"""Read-only profile of the drawing items a rebuilt standard still publishes as figure blocks."""

import argparse
import asyncio
import json
from collections import Counter

from app.core.database import AsyncSessionFactory, engine
from app.core.storage import storage_service
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.normalization.qnu_markdown import QnuStructuredDocument
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document


def shape(raw: dict, page_area: float) -> str:
    box = raw.get("rect") or [0, 0, 0, 0]
    items = raw.get("items") or []
    kinds = Counter(item[0] for item in items if isinstance(item, (list, tuple)) and item)
    return json.dumps({
        "rect": [round(v, 1) for v in box],
        "w": round(box[2] - box[0], 1), "h": round(box[3] - box[1], 1),
        "type": raw.get("type"), "width": raw.get("width"), "fill": raw.get("fill"),
        "color": raw.get("color"), "items": len(items), "kinds": dict(kinds),
        "area_pct": round(max(0.0, (box[2] - box[0]) * (box[3] - box[1])) / page_area * 100, 2),
    }, ensure_ascii=False)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--page", type=int)
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    async with AsyncSessionFactory() as db:
        revision = await db.get(KnowledgeSourceRevision, args.revision)
        artifact = (revision.snapshot_metadata or {}).get("qnu_markdown") or {}
        stored = QnuStructuredDocument.model_validate_json(await storage_service.get(artifact["structured_path"]))
        reference = stored.document_meta.get("raw_evidence") or {}
        evidence = json.loads(await storage_service.get(reference["path"]))

    page_area = {(p["native"]["page"]): p["native"]["width"] * p["native"]["height"] for p in evidence["pages"]}
    rebuilt = build_pdf_document(evidence, filename=stored.source.filename, sha256=stored.source.sha256)
    buckets: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for block in rebuilt.blocks:
        if block.type != "figure":
            continue
        page = block.source_locations[0].page
        if args.page and page != args.page:
            continue
        raw = (block.source_data or {}).get("raw") or {}
        box = raw.get("rect") or [0, 0, 0, 0]
        short = min(box[2] - box[0], box[3] - box[1])
        key = ("image" if not raw.get("rect") else f"short={round(short)} items={len(raw.get('items') or [])} "
               f"type={raw.get('type')} fill={'yes' if raw.get('fill') else 'no'}")
        buckets[f"page{page} {key}"] += 1
        samples.setdefault(f"page{page} {key}", []).append(shape(raw, page_area.get(page, 1)))
    for key, count in buckets.most_common(25):
        print(json.dumps({"bucket": key, "count": count, "samples": samples[key][: args.limit]}, ensure_ascii=False))
    print(json.dumps({"total_figures": sum(buckets.values()), "source_sha256_match": rebuilt.source.sha256 == stored.source.sha256}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
