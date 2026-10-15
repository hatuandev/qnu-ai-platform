"""Read-only retrieval diagnosis: no model/OCR calls, no reindex or publication."""

import argparse
import asyncio
import json
import time
from pathlib import Path

from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.modules.rag.facts import fact_layer
from app.modules.rag.query_router import query_classifier
from app.modules.rag.schemas import RetrievalSnapshot
from app.modules.rag.source_rows import load_row_anchors, merge_row_anchors
from scripts.audit_rag_floor_stage1 import fingerprint, inspect_publication, serializable


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"mode": "read_only_retrieval", "model_calls": 0, "cases": []}
    try:
        before = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
        snapshot = RetrievalSnapshot.model_validate(before["snapshot"])
        report["evidence_policy_enabled"] = ((before["configuration"].get("knowledge_policy") or {})
            .get("evidence_policy") or {}).get("enabled", False)
        report["runtime_branch"] = "evidence" if report["evidence_policy_enabled"] else "fact_hybrid"
        report["snapshot"] = snapshot.model_dump()
        async with AsyncSessionFactory() as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            for name in ("Quản lý giáo dục", "Sư phạm Toán học"):
                question = f"Điểm sàn ngành {name} năm 2026 là bao nhiêu?"
                started = time.perf_counter()
                rows = await load_row_anchors(db, snapshot, question)
                analysis = query_classifier.analyze(question, module_code="admissions")
                facts = await fact_layer.lookup_facts(db, snapshot.collection_id, keywords=analysis.keywords,
                    entity_codes=analysis.entity_codes, target_entities=analysis.target_entities, limit=10,
                    tenant_id=snapshot.tenant_id, workspace_id=snapshot.workspace_id,
                    active_index_revision_ids=set(snapshot.binding_revisions.values()), requested_years=[2026])
                report["cases"].append({"question": question, "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "analysis": serializable(analysis), "anchors": serializable(rows),
                    "retained_context": serializable(merge_row_anchors([], rows, 5)),
                    "fact_entities": sorted({fact.entity_name for fact in facts}),
                    "fact_count": len(facts), "untyped_facts_promoted": bool(analysis.fact_attributes),
                    "first_source_is_target": bool(rows and rows[0].binding_id == before["target"]["binding_id"])})
            foreign = snapshot.model_copy(update={"tenant_id": snapshot.tenant_id + "_denied"})
            report["wrong_tenant_empty"] = not await load_row_anchors(db, foreign, report["cases"][0]["question"])
        after = await inspect_publication("admissions", "TB điểm sàn 26.pdf")
        keys = ("configuration_fingerprint", "snapshot_fingerprint", "collection_metadata_fingerprint", "target_data_fingerprint", "inventory")
        report["before"] = {key: fingerprint(before[key]) for key in keys}
        report["after"] = {key: fingerprint(after[key]) for key in keys}
        report["publication_unchanged"] = report["before"] == report["after"]
    finally:
        await engine.dispose()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mode": report["mode"], "model_calls": 0, "publication_unchanged": report["publication_unchanged"],
        "wrong_tenant_empty": report["wrong_tenant_empty"], "cases": [{key: case[key] for key in
            ("question", "latency_ms", "first_source_is_target", "fact_count", "untyped_facts_promoted")} for case in report["cases"]]}, ensure_ascii=True))


if __name__ == "__main__":
    asyncio.run(main())
