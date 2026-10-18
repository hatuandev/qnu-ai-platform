"""Opt-in, internal-only retrieval comparison. No generation/config/index writes."""

import argparse
import asyncio
import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.core.retrieval_policy import configured_policy
from app.modules.rag.retriever import hybrid_retriever


async def fingerprints(db, collection_id: str, assistant: str) -> dict:
    row = (await db.execute(text("""SELECT
        (SELECT md5(config::text) FROM assistants WHERE code=:assistant) AS assistant,
        (SELECT md5(coalesce(collection_metadata::text,'')) FROM knowledge_collections WHERE id=:c) AS metadata,
        (SELECT md5(coalesce(string_agg(id || ':' || coalesce(active_index_revision_id,'') || ':' || status, ',' ORDER BY id),''))
         FROM knowledge_bindings WHERE collection_id=:c) AS publication"""), {"c": collection_id, "assistant": assistant})).mappings().one()
    return dict(row)


async def main(args) -> None:
    if not args.live:
        raise SystemExit("Use --live for internal-only retrieval; this does not run LLM answer generation.")
    questions = re.findall(r"^(\d+)\.\s+(.+)$", args.questions.read_text(encoding="utf-8"), re.MULTILINE)[:args.limit]
    if not questions:
        raise SystemExit("No numbered questions found.")
    original_send = httpx.AsyncClient.send

    async def internal_send(client, request, *a, **kw):
        if request.url.host not in {"100.105.13.53", "127.0.0.1", "localhost"}:
            raise RuntimeError("INTERNAL_ONLY_DIAGNOSTIC_EGRESS_BLOCKED")
        return await original_send(client, request, *a, **kw)

    report = {"kind": "retrieval_only", "generation": "NOT_RUN", "correctness": "NOT_SCORED",
              "quality_warning": "No reviewed gold IDs; hit count is not accuracy. Sequential calls, cache effects uncontrolled.",
              "results": []}
    async with AsyncSessionFactory() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        record = (await db.execute(text("SELECT collection_id,config FROM assistants WHERE code=:code"), {"code": args.assistant})).mappings().one()
        collection_id = record["collection_id"]
        before = await fingerprints(db, collection_id, args.assistant)
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, collection_id)
        report["snapshot"] = snapshot.cache_fingerprint()
        policy = configured_policy({"knowledge_policy": {"retrieval_policy": {"profile": "configured",
            "dense_top_k": 30, "lexical_top_k": 30, "fusion_top_k": 30, "context_top_k": 5}}})
        reranker = (record["config"].get("knowledge_policy") or {}).get("reranker_policy")
        with patch.object(httpx.AsyncClient, "send", internal_send):
            for qid, question in questions:
                for profile in ("legacy", "configured"):
                    trace = {}
                    try:
                        hits = await asyncio.wait_for(hybrid_retriever.retrieve(db, collection_id, question,
                            top_k=12, rerank_top_k=5, snapshot=snapshot, reranker_policy=reranker,
                            retrieval_policy=policy if profile == "configured" else None,
                            diagnostics=trace), timeout=45)
                        degraded = bool(trace.get("degradations")) or trace.get("rerank_scores_observed") is False
                        result = {"id": qid, "profile": profile, "status": "degraded" if degraded else "completed",
                            "trace": trace, "ranked_ids": [h.chunk_id for h in hits],
                            "provenance": [{"binding": h.binding_id, "index": h.index_revision_id} for h in hits]}
                    except Exception as exc:
                        result = {"id": qid, "profile": profile, "status": "error", "error_type": type(exc).__name__,
                            "error_code": getattr(exc, "code", None), "trace": trace}
                    report["results"].append(result)
                    print(json.dumps({"id": qid, "profile": profile, "status": result["status"],
                        "count": trace.get("returned_count"), "total_ms": trace.get("total_ms")}), flush=True)
                    if result["status"] != "completed":
                        report["stopped_on_infrastructure"] = True
                        break
                if report.get("stopped_on_infrastructure"):
                    break
        after = await fingerprints(db, collection_id, args.assistant)
        report["unchanged"] = {k: value == after[k] for k, value in before.items()}
        report["question_set_hash"] = hashlib.sha256(json.dumps(questions, ensure_ascii=False).encode()).hexdigest()
        await db.rollback()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"completed_records": len(report["results"]), "expected_records": len(questions) * 2,
                      "unchanged": report["unchanged"]}), flush=True)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--assistant", default="admissions")
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 83))
    parser.add_argument("--questions", type=Path, default=Path("../docs/kiem_thu/82_cau_hoi_chatbot_tuyen_sinh.md"))
    parser.add_argument("--output", type=Path, default=Path("storage/retrieval_489/comparison.json"))
    asyncio.run(main(parser.parse_args()))
