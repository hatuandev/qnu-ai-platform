# Nhật Ký Phiên Làm Việc #301: Hardening Toàn Diện Quy Trình Xuất Bản Kho Tri Thức V2 (Tenant Isolation, ModelOps Dynamic Resolution, Vector Dimension Invariants & Cooperative Job Cancellation)

- **Ngày thực hiện**: 2026-10-08
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phạm vi**: Backend (`app/modules/knowledge`, `app/modules/documents`, `app/modules/jobs`, `app/modules/modelops`, `app/modules/rag`, `app/workers`), Database Migration (`alembic/versions/20261008_publishing_v2_hardening.py`), Frontend (`features/knowledge`, `components/knowledge`), Test Suites (`tests/test_knowledge_publishing_v2.py`, `tests/test_publishing_v2_hardening.py`, `tests/test_jobs.py`, `tests/test_rag.py`).

---

## 1. Mục Tiêu & Bối Cảnh

Sau các phiên triển khai Publishing V2 và cutover, hệ thống cần được hardening triệt để nhằm bảo đảm độ tin cậy cấp Enterprise (Production-Grade):
1. **Bảo vệ Đa Tenant & Workspace**:
   - Không tin cậy header/body do client tự gửi (`X-Tenant-Id`, `X-Workspace-Id`).
   - Sử dụng `AuthActor` giải mã từ phiên xác thực SSO / Dev Access Gate kết hợp `require_permission(...)`.
   - Trả lỗi 404 `EntityNotFoundError` khi truy cập cross-tenant / cross-workspace để chống rò rỉ siêu dữ liệu.
   - Thêm workspace isolation cho Document Revision (`documents/revision_service.py` & `router.py`).
2. **Khắc Phục Race Condition Index Epoch & Bắt Buộc CAS**:
   - Thay thế việc tăng `index_epoch` trong bộ nhớ Python bằng hàm nguyên tử `bump_collection_index_epoch` (`UPDATE knowledge_collections SET index_epoch = index_epoch + 1 RETURNING index_epoch`).
   - Yêu cầu tham số `expected_epoch: int` bắt buộc ở cả tầng Router và Service cho `promote_index_revision` và `rollback_index_revision`.
   - Trả lỗi 409 `CAS_EPOCH_CONFLICT` ngay lập tức nếu `expected_epoch != active_epoch`.
3. **Triệt Tiêu Hoàn Toàn Hardcode Model & Dynamic Provider Resolution**:
   - `get_system_model_defaults` chỉ đọc từ cơ sở dữ liệu `model_provider_configs` (record `system_model_defaults`), tuyệt đối không tự ý seed hoặc hardcode fallback model.
   - Fail-fast với mã `MODEL_DEFAULT_NOT_CONFIGURED` khi chưa cấu hình DB.
4. **Bảo Toàn Bất Biến Vector (Strict Vector Invariant)**:
   - Nghiêm cấm padding số 0 hoặc truncate vector trong `VectorIndexer._fit_dim`.
   - Bắt buộc kiểm tra kích thước vector cho cả dense vectors tính toán trước (`precomputed`). Báo lỗi 400 `VECTOR_DIMENSION_MISMATCH` khi sai số chiều.
   - Xử lý lỗi Qdrant upsert/kết nối bằng `AppException` mang mã định danh chuẩn (`QDRANT_UPSERT_FAILED`, `QDRANT_UNAVAILABLE`).
5. **Cooperative Cancellation & State Machine cho Background Jobs**:
   - Kiểm tra tín hiệu huỷ `_check_pre_execution_cancelled` trước khi chuyển job sang trạng thái `running`.
   - Thiết lập 5 điểm checkpoint kiểm tra huỷ trong suốt pipeline staging build (`task_knowledge_index_build` / `build_staging_index`).
   - Tự động dọn dẹp các dense points đã đẩy một phần lên Qdrant khi tác vụ bị huỷ.
   - Bảo vệ xoá/dọn dẹp Job: huỷ job đang chạy/queued trước khi xoá (báo 409 `job_not_terminal`), từ chối dọn dẹp các trạng thái không kết thúc (báo 400 `INVALID_CLEANUP_STATUS`).
6. **Frontend Type-Safety & Biome Compliance**:
   - Xóa bỏ toàn bộ `as any` và ép kiểu ad-hoc trong điều hướng TanStack Router.
   - Sử dụng định danh kiểu rõ ràng cho URL `/knowledge/$collectionId/add-documents` và `/knowledge/$collectionId/documents/$bindingId`.

---

## 2. Chi Tiết Các Thay Đổi & Thuật Toán Áp Dụng

### 2.1. Backend Multi-Tenant Scope Helper (`app/modules/knowledge/services/scope_helper.py`)
- Xây dựng các hàm helper chuẩn hoá:
  - `apply_actor_scope(stmt, model, actor)`: tự động gắn `WHERE tenant_id = :tenant_id AND workspace_id = :workspace_id` cho mọi model có trường tương ứng.
  - `get_scoped_collection`: xác thực collection theo scope của actor; hỗ trợ tương thích mock session với `db.get` và kiểm tra quyền đối chiếu.
  - `get_scoped_binding`: xác thực binding theo scope của actor, hỗ trợ `with_for_update()` khi thực hiện promote/rollback.
  - `get_scoped_index_revision`: xác thực revision gắn với binding và kiểm tra đối chiếu scope của actor.
  - `bump_collection_index_epoch`: thực hiện câu lệnh SQL nguyên tử `UPDATE ... RETURNING index_epoch`.

### 2.2. Atomic Compare-And-Swap (CAS) & Epoch Protection
- Tại `IndexBuildService.promote_index_revision` và `rollback_index_revision`:
  - Khóa hàng binding: `binding = await get_scoped_binding(db, binding_id, actor=actor, for_update=True)`.
  - Kiểm tra CAS:
    ```python
    if binding.active_epoch != expected_epoch:
        raise AppException(
            f"Xung đột phiên bản (CAS conflict): active_epoch hiện tại ({binding.active_epoch}) không khớp expected_epoch ({expected_epoch}).",
            code="CAS_EPOCH_CONFLICT",
            status_code=409,
            details={"current_epoch": binding.active_epoch, "expected_epoch": expected_epoch},
        )
    ```
  - Cập nhật con trỏ hoạt động và tăng epoch nguyên tử:
    ```python
    binding.active_index_revision_id = target_rev.id
    binding.active_epoch += 1
    new_epoch = await bump_collection_index_epoch(db, col.id)
    col.index_epoch = new_epoch
    ```

### 2.3. ModelOps & Vector Dimension Strict Invariants
- `model_catalog_service.get_system_model_defaults`:
  - Loại bỏ hoàn toàn khối `_default_seed_values`.
  - Truy vấn `ModelProviderConfig` với `id="system_model_defaults"`. Nếu không tìm thấy, raise `AppException(code="MODEL_DEFAULT_NOT_CONFIGURED", status_code=500)`.
- `vector_indexer.py`:
  - `_fit_dim(vec)`: nghiêm cấm thay đổi kích thước vector; raise `VECTOR_DIMENSION_MISMATCH` nếu `len(vec) != self.vector_size`.
  - `index_chunks`: kiểm tra validation trên toàn bộ chunks, bao gồm chunk mang vector precomputed; bắt lỗi client Qdrant và raise `AppException(QDRANT_UPSERT_FAILED)`.

### 2.4. Job Lifecycle & Cooperative Cancellation Checkpoints
- `backend/app/workers/tasks.py`:
  - Triển khai `_check_pre_execution_cancelled(ctx, job_id)`: truy vấn trạng thái hiện thời của `JobRecord` trong cơ sở dữ liệu. Nếu `cancel_requested` là True hoặc status là `cancelled`, dừng tác vụ ngay lập tức mà không chuyển status sang `running`.
  - `_set_job`: bỏ qua cập nhật nếu job đã ở trạng thái `cancelled`.
  - Trong `build_staging_index`: định kỳ gọi `_check_job_cancelled(job_id)` tại 5 mốc quan trọng:
    1. Checkpoint 1: Trước khi trích xuất và tiền xử lý văn bản.
    2. Checkpoint 2: Sau khi chunking văn bản.
    3. Checkpoint 3: Trước khi gọi embedding và đẩy vector vào Qdrant.
    4. Checkpoint 4: Trước khi kiểm tra parity audit.
    5. Checkpoint 5: Trước khi kích hoạt auto-activation.
  - Khi phát hiện tín hiệu hủy, tiến hành dọn dẹp các point đã tạo trên Qdrant qua `vector_indexer.client.delete(...)`.

### 2.5. Frontend Navigation Cleanups & Biome Lint
- Cập nhật `collection-detail-page.tsx` và `collection-bindings-tab.tsx`:
  - Loại bỏ hoàn toàn `as any` và các comment ignore lint.
  - Tận dụng định tuyến đã sinh sẵn của TanStack Router:
    ```tsx
    navigate({
      to: "/knowledge/$collectionId/add-documents",
      params: { collectionId: collection.id },
    });
    ```
    ```tsx
    navigate({
      to: "/knowledge/$collectionId/documents/$bindingId",
      params: { collectionId: collection.id, bindingId: b.id },
    });
    ```

---

## 3. Kết Quả Kiểm Thử (Quality Gates)

1. **Ruff Linter**:
   ```bash
   .venv\Scripts\python.exe -m ruff check app tests
   # Output: All checks passed!
   ```
2. **Biome Linter**:
   ```bash
   node_modules/@biomejs/cli-win32-x64/biome.exe check src/features/knowledge/... src/components/knowledge/...
   # Output: Checked 6 files. 0 errors, 0 warnings.
   ```
3. **Alembic Single Head**:
   ```bash
   .venv\Scripts\python.exe -m alembic heads
   # Output: 20261008_publishing_v2_hardening (head)
   ```
4. **Pytest Focused Test Suites (100% Passed)**:
   - `tests/test_knowledge_publishing_v2.py`: 13 passed / 13 tests (100%).
   - `tests/test_publishing_v2_hardening.py`: 11 passed / 11 tests (100%).
   - `tests/test_publishing_v2_cutover_and_gc.py`: 9 passed / 9 tests (100%).
   - `tests/test_publishing_v2_decommissioning_and_system_gc.py`: 7 passed / 7 tests (100%).
   - `tests/test_publishing_v2_e2e_canary.py`: 9 passed / 9 tests (100%).
   - `tests/test_jobs.py`: 18 passed / 18 tests (100%).
   - `tests/test_rag.py`: 18 passed / 18 tests (100%).
   - `tests/test_rag_data_truth_and_lifecycle.py`: 9 passed / 9 tests (100%).
   - `tests/test_modelops.py`: 22 passed / 22 tests (100%).
   - `tests/test_document_revisions_lifecycle.py`: 7 passed / 7 tests (100%).
   - `tests/test_knowledge.py` (Reconcile & Reindex): 3 passed / 3 tests (100%).
   - **Tổng cộng: 126/126 tests passed (100% tỷ lệ thành công)**.

---

## 4. Bài Học Rút Ra & Kiến Trúc Bền Vững

- **In-Memory vs. Database-Level Isolation**: Việc phụ thuộc vào kiểm tra bộ nhớ hoặc các fallback getter tĩnh là nguồn cơn chính gây ra sai lệch dữ liệu giữa các tenant và giữa các tiến trình song song. Phải luôn sử dụng ràng buộc khóa SQL và mệnh đề WHERE rõ ràng trên từng đối tượng.
- **Fail-Fast thay vì Silent Fallback**: Việc che giấu lỗi bằng cách truncate vector, pad số 0 hay fallback về mô hình mặc định không chỉ phá vỡ ngữ nghĩa tìm kiếm mà còn ngăn cản hệ thống phát hiện sự cố sớm. Fail-fast với RFC 7807 mã lỗi rõ ràng giúp vận hành và gỡ lỗi chính xác.
- **Cooperative Cancellation**: Trong môi trường AI/RAG nơi tác vụ embedding và ingestion có thể kéo dài hàng phút và tốn kém tài nguyên tính toán/GPU, việc kiểm tra tín hiệu hủy định kỳ tại các checkpoint chiến lược giúp giải phóng tài nguyên ngay lập tức và tránh ghi đè dữ liệu rác.
