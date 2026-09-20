# NHẬT KÝ PHIÊN LÀM VIỆC #153
# Ngày: 2026-09-20 | Triển khai Chặng 3: Revision-Safe Qdrant Indexing, Fact-First Query Routing & Citation Grounding

---

## 1. Mục Tiêu Phiên Làm Việc

Hoàn thành trọn vẹn **Chặng 3** theo kế hoạch tại [`docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`](../ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md):
- **Đợt 5: Revision-Safe Qdrant Indexing**: Vòng đời revision staging; `verify_revision_parity` kiểm tra tính toàn vẹn 100% point Qdrant trước khi kích hoạt; `activate_document_revision` kích hoạt nguyên tử; `purge_stale_revisions` dọn sạch points cũ, rollback an toàn không mất dữ liệu.
- **Đợt 6: Fact-First Query Routing & Retrieval Grounding**: Phân loại ý định truy vấn qua `QueryClassifier` (`EXACT_FACT`, `NARRATIVE`, `MIXED`); trích xuất mã ngành, mã nhiệm vụ, chứng chỉ quy đổi; ưu tiên tra cứu trực tiếp từ Structured Fact Layer; điều chỉnh retrieval `top_k` thích ứng để chống loãng thông tin.
- **Citation Guarding**: Trích xuất `source_pages`, `entity_key`, `quote_text` bám sát nguồn, kiên quyết kích hoạt No-Answer policy khi thiếu căn cứ.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật & Chi Tiết Thay Đổi |
| :--- | :--- | :--- |
| [`backend/app/modules/rag/vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py) | **MODIFY** | Bổ sung 3 phương thức cốt lõi: `verify_revision_parity` (đối soát số point và metadata Qdrant với PostgreSQL chunks), `activate_document_revision` (kích hoạt nguyên tử payload `is_retrievable=True` và `document_status="ready"`), và `purge_stale_revisions` (xóa các points có `document_revision < current_revision`). Hỗ trợ mock detection an toàn cho test environment. |
| [`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py) | **MODIFY** | Nâng cấp luồng indexing trong `approve_document`: Chunks được nạp ở trạng thái staging (`is_retrievable=False`, `document_status="indexing"`), chạy `verify_revision_parity`, nếu đạt mới gọi `activate_document_revision` và `purge_stale_revisions`. Nếu không đạt, giữ nguyên trạng thái `approved` kèm mã lỗi parity mismatch mà không xóa points cũ. |
| [`backend/app/modules/knowledge/services/reconciliation_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/reconciliation_service.py) | **MODIFY** | Đồng bộ luồng `reindex_document` theo chuẩn Revision-Safe Qdrant Indexing tương tự như `approve_document`. |
| [`backend/app/modules/rag/query_router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/query_router.py) | **NEW** | Xây dựng bộ phân loại ý định `QueryClassifier` nhận diện 3 intents (`EXACT_FACT`, `NARRATIVE`, `MIXED`), bóc tách regex mã ngành (`7\d{6}`), mã nhiệm vụ (`\d+\.\d+`), IELTS/VSTEP, và từ khóa thuộc tính nghiệp vụ. |
| [`backend/app/modules/rag/facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/facts.py) | **MODIFY** | Nâng cấp `FactLayer.lookup_facts` hỗ trợ tìm kiếm kết hợp theo `entity_codes` và `fact_attributes` song song với `keywords`. |
| [`backend/app/modules/rag/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/schemas.py) | **MODIFY** | Mở rộng DTO `Citation` bổ sung `source_pages: list[int] | None = None` và `entity_key: str | None = None`. |
| [`backend/app/modules/rag/citation_guard.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/citation_guard.py) | **MODIFY** | Nâng cấp `build_citations` trích xuất `source_pages` và `entity_key` từ metadata của chunk. |
| [`backend/app/modules/rag/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py) | **MODIFY** | Tích hợp `query_classifier.analyze` vào luồng `ask()`: Khi câu hỏi là `EXACT_FACT`, ưu tiên bốc dữ liệu từ `lookup_facts` đưa lên đầu context prompt và thu gọn `top_k=4`, `rerank_top_k=3` cho hybrid search. |
| [`backend/tests/test_revision_safe_qdrant_and_retrieval.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_revision_safe_qdrant_and_retrieval.py) | **NEW** | Tạo test suite toàn diện với 11 test cases kiểm thử: Intent classification (admissions & tasks), Parity verification pass/fail, Atomic activation, Stale revision purge, Citation extraction, và Fact-First RAG flow. |
| [`docs/quy_trinh/03_hybrid_rag_truy_xuat.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/03_hybrid_rag_truy_xuat.md) | **MODIFY** | Cập nhật Bước 2.5 (Fact-First Query Routing) và Bước 3.5 (Revision-Safe Qdrant Indexing). |

---

## 3. Kết Quả Kiểm Thử (Verification)

### Backend
- **Ruff Check**: `uv run ruff check .` $\rightarrow$ **All checks passed (0 lỗi, 0 cảnh báo)**.
- **Pytest Suite Chặng 3**: `uv run --extra dev pytest tests/test_revision_safe_qdrant_and_retrieval.py -v` $\rightarrow$ **11/11 passed (100%) in 2.43s**.
- **Pytest Suite Regression**:
  * `tests/test_rag_data_truth_and_lifecycle.py`: **9/9 passed (100%) in 3.67s**.
  * `tests/test_knowledge.py`: **31/31 passed (100%) in 45.40s**.
  * `tests/test_table_reconstructor.py`: **10/10 passed (100%) in 1.18s**.
- **Unicode NFC & Zero Mojibake**: Quét 220 tệp Python $\rightarrow$ **0 file lỗi UTF-8/mojibake**.

### Frontend
- **Biome Linter**: `npm run lint` $\rightarrow$ Checked 165 files, **0 lỗi, 0 cảnh báo**.
- **TypeScript Typecheck**: `npm run typecheck` $\rightarrow$ **0 lỗi**.
- **Vite Production Build**: `npm run build` $\rightarrow$ **✓ built in 9.77s**.
