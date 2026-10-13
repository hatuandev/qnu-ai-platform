"""Validate local batch originals using real parsers/ModelOps, without changing sources."""

import asyncio
import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.services.source_artifact import add_layout_issues, build_source_artifact
from app.modules.knowledge.services.source_extraction import extract_source
from app.modules.knowledge.services.source_pages import normalize_source_pages

ROOT = Path(__file__).resolve().parents[2]
BATCH = "imp_batch_dc04584eee1f"


async def validate(row: dict, slots: asyncio.Semaphore) -> dict:
    async with slots, AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        file = ROOT / "docs/tai_lieu/tuyen_sinh" / row["origin_file_name"]
        content = await asyncio.to_thread(file.read_bytes)
        result = {"file": file.name, "original_status": row["status"]}
        print(json.dumps({"checking": file.name}, ensure_ascii=False), flush=True)
        if hashlib.sha256(content).hexdigest() != row["origin_file_hash"]:
            return {**result, "error": "ORIGINAL_HASH_MISMATCH"}
        try:
            extraction = await extract_source(db, content, file.name, file.suffix, "standard", None, row["tenant_id"])
            md, manifest = normalize_source_pages(extraction.raw_text, extraction.page_count, extraction.pages)
            artifact = build_source_artifact(md, extraction.page_count, {}, extraction.canonical_tables)
            add_layout_issues(artifact, extraction.pages)
            result.update(engine=extraction.engine_used, pages=extraction.page_count, chars=len(md),
                          tables=len(artifact["tables"]), facts=len(artifact["facts"]), issues=artifact["issues"],
                          blank_pages=[p["page"] for p in manifest if p.get("content_status") == "blank"])
        except Exception as exc:
            result.update(error=getattr(exc, "code", type(exc).__name__), detail=str(exc)[:300])
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if "error" not in result:
            result["evidence"] = {"markdown": md, "pages": extraction.pages, "parser_tables": extraction.canonical_tables}
        return result


async def main() -> None:
    report = ROOT / "backend/storage/ingestion389_corpus_final_report.json"
    if "--analyze" in sys.argv:
        results = json.loads(report.read_text(encoding="utf-8"))
        for result in results:
            evidence = result.get("evidence")
            if not evidence:
                continue
            artifact = build_source_artifact(evidence["markdown"], result["pages"], {}, evidence["parser_tables"])
            add_layout_issues(artifact, evidence["pages"])
            result.update(issues=artifact["issues"], facts=len(artifact["facts"]), tables=len(artifact["tables"]), artifact_version=artifact["version"])
        report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"total": len(results), "errors": sum("error" in r for r in results), "review": [{"file": r["file"], "reasons": sorted({issue["code"] for issue in r.get("issues", [])})} for r in results if r.get("issues")]}, ensure_ascii=False))
        return
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        rows = (await db.execute(text("SELECT i.origin_file_name,i.origin_file_hash,i.status,b.tenant_id FROM knowledge_import_items i JOIN knowledge_import_batches b ON b.id=i.batch_id WHERE i.batch_id=:batch ORDER BY i.created_at,i.id"), {"batch": BATCH})).mappings().all()
    slots = asyncio.Semaphore(1)
    results = await asyncio.gather(*(validate(dict(row), slots) for row in rows))
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"total": len(results), "errors": sum("error" in r for r in results), "review": sum(bool(r.get("issues")) for r in results)}))
    await engine.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
