"""Local audit of published evidence coverage; not a runtime vocabulary."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.models import (
    KnowledgeFact,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
)
from app.modules.rag.evidence_blocks import load_published_blocks, rank_blocks
from app.modules.rag.retriever import hybrid_retriever


async def main():
    async with AsyncSessionFactory() as db:
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, "col_admissions", tenant_id="tenant_qnu")
        blocks = await load_published_blocks(db, snapshot)
        records = (await db.execute(select(KnowledgeSourceRevision, KnowledgeIndexRevision).join(
            KnowledgeIndexRevision, KnowledgeIndexRevision.source_revision_v2_id == KnowledgeSourceRevision.id).where(
            KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values())))).all()
        report = {"block_count": len(blocks), "source_details": []}
        facts = (await db.execute(select(KnowledgeFact).where(
            KnowledgeFact.index_revision_id.in_(snapshot.binding_revisions.values()),
            KnowledgeFact.entity_text.ilike("%Mầm%")))).scalars().all()
        report["floor_facts"] = [{"id": f.id, "index": f.index_revision_id, "entity": f.entity_name,
            "attribute": f.attribute_name, "value": f.attribute_value, "raw": f.raw_data} for f in facts]
        for source, index in records:
            text = source.canonical_markdown or ""
            terms = [v for v in ["5.173", "5173", "1,65", "1.65", "13,34", "13.34"] if v in text]
            if terms:
                report["source_details"].append({"source": source.id, "title": (source.snapshot_metadata or {}).get("title"),
                    "head": text[:3500], "manifest": source.citation_metadata, "fact_manifest": index.parity_report,
                    "matches": [{"term": term, "context": text[max(0, text.index(term)-500):text.index(term)+600],
                        "blocks": [b.model_dump() for b in blocks if b.source_revision_id == source.id and term in b.text]}
                        for term in terms]})
        report["ranked_quota"] = [b.model_dump() for b in rank_blocks(blocks,
            ["Tổng chỉ tiêu tuyển sinh đại học chính quy năm 2026 Trường Đại học Quy Nhơn"], 12)]
    Path("storage/evidence417_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"blocks": len(blocks), "sources": len(report["source_details"])}))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
