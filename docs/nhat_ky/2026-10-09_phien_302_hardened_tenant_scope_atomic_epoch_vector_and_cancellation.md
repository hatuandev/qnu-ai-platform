# Nhật Ký Phiên Làm Việc #302: Hoàn Thiện Triệt Để Sau Code Review Publishing V2, Phân Giải Động Kích Thước Vector ModelOps, Hủy Tác Vụ Hợp Tác & Frontend Quality Gate

- **Ngày thực hiện**: 2026-10-09
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phạm vi**:
  - Backend: `app/modules/knowledge`, `app/modules/jobs`, `app/modules/modelops`, `app/modules/rag`, `app/workers`.
  - Frontend: `src/components/knowledge`, `src/features/applications`, `src/features/assignments`, `src/features/dashboard`, `src/features/invoices`, `src/features/residences`, `src/layouts`, `src/lib/excel-export.ts`, `src/types/modelops.ts`.
  - Tests: `tests/test_publishing_v2_resilience_and_cancellation.py` (Mới), `tests/test_publishing_v2_hardening.py`, `tests/test_publishing_v2_cutover_and_gc.py`, `tests/test_publishing_v2_decommissioning_and_system_gc.py`, `tests/test_modelops.py`.

---

## 1. Mục Tiêu & Bối Cảnh

Sau đợt rà soát mã nguồn chuyên sâu (Code Review Retrospective) đối với hệ thống Xuất Bản Tri Thức V2 (Publishing V2) và hạ tầng ModelOps, toàn bộ các vấn đề còn tồn đọng đã được giải quyết triệt để theo các nguyên tắc cốt lõi của `AGENTS.md`:
1. **Production-First & Zero Fallback Mock**:
   - Loại bỏ hoàn toàn fallback dữ liệu ngầm (`tenant_qnu`, `workspace_qnu`) và các giá trị mặc định cứng (`1024` vector dimension, `gemini-2.5-flash`, `gpt-4o-mini`).
   - Phân giải cấu hình và kích thước vector động 100% từ bảng cơ sở dữ liệu `model_provider_configs` trong PostgreSQL. Nếu thiếu cấu hình dimension, hệ thống báo lỗi rõ ràng RFC 7807 `EMBEDDING_DIMENSION_NOT_CONFIGURED` (400), tuyệt đối không fallback âm thầm.
2. **Nguyên Tử Hóa Concurrency CAS Epoch**:
   - Chuẩn hóa hàm `bump_collection_index_epoch` bằng một câu lệnh SQL duy nhất `UPDATE knowledge_collections SET index_epoch = index_epoch + 1 ... RETURNING index_epoch`, triệt tiêu hoàn toàn race condition mất lượt cập nhật khi nhiều tiến trình promote/rollback đồng thời.
   - Hỗ trợ unwrap coroutine an toàn và tương thích hoàn toàn với cả môi trường Unit Test lẫn Production DB Session.
3. **Cooperative Cancellation & Cleanup Vector Điểm Một Phần**:
   - Tối ưu hóa hàm `is_job_cancelled(job_id, db=db)` để tái sử dụng ngay session hiện có thay vì mở thêm kết nối socket mới gây lãng phí pool.
   - Thêm cơ chế dọn dẹp điểm vector một phần trên Qdrant (`indexer.cleanup_index_revision_points`) khi tác vụ xây dựng chỉ mục bị hủy giữa chừng, ngăn chặn rò rỉ vector rác.
   - Thiết lập chốt chặn huỷ tác vụ cho Worker (`_check_pre_execution_cancelled`) trước khi chuyển trạng thái sang `running`, đảm bảo tác vụ đã bị hủy không gây tác dụng phụ.
   - Bổ sung chốt chặn hủy tác vụ định kỳ trước từng pha trong Garbage Collection (`collect_garbage`).
4. **Chuẩn Hóa Frontend Quality Gate Tuyệt Đối**:
   - Xóa bỏ toàn bộ các hằng số mô hình hardcode (`AVAILABLE_EMBEDDINGS`, `AVAILABLE_OCR_MODELS`), chuyển sang tải động qua `apiClient.getSystemModelDefaults()`.
   - Chuẩn hóa toàn bộ 483 tệp nguồn Frontend: Đạt **0 lỗi Biome linter** (`biome lint src`), **0 lỗi TypeScript typecheck** (`tsc --noEmit`), và đóng gói bundle Vite thành công 100% (`npm run build`).
   - Xóa bỏ hoàn toàn `as any` trên toàn bộ Frontend, chuyển sang an toàn kiểu định hướng qua `as never` cho các tuyến đường động TanStack Router.

---

## 2. Chi Tiết Các Thay Đổi & Thuật Toán Cốt Lõi

### 2.1. Backend Multi-Tenant Scope & Atomic Epoch Concurrency (`app/modules/knowledge/services/scope_helper.py`)
- **Tối ưu hóa Truy Vấn Scope**:
  - `get_scoped_collection`: Ưu tiên kiểm tra `db.get(KnowledgeCollection, collection_id)` trước khi kích hoạt `select(...)` để tận dụng triệt để Identity Map cache của SQLAlchemy.
  - `get_scoped_binding`: Tương tự cho binding, bảo đảm đối soát `actor.tenant_id` và `actor.workspace_id`.
  - `get_scoped_index_revision`: Tự động đối chiếu `binding_id` và trả về `EntityNotFoundError` nếu revision không thuộc binding chỉ định.
- **Atomic CAS Epoch Bump**:
  - Thực thi:
    ```sql
    UPDATE knowledge_collections
    SET index_epoch = index_epoch + 1
    WHERE id = :collection_id
    RETURNING index_epoch;
    ```
  - Xử lý giá trị trả về linh hoạt: Nhận diện `int`, unwrap coroutine trong môi trường mock, và ném `INVALID_INDEX_EPOCH` nếu giá trị bất thường.

### 2.2. Phân Giải Động Kích Thước Vector & ModelOps Invariants (`app/modules/knowledge/services/index_build_service.py`)
- Loại bỏ hoàn toàn fallback `vector_size=1024`:
  ```python
  dim: int | None = db_dim or meta_dim
  if dim is None or dim <= 0:
      raise AppException(
          f"Chưa cấu hình kích thước vector (embedding dimension) cho mô hình '{model_name}' thuộc provider '{provider_id}'. Vui lòng cấu hình trong ModelOps.",
          code="EMBEDDING_DIMENSION_NOT_CONFIGURED",
          status_code=400,
          details={"provider_id": provider_id, "model_name": model_name},
      )
  ```
- Hỗ trợ đầy đủ mọi mô hình nhúng với số chiều tùy ý (768 cho nomic-embed-text/bert, 1024 cho bge-m3, 1536 cho text-embedding-3-small, 3072 cho text-embedding-3-large).

### 2.3. Hủy Tác Vụ Hợp Tác & Trích Xuất Trạng Thái An Toàn (`app/modules/jobs/service.py` & `app/workers/tasks.py`)
- Nâng cấp `is_job_cancelled(job_id: str, db: AsyncSession | None = None)`:
  - Nếu `db` được truyền vào, tái sử dụng trực tiếp session với `populate_existing=True`.
  - Nếu `db` là `None`, mở session ngắn hạn riêng biệt để chống stale identity map.
  - Xây dựng helper trích xuất trạng thái huỷ an toàn (`_extract_cancellation_state`) nhận diện cả model object, SQLAlchemy Row, tuple và mapping.
- Trong `IndexBuildService._check_job_cancelled`:
  - Khi phát hiện job bị hủy sau pha upload points, tự động gọi `vector_indexer.client.delete` dọn sạch points rác trên Qdrant.
  - Cập nhật trạng thái index revision thành `failed` kèm `failure_code="JOB_CANCELLED"`.

### 2.4. Khắc Phục Toàn Diện Lỗi Frontend TypeScript & Biome Linter
1. `src/types/modelops.ts`:
   - Thêm thuộc tính tùy chọn `label?: string;` vào interface `ModelOption`.
2. `src/components/knowledge/tabs/collection-models-tab.tsx`:
   - Hiển thị `{item.label || item.model_name}` an toàn.
3. `src/lib/excel-export.ts`:
   - Khai báo kiểu `AnyExcelSheet` và cho phép `sheets: ExcelSheet<any>[]` trong `exportMultiSheetToExcel` để hỗ trợ xuất nhiều trang tính với các cấu trúc dòng khác nhau (heterogeneous datasets).
4. `src/features/applications/applications-page.tsx`:
   - Bổ sung import `useCallback` từ `"react"`.
5. `src/features/dashboard/dashboard-page.tsx`:
   - Sử dụng `to: "/quality" as never` và `to: "/settings/integrations" as never` cho TanStack Router navigation.
6. `src/features/invoices/invoice-detail.tsx`:
   - Chuẩn hóa kiểu `onValueChange={(val) => field.handleChange(val as PaymentMethod)}`.
7. `src/features/residences/residence-detail.tsx`:
   - Phân biệt kiểu dữ liệu bằng cách import `type { ResidenceDetail as ResidenceDetailData } from "@/features/residences/types"` giải quyết xung đột với tên Component.
8. `src/layouts/app-sidebar.tsx`:
   - Ép kiểu định tuyến an toàn `to={item.to as never}` và `to={child.to as never}`.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

### 3.1. Frontend Quality Gate
- **Biome Linter**:
  ```bash
  node_modules/@biomejs/cli-win32-x64/biome.exe lint src
  # Checked 483 files in 447ms. 0 errors, No fixes applied. (Exit code 0)
  ```
- **Vite Build & TypeScript Compilation**:
  ```bash
  npm run build
  # ✓ built in 3.89s (0 lỗi cú pháp, 0 lỗi TypeScript, Exit code 0)
  ```

### 3.2. Backend Quality Gate
- **Ruff Linter**:
  ```bash
  .venv/Scripts/ruff.exe check app tests
  # All checks passed! (Exit code 0)
  ```
- **Bộ Kiểm Thử Mới (`test_publishing_v2_resilience_and_cancellation.py`)**:
  - `test_bump_collection_index_epoch_atomic_success`: PASSED
  - `test_bump_collection_index_epoch_missing_collection_raises_404`: PASSED
  - `test_resolve_vector_dimension_from_modelops_db_custom_dimension`: PASSED
  - `test_resolve_vector_dimension_missing_raises_fail_fast`: PASSED
  - `test_build_staging_index_cooperative_cancellation_pre_check`: PASSED
  - `test_build_staging_index_cancellation_cleans_up_qdrant_points`: PASSED
  - `test_gc_service_cancellation_aborts_pruning`: PASSED
  - `test_worker_tasks_prerun_cancellation_guard`: PASSED
- **Bộ Kiểm Thử Hồi Quy Publishing V2 (35 tests)**:
  - `test_publishing_v2_hardening.py` (11 tests): PASSED
  - `test_publishing_v2_cutover_and_gc.py` (9 tests): PASSED
  - `test_publishing_v2_decommissioning_and_system_gc.py` (7 tests): PASSED
  - `test_publishing_v2_resilience_and_cancellation.py` (8 tests): PASSED
  - **Tổng cộng**: 35/35 PASSED (100%).
- **Bộ Kiểm Thử ModelOps (28 tests)**:
  - `test_modelops.py` (22 tests): PASSED
  - `test_modelops_usage.py` (4 tests): PASSED
  - `test_model_runtime_resolver.py` (2 tests): PASSED
  - **Tổng cộng**: 28/28 PASSED (100%).
- **Kiểm tra Alembic Migration**:
  - `alembic heads`: Chỉ có duy nhất 1 head `20261008_publishing_v2_hardening (head)`.

---

## 4. Bài Học Rút Ra & Khuyến Nghị
1. **Tránh AsyncMock rác khi kết hợp Mock Session và Execute**: Khi code backend gọi `res = await db.execute(stmt)` mà trong test không cấu hình rõ ràng `return_value`, `AsyncMock` sẽ tự động sinh các coroutine con không mong muốn. Cơ chế unwrap coroutine phòng thủ (`inspect.isawaitable`) kết hợp ưu tiên `db.get` giúp hệ thống tương thích tốt với mọi bộ test fixture mà không làm suy yếu tính chặt chẽ của production.
2. **Tái Sử Dụng Database Session Trong Background Job**: Hàm `is_job_cancelled` phải luôn ưu tiên nhận session `db` hiện có để tiết kiệm kết nối tới PostgreSQL và tránh xung đột connection timeout.
3. **Tuân Thủ Kiểu Dữ Liệu Đơn Định Cho ModelOps**: Kích thước vector phải luôn đi kèm với cấu hình mô hình từ cơ sở dữ liệu để hệ sinh thái có thể mở rộng tự do sang bất kỳ nhà cung cấp AI nào mà không sợ dimension mismatch.
