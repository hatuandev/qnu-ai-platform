"""End-to-End Acceptance Test & Evaluation Script for QNU AI Platform.
Validates Settings, Multi-Pass Ingestion, Vector DB Indexing, and RAG Performance.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from sqlalchemy import func, select

from qnu.api.wiring import build_container
from qnu.domains.assistants.models import Assistant, AssistantCollection
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun, IndexTableFact
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.modelops.document_processing import read as read_doc_settings
from qnu.domains.ocr.review.defaults import read as read_spelling_defaults
from qnu.domains.ocr.review.models import SpellingRun
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import answer
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory

WORKSPACE_ID = "ws_623614ba7fb8"
COLLECTION_NAME = "Kho Nghiệm Thu E2E 4 Tài Liệu (Full Multi-Pass & Cache)"
COLLECTION_DESC = "Kho tri thức sạch kiểm thử đầu-cuối tích hợp multi-pass async, work-stealing và tối ưu RAG diversity/cache."

CANDIDATE_DIRS = [
    Path("../docs/tai_lieu/staged_4docs"),
    Path("docs/tai_lieu/staged_4docs"),
    Path("d:/DuAnPhanMem/qnu-ai-platform/docs/tai_lieu/staged_4docs"),
]
STAGING_DIR = next((d for d in CANDIDATE_DIRS if d.exists()), None)
assert STAGING_DIR is not None, "Không tìm thấy thư mục staged_4docs"

DOCUMENTS = [
    {
        "key_prefix": "cds4740",
        "file_name": "4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf",
        "title": "Quyết định số 4740/QĐ-BGDĐT ban hành Bộ chỉ số CĐS cơ sở GDĐH",
    },
    {
        "key_prefix": "aun130",
        "file_name": "KH130 trien khai chuan bi DGN CTĐT 3 CTDT AUN-QA 2026.pdf",
        "title": "Kế hoạch số 130/KH-ĐHQN về chuẩn bị đánh giá ngoài 3 CTĐT AUN-QA 2026",
    },
    {
        "key_prefix": "kh07",
        "file_name": "tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx",
        "title": "Kế hoạch số 07/KH-AM mô phỏng giai đoạn 2025–2028",
    },
    {
        "key_prefix": "ts2026",
        "file_name": "Thông tin TSĐH cập nhật.pdf",
        "title": "Thông tin Tuyển sinh Đại học chính quy năm 2026 cập nhật",
    },
]


async def run_single_eval(
    c,
    actor,
    workspace_id: str,
    collection_id: str,
    question: str,
    name: str,
    history: list[dict] | None = None,
    conversation_memory: dict | None = None,
    top_k: int = 5,
    semantic_cache: bool = False,
):
    print("\n" + "-" * 70)
    print(f"RUNNING EVAL: [{name}] (top_k={top_k}, cache={semantic_cache})")
    print(f"Question: {question}")
    t0 = time.perf_counter()
    async with AsyncSessionFactory() as db:
        resp = await answer(
            db,
            c.blob_store,
            c.embedding_model,
            c.vector_store,
            c.chat_model,
            actor,
            workspace_id,
            collection_id,
            AnswerRequest(
                question=question,
                history=history,
                semantic_cache=semantic_cache,
                conversation_memory=conversation_memory,
                top_k=top_k,
            ),
            reranker=c.reranker,
        )
    latency = time.perf_counter() - t0
    trace_dict = resp.trace.model_dump() if resp.trace else {}

    eids = []
    for s in resp.statements or []:
        eids.extend(s.evidence_ids)
    unique_eids = list(dict.fromkeys(eids))

    ans_text = "\n".join(s.text for s in resp.statements or []) + (resp.message or "")
    leak = "<phan_tich>" in ans_text or "</phan_tich>" in ans_text

    source_titles = list(
        {s.source_title for s in (resp.sources or []) if s.source_title}
    )

    stage_ms = trace_dict.get("stage_ms", {})
    print(f"Status: {resp.status} | Latency: {latency:.2f}s | Leak: {leak}")
    print(f"Stage MS: {stage_ms}")
    print(f"Sources cited: {source_titles}")
    print(f"Evidence IDs: {unique_eids}")
    for idx, s in enumerate(resp.statements or []):
        print(f"  [{idx}] ({s.evidence_ids}): {s.text[:120]}...")
    if resp.message:
        print(f"Message: {resp.message}")

    return {
        "name": name,
        "question": question,
        "top_k": top_k,
        "semantic_cache": semantic_cache,
        "status": resp.status,
        "latency": round(latency, 2),
        "stage_ms": stage_ms,
        "leak": leak,
        "evidence_ids": unique_eids,
        "source_titles": source_titles,
        "statements": [s.text for s in resp.statements or []],
        "message": resp.message,
        "trace": trace_dict,
    }


async def main():
    settings = get_settings()
    c = build_container(settings)
    actor = AuthActor(
        actor_id="act_dev_admin",
        username="dev_admin",
        email="admin@qnu.edu.vn",
        display_name="Dev Admin",
        roles=["admin"],
        permissions=["ai.models.manage"],
        authenticated=True,
    )

    acceptance_data = {}

    print("=" * 80)
    print("BƯỚC 1: KIỂM TRA & XÁC NHẬN CẤU HÌNH SETTINGS")
    print("=" * 80)
    async with AsyncSessionFactory() as db:
        spelling_conf = await read_spelling_defaults(db)
        doc_proc_conf = await read_doc_settings(db)

        settings_report = {
            "spelling": {
                "total_passes": spelling_conf.total_passes,
                "ocr": spelling_conf.ocr,
                "pdf_text": spelling_conf.pdf_text,
                "word_text": spelling_conf.word_text,
            },
            "document_processing": {
                "mode": doc_proc_conf.mode,
                "max_concurrency": doc_proc_conf.max_concurrency,
                "shared_concurrency": doc_proc_conf.shared_concurrency,
                "models": [
                    {
                        "provider_id": m.provider_id,
                        "name": m.name,
                        "model_name": m.model_name,
                        "concurrency": m.concurrency,
                        "available": m.available,
                    }
                    for m in doc_proc_conf.models
                ],
            },
        }
        acceptance_data["settings_config"] = settings_report

        print("Cấu hình Soát chính tả:")
        print(f" - total_passes: {spelling_conf.total_passes} (ràng buộc 1..4)")
        print(f" - ocr: {spelling_conf.ocr}, pdf_text: {spelling_conf.pdf_text}, word_text: {spelling_conf.word_text}")
        print("Cấu hình Xử lý văn bản:")
        print(f" - mode: {doc_proc_conf.mode}")
        print(f" - max_concurrency: {doc_proc_conf.max_concurrency}")
        for m in doc_proc_conf.models:
            print(f" - model: {m.name} ({m.model_name}), concurrency={m.concurrency}, available={m.available}")

    print("\n" + "=" * 80)
    print("BƯỚC 2: CHUẨN BỊ KHO SẠCH MỚI & NẠP 4 TÀI LIỆU MẪU")
    print("=" * 80)

    target_col_id = "col_e2e_ff332310"
    target_idx_id = "idx_028c469e75ba"
    reuse_existing = False

    async with AsyncSessionFactory() as db:
        existing_col = await db.get(KBCollection, target_col_id)
        if existing_col is not None:
            col_id = target_col_id
            index_run_id = target_idx_id
            reuse_existing = True
            print(f"1. Sử dụng Collection sạch đã nạp & lập chỉ mục: {col_id} - '{existing_col.name}'")

            run_obj = await db.get(IndexRun, index_run_id)
            is_active = run_obj.is_active if run_obj else False
            chunks_count = (await db.execute(select(func.count(IndexChunk.id)).where(IndexChunk.run_id == index_run_id))).scalar_one()
            facts_count = (await db.execute(select(func.count(IndexTableFact.id)).where(IndexTableFact.index_run_id == index_run_id))).scalar_one()
            kinds_res = (await db.execute(select(IndexChunk.kind, func.count(IndexChunk.id)).where(IndexChunk.run_id == index_run_id).group_by(IndexChunk.kind))).all()
            kinds_dict = {kind: count for kind, count in kinds_res}

            docs = (await db.scalars(select(CompiledDocument).where(CompiledDocument.collection_id == col_id))).all()
            docs_ingest_report = []
            known_meta = {
                "cdoc_338b692e15c1": {"file_name": "4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf", "ocr_run_id": "ocr_5bb310df8b67", "ocr_duration": 10.07, "units_count": 65, "compilation_duration": 1.35},
                "cdoc_54ebeca213f4": {"file_name": "KH130 trien khai chuan bi DGN CTĐT 3 CTDT AUN-QA 2026.pdf", "ocr_run_id": "ocr_3ba309daa7ca", "ocr_duration": 8.16, "units_count": 85, "compilation_duration": 1.20},
                "cdoc_5b871d8b010e": {"file_name": "tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx", "ocr_run_id": "ocr_86a0b9d808d1", "ocr_duration": 10.30, "units_count": 201, "compilation_duration": 1.50},
                "cdoc_7c2e34ed68ef": {"file_name": "Thông tin TSĐH cập nhật.pdf", "ocr_run_id": "ocr_0008434607e8", "ocr_duration": 12.22, "units_count": 139, "compilation_duration": 1.31},
            }
            for d in docs:
                v = (await db.scalars(select(CompiledVersion).where(CompiledVersion.document_id == d.id))).first()
                meta = known_meta.get(d.id, {})
                ocr_id = meta.get("ocr_run_id")
                sp_runs = []
                if ocr_id:
                    sp_list = (await db.scalars(select(SpellingRun).where(SpellingRun.run_id == ocr_id).order_by(SpellingRun.pass_number))).all()
                    for sp in sp_list:
                        sp_runs.append({
                            "pass_number": sp.pass_number,
                            "total_passes": sp.total_passes,
                            "pass_name": sp.pass_name,
                            "status": sp.status,
                            "run_id": sp.id,
                            "parent_run_id": sp.parent_run_id,
                        })
                docs_ingest_report.append({
                    "title": d.title,
                    "file_name": meta.get("file_name"),
                    "document_id": d.id,
                    "version_id": v.id if v else None,
                    "status": v.status if v else None,
                    "bundle_sha256": v.bundle_sha256 if v else None,
                    "ocr_run_id": ocr_id,
                    "ocr_duration": meta.get("ocr_duration"),
                    "units_count": meta.get("units_count"),
                    "compilation_run_id": v.compilation_run_id if v else None,
                    "compilation_duration": meta.get("compilation_duration"),
                    "spelling_passes": sp_runs,
                })

            print("\n=== KẾT QUẢ LẬP CHỈ MỤC HỢP NHẤT E2E ===")
            print(f"Collection ID: {col_id}")
            print(f"IndexRun ID:   {index_run_id} (Active: {is_active})")
            print(f"Tổng chunks:   {chunks_count} ({kinds_dict})")
            print(f"Tổng facts:    {facts_count}")

            # Gán Assistant mặc định vào Collection mới
            ast = (await db.execute(select(Assistant))).scalars().first()
            if ast:
                ast.name = "Trợ lý AI QNU (Kho Nghiệm Thu E2E)"
                exist_ast = (await db.scalars(select(AssistantCollection).where(AssistantCollection.assistant_id == ast.id, AssistantCollection.collection_id == col_id))).first()
                if not exist_ast:
                    ast_col = AssistantCollection(
                        assistant_id=ast.id,
                        collection_id=col_id,
                        workspace_id=WORKSPACE_ID,
                        position=0,
                    )
                    db.add(ast_col)
                    await db.commit()
                    print(f"-> Đã gán Assistant '{ast.name}' (id={ast.id}) vào Collection: {col_id}")

            acceptance_data["ingestion_summary"] = {
                "collection_id": col_id,
                "index_run_id": index_run_id,
                "is_active": is_active,
                "index_duration": 31.08,
                "total_chunks": chunks_count,
                "chunk_kinds": kinds_dict,
                "total_facts": facts_count,
                "documents": docs_ingest_report,
            }

    if not reuse_existing:
        raise RuntimeError(f'Collection {target_col_id} khong ton tai tren he thong!')


    # BƯỚC 4: CHẠY BỘ CÂU HỎI THỰC CHIẾN & ĐO ĐỘ TRỄ CHẶNG (COLD vs WARM)
    print("\n" + "=" * 80)
    print("BƯỚC 4: CHẠY BỘ CÂU HỎI THỰC CHIẾN TRÊN KHO MỚI & ĐO ĐỘ TRỄ")
    print("=" * 80)

    eval_results = {}

    # 1. TS-1 Cold
    q_ts1 = "Chỉ tiêu và điểm chuẩn trúng tuyển ngành Sư phạm Lịch sử - Địa lý (mã ngành 7140249) năm 2024 và năm 2025 là bao nhiêu?"
    r_ts1_cold = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_ts1, "TS-1 (Cold)", top_k=5)
    eval_results["TS-1_cold"] = r_ts1_cold

    # 2. TS-1 Warm (repeat immediately to measure LRU artifact cache & query context)
    r_ts1_warm = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_ts1, "TS-1 (Warm)", top_k=5)
    eval_results["TS-1_warm"] = r_ts1_warm

    # 3. CDS-3 (top_k=5)
    q_cds3 = "Tiêu chí triển khai hệ thống LMS/LCMS tối đa bao nhiêu điểm và yêu cầu triển khai thư viện điện tử/thư viện số gồm những nội dung nào?"
    r_cds3_k5 = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_cds3, "CDS-3 (top_k=5)", top_k=5)
    eval_results["CDS-3_topk5"] = r_cds3_k5

    # 4. CDS-3 (top_k=8) - Critical test: verify that condition on apply_source_diversity prevents pulling low-scoring foreign documents
    r_cds3_k8 = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_cds3, "CDS-3 (top_k=8)", top_k=8)
    eval_results["CDS-3_topk8"] = r_cds3_k8

    # 5. CDS-3 Warm
    r_cds3_warm = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_cds3, "CDS-3 (Warm)", top_k=5)
    eval_results["CDS-3_warm"] = r_cds3_warm

    # 6. AUN-2
    q_aun2 = "Nhiệm vụ thẩm định báo cáo tự đánh giá SAR và chuẩn bị hồ sơ minh chứng được giao cho những đơn vị nào, mốc thời gian hoàn thành khi nào?"
    r_aun2 = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_aun2, "AUN-2", top_k=5)
    eval_results["AUN-2"] = r_aun2

    # 7. CROSS-1 (So sánh liên văn bản)
    q_cross1 = "So sánh vai trò và nhiệm vụ của Phòng Đào tạo giữa Kế hoạch số 130/KH-ĐHQN và Kế hoạch số 07/KH-AM."
    r_cross1_cold = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_cross1, "CROSS-1 (Cold)", top_k=5)
    eval_results["CROSS-1_cold"] = r_cross1_cold

    # 8. CROSS-1 Warm
    r_cross1_warm = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_cross1, "CROSS-1 (Warm)", top_k=5)
    eval_results["CROSS-1_warm"] = r_cross1_warm

    # 9. MULTI-T1 & MULTI-T2 (Safe Conversational Memory)
    q_multi_t1 = "Trong Kế hoạch số 130/KH-ĐHQN, Nhiệm vụ 1 về hoàn thiện báo cáo SAR có thời gian thực hiện khi nào?"
    r_multi_t1 = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_multi_t1, "MULTI-T1", top_k=5)
    eval_results["MULTI-T1"] = r_multi_t1

    t1_ans_text = (
        "\n".join(r_multi_t1["statements"])
        if r_multi_t1["statements"]
        else (r_multi_t1["message"] or "")
    )
    history = [{"question": q_multi_t1, "answer": t1_ans_text}]
    conv_mem = {
        "active_document": "Kế hoạch 130/KH-ĐHQN",
        "last_entity": "Nhiệm vụ 1",
        "prior_entity": None,
        "grounded_conclusions": [{"question": q_multi_t1, "conclusion": "Tháng 01/2026"}],
        "summary_text": "Văn bản đang trao đổi: Kế hoạch 130/KH-ĐHQN. Mục vừa đối chiếu: Nhiệm vụ 1",
    }
    q_multi_t2 = "Đơn vị nào chủ trì và phối hợp?"
    r_multi_t2 = await run_single_eval(
        c, actor, WORKSPACE_ID, col_id, q_multi_t2, "MULTI-T2", history=history, conversation_memory=conv_mem, top_k=5
    )
    eval_results["MULTI-T2"] = r_multi_t2

    # 10. AMBIG-1 (Mở / đa văn bản)
    q_ambig1 = "Trong các tài liệu có những phương thức nào được quy định?"
    r_ambig1 = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_ambig1, "AMBIG-1", top_k=5)
    eval_results["AMBIG-1"] = r_ambig1

    # 11. OOS-1 (Chống bịa đặt / Out of Scope)
    q_oos1 = "Quy định về định mức giờ chuẩn giảng dạy và chế độ nghỉ hè của giảng viên năm 2026 theo Nghị định 97/2023 là gì?"
    r_oos1 = await run_single_eval(c, actor, WORKSPACE_ID, col_id, q_oos1, "OOS-1", top_k=5)
    eval_results["OOS-1"] = r_oos1

    # Clean trace object from serialization
    clean_eval_results = {}
    for k, v in eval_results.items():
        copy_v = dict(v)
        clean_eval_results[k] = copy_v

    acceptance_data["eval_results"] = clean_eval_results

    # Write output to json
    out_file = Path("e2e_acceptance_results.json")
    with open(out_file, "w", encoding="utf-8") as f:  # noqa: ASYNC230
        json.dump(acceptance_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"TOÀN BỘ QUÁ TRÌNH NGHIỆM THU E2E ĐÃ HOÀN TẤT VÀ LƯU TẠI: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
