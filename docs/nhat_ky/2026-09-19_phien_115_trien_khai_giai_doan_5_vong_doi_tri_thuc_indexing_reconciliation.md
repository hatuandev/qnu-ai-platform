# Nhật Ký Làm Việc — Phiên #115 (Giai Đoạn 5)
# Ngày: 2026-09-19 | Triển Khai Giai Đoạn 5: Chuẩn Hóa Vòng Đời Tri Thức, Indexing Nguyên Tử & Đối Soát Bền Vững 4 Tầng (P1-09 đến P1-13)

---

## 1. Mục Tiêu Phiên Làm Việc
- Khảo sát hiện trạng hệ thống tri thức sau Giai đoạn 4, đọc kỹ Memory System và Work Log.
- Khắc phục triệt để lỗ hổng nghiêm trọng P1-09: Tài liệu chuyển trạng thái `approved` nhưng vector chưa vào Qdrant hoặc lỗi vector bị nuốt âm thầm.
- Bổ sung `index_status` (`pending`, `indexing`, `indexed`, `index_failed`) và `index_error` vào thực thể `KnowledgeDocument`.
- Tách bạch `job_type="ingestion_extract"` (lúc upload) khỏi `job_type="vector_indexing"` (lúc approve/reindex) (P1-10).
- Bổ sung đầy đủ metadata cô lập đa người thuê (`tenant_id`, `workspace_id`, `document_status="approved"`, `is_retrievable=True`) vào payload Qdrant (P1-11).
- Hoàn thiện xóa sạch 4 tầng thác đổ khi xóa collection (Storage files, Qdrant vectors, DB chunks/facts/doc, Redis semantic cache) (P1-12).
- Xây dựng cơ chế Reconciliation đối soát 4 tầng và nút `[Đối soát Kho]`, `[⚡ Thử lại Index]`, `[Đồng bộ tất cả]` trên UI (P1-13).
- Bảo đảm 100% Test suite passed, 0 lỗi Biome, 0 lỗi TypeScript, 0 lỗi Ruff, Zero Mojibake.

---

## 2. Chi Tiết Các Tệp Tin Chỉnh Sửa & Tạo Mới

| Tệp Tin | Loại | Mô Tả Thay Đổi Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/knowledge/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/models.py) | Cập nhật | Bổ sung 2 trường `index_status` (mặc định `"pending"`) và `index_error` (nullable) vào bảng `knowledge_documents`. |
| [`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py) | Cập nhật | Bổ sung `index_status`, `index_error` vào `DocumentResponse` và `ApproveDocumentResponse`; định nghĩa schemas cho `ReindexDocumentResponse`, `KnowledgeReconciliationResponse`, `KnowledgeReconciliationDiscrepancy`, `ReconcileFixResponse`. |
| [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) | Cập nhật | - `ingest_document`: Khởi tạo `index_status="pending"`, ghi nhận `JobRecord(job_type="ingestion_extract")`.<br>- `approve_document`: Chuyển `index_status="indexing"`, truyền `tenant_id`, `workspace_id`, `document_status="approved"` vào Qdrant, chuyển `index_status="indexed"` hoặc `"index_failed"` kèm `index_error` (không nuốt lỗi), ghi nhận `JobRecord(job_type="vector_indexing")`.<br>- `reindex_document`: Khôi phục lập chỉ mục vector cho 1 tài liệu đơn lẻ.<br>- `delete_collection`: Dọn sạch tệp vật lý trên Storage driver trước khi xóa DB.<br>- `reconcile_collection`: Đối soát số lượng/ID trên 4 tầng (DB, Qdrant, MinIO/Local Storage, Redis Cache), phát hiện sai lệch.<br>- `reconcile_fix_collection`: Tự động re-index toàn bộ tài liệu approved bị thiếu vector. |
| [`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py) | Cập nhật | Bổ sung 3 endpoints mới: `POST /documents/{id}/reindex`, `GET /collections/{id}/reconcile`, `POST /collections/{id}/reconcile-fix`. |
| [`backend/tests/test_knowledge.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_knowledge.py) | Cập nhật | Bổ sung 4 unit/integration tests mới: `test_approve_document_sets_index_status_and_records_job`, `test_approve_document_index_failed_gracefully`, `test_reindex_document_endpoint_recovers_vector`, `test_reconcile_collection_audits_parity`. Toàn bộ 31/31 tests passed. |
| [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts) | Cập nhật | Bổ sung `index_status` và `index_error` vào `KnowledgeDocument`; thêm types `ReindexDocumentResponse`, `KnowledgeReconciliationReport`, `ReconcileFixResponse`. |
| [`frontend/src/services/knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/knowledge-api.ts) | Cập nhật | Cập nhật `getDocuments` mapper cho `index_status`/`index_error`; thêm các hàm API `reindexDocument`, `reconcileCollection`, `fixReconciliation`. |
| [`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx) | Cập nhật | - Thêm nút `[Đối soát Kho]` trên Top Toolbar.<br>- Hiển thị huy hiệu kép trên cột trạng thái (`Đã duyệt` + `Đã index` / `Đang index` / `Lỗi index`).<br>- Thêm nút `[⚡ Thử lại Index]` thao tác nhanh cho tài liệu `approved` bị lỗi vector.<br>- Thêm Dialog **Reconciliation Audit 4 Tầng** hiển thị 4 KPI cards, chi tiết sai lệch và nút `[Đồng bộ tất cả]`. |
| [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md) | Cập nhật | Bổ sung **Bước 11**: Vòng Đời Lập Chỉ Mục Kép, Tách Bạch Hàng Đợi & Đối Soát Bền Vững 4 Tầng (P1-09 đến P1-13). |

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Backend Tests (Pytest)**:
   - `uv run --extra dev pytest -v`
   - **Kết quả: 232 passed, 0 failed, 40 warnings** (100% passed toàn bộ backend test suite).
2. **Backend Code Quality (Ruff)**:
   - `uv run ruff check .`
   - **Kết quả: All checks passed!**
3. **Frontend Code Quality (Biome Lint)**:
   - `npm run lint`
   - **Kết quả: Checked 130 files in 150ms. No fixes applied. 0 errors.**
4. **Frontend Type Safety (TypeScript)**:
   - `npm run typecheck`
   - **Kết quả: tsc --noEmit: 0 errors.**
5. **Frontend Production Build (Vite)**:
   - `npm run build`
   - **Kết quả: Built in 7.59s thành công.**
6. **Zero Mojibake Check**:
   - `python scripts/check_mojibake.py`
   - **Kết quả: Đã quét 286 tệp. 100% UTF-8 sạch, không phát hiện ký tự rác.**

---

## 4. Trạng Thái Hoàn Thành
- Giai đoạn 5 (P1-09 đến P1-13) hoàn thành xuất sắc, sẵn sàng cho Giai đoạn 6.
