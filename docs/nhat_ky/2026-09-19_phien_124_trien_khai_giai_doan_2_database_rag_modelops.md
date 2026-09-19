# NHẬT KÝ PHIÊN LÀM VIỆC #124
**Ngày**: 2026-09-19 20:45 | **Kỹ sư**: AI Senior Full-Stack Architect  
**Mục tiêu**: Triển khai Giai đoạn 2 (Database & Cross-Store Integrity, RAG Hybrid Hardening & Groundedness, ModelOps Dynamic Fallback & Usage Accounting) theo Kế hoạch Cải thiện Toàn diện 07 ([`docs/ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md`](../ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md)).

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Sau khi hoàn thành Giai đoạn 1 (Bảo mật Fail-Fast & Truthful Runtime), hệ thống đã loại bỏ hoàn toàn các rò rỉ dữ liệu giả và khóa chặt API. Giai đoạn 2 tập trung giải quyết các điểm yếu về tính toàn vẹn dữ liệu, khả năng chịu lỗi và tính toán hạn ngạch:
1. **Database & Cross-Store Integrity (P1)**:
   - `knowledge_facts.document_id` thiếu ràng buộc khóa ngoại `ForeignKey("knowledge_documents.id", ondelete="CASCADE")`, gây nguy cơ tạo ra các facts mồ côi (orphan facts) khi tài liệu bị xóa.
   - `app/main.py` thực thi các câu lệnh raw SQL `ALTER TABLE IF EXISTS ...` trong lifecycle startup, vi phạm nguyên tắc quản lý schema qua Alembic migrations.
2. **RAG Hybrid Hardening & Groundedness (P0 / P1)**:
   - `FactLayer.lookup_facts` có điều kiện `KnowledgeDocument.id.is_(None)` và legacy status `completed`, `processed`, cho phép facts không có tài liệu thật lọt vào ngữ cảnh RAG.
   - Hàm `search_sparse_fts` trong `retriever.py` gặp lỗi `UnboundLocalError: local variable 'stmt_ilike' referenced before assignment` khi câu hỏi ngắn (chỉ 1 ký tự hoặc toàn stop words).
   - Bộ tìm kiếm vector `search_dense` trong `vector_indexer.py` thiếu cơ chế Degraded Mode, có thể gây crash toàn bộ pipeline RAG khi embedding service gặp sự cố.
3. **ModelOps Dynamic Fallback & Usage Accounting (P0 / P1)**:
   - `modelops_service.generate()` chưa ưu tiên định tuyến theo `fallback_model_name` khi primary model gặp lỗi.
   - `modelops_service.generate_stream()` hoàn toàn bỏ qua việc ghi log `LLMUsageLog` và trừ hạn ngạch (`quota.tokens_used`, `quota.cost_used_usd`), tạo lỗ hổng bypass quota khi stream token.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 2.1. Database & Cross-Store Integrity
- **[`backend/app/modules/knowledge/models.py`](../../backend/app/modules/knowledge/models.py)**:
  - Bổ sung `ForeignKey("knowledge_documents.id", ondelete="CASCADE")` vào trường `KnowledgeFact.document_id`.
  - Thiết lập quan hệ ORM hai chiều chuẩn hóa:
    - `KnowledgeFact.document: Mapped[KnowledgeDocument] = relationship("KnowledgeDocument", back_populates="facts")`
    - `KnowledgeDocument.facts: Mapped[list[KnowledgeFact]] = relationship("KnowledgeFact", back_populates="document", cascade="all, delete-orphan")`
- **[`backend/alembic/versions/20260919_facts_foreign_key_and_schema_sync.py`](../../backend/alembic/versions/20260919_facts_foreign_key_and_schema_sync.py)**:
  - Khởi tạo migration Alembic mới với cơ chế phòng vệ schema introspection (`sa.inspect(bind)`).
  - Tự động xóa facts mồ côi trước khi gắn constraint `fk_knowledge_facts_document_id_knowledge_documents`.
  - Đồng bộ an toàn cột `document_type_code` trên bảng `knowledge_documents`.
- **[`backend/app/main.py`](../../backend/app/main.py)**:
  - Dọn sạch toàn bộ các câu lệnh raw SQL `ALTER TABLE IF EXISTS ...` trong lifecycle startup.

### 2.2. RAG Hybrid Hardening & Groundedness
- **[`backend/app/modules/rag/facts.py`](../../backend/app/modules/rag/facts.py)**:
  - Loại bỏ hoàn toàn điều kiện chấp nhận fact mồ côi `KnowledgeDocument.id.is_(None)`.
  - Chuyển `outerjoin` sang `join(KnowledgeDocument)` với điều kiện bắt buộc `KnowledgeDocument.is_active.is_(True)` và `KnowledgeDocument.status.in_(["approved", "ready"])`.
  - Bổ sung bộ lọc cô lập `tenant_id` và `workspace_id` thông qua join với `KnowledgeCollection`.
- **[`backend/app/modules/rag/vector_indexer.py`](../../backend/app/modules/rag/vector_indexer.py)**:
  - Bọc lời gọi `self.embed_texts([query])` trong khối `try...except` của `search_dense`. Khi gặp lỗi embedding, ghi log cảnh báo và trả về danh sách rỗng `[]` thay vì làm gián đoạn luồng truy vấn.
- **[`backend/app/modules/rag/retriever.py`](../../backend/app/modules/rag/retriever.py)**:
  - Sửa lỗi `UnboundLocalError`: Đưa khối `try: res_ilike = await db.execute(stmt_ilike)` vào trong phạm vi `if meaningful_tokens:`.
  - Chuẩn hóa điều kiện lọc trạng thái tài liệu sang `["approved", "ready"]`.
  - Bổ sung phương thức `_safe_dense_search` trong `retrieve()` để tự động kích hoạt Degraded Mode (chỉ sử dụng Sparse FTS) khi bộ tìm kiếm vector Dense không khả dụng.

### 2.3. ModelOps Dynamic Fallback & Usage Accounting
- **[`backend/app/modules/modelops/service.py`](../../backend/app/modules/modelops/service.py)**:
  - Nâng cấp hàm chấm điểm `_match_score` trong `generate()` và `generate_stream()`: ưu tiên `preferred_model_name` (+50 điểm) và `fallback_model_name` (+25 điểm).
  - Tự động đánh dấu `is_fallback = True` khi phản hồi được sinh ra từ provider không khớp với `preferred_provider_id` hoặc `preferred_model_name`.
  - Viết lại luồng `generate_stream()`:
    - Bổ sung Quota Pre-check (`check_quota_available`) trước khi mở stream.
    - Duyệt qua danh sách providers với cơ chế Circuit Breaker và Key Pool rotation.
    - Tích lũy số token sinh ra trong quá trình yield SSE chunk (`completion_tokens`).
    - Tính toán chi phí USD và ghi nhận vào `LLMUsageLog` sau khi stream kết thúc.
    - Cập nhật số liệu quota sử dụng (`quota.tokens_used`, `quota.cost_used_usd`) trên CSDL.

### 2.4. Mở Rộng Test Suite
- **[`backend/tests/test_rag.py`](../../backend/tests/test_rag.py)**:
  - `test_sparse_fts_handles_empty_or_short_query_without_unbound_local`: Kiểm tra sparse FTS với query 1 ký tự hoặc rỗng, bảo đảm không bị `UnboundLocalError`.
  - `test_search_dense_gracefully_degrades_when_embedding_fails`: Kiểm tra cơ chế Degraded Mode khi embedding service ném ngoại lệ.
- **[`backend/tests/test_modelops.py`](../../backend/tests/test_modelops.py)**:
  - `test_generate_stream_records_usage_and_deducts_quota`: Kiểm tra luồng stream ghi nhận đúng `LLMUsageLog` và trừ quota của tenant.
  - `test_generate_prioritizes_fallback_model_when_primary_unavailable`: Kiểm tra fallback model được ưu tiên kích hoạt khi primary model trả về lỗi 500.

---

## 3. Bảng Kiểm Thử & Nghiệm Thu (Verification)

| Phân hệ / Bộ Kiểm Tra | Lệnh Thực Hiện | Kết Quả Thực Tế | Trạng Thái |
| :--- | :--- | :--- | :--- |
| **Backend Linter** | `uv run ruff check .` | **All checks passed!** (0 error, 0 warning) | ✅ ĐẠT |
| **Backend ModelOps Test** | `uv run --extra dev pytest tests/test_modelops.py -v` | **18 passed**, 1 warning (insecure api_key test env) in 2.62s | ✅ ĐẠT |
| **Backend RAG Test** | `uv run --extra dev pytest tests/test_rag.py -v` | **16 passed**, 1 warning in 2.50s | ✅ ĐẠT |
| **Backend Full Test Suite** | `uv run --extra dev pytest -v` | **245 passed**, 47 warnings in 45.90s (100% pass) | ✅ ĐẠT |
| **Frontend Linter** | `npm run lint` | **Checked 162 files in 148ms. No fixes applied.** | ✅ ĐẠT |
| **Frontend TypeCheck** | `npm run typecheck` | `tsc --noEmit` hoàn tất không có lỗi | ✅ ĐẠT |
| **Frontend Production Build** | `npm run build` | `vite v6.4.3 building for production... ✓ built in 7.60s` | ✅ ĐẠT |

---

## 4. Kế Hoạch Tiếp Theo (Giai Đoạn 3)

Theo kế hoạch cải thiện toàn diện 07:
- **Giai đoạn 3 (Workflow, Tools & Multi-Turn Conversations)**:
  - Khép kín vòng lặp kiểm tra Tool Gateway allowlist phía client & server.
  - Tối ưu hóa DAG compiler & runtime handler validation.
  - Đồng bộ hội thoại đa lượt và lưu vết conversation history cho Chat Studio.
