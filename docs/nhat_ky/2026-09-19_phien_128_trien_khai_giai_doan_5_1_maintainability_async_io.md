# NHẬT KÝ LÀM VIỆC — PHIÊN #128
**Ngày**: 2026-09-19 (22:45 – 22:55 UTC+7)  
**Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu phiên**: Triển khai Giai đoạn 5.1 — Backend Maintainability, Non-blocking Async I/O & Triệt Tiêu Toàn Bộ Pytest Warnings.

---

## 1. Tóm Tắt Nhiệm Vụ & Bối Cảnh

Theo định hướng nâng cấp mã nguồn tại [Kế hoạch 07 (Đợt 8)](../ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md) và [Hướng dẫn 08](../ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md), Giai đoạn 5 được chia thành 2 phần:
- **Giai đoạn 5.1 (Ưu tiên làm trước)**: Chuẩn hóa Non-blocking Async I/O cho MinIO, phân rã 2 service monolithic (`KnowledgeService` và `AssistantService`), triệt tiêu 100% Pytest Warnings & RuntimeErrors, đạt chuẩn Clean Code và Boy Scout Rule.
- **Giai đoạn 5.2 (Làm sau)**: Refactor ModelOps Service (~2.260 dòng), hoàn thiện OpenTelemetry Tracing / Prometheus Metrics, và củng cố Docker Compose production baseline.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Non-blocking Async I/O cho Storage (`storage.py` & `main.py`)
- **Vấn đề**: `StorageService` sử dụng thư viện `minio` vốn là synchronous SDK. Khi gọi `client.put_object`, `client.get_object`, `client.stat_object` trong các async endpoint, event loop của FastAPI bị block dẫn đến suy giảm throughput và nghẽn I/O khi nạp file dung lượng lớn. Ngoài ra, `__init__` gọi blocking `_ensure_bucket()` ngay lúc import module.
- **Giải pháp**:
  - Chuyển toàn bộ các phương thức `put`, `get`, `delete`, `exists`, `get_url` sang `await asyncio.to_thread(...)`.
  - Tách `_ensure_bucket()` thành async method `ensure_bucket()` và đưa vào lifespan startup của FastAPI (`app/main.py`), đảm bảo khởi động phi đồng bộ sạch sẽ.

### 2.2. Phân Rã `KnowledgeService` (~1.927 dòng → Facade 249 dòng)
- **Vấn đề**: Vi phạm nghiêm trọng nguyên tắc Zero Big-Ball-of-Mud và Single Responsibility Principle (SRP). `KnowledgeService` chứa đồng thời CRUD Collection, Ingestion Pipeline, OCR Preview, Batch Approval, Chunking/Indexing, Excel Facts, và Reconciliation.
- **Giải pháp**: Phân rã thành 4 sub-services độc lập trong `backend/app/modules/knowledge/services/`:
  1. [`collection_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/collection_service.py): Quản lý bộ sưu tập, thống kê dung lượng, studio view.
  2. [`ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py): Xử lý tải lên tài liệu, OCR preview, phê duyệt hàng loạt, bóc tách chunk và nạp vector/FTS dual index. Thiết kế cơ chế Facade-aware helpers (`_get_storage_service()`, `_call_get_document()`, `_call_get_collection()`) để tương thích hoàn toàn với monkeypatching trong test suites.
  3. [`facts_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/facts_service.py): Quản lý Structured Facts từ Excel/CSV, trích xuất thực thể, deduplication.
  4. [`reconciliation_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/reconciliation_service.py): Đối soát dữ liệu giữa PostgreSQL, Qdrant và MinIO; tái lập chỉ mục và dual indexing audit.
  5. [`service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py): Rút gọn thành Facade Pattern mỏng (249 dòng), ủy quyền toàn bộ cho 4 sub-services và re-export đầy đủ `__all__ = ["KnowledgeService", "knowledge_service", "storage_service"]`.

### 2.3. Phân Rã `AssistantService` (~1.143 dòng → Facade 230 dòng)
- **Vấn đề**: `AssistantService` gộp lẫn toàn bộ logic quản lý vòng đời (CRUD, snapshot versioning, 1-click rollback, workflow forking, template seeding) với logic runtime chat (SSE streaming, multi-turn history, HITL paused_for_approval, usage tracking).
- **Giải pháp**: Phân rã thành 2 sub-services độc lập trong `backend/app/modules/assistants/services/`:
  1. [`assistant_lifecycle_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/services/assistant_lifecycle_service.py): Đảm nhiệm toàn bộ vòng đời trợ lý, tính toán điểm readiness, tạo snapshot phiên bản, rollback trạng thái, fork private workflow.
  2. [`assistant_chat_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/services/assistant_chat_service.py): Đảm nhiệm runtime đối thoại, parse attachments, tương tác Workflow Engine, stream token SSE, xử lý HITL approval event, và ghi log usage ModelOps.
  3. [`service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/service.py): Rút gọn thành Facade Pattern mỏng (230 dòng), re-export đầy đủ `__all__ = ["AssistantService", "assistant_service", "_clean_text", "_to_response", "workflow_service"]`.

### 2.4. Triệt Tiêu Toàn Bộ Pytest Warnings & Mock Coroutine Leaks
- **Vấn đề**: Khi chạy test suite, xuất hiện 47 warnings gồm:
  - Deprecation/User warnings từ third-party dependencies (`torch`, `easyocr`, `docling`, `pydantic`).
  - `RuntimeWarning: coroutine was never awaited` do SQLAlchemy `session.add()` là synchronous method nhưng test sử dụng `db = AsyncMock()`, khiến lệnh gọi `db.add()` sinh ra coroutine không được await.
- **Giải pháp**:
  - Cập nhật [`backend/pyproject.toml`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/pyproject.toml) với `filterwarnings` chuẩn hóa.
  - Chuẩn hóa mock sessions (`mock_db.add = MagicMock()`, `mock_db.execute.return_value = mock_exec`) trên 11 file test: `test_knowledge.py`, `test_assistants.py`, `test_assistant_versions.py`, `test_assistant_workflow_ownership.py`, `test_workflow_hitl_and_history.py`, `test_evaluation.py`, `test_tools.py`, `test_modelops_usage.py`, `test_conversations_handoff.py`, `test_excel_facts_ingestion.py`, `test_assistant_readiness.py`.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

1. **Backend Test Suite**:
   - Lệnh: `uv run --extra dev pytest -q`
   - Kết quả: **257 passed in 51.69s (100% pass, 0 failed, 0 warnings)**.
2. **Backend Linter & Formatting**:
   - Lệnh: `uv run ruff check .`
   - Kết quả: **All checks passed! (0 errors)**.
3. **Frontend Linter & Typecheck**:
   - Lệnh: `npm run lint` → **Checked 164 files in 201ms. No fixes applied. (0 errors)**.
   - Lệnh: `npm run typecheck` → **0 errors**.
   - Lệnh: `npm run build` → **✓ built in 7.81s (0 errors)**.
4. **Kiểm Tra Font Chữ Tiếng Việt (Zero Mojibake)**:
   - Lệnh: `python scripts/check_mojibake.py`
   - Kết quả: **328 tệp đã quét, 100% UTF-8 sạch, 0 lỗi Mojibake**.

---

## 4. Kế Hoạch Tiếp Theo

- **Tiến hành Giai đoạn 5.2**:
  1. Phân rã `ModelOpsService` (~2.260 dòng) thành các sub-services chuyên biệt (`provider_service`, `model_catalog_service`, `inference_service`, `usage_accounting_service`).
  2. Bổ sung OpenTelemetry Tracing / Prometheus Metrics middleware.
  3. Củng cố Docker Compose production baseline (kiểm tra healthcheck thực tế của MinIO, Qdrant, Redis, Postgres).
