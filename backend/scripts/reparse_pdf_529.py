"""Operator reparse for PDF sources whose parser defects were fixed in phiên 529.

Reserves derived revisions through the existing service without broker dispatch, then runs
the task inline so the current parser code produces them. Nothing is indexed or published;
new revisions land pending review and old revisions are never overwritten.
"""

import argparse
import asyncio
import json

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.core.redis import get_redis_client
from app.modules.jobs.models import JobRecord
from app.modules.knowledge.models import KnowledgeSourceRevision
from app.modules.knowledge.services.source_reparse import queue_reparse
from app.workers.tasks import task_knowledge_source_reparse


def _requested_engine(recorded: object) -> str | None:
    """Replay the original request: engine_used proves an explicit engine only when it names one."""
    if isinstance(recorded, str) and "+" not in recorded and recorded not in ("auto", "native"):
        return recorded
    return None


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    redis = get_redis_client()
    try:
        async with AsyncSessionFactory() as db:
            plan = []
            for source_id in args.source:
                base = await db.scalar(
                    select(KnowledgeSourceRevision)
                    .where(
                        KnowledgeSourceRevision.binding_id == source_id,
                        KnowledgeSourceRevision.status.in_(("ready", "review_required")),
                    )
                    .order_by(KnowledgeSourceRevision.revision_no.desc())
                )
                if not base:
                    raise ValueError(f"No terminal revision for {source_id}")
                provenance = base.parse_provenance or {}
                plan.append(
                    {
                        "source_id": source_id,
                        "base_revision_id": base.id,
                        "base_revision_no": base.revision_no,
                        "origin_file_hash": base.origin_file_hash,
                        "parser_profile": provenance.get("parser_profile", "standard"),
                        "recorded_engine": provenance.get("ocr_engine"),
                        "requested_engine": _requested_engine(provenance.get("ocr_engine")),
                    }
                )
            print(json.dumps({"plan": plan}, ensure_ascii=True), flush=True)
            if args.dry_run:
                return
            for item in plan:
                revision = await queue_reparse(
                    db,
                    args.collection,
                    item["source_id"],
                    item["parser_profile"],
                    item["requested_engine"],
                    "tenant_qnu",
                    "workspace_qnu",
                    dispatch=False,
                )
                job = await db.scalar(
                    select(JobRecord)
                    .where(
                        JobRecord.job_type == "knowledge_source_reparse",
                        JobRecord.payload["revision_id"].astext == revision.id,
                    )
                    .order_by(JobRecord.created_at.desc())
                    .limit(1)
                )
                print(
                    json.dumps(
                        {
                            "source_id": item["source_id"],
                            "base_revision_id": item["base_revision_id"],
                            "revision_id": revision.id,
                            "revision_no": revision.revision_no,
                            "job_id": job.id,
                        },
                        ensure_ascii=True,
                    ),
                    flush=True,
                )
                try:
                    result = await task_knowledge_source_reparse({"redis": redis}, job.id)
                except Exception as error:
                    print(
                        json.dumps(
                            {
                                "revision_id": revision.id,
                                "status": "failed",
                                "code": getattr(error, "code", type(error).__name__),
                            },
                            ensure_ascii=True,
                        ),
                        flush=True,
                    )
                    continue
                fresh = await db.get(KnowledgeSourceRevision, revision.id)
                await db.refresh(fresh)
                standard = (fresh.snapshot_metadata or {}).get("qnu_markdown") or {}
                print(
                    json.dumps(
                        {
                            "revision_id": fresh.id,
                            "task": result.get("status"),
                            "status": fresh.status,
                            "quality": (fresh.quality_report or {}).get("overall_status"),
                            "standard_status": standard.get("status"),
                            "engine_used": (fresh.parse_provenance or {}).get("ocr_engine"),
                            "origin_file_hash_match": fresh.origin_file_hash == item["origin_file_hash"],
                            "snapshot_match": fresh.snapshot_storage_path
                            == await db.scalar(
                                select(KnowledgeSourceRevision.snapshot_storage_path).where(
                                    KnowledgeSourceRevision.id == item["base_revision_id"]
                                )
                            ),
                        },
                        ensure_ascii=True,
                    ),
                    flush=True,
                )
    finally:
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
