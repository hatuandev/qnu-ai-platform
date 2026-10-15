"""Read-only shape probe: what the conversion engine actually sees from reviewed_fact_blocks.

Session 482 Task A. No writes, no model calls, no reindex, no publication change.
"""

import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.database import AsyncSessionFactory
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.schemas import AskRequest

COLLECTION = "col_admissions"
BINDING = "bnd_e52fd3712ac3"
INDEX_REVISION = "idx_rev_5f5f3f114ca1"
OUTPUT = Path("storage/rag_conversion_482/shape_probe.json")


def serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


async def main() -> None:
    report: dict[str, Any] = {"mode": "read_only_shape_probe", "writes": 0, "model_calls": 0}
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
            db, COLLECTION, tenant_id=None, workspace_id=None)
        report["snapshot"] = {"snapshot_id": snapshot.snapshot_id, "collection_id": snapshot.collection_id,
                              "tenant_id": snapshot.tenant_id, "workspace_id": snapshot.workspace_id,
                              "binding_revisions": dict(snapshot.binding_revisions)}
        report["resolved_binding_revision"] = snapshot.binding_revisions.get(BINDING)
        # The engine pins the snapshot to the single reviewed binding before loading evidence.
        snapshot = snapshot.model_copy(update={"binding_revisions": {BINDING: INDEX_REVISION}})
        blocks = await load_published_blocks(db, snapshot)
        req = AskRequest(question="Score conversion", collection_id=COLLECTION,
                         tenant_id=snapshot.tenant_id, workspace_id=snapshot.workspace_id)
        rows = await reviewed_fact_blocks(db, req, snapshot, QueryPlan(query=req.question), blocks, exhaustive=True)

    report["published_blocks"] = len(blocks)
    report["fact_blocks"] = len(rows)
    report["cells_per_block"] = Counter(len(b.fact_context.get("cells", [])) for b in rows)
    report["fact_context_keys"] = Counter(k for b in rows for k in b.fact_context)
    report["row_context_present"] = sum(1 for b in rows if (b.fact_context.get("row_context") or []))

    def attributes(block) -> set[str]:
        return {cell["attribute"] for cell in block.fact_context.get("cells", [])}

    grid = [b for b in rows if "ĐNL" in attributes(b)]
    mapping = [b for b in rows if "Tổ hợp gốc tương đương" in attributes(b)]
    other = [b for b in rows if b.id not in {x.id for x in (*grid, *mapping)}]
    report["grid_rows"] = len(grid)
    report["mapping_rows"] = len(mapping)
    report["other_fact_blocks"] = len(other)
    report["mapping_row_context"] = [b.fact_context.get("row_context") for b in mapping]
    report["grid_entity_names"] = [b.fact_context.get("entity_name") for b in grid]
    report["grid_attributes"] = sorted({c["attribute"] for b in grid for c in b.fact_context["cells"]})
    report["mapping_full"] = [
        {"block_id": b.id, "entity_name": b.fact_context.get("entity_name"),
         "row_context": b.fact_context.get("row_context"), "page_number": b.page_number,
         "cells": [{"fact_id": c["fact_id"], "attribute": c["attribute"], "value": c["value"]}
                   for c in b.fact_context.get("cells", [])]}
        for b in mapping]
    report["grid_full"] = [
        {"block_id": b.id, "entity_name": b.fact_context.get("entity_name"), "page_number": b.page_number,
         "canonical_hash": b.canonical_hash, "source_revision_id": b.source_revision_id,
         "cells": [{"fact_id": c["fact_id"], "attribute": c["attribute"], "value": c["value"]}
                   for c in b.fact_context.get("cells", [])]}
        for b in grid]
    report["canonical_blocks"] = [
        {"block_id": b.id, "page_number": b.page_number, "start": b.start, "end": b.end, "text": b.text}
        for b in blocks if b.origin == "canonical" and b.page_number in (1, 2)]

    if grid:
        first = grid[0]
        report["grid_row_example"] = {"entity_name": first.fact_context.get("entity_name"),
                                      "page_number": first.page_number, "section": first.section,
                                      "header_context": first.header_context[:300],
                                      "cells": first.fact_context.get("cells")[:3],
                                      "origin": first.origin, "canonical_hash": first.canonical_hash,
                                      "binding_id": first.binding_id,
                                      "index_revision_id": first.index_revision_id,
                                      "source_revision_id": first.source_revision_id,
                                      "scope_years": first.scope_years,
                                      "temporal_scope": first.temporal_scope.model_dump(mode="json")}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(serializable(report), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("grid_attributes", "grid_full", "mapping_full", "canonical_blocks")},
                     ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
