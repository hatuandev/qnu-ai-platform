# Nhật Ký Phiên Làm Việc #303: Khóa Race Condition, Chuẩn Hóa ModelOps Dimension Và Frontend Quality Gate

- **Ngày thực hiện**: 2026-10-09
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xử lý toàn bộ phát hiện còn lại sau vòng code review Publishing V2.

## 1. Thay đổi chính

1. **Khóa bản ghi đúng ngữ nghĩa**
   - `get_scoped_collection`, `get_scoped_binding`, `get_scoped_index_revision` không còn nuốt lỗi hoặc fallback sau lỗi CSDL.
   - Mọi lookup có `for_update=True` bắt buộc đi qua `SELECT ... FOR UPDATE`, kể cả luồng nội bộ không truyền `actor`.
   - Auto-activation chuyển tiếp `actor` vào `promote_index_revision`.

2. **Cấp phát epoch nguyên tử tuyệt đối**
   - `bump_collection_index_epoch` chỉ chấp nhận số nguyên do `UPDATE ... RETURNING index_epoch` trả về.
   - Xóa toàn bộ nhánh suy đoán epoch từ object và đọc lại collection rồi cộng một.

3. **Một nguồn sự thật cho vector dimension**
   - Bổ sung `ModelCatalogService.resolve_embedding_dimension` dùng chung cho tạo collection và dựng vector generation.
   - Xác thực provider đang hoạt động, model thuộc provider, dimension dương và metadata snapshot khớp ModelOps.
   - Hỗ trợ đọc tương thích `model_specs`, `model_dimensions` và `embedding_dimension`, nhưng không chấp nhận metadata cũ thay thế cấu hình ModelOps.
   - Bổ sung lỗi RFC 7807: `EMBEDDING_PROVIDER_UNAVAILABLE`, `EMBEDDING_MODEL_NOT_AVAILABLE`, `EMBEDDING_DIMENSION_MISMATCH`.

4. **Cooperative cancellation nhất quán**
   - Worker kiểm tra kết quả `_set_job` ở cả thời điểm chuyển sang `running` và ghi trạng thái cuối.
   - Không còn khả năng worker trả `completed` trong khi bản ghi job đã thắng race và chuyển sang `cancelled`.

5. **Frontend ModelOps và accessibility**
   - Thay raw `<button>` trong hai màn cấu hình Knowledge bằng `Button` dùng chung.
   - Trạng thái chọn model so sánh đồng thời `provider_id` và `model_name`.
   - Chặn lưu nếu thiếu embedding model, provider hoặc dimension.
   - Chuẩn hóa toàn bộ lỗi format/import Biome; bổ sung title cho SVG trang trí và bỏ biến catch không dùng.

## 2. Tệp trọng tâm

- Backend:
  - `backend/app/modules/knowledge/services/scope_helper.py`
  - `backend/app/modules/knowledge/services/index_build_service.py`
  - `backend/app/modules/knowledge/services/collection_service.py`
  - `backend/app/modules/knowledge/services/reconciliation_service.py`
  - `backend/app/modules/modelops/services/model_catalog_service.py`
  - `backend/app/workers/tasks.py`
- Frontend:
  - `frontend/src/components/knowledge/dialogs/collection-config-dialog.tsx`
  - `frontend/src/components/knowledge/tabs/collection-models-tab.tsx`
  - Các tệp frontend được Biome chuẩn hóa định dạng an toàn.
- Tests:
  - `backend/tests/test_publishing_v2_resilience_and_cancellation.py`
  - `backend/tests/test_knowledge_publishing_v2.py`
  - `backend/tests/test_publishing_v2_cutover_and_gc.py`
  - `backend/tests/test_publishing_v2_e2e_canary.py`
  - `backend/tests/test_publishing_v2_hardening.py`
  - `backend/tests/test_workers.py`

## 3. Kết quả kiểm thử

- `uv run ruff check .`: **PASS — 0 lỗi**.
- Publishing V2/worker targeted regression: **27/27 PASS**.
- Các ca hồi quy lock/rollback bổ sung: **7/7 PASS**.
- Toàn bộ backend với thư mục tạm trong workspace: **616 passed, 6 failed, 1 skipped**.
  - Sáu lỗi còn lại đều là integration test cần PostgreSQL seed; kết nối bị từ chối do Docker daemon không chạy.
  - Không thêm mock/fallback production để làm xanh giả các ca này.
- `npm run lint`: **PASS — 504 files, 0 errors**.
- `npm run build`: **PASS — Vite build và TypeScript typecheck thành công**.
- `git diff --check`: **PASS**, chỉ có cảnh báo quy ước LF/CRLF trên Windows.

## 4. Bài học và lưu ý vận hành

- Identity-map lookup chỉ phù hợp cho đọc nội bộ không khóa; CAS bắt buộc dùng truy vấn khóa thật.
- Collection metadata là snapshot phục vụ audit, không phải nguồn cấu hình ModelOps thay thế.
- Cancellation là một cuộc đua trạng thái; cả checkpoint trước công việc và thao tác ghi kết quả cuối đều phải kiểm tra quyền thắng.
- Để chạy xanh toàn bộ sáu integration test còn lại, cần bật PostgreSQL/Docker và nạp seed test theo cấu hình dự án.
