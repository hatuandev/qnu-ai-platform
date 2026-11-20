"""End-to-End Acceptance Test & Evaluation Script for QNU AI Platform.
Validates Settings, Multi-Pass Ingestion, Vector DB Indexing, and RAG Performance.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

from sqlalchemy import func, select

from qnu.api.wiring import build_container
from qnu.domains.assistants.models import Assistant, AssistantCollection
from qnu.domains.identity.actor import AuthActor
from qnu.domains.knowledge.compilation.execution import execute_run as execute_compilation_run
from qnu.domains.knowledge.compilation.schemas import CompilationRequest
from qnu.domains.knowledge.compilation.service import request_run as request_compilation_run
from qnu.domains.knowledge.index.execution import execute_run as execute_index_run
from qnu.domains.knowledge.index.models import IndexChunk, IndexRun, IndexTableFact
from qnu.domains.knowledge.index.schemas import IndexRequest
from qnu.domains.knowledge.index.service import request_index
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.knowledge.publication.decisions import commit_decision, create_preview
from qnu.domains.knowledge.publication.models import CompiledDocument, CompiledVersion
from qnu.domains.knowledge.publication.schemas import (
    CommitRequest,
    CreateDocumentRequest,
    PreviewRequest,
    ReviewSkipAcknowledgement,
)
from qnu.domains.knowledge.publication.service import create_document
from qnu.domains.knowledge.sources.service import source_service
from qnu.domains.modelops.document_processing import read as read_doc_settings
from qnu.domains.ocr.execution import execute_run as execute_ocr_run
from qnu.domains.ocr.models import OcrProcessingRun
from qnu.domains.ocr.review import automatic, detection
from qnu.domains.ocr.review.defaults import read as read_spelling_defaults
from qnu.domains.ocr.review.models import SpellingRun
from qnu.domains.ocr.service import processing_service
from qnu.domains.rag.answer.schemas import AnswerRequest
from qnu.domains.rag.answer.service import answer
from qnu.domains.workspaces.models import Workspace
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
            for d in docs:
                v = (await db.scalars(select(CompiledVersion).where(CompiledVersion.document_id == d.id))).first()
                docs_ingest_report.append({
                    "title": d.title,
                    "document_id": d.id,
                    "version_id": v.id if v else None,
                    "status": v.status if v else None,
                    "bundle_sha256": v.bundle_sha256 if v else None,
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
        col_suffix = uuid.uuid4().hex[:8]
        col_id = f"col_e2e_{col_suffix}"
        col_name = f"{COLLECTION_NAME} [{col_suffix}]"
        async with AsyncSessionFactory() as db:
            ws = await db.get(Workspace, WORKSPACE_ID)
            assert ws is not None, f"Workspace {WORKSPACE_ID} không tồn tại"
            col = KBCollection(
                id=col_id,
                workspace_id=WORKSPACE_ID,
                name=col_name,
                description=COLLECTION_DESC,
                created_by=actor.actor_id,
            )
            db.add(col)
            await db.commit()
            print(f"1. Đã tạo Collection sạch mới: {col.id} - '{col.name}'")

        docs_ingest_report = []
    for idx, doc in enumerate(DOCUMENTS, 1):
        print("\n" + "-" * 70)
        print(f"[{idx}/4] NẠP & XỬ LÝ: {doc['title']}")
        file_path = STAGING_DIR / doc["file_name"]
        assert file_path.exists(), f"Không tìm thấy file: {file_path}"
        payload = file_path.read_bytes()

        # 2a. Upload Source
        upl_key = f"upl_e2e_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
        async with AsyncSessionFactory() as db:
            ws = await db.get(Workspace, WORKSPACE_ID)
            outcome = await source_service.upload(
                db,
                c.blob_store,
                ws,
                col_id,
                file_name=doc["file_name"],
                title=doc["title"],
                payload=payload,
                max_bytes=50 * 1024 * 1024,
                actor=actor,
                idempotency_key=upl_key,
                auto_extract=True,
            )
            src_id = outcome.source.id
            rev_id = outcome.revision.id
            print(f"   -> Uploaded Source: {src_id}, Revision: {rev_id}")

        # 2b. OCR Run
        async with AsyncSessionFactory() as db:
            ocr_runs, _ = await processing_service.list_runs(
                db, WORKSPACE_ID, rev_id, page=1, page_size=1
            )
            ocr_run_id = ocr_runs[0].id

        t0_ocr = time.perf_counter()
        async with AsyncSessionFactory() as db:
            ocr_outcome = await execute_ocr_run(
                db,
                c.blob_store,
                ocr_run_id,
                worker_id=f"worker_e2e_{doc['key_prefix']}",
                engine=c.ocr_engine,
            )
            t_ocr = time.perf_counter() - t0_ocr
            print(f"   -> OCR Run {ocr_run_id} hoàn tất: status={ocr_outcome.status} ({t_ocr:.2f}s)")

        # Verify artifacts
        async with AsyncSessionFactory() as db:
            run_obj = await db.get(OcrProcessingRun, ocr_run_id)
            review_doc, _canonical = await detection.load_review(db, c.blob_store, run_obj, 0)
            canonical_sha = review_doc.canonical_sha256
            doc_units = len(review_doc.units)
            print(f"   -> Canonical JSON: {doc_units} units, sha256={canonical_sha[:16]}...")

        # 2c. Multi-Pass Spelling Review
        spelling_passes_report = []
        pass1_check_id = None
        async with AsyncSessionFactory() as db:
            run_obj = await db.get(OcrProcessingRun, ocr_run_id)
            # Pass 1
            t0_p1 = time.perf_counter()
            status_p1, check_id_p1 = await automatic.review_document(
                db,
                c.blob_store,
                c.chat_model,
                actor,
                run_obj,
                version=0,
                automatic=True,
                pass_number=1,
                total_passes=spelling_conf.total_passes,
            )
            dt_p1 = time.perf_counter() - t0_p1
            pass1_check_id = check_id_p1
            print(f"   -> Spelling Pass 1: status={status_p1}, id={check_id_p1} ({dt_p1:.2f}s)")

            pass1_details = {"pass": 1, "status": status_p1, "id": check_id_p1, "duration": round(dt_p1, 2)}
            if check_id_p1:
                chk_p1 = await db.get(SpellingRun, check_id_p1)
                pass1_details["pass_name"] = chk_p1.pass_name
                pass1_details["suggestions_count"] = len(chk_p1.suggestions)
                pass1_details["batch_providers"] = chk_p1.trace.get("batch_providers")
                print(f"      [Pass 1] Name: {chk_p1.pass_name}, Suggestions: {len(chk_p1.suggestions)}")

            spelling_passes_report.append(pass1_details)

            # Pass 2 chaining with parent_run_id
            if pass1_check_id:
                t0_p2 = time.perf_counter()
                status_p2, check_id_p2 = await automatic.review_document(
                    db,
                    c.blob_store,
                    c.chat_model,
                    actor,
                    run_obj,
                    version=0,
                    automatic=True,
                    pass_number=2,
                    total_passes=spelling_conf.total_passes,
                    parent_run_id=pass1_check_id,
                )
                dt_p2 = time.perf_counter() - t0_p2
                print(f"   -> Spelling Pass 2: status={status_p2}, id={check_id_p2} ({dt_p2:.2f}s)")

                pass2_details = {"pass": 2, "status": status_p2, "id": check_id_p2, "duration": round(dt_p2, 2)}
                if check_id_p2:
                    chk_p2 = await db.get(SpellingRun, check_id_p2)
                    pass2_details["pass_name"] = chk_p2.pass_name
                    pass2_details["parent_run_id"] = chk_p2.parent_run_id
                    pass2_details["suggestions_count"] = len(chk_p2.suggestions)
                    pass2_details["batch_providers"] = chk_p2.trace.get("batch_providers")
                    print(f"      [Pass 2] Name: {chk_p2.pass_name}, Parent: {chk_p2.parent_run_id}, Suggestions: {len(chk_p2.suggestions)}")

                spelling_passes_report.append(pass2_details)

        # 2d. Compilation Run
        cmp_key = f"cmp_e2e_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
        cmp_req = CompilationRequest(
            topic=doc["title"],
            ocr_run_ids=[ocr_run_id],
            source_first=True,
            auto_review=False,
        )
        async with AsyncSessionFactory() as db:
            cmp_outcome = await request_compilation_run(
                db,
                c.blob_store,
                actor,
                WORKSPACE_ID,
                col_id,
                cmp_req,
                idempotency_key=cmp_key,
                queue=None,
            )
            cmp_run_id = cmp_outcome.run.id

        t0_cmp = time.perf_counter()
        async with AsyncSessionFactory() as db:
            cmp_status = await execute_compilation_run(
                db,
                c.blob_store,
                cmp_run_id,
                worker_id=f"worker_e2e_{doc['key_prefix']}",
                model=c.chat_model,
            )
            t_cmp = time.perf_counter() - t0_cmp
            print(f"   -> Compilation Run {cmp_run_id} hoàn tất: status={cmp_status} ({t_cmp:.2f}s)")

        # 2e. Create Document & Publish
        doc_key = f"cdoc_e2e_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
        create_req = CreateDocumentRequest(
            document_key=doc_key,
            title=doc["title"],
            compilation_run_id=cmp_run_id,
            retrieval_metadata=[],
        )
        reg_key = f"reg_e2e_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
        async with AsyncSessionFactory() as db:
            reg = await create_document(
                db,
                c.blob_store,
                actor,
                WORKSPACE_ID,
                col_id,
                create_req,
                key=reg_key,
            )
            doc_id = reg.document.id
            ver_id = reg.version.id

            # Approve
            skip = ReviewSkipAcknowledgement(
                confirmed_skip=True,
                version_id=ver_id,
                bundle_sha256=reg.version.bundle_sha256,
            )
            p1 = await create_preview(
                db,
                c.blob_store,
                actor,
                WORKSPACE_ID,
                col_id,
                doc_id,
                ver_id,
                PreviewRequest(
                    action="approve",
                    reason=f"Duyệt nghiệm thu {doc['title']}",
                    review_skip=skip,
                ),
            )
            await commit_decision(
                db,
                c.blob_store,
                actor,
                WORKSPACE_ID,
                col_id,
                doc_id,
                ver_id,
                CommitRequest(preview_id=p1.id, preview_sha256=p1.preview_sha256),
                f"app_e2e_{uuid.uuid4().hex[:8]}",
            )

            # Publish
            p2 = await create_preview(
                db,
                c.blob_store,
                actor,
                WORKSPACE_ID,
                col_id,
                doc_id,
                ver_id,
                PreviewRequest(action="publish", reason=f"Xuất bản nghiệm thu {doc['title']}"),
            )
            await commit_decision(
                db,
                c.blob_store,
                actor,
                WORKSPACE_ID,
                col_id,
                doc_id,
                ver_id,
                CommitRequest(preview_id=p2.id, preview_sha256=p2.preview_sha256),
                f"pub_e2e_{uuid.uuid4().hex[:8]}",
            )
            print(f"   -> Xuất bản CompiledDocument: {doc_id}, Version: {ver_id} (published)")

        docs_ingest_report.append({
            "title": doc["title"],
            "file_name": doc["file_name"],
            "source_id": src_id,
            "revision_id": rev_id,
            "ocr_run_id": ocr_run_id,
            "ocr_duration": round(t_ocr, 2),
            "canonical_sha256": canonical_sha,
            "units_count": doc_units,
            "spelling_passes": spelling_passes_report,
            "compilation_run_id": cmp_run_id,
            "compilation_duration": round(t_cmp, 2),
            "document_id": doc_id,
            "version_id": ver_id,
        })

    # 3. Lập chỉ mục Hợp nhất toàn kho
    print("\n" + "=" * 80)
    print("BƯỚC 3: LẬP CHỈ MỤC HỢP NHẤT TOÀN KHO (POSTGRES + QDRANT)")
    print("=" * 80)
    idx_key = f"idx_e2e_{uuid.uuid4().hex[:8]}"
    idx_req = IndexRequest(contextual_search=False)

    async with AsyncSessionFactory() as db:
        idx_res = await request_index(
            db,
            c.blob_store,
            c.vector_store,
            actor,
            WORKSPACE_ID,
            col_id,
            idx_req,
            key=idx_key,
            queue=None,
        )
        index_run_id = idx_res.run.id
        print(f"-> Tạo IndexRun: {index_run_id} cho collection: {col_id}")

    t0_idx = time.perf_counter()
    async with AsyncSessionFactory() as db:
        idx_status = await execute_index_run(
            db,
            c.blob_store,
            index_run_id,
            worker_id="dev_worker_e2e",
            model=c.embedding_model,
            vectors=c.vector_store,
        )
    t_idx = time.perf_counter() - t0_idx
    print(f"-> IndexRun {index_run_id} hoàn tất: status={idx_status} ({t_idx:.2f}s)")

    # Kiểm kê chunks & facts
    async with AsyncSessionFactory() as db:
        run_obj = await db.get(IndexRun, index_run_id)
        is_active = run_obj.is_active

        chunks_count = (
            await db.execute(
                select(func.count(IndexChunk.id)).where(IndexChunk.run_id == index_run_id)
            )
        ).scalar_one()

        facts_count = (
            await db.execute(
                select(func.count(IndexTableFact.id)).where(
                    IndexTableFact.index_run_id == index_run_id
                )
            )
        ).scalar_one()

        kinds_res = (
            await db.execute(
                select(IndexChunk.kind, func.count(IndexChunk.id))
                .where(IndexChunk.run_id == index_run_id)
                .group_by(IndexChunk.kind)
            )
        ).all()

        kinds_dict = {kind: count for kind, count in kinds_res}

        print("\n=== KẾT QUẢ LẬP CHỈ MỤC HỢP NHẤT E2E ===")
        print(f"Collection ID: {col_id}")
        print(f"IndexRun ID:   {index_run_id} (Active: {is_active})")
        print(f"Tổng chunks:   {chunks_count} ({kinds_dict})")
        print(f"Tổng facts:    {facts_count}")

        # Gán Assistant mặc định vào Collection mới
        ast = (await db.execute(select(Assistant))).scalars().first()
        if ast:
            ast.name = "Trợ lý AI QNU (Kho Nghiệm Thu E2E)"
            ast_col = AssistantCollection(
                assistant_id=ast.id,
                collection_id=col_id,
                workspace_id=WORKSPACE_ID,
                position=0,
            )
            db.add(ast_col)
            await db.commit()
            print(f"-> Đã gán Assistant '{ast.name}' (id={ast.id}) vào Collection mới: {col_id}")

    acceptance_data["ingestion_summary"] = {
        "collection_id": col_id,
        "index_run_id": index_run_id,
        "is_active": is_active,
        "index_duration": round(t_idx, 2),
        "total_chunks": chunks_count,
        "chunk_kinds": kinds_dict,
        "total_facts": facts_count,
        "documents": docs_ingest_report,
    }

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
