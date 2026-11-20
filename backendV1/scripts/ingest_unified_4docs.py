"""Ingest, OCR, Compile, Publish, and Index all 4 documents into 1 single unified collection.
1. 4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf (QĐ 4740/QĐ-BGDĐT)
2. KH130 trien khai chuan bi DGN CTĐT 3 CTDT AUN-QA 2026.pdf (KH 130/KH-ĐHQN)
3. tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx (KH 07/KH-AM)
4. Thông tin TSĐH cập nhật.pdf (Tuyển sinh 2026)
"""

from __future__ import annotations

import asyncio
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
from qnu.domains.knowledge.index.models import IndexChunk, IndexTableFact
from qnu.domains.knowledge.index.schemas import IndexRequest
from qnu.domains.knowledge.index.service import request_index
from qnu.domains.knowledge.models import KBCollection
from qnu.domains.knowledge.publication.decisions import commit_decision, create_preview
from qnu.domains.knowledge.publication.schemas import (
    CommitRequest,
    CreateDocumentRequest,
    PreviewRequest,
    ReviewSkipAcknowledgement,
)
from qnu.domains.knowledge.publication.service import create_document
from qnu.domains.knowledge.sources.service import source_service
from qnu.domains.ocr.execution import execute_run as execute_ocr_run
from qnu.domains.ocr.service import processing_service
from qnu.domains.workspaces.models import Workspace
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory

WORKSPACE_ID = "ws_623614ba7fb8"
COLLECTION_NAME = "Kho kiểm thử tích hợp 4 tài liệu (QĐ 4740, KH 130, 07/KH-AM, Tuyển sinh 2026)"
COLLECTION_DESC = "Kho tri thức tích hợp toàn diện 4 tài liệu phục vụ kiểm thử liên văn bản, so sánh, thống kê và hội thoại đa lượt."

STAGING_DIR = Path("../docs/tai_lieu/staged_4docs")

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


async def main():
    settings = get_settings()
    c = build_container(settings)
    actor = AuthActor(
        actor_id="act_dev_admin",
        username="dev_admin",
        email="admin@qnu.edu.vn",
        display_name="Dev Admin",
        roles=["admin"],
        authenticated=True,
    )

    print("=" * 80)
    print("QUY TRÌNH NẠP 4 TÀI LIỆU VÀO 1 KHO TRI THỨC DUY NHẤT")
    print(f"Kho: '{COLLECTION_NAME}'")
    print(f"Workspace: {WORKSPACE_ID}")
    print("=" * 80)

    # 1. Tạo Collection duy nhất
    col_id = f"col_unified_{uuid.uuid4().hex[:8]}"
    async with AsyncSessionFactory() as db:
        ws = await db.get(Workspace, WORKSPACE_ID)
        assert ws is not None, f"Workspace {WORKSPACE_ID} không tồn tại"
        col = KBCollection(
            id=col_id,
            workspace_id=WORKSPACE_ID,
            name=COLLECTION_NAME,
            description=COLLECTION_DESC,
            created_by=actor.actor_id,
        )
        db.add(col)
        await db.commit()
        await db.refresh(col)
        print(f"1. Đã tạo Collection duy nhất: {col.id} - '{col.name}'\n")

    # 2. Xử lý từng tài liệu: Upload -> OCR -> Compile -> Publish
    published_docs = []
    for idx, doc in enumerate(DOCUMENTS, 1):
        print("-" * 80)
        print(f"[{idx}/4] XỬ LÝ: {doc['title']}")
        print(f"      Tệp: {doc['file_name']}")
        file_path = STAGING_DIR / doc["file_name"]
        assert file_path.exists(), f"Không tìm thấy file: {file_path}"
        payload = file_path.read_bytes()
        print(f"      Kích thước: {len(payload):,} bytes")

        # 2a. Upload
        upl_key = f"upl_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
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
            print(f"      -> Uploaded Source: {src_id}, Revision: {rev_id}")

        # 2b. OCR Run
        async with AsyncSessionFactory() as db:
            ocr_runs, _ = await processing_service.list_runs(
                db, WORKSPACE_ID, rev_id, page=1, page_size=1
            )
            assert len(ocr_runs) > 0, "Không tìm thấy OCR run"
            ocr_run_id = ocr_runs[0].id
            print(f"      -> OCR Run ID: {ocr_run_id}")

        t0 = time.perf_counter()
        async with AsyncSessionFactory() as db:
            ocr_outcome = await execute_ocr_run(
                db,
                c.blob_store,
                ocr_run_id,
                worker_id=f"worker_{doc['key_prefix']}",
                engine=c.ocr_engine,
            )
            t_ocr = time.perf_counter() - t0
            print(f"      -> OCR Run hoàn tất: status={ocr_outcome.status} ({t_ocr:.2f}s)")

        # 2c. Compilation Run
        cmp_key = f"cmp_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
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
            print(f"      -> Compilation Run ID: {cmp_run_id}")

        t0 = time.perf_counter()
        async with AsyncSessionFactory() as db:
            cmp_status = await execute_compilation_run(
                db,
                c.blob_store,
                cmp_run_id,
                worker_id=f"worker_{doc['key_prefix']}",
                model=c.chat_model,
            )
            t_cmp = time.perf_counter() - t0
            print(f"      -> Compilation Run hoàn tất: status={cmp_status} ({t_cmp:.2f}s)")

        # 2d. Create CompiledDocument, Approve & Publish
        doc_key = f"cdoc_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
        create_req = CreateDocumentRequest(
            document_key=doc_key,
            title=doc["title"],
            compilation_run_id=cmp_run_id,
            retrieval_metadata=[],
        )
        reg_key = f"reg_{doc['key_prefix']}_{uuid.uuid4().hex[:8]}"
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
                    reason=f"Duyệt {doc['title']}",
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
                f"app_{uuid.uuid4().hex[:8]}",
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
                PreviewRequest(action="publish", reason=f"Xuất bản {doc['title']}"),
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
                f"pub_{uuid.uuid4().hex[:8]}",
            )
            print(f"      -> Xuất bản CompiledDocument: {doc_id}, Version: {ver_id} (published)")
            published_docs.append((doc["title"], doc_id, ver_id))

    # 3. Lập chỉ mục Hợp nhất (Unified Indexing) cho toàn bộ 4 tài liệu trong kho
    print("\n" + "=" * 80)
    print("3. BẮT ĐẦU LẬP CHỈ MỤC HỢP NHẤT TOÀN BỘ 4 TÀI LIỆU TRONG KHO")
    print("=" * 80)
    idx_key = f"idx_unified_{uuid.uuid4().hex[:8]}"
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

    t0 = time.perf_counter()
    async with AsyncSessionFactory() as db:
        idx_status = await execute_index_run(
            db,
            c.blob_store,
            index_run_id,
            worker_id="dev_worker_unified",
            model=c.embedding_model,
            vectors=c.vector_store,
        )
    t_idx = time.perf_counter() - t0
    print(f"-> IndexRun {index_run_id} hoàn tất: status={idx_status} ({t_idx:.2f}s)")

    # 4. Kiểm kê số lượng Chunks và Table Facts
    async with AsyncSessionFactory() as db:
        chunks_count = (
            await db.execute(
                select(func.count(IndexChunk.id)).where(IndexChunk.index_run_id == index_run_id)
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
                .where(IndexChunk.index_run_id == index_run_id)
                .group_by(IndexChunk.kind)
            )
        ).all()

        print("\n=== KẾT QUẢ LẬP CHỈ MỤC HỢP NHẤT ===")
        print(f"Collection ID: {col_id}")
        print(f"IndexRun ID:   {index_run_id}")
        print(f"Tổng chunks:   {chunks_count}")
        for kind, count in kinds_res:
            print(f"   - {kind}: {count}")
        print(f"Tổng facts:    {facts_count}")

    # 5. Ràng buộc trợ lý AI mặc định vào kho mới
    async with AsyncSessionFactory() as db:
        ast = (await db.execute(select(Assistant))).scalars().first()
        if ast:
            # Update name to reflect multi-document capability
            ast.name = "Trợ lý AI QNU (Kho 4 Tài liệu Tích hợp)"
            ast_col = AssistantCollection(
                assistant_id=ast.id,
                collection_id=col_id,
                workspace_id=WORKSPACE_ID,
                position=0,
            )
            db.add(ast_col)
            await db.commit()
            print(f"\n5. Đã gán Assistant '{ast.name}' (id={ast.id}) vào Collection mới: {col_id}")

    print("\n" + "=" * 80)
    print("HOÀN TẤT NẠP VÀ LẬP CHỈ MỤC 4 TÀI LIỆU VÀO 1 KHO DUY NHẤT!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
