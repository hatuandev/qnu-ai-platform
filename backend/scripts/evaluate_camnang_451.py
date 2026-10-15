"""Sequential live handbook evaluation; only normal chat/audit records are written."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
from qdrant_client import models as qmodels
from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.knowledge.models import (
    KnowledgeFact,
    KnowledgeIndexRevision,
    KnowledgeSourceRevision,
    KnowledgeVectorGeneration,
)
from app.modules.modelops.models import LLMUsageLog
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.retriever import hybrid_retriever
from app.modules.rag.vector_indexer import vector_indexer
from scripts.evaluate_admissions_412 import save_result
from scripts.evaluate_camnang_447 import CASES as PREVIOUS_CASES
from scripts.evaluate_camnang_447 import runtime_fingerprint

CASES = PREVIOUS_CASES + [
    {"id": 2101, "question": "Theo cẩm nang tuyển sinh năm 2025, Trường Đại học Quy Nhơn tuyển bao nhiêu chỉ tiêu?"},
    {"id": 2102, "question": "Cẩm nang tuyển sinh QNU năm 2025 nêu những phương thức xét tuyển nào?"},
    {"id": 2103, "question": "Năm 2025 các ngành sư phạm của QNU có xét học bạ không?"},
    {"id": 2104, "question": "Năm 2025 các ngành sư phạm của QNU có xét kết quả ĐGNL ĐHQG TP.HCM không?"},
    {"id": 2105, "question": "Năm 2025 ngành Giáo dục Mầm non của QNU xét tuyển bằng tổ hợp môn nào?"},
    {"id": 2106, "question": "Năm 2025 ngành Giáo dục Thể chất của QNU có những tổ hợp môn xét tuyển nào?"},
    {"id": 2107, "question": "Năm 2025 ngành Ngôn ngữ Trung Quốc của QNU có những tổ hợp môn xét tuyển nào?"},
    {"id": 2108, "question": "Theo cẩm nang năm 2025, ngành Khoa học vật liệu có mã ngành nào, học bao lâu và được cấp bằng gì?"},
    {"id": 2109, "question": "Theo cẩm nang tuyển sinh 2025, sinh viên Sư phạm Toán học có những cơ hội học bổng nào?"},
    {"id": 2110, "question": "Theo cẩm nang tuyển sinh 2025, ngành Công nghệ kỹ thuật ô tô có những đối tác tuyển dụng nào?"},
    {"id": 2111, "question": "Cẩm nang tuyển sinh QNU năm 2025 ghi số điện thoại, email và website tư vấn tuyển sinh nào?"},
    {"id": 2112, "question": "Năm 2026 ngành Kỹ thuật phần mềm của QNU học bao lâu và có những cơ hội việc làm nào?"},
    {"id": 2113, "question": "Năm 2026 ngành Sư phạm Toán học của QNU học bao lâu và ra trường có thể làm công việc gì?"},
    {"id": 2114, "question": "Theo cẩm nang tuyển sinh 2025, ngành Kỹ thuật phần mềm có đảm bảo 100% sinh viên có việc làm sau tốt nghiệp không?"},
]


async def publication_audit(assistant: dict, file_hash: str) -> tuple[dict, object]:
    async with AsyncSessionFactory() as db:
        snapshot = await hybrid_retriever.resolve_retrieval_snapshot(db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
        blocks = await load_published_blocks(db, snapshot)
        records = (await db.execute(select(KnowledgeSourceRevision, KnowledgeIndexRevision).join(
            KnowledgeIndexRevision, KnowledgeIndexRevision.source_revision_v2_id == KnowledgeSourceRevision.id).where(
            KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values())))).all()
        matched = []
        for source, index in records:
            if source.origin_file_hash != file_hash:
                continue
            facts = (await db.execute(select(KnowledgeFact).where(KnowledgeFact.index_revision_id == index.id))).scalars().all()
            generation = await db.get(KnowledgeVectorGeneration, index.vector_generation_id)
            conditions = [qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=value)) for key,value in {
                "index_revision_id":index.id, "tenant_id":snapshot.tenant_id, "workspace_id":snapshot.workspace_id,
                "collection_id":snapshot.collection_id, "is_retrievable":True}.items()]
            count = await vector_indexer.client.count(collection_name=generation.qdrant_collection_name,
                count_filter=qmodels.Filter(must=conditions), exact=True)
            selected = [block for block in blocks if block.source_revision_id == source.id]
            matched.append({"source":source.id, "binding":index.binding_id, "index":index.id,
                "title":(source.snapshot_metadata or {}).get("title"), "origin_hash":source.origin_file_hash,
                "canonical_hash":source.canonical_hash, "canonical_chars":len(source.canonical_markdown or ""),
                "source_status":source.status, "index_status":index.status, "chunk_count":index.chunk_count,
                "fact_count":len(facts), "fact_years":dict(Counter(str(f.applicability_year) for f in facts)),
                "qdrant_retrievable_points":count.count, "parity":index.parity_report,
                "block_count":len(selected), "year_scopes":dict(Counter(
                    (b.temporal_scope.status + ":" + b.temporal_scope.role) for b in selected)),
                "heading_samples":[{"text":b.text[:160],"section":b.section,"parent":b.parent_id,"page":b.page_number}
                    for b in selected if any(word in b.text for word in ("SƯ PHẠM TOÁN HỌC","KỸ THUẬT PHẦN MỀM","GIỚI THIỆU"))][:12]})
        sources = list({b.source_revision_id:{"source":b.source_revision_id,"title":b.title,
            "binding":b.binding_id,"index":b.index_revision_id,"hash":b.canonical_hash} for b in blocks}.values())
    return {"snapshot":snapshot.model_dump(mode="json"),"fingerprint":snapshot.cache_fingerprint(),
            "sources":sources,"matched_handbook":matched}, snapshot


async def run(args: argparse.Namespace) -> None:
    cases = [case for case in CASES if not args.case_ids or case["id"] in args.case_ids]
    report = {"started_at":datetime.now(UTC).isoformat(),"cases":cases,"results":[],
        "method":"Sequential fresh chat questions; no expected answers sent; statuses are not accuracy.",
        "code_fingerprint":runtime_fingerprint(),"file_hash":hashlib.sha256(args.document.read_bytes()).hexdigest()}
    url = "http://localhost:8001/platform/v1alpha1/assistants/admissions"
    try:
        async with httpx.AsyncClient(timeout=140,trust_env=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            assistant = response.json()
            report["assistant"] = {key:assistant[key] for key in ("collection_id","tenant_id","updated_at")}
            report["configuration_fingerprint"] = hashlib.sha256(json.dumps(assistant["config"],sort_keys=True).encode()).hexdigest()
            report["model_policy"] = assistant["config"].get("model_policy")
            report["evidence_policy"] = (assistant["config"].get("knowledge_policy") or {}).get("evidence_policy")
            report["publication"], snapshot = await publication_audit(assistant, report["file_hash"])
            save_result(args.output,report)
            print(json.dumps({"preflight":report["publication"]["matched_handbook"],
                "sources":len(report["publication"]["sources"])},ensure_ascii=False),flush=True)
            if not report["publication"]["matched_handbook"]:
                raise ValueError("The supplied handbook file hash is not in the published retrieval snapshot")
            if args.preflight_only:
                return
            for case in cases:
                conversation = args.prefix + "_" + uuid.uuid4().hex[:16]
                item = {**case,"route":"chat","conversation_id":conversation}
                started = time.monotonic()
                try:
                    response = await client.post(url + "/chat",json={"message":case["question"],"conversation_id":conversation})
                    item.update(http=response.status_code,response=response.json())
                except httpx.HTTPError as exc:
                    item.update(error=f"{type(exc).__name__}: {exc}",failure_kind="infrastructure")
                item["elapsed_seconds"] = round(time.monotonic()-started,2)
                async with AsyncSessionFactory() as db:
                    usage = (await db.execute(select(LLMUsageLog).where(LLMUsageLog.conversation_id==conversation))).scalars().all()
                item["served_models"] = [{"model":u.model_name,"provider":u.provider,"fallback":u.is_fallback,
                    "status":u.status,"prompt_tokens":u.prompt_tokens,"completion_tokens":u.completion_tokens,
                    "latency_ms":u.latency_ms} for u in usage]
                report["results"].append(item)
                save_result(args.output,report)
                decision = (item.get("response") or {}).get("answer_decision") or {}
                print(json.dumps({"id":case["id"],"http":item.get("http"),"decision":decision.get("status"),
                    "reason":decision.get("reason"),"historical":decision.get("historical_reference"),
                    "seconds":item["elapsed_seconds"]},ensure_ascii=False),flush=True)
                if item.get("error") or item.get("http",0)>=500:
                    report["interruption_reason"]="Infrastructure failed; remaining questions not attempted."
                    break
            final = await client.get(url)
            final.raise_for_status()
            report["configuration_unchanged"] = hashlib.sha256(json.dumps(final.json()["config"],sort_keys=True).encode()).hexdigest()==report["configuration_fingerprint"]
            async with AsyncSessionFactory() as db:
                after = await hybrid_retriever.resolve_retrieval_snapshot(db,assistant["collection_id"],tenant_id=assistant["tenant_id"])
            report["publication_unchanged"] = after.cache_fingerprint()==snapshot.cache_fingerprint()
            report["code_unchanged"] = runtime_fingerprint()==report["code_fingerprint"]
            report["finished_at"] = datetime.now(UTC).isoformat()
            save_result(args.output,report)
    except Exception as exc:
        report["error"]=f"{type(exc).__name__}: {exc}"
        save_result(args.output,report)
        raise
    finally:
        await engine.dispose()


if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--document",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=Path("storage/admissions_eval451_camnang20.json"))
    parser.add_argument("--preflight-only",action="store_true")
    parser.add_argument("--case-ids",type=int,nargs="*")
    parser.add_argument("--prefix",default="eval451")
    asyncio.run(run(parser.parse_args()))
