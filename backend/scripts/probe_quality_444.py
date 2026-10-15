"""Live probe of six residual quality groups after the 444 fixes.

Chat route only, fresh fingerprint (code changed vs 443 on purpose). Small set:
six base questions plus paraphrase/history/scope controls. No full 82 run.
Provider timeouts are recorded as infrastructure errors, never as answers.
"""

import argparse
import asyncio
import hashlib
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionFactory, engine
from app.modules.modelops.models import LLMUsageLog
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.retriever import hybrid_retriever
from scripts.evaluate_admissions_412 import save_result

CASES = [
    {"id": 6, "question": "Năm 2026 Trường có bao nhiêu ngành/chương trình tuyển sinh?"},
    {"id": 9, "question": "Năm 2026 QNU có những phương thức xét tuyển nào?"},
    {"id": 13, "question": "Ngành sư phạm có xét ĐGNL Trường ĐHSP Hà Nội không?"},
    {"id": 25, "question": "Năm 2026 môn tiếng Anh ở Ngôn ngữ Anh/Sư phạm Tiếng Anh có nhân hệ số 2 không?"},
    {"id": 62, "question": "Có công thức quy đổi chung để tự tính không?"},
    {"id": 75, "question": "Đăng ký xét bổ sung ở đâu?"},
    {"id": 1006, "question": "Cho biết số ngành đào tạo mà Trường tuyển sinh năm 2026?"},
    {"id": 1013, "question": "Các ngành đào tạo giáo viên có dùng điểm ĐGNL của ĐHSP Hà Nội để xét tuyển 2026 không?"},
    {"id": 1025, "question": "Môn tiếng Anh có được nhân đôi khi xét tuyển Ngôn ngữ Anh năm 2026 không?"},
    {"id": 1075, "question": "Muốn đăng ký xét tuyển bổ sung năm 2026 thì đăng ký ở đâu?"},
    {"id": 1066, "question": "Có thể lấy điểm chuẩn 2025 để khẳng định đậu 2026 không?"},
    {"id": 1113, "question": "Ngành Giáo dục Mầm non có xét ĐGNL Trường ĐHSP Hà Nội không?"},
]


async def evaluate(args):
    output = Path(args.output)
    code_files = sorted([*Path("app/modules/rag").glob("evidence_*.py"),
        Path("app/core/evidence_policy.py"), Path("app/modules/rag/service.py"),
        Path("app/modules/rag/router.py"), Path("app/modules/rag/schemas.py")])
    code_fingerprint = hashlib.sha256(b"".join(p.read_bytes() for p in code_files)).hexdigest()
    report = {"started_at": datetime.now(UTC).isoformat(), "cases": CASES, "results": [],
        "method": "Targeted probe only; statuses are not accuracy."}
    report["code_fingerprint"] = code_fingerprint
    async with httpx.AsyncClient(timeout=130, trust_env=False) as client:
        response = await client.get(args.base + "/assistants/admissions")
        response.raise_for_status()
        assistant = response.json()
        report["assistant"] = {"collection_id": assistant["collection_id"],
            "tenant_id": assistant["tenant_id"], "updated_at": assistant["updated_at"]}
        async with AsyncSessionFactory() as db:
            snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
                db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
            blocks = await load_published_blocks(db, snapshot)
            report["publication"] = {"fingerprint": snapshot.cache_fingerprint(),
                "sources": sorted({b.source_revision_id for b in blocks})}
        save_result(output, report)
        for case in CASES:
            start = time.monotonic()
            conversation = f"eval444_{uuid.uuid4().hex[:16]}"
            item = {"id": case["id"], "question": case["question"],
                    "route": "chat", "conversation_id": conversation}
            try:
                result = await client.post(args.base + "/assistants/admissions/chat",
                    json={"message": case["question"], "conversation_id": conversation})
                item.update(http=result.status_code, response=result.json())
            except Exception as exc:
                item.update(error=f"{type(exc).__name__}: {exc}", failure_kind="infrastructure")
            item["elapsed_seconds"] = round(time.monotonic() - start, 2)
            try:
                async with AsyncSessionFactory() as db:
                    usage = (await db.execute(select(LLMUsageLog).where(
                        LLMUsageLog.conversation_id == conversation))).scalars().all()
                    item["served_models"] = [{"provider": u.provider, "model": u.model_name,
                        "fallback": u.is_fallback, "status": u.status} for u in usage]
            except Exception as exc:
                item["usage_error"] = repr(exc)[:200]
            decision = (item.get("response") or {}).get("answer_decision") or {}
            print(json.dumps({"id": case["id"], "http": item.get("http"),
                "status": decision.get("status"), "reason": decision.get("reason"),
                "missing": decision.get("missing_constraints"),
                "error": item.get("error")}, ensure_ascii=True), flush=True)
            report["results"].append(item)
            save_result(output, report)
        final = await client.get(args.base + "/assistants/admissions")
        final.raise_for_status()
        report["configuration_unchanged"] = final.json()["updated_at"] == assistant["updated_at"]
        async with AsyncSessionFactory() as db:
            final_snapshot = await hybrid_retriever.resolve_retrieval_snapshot(
                db, assistant["collection_id"], tenant_id=assistant["tenant_id"])
            report["publication_unchanged"] = final_snapshot.cache_fingerprint() == snapshot.cache_fingerprint()
        report["finished_at"] = datetime.now(UTC).isoformat()
        save_result(output, report)
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="storage/admissions_eval444_probe6.json")
    parser.add_argument("--base", default="http://localhost:8001/platform/v1alpha1")
    asyncio.run(evaluate(parser.parse_args()))
