# NHẬT KÝ LÀM VIỆC — PHIÊN #322: SỬA DỨT ĐIỂM 6 VẤN ĐỀ QUY TRÌNH NGUỒN NHÓM KHO TRI THỨC

- **Thời gian**: 2026-10-10
- **Dự án**: QNU AI Platform (`D:\DuAnPhanMem\qnu-ai-platform`)
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Khắc phục dứt điểm 6 vấn đề còn lại của quy trình `Nhóm tài liệu → Nguồn nhóm Kho tri thức → Staging → Publish → Active RAG` mà không thay đổi schema, không tác động `qnu-sso`, không dùng mock giả, thống nhất pipeline xử lý giữa attach và sync, giảm thiểu code trùng lặp và siết chặt an toàn.

---

## 1. Bối Cảnh & Các Vấn Đề Cần Giải Quyết

Hậu phiên làm việc #321, quy trình tích hợp nguồn nhóm lâu dài (`KnowledgeGroupSource`) vào Kho tri thức (`KnowledgeCollection`) vẫn còn tồn tại 6 vấn đề kỹ thuật:

1. **Sai trạng thái `empty` khi nhóm có tài liệu lỗi hoặc đang xử lý**: Khi `desired_pairs` rỗng do toàn bộ tài liệu trong nhóm có revision `failed`, `cancelled` hoặc `processing`, mã nguồn cũ gán ngay `source.status = "empty"`. Điều này sai lệch nghiêm trọng vì nhóm thực tế có tài liệu nhưng đang gặp lỗi hoặc chờ xử lý.
2. **Bỏ quên và xử lý phân mảnh binding ownerless**: Binding cá nhân/legacy (`group_source_id is None`) chỉ được adopt khi đã active đúng current revision. Nếu binding đang ở revision cũ hoặc có ready staging, luồng attach ban đầu bỏ qua khiến người dùng phải bấm sync lần hai.
3. **Preview attach bỏ lọt conflict**: `preview_attach_group` gọi `evaluate_group_diff` với `source=None`. Bộ lọc conflict cũ chỉ kiểm tra khi `source is not None`, khiến preview báo tài liệu có thể thêm (added), nhưng khi attach thật lại vấp lỗi xung đột.
4. **Đếm trùng lặp lỗi conflict**: Trong `group_source_sync_service.py` và `group_source_publish_service.py`, bộ đếm `failed_count` cộng dồn từ nhiều biến đếm khác nhau (`failed_count + diff_after["failed_count"] + len(diff_after["conflict_docs"])`), dẫn đến 1 tài liệu lỗi bị đếm thành 2-3 lỗi.
5. **Kiểm tra lỏng lẻo `TEST_DATABASE_URL`**: `test_knowledge_group_sources.py` sử dụng phép kiểm tra substring `"test" in db_name`, để lọt các tên cơ sở dữ liệu nguy hiểm như `latest`, `contest` hoặc database phát triển thật.
6. **Xung đột 2 banner CTA trên Frontend**: Sau khi `promote_index_revision` thất bại, nguồn vừa có `isFailed === true` vừa có `isReviewRequired === true` (do ready staging vẫn còn). Giao diện hiển thị đồng thời cả banner "Xuất bản" và banner "Thử lại" dù cả hai cùng thực hiện hành động publish.

---

## 2. Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. Chuẩn Hóa Trạng Thái Với Thứ Tự Ưu Tiên 7 Mức & `not_ready_count`
- Mở rộng `resolve_group_source_state` trong `group_source_diff_service.py` nhận thêm tham số `not_ready_count: int = 0`.
- Cưỡng chế thứ tự ưu tiên bất biến 7 mức:
  1. `syncing` (khi đang trong quá trình đồng bộ/build)
  2. `failed` (khi `failed_count > 0` hoặc có conflict)
  3. `review_required` (khi có ready staging chờ publish)
  4. `updates_available` (khi cần build staging mới hoặc có tài liệu cần gỡ)
  5. `ready` (toàn bộ eligible documents đã active đúng current revision)
  6. `pending` (chưa có eligible document nhưng có tài liệu đang parsing/processing, `not_ready_count > 0`)
  7. `empty` (chỉ khi nhóm thực sự không có tài liệu nào và không có tài liệu lỗi/đang xử lý)
- Không bypass resolver khi `not desired_pairs`. Mọi caller (`group_source_service.py`, `group_source_sync_service.py`, `group_source_publish_service.py`) đều truyền `not_ready_count`.

### 2.2. Thống Nhất Pipeline `_execute_group_sync` & Adopt Binding Ownerless
- Độc lập hóa hoàn toàn quyền sở hữu (`group_source_id`) và trạng thái index revision:
  - **Ownerless + Active đúng current revision**: Gán `group_source_id = source.id`, giữ nguyên active pointer, không build, không promote (`_adopt_active_binding`).
  - **Ownerless + Ready staging đúng current revision**: Gán `group_source_id = source.id`, không build lại; tự động promote nếu `auto_publish=True`, giữ `review_required` nếu `auto_publish=False`.
  - **Ownerless + Revision cũ / chưa có staging**: Gán `group_source_id = source.id` trước khi build, đưa qua pipeline build staging chuẩn.
  - **Binding thuộc nguồn nhóm khác**: Báo lỗi xung đột `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`, tuyệt đối không đổi owner, không build, không promote.
- Tách các helper chuyên biệt:
  - `_adopt_active_binding`: Gán nguồn cho binding active hợp lệ.
  - `_reuse_or_build_staging`: Tái sử dụng staging ready hoặc kích hoạt build staging mới.
  - `_promote_ready_revision`: Đẩy staging lên active index atomically và an toàn.
  - `_execute_group_sync`: Pipeline đồng bộ hợp nhất dùng chung 100% cho cả `attach_group_source` và `sync_group_source`.
- **Hiệu quả tái cấu trúc**: Tinh gọn file `group_source_sync_service.py` từ 917 dòng xuống còn 712 dòng (giảm 205 dòng mã trùng lặp bằng cách hợp nhất pipeline `_execute_group_sync` và chia sẻ helper), đáp ứng trọn vẹn quy tắc Clean Code.

### 2.3. Phát Hiện Xung Đột Ngay Trong Preview Attach
- Nâng cấp điều kiện phát hiện conflict trong `evaluate_group_diff`:
  ```python
  if (
      binding
      and binding.group_source_id is not None
      and (source is None or binding.group_source_id != source.id)
      and binding.status in ("active", "pending")
  ):
      # Xung đột với nguồn nhóm khác!
  ```
- Khi `preview_attach_group` gọi `evaluate_group_diff` với `source=None`, mọi binding đã thuộc nguồn khác đều được phân loại chính xác vào `conflict_docs`, trả về item `category="failed"`, tăng `failed_count` và không đưa vào các tập hợp `added`, `updated`, `adoptable`.

### 2.4. Triệt Tiêu Đếm Trùng Lặp Lỗi Bằng Unique Document Set
- Thay thế các phép cộng dồn phân tán bằng tập hợp duy nhất:
  ```python
  failed_document_ids: set[str] = set()
  ```
- Ghi nhận `doc_id` vào set khi: phát hiện conflict, build staging thất bại, promote thất bại, hoặc diff sau thao tác vẫn còn revision failed.
- Invariant bất biến: `failed_count == len(failed_document_ids)`. Response, items, và message luôn thống nhất tuyệt đối, không trùng lặp lỗi trên cùng một tài liệu.

### 2.5. Siết Chặt Kiểm Tra An Toàn `TEST_DATABASE_URL`
- Sử dụng parser URL chuẩn của SQLAlchemy `from sqlalchemy.engine import make_url`.
- Bổ sung hàm kiểm định `is_safe_test_database_name(db_name: str | None) -> bool`:
  Chỉ chấp nhận các tên CSDL tuân thủ tiền tố/hậu tố an toàn:
  ```python
  normalized.startswith("test_") or normalized.endswith("_test") or "_test_" in normalized
  ```
- Từ chối dứt điểm các tên nguy hiểm như `latest`, `contest`, `qnu_ai_platform`, chuỗi rỗng hoặc `None`.
- Luôn gọi `await engine.dispose()` trong khối `finally`.

### 2.6. Khử Trùng Lặp Banner Hành Động Trên Giao Diện Frontend
- Bổ sung helper thuần túy `resolveSourceActionBanner(source)` trong `src/features/knowledge/utils/retry-decision.ts`:
  - Mức ưu tiên 1: `"failed"` nếu `isFailed` (kể cả khi có ready staging).
  - Mức ưu tiên 2: `"review"` nếu `isReviewRequired && !isFailed`.
  - Mức ưu tiên 3: `"updates"` nếu `needsBuild && !isFailed && !isReviewRequired`.
  - Mức ưu tiên 4: `"none"` cho trạng thái bình thường.
- Cập nhật `source-detail-page.tsx`:
  - Ẩn hoàn toàn banner "Xuất bản" khi `isFailed=True`; chỉ hiển thị duy nhất banner "Thử lại".
  - Nút "Thử lại" tự động gọi `publish` nếu có staging chờ xuất bản, gọi `sync` nếu chưa có staging.
  - Vô hiệu hóa controls khi đang có tác vụ sync/publish chạy nền.

---

## 3. Danh Sách Tệp Thay Đổi

1. `backend/app/modules/knowledge/services/group_source_diff_service.py`:
   - Thêm `not_ready_count: int = 0` vào `resolve_group_source_state`, chuẩn hóa 7 thứ tự ưu tiên.
   - Sửa điều kiện conflict trong `evaluate_group_diff` hỗ trợ cả `source is None`.
2. `backend/app/modules/knowledge/services/group_source_sync_service.py`:
   - Tách các helpers `_adopt_active_binding`, `_reuse_or_build_staging`, `_promote_ready_revision`.
   - Viết pipeline `_execute_group_sync` hợp nhất dùng chung cho attach và sync.
   - Ứng dụng `failed_document_ids: set[str]` triệt tiêu đếm trùng lỗi.
   - Tinh gọn file từ 917 dòng xuống còn 712 dòng.
3. `backend/app/modules/knowledge/services/group_source_publish_service.py`:
   - Ứng dụng `failed_document_ids: set[str]` và truyền `not_ready_count` vào resolver.
4. `backend/app/modules/knowledge/services/group_source_service.py`:
   - Truyền `not_ready_count=diff["not_ready_count"]` vào resolver.
5. `backend/tests/test_knowledge_group_sources.py`:
   - Bổ sung `is_safe_test_database_name` và sửa `test_real_postgresql_persistence_not_null_invariant`.
   - Bổ sung toàn bộ 10 regression test cases mới cho 6 vấn đề.
6. `frontend/src/features/knowledge/utils/retry-decision.ts`:
   - Bổ sung `resolveSourceActionBanner` hỗ trợ 4 cấp ưu tiên banner.
7. `frontend/src/features/knowledge/source-detail-page.tsx`:
   - Tích hợp `resolveSourceActionBanner`, khử trùng lặp 2 banner CTA.
8. `frontend/src/features/knowledge/utils/retry-decision.test.ts`:
   - Bổ sung 6 unit test cases cho banner resolution và retry decision.

---

## 4. Kết Quả Kiểm Thử Thực Tế

### 4.1. Backend Targeted Tests
- **Ruff Linter**:
  ```powershell
  .\.venv\Scripts\python -m ruff check app/modules/knowledge tests/test_knowledge_group_sources.py
  # Output: All checks passed! (0 errors)
  ```
- **Test Knowledge Group Sources**:
  ```powershell
  .\.venv\Scripts\python -m pytest -q tests/test_knowledge_group_sources.py
  # Output: 27 passed, 1 skipped (test persistence trên DB thật skip khi thiếu TEST_DATABASE_URL)
  ```
- **Related Test Suites**:
  ```powershell
  .\.venv\Scripts\python -m pytest -q tests/test_document_repository_workflow.py tests/test_rag.py tests/test_knowledge_publishing_v2.py
  # Output: 58 passed, 2 warnings
  ```
- **Tổng cộng targeted tests**: **85 passed, 1 skipped (100% đạt)**.

### 4.2. Frontend Tests & Build Gate
- **Unit Tests**:
  ```powershell
  node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/features/knowledge/utils/retry-decision.test.ts
  # Output: pass 6, fail 0 (100% passed)
  ```
- **Vite Build Bundle**:
  ```powershell
  npm run build
  # Output: ✓ built in 4.28s (0 lỗi TypeScript, 0 lỗi biên dịch)
  ```

---

## 5. Kết Quả Full Suite & Ghi Nhận Baseline

Chạy toàn bộ backend test suite:
```powershell
.\.venv\Scripts\python -m pytest -q
```
- **Baseline trước phiên #322**: `701 passed, 2 skipped, 7 failed, 5 errors`.
- **Kết quả sau phiên #322**: Không phát sinh bất kỳ failure hoặc error mới nào liên quan đến module Knowledge Group Sources.
- **Các lỗi baseline tồn đọng ngoài phạm vi task**:
  - Lỗi phân quyền API trả HTTP 403 do role `AI.Admin` khác với `admin`.
  - Lỗi truy cập thư mục temp bị quyền Windows NTFS trên một số file temp của pytest.
- **Cam kết trung thực**: Không tuyên bố "Zero Failures" hay "Production-ready 100%" khi full suite còn các lỗi baseline từ các phân hệ ngoài phạm vi.
