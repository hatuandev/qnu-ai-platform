"""Read-only raw span/hash verification for a pinned live evaluation report."""

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from app.core.database import AsyncSessionFactory, engine
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_facts import reviewed_fact_blocks
from app.modules.rag.evidence_schemas import QueryPlan
from app.modules.rag.evidence_validation import validate_decision_integrity
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot


async def verify_report(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    snapshot = RetrievalSnapshot.model_validate(report["publication"]["snapshot"])
    try:
        async with AsyncSessionFactory() as db:
            blocks = await load_published_blocks(db, snapshot)
        statuses, failures = Counter(), []
        checked = 0
        checked_facts = 0
        for item in report["results"]:
            response = item.get("response") or {}
            decision = response.get("answer_decision") or {}
            statuses[decision.get("status") or f"http_{item.get('http')}"] += 1
            citations = response.get("citations") or []
            fact_blocks = []
            if any(citation.get("evidence_origin") == "reviewed_fact" for citation in citations):
                async with AsyncSessionFactory() as fact_db:
                    fact_blocks = await reviewed_fact_blocks(fact_db, AskRequest(question=item["question"],
                        collection_id=snapshot.collection_id, tenant_id=snapshot.tenant_id, workspace_id=snapshot.workspace_id),
                        snapshot, QueryPlan.model_validate(decision["requested"]), blocks)
            if decision.get("status") in {"supported", "partial"} and not validate_decision_integrity(
                    decision, response.get("answer", ""), citations):
                failures.append({"id": item["id"], "reason": "decision_integrity"})
            for citation in citations:
                if citation.get("evidence_origin") == "reviewed_fact":
                    valid = any(all(citation.get(key) == getattr(block, key) for key in (
                        "binding_id", "index_revision_id", "source_revision_id", "canonical_hash", "fact_id")) and
                        citation["quote"] == block.text for block in fact_blocks)
                    if not valid:
                        failures.append({"id": item["id"], "reason": "reviewed_fact_identity_or_value"})
                    checked_facts += 1
                    continue
                if citation.get("evidence_origin") != "canonical":
                    failures.append({"id": item["id"], "reason": "noncanonical_requires_fact_verification"})
                    continue
                start, end = citation.get("span_start"), citation.get("span_end")
                valid = isinstance(start, int) and isinstance(end, int) and any(
                    all(citation.get(key) == getattr(block, key) for key in (
                        "binding_id", "index_revision_id", "source_revision_id", "canonical_hash")) and
                    block.start <= start < end <= block.end and
                    block.text[start - block.start:end - block.start] == citation["quote"] for block in blocks)
                if not valid:
                    failures.append({"id": item["id"], "reason": "raw_span_or_hash"})
                checked += 1
        durations = [item["elapsed_seconds"] for item in report["results"]]
        return {"report": str(path), "cases": len(report["results"]), "statuses": dict(statuses),
            "canonical_citations_checked": checked, "failures": failures,
            "reviewed_fact_citations_checked": checked_facts,
            "mean_seconds": round(sum(durations) / max(1, len(durations)), 2),
            "runtime_unchanged": report.get("code_unchanged"),
            "configuration_unchanged": report.get("configuration_unchanged"),
            "publication_unchanged": report.get("publication_unchanged"),
            "workflow_executions": sum(bool((item.get("response") or {}).get("execution_id")) for item in report["results"])}
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    print(json.dumps(asyncio.run(verify_report(parser.parse_args().report)), ensure_ascii=False, indent=2))
