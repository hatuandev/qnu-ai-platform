# Nhật Ký Làm Việc — Hoàn Thiện Nút Xóa Tác Vụ, Nút Dọn Dẹp Đã Xong & Khắc Phục Lỗi Hủy Job HTTP 409

- **Thời gian**: 2026-09-17 16:50 (UTC+7)
- **Phiên số**: #51
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  1. Khắc phục lỗi `Hủy job thất bại (HTTP 409)` khi người dùng bấm nút Hủy (`X`) trên tab Tiến trình tác vụ.
  2. Thêm nút Xóa tác vụ (`Trash2`) cho từng dòng trong bảng Tiến trình & Lịch sử tác vụ kèm dialog xác nhận.
  3. Hiện thực hóa chức năng của nút "Dọn dẹp đã xong" trên thanh công cụ tác vụ để xóa các tác vụ đã hoàn tất/đã hủy/lỗi.
  4. Triệt tiêu triệt để Mock Trap trong hàng đợi tác vụ khi danh sách trả về `[]`.

---

## 1. Phân Tích Nguyên Nhân Gốc Rễ

### 1.1. Lỗi HTTP 409 khi bấm nút Hủy (`X`)
- **Tình trạng**: Người dùng thấy tác vụ mang tên *"Nạp lại vector collection"* hiển thị badge *"Đang xử lý"* kèm nút Hủy (`X`). Khi bấm `X`, hệ thống báo lỗi đỏ: `(!) Hủy job thất bại (HTTP 409).`
- **Nguyên nhân trong DB & Backend**:
  - Truy vấn CSDL bảng `job_records` cho thấy bản ghi `job_01f26a79f7a9` đã có `status: "cancelled"` với lỗi `"Đã hủy bởi người dùng (cooperative cancel)."`.
  - Backend `backend/app/modules/jobs/service.py` có đoạn kiểm tra:
    ```python
    TERMINAL_STATUSES = ("completed", "failed", "cancelled")
    if job.status in TERMINAL_STATUSES:
        raise AppException(f"Job '{job_id}' đã kết thúc ({job.status}), không thể hủy.", code="job_already_terminal", status_code=409)
    ```
- **Nguyên nhân cốt lõi trong Frontend**:
  - Tại `frontend/src/services/api-client.ts`, hàm `mapJobToIngestionTask` trước đây viết:
    ```typescript
    status: status === "completed" ? "completed" : status === "failed" ? "failed" : "processing"
    ```
  - Khi `status` từ API trả về `"cancelled"`, logic trên đã gộp nhầm thành `"processing"`, làm UI hiểu lầm job vẫn đang chạy và render nút Hủy (`X`). Khi người dùng bấm `X`, request gửi lên Backend bị từ chối với mã 409 vì job thực chất đã hủy rồi!

### 1.2. Nút "Dọn dẹp đã xong" và nút xóa từng tác vụ
- Nút "Dọn dẹp đã xong" trong `collection-detail-page.tsx` trước đó hoàn toàn không có handler `onClick`.
- Bảng tác vụ chỉ có các nút: xem log Terminal, Retry (khi failed), Cancel (khi processing), thiếu nút Xóa (`Trash2`) để loại bỏ một bản ghi tác vụ cụ thể khỏi lịch sử.
- Backend thiếu endpoint `DELETE /jobs/{job_id}` và `DELETE /jobs/cleanup`.

---

## 2. Giải Pháp Kỹ Thuật Đã Thực Hiện

### 2.1. Backend (`app/modules/jobs/`)
1. **Idempotent Cancel**:
   - Nếu `job.status == "cancelled"`, phương thức `cancel_job` trả về ngay bản ghi job mà không throw 409, đảm bảo tính idempotent và an toàn khi retry/client desync.
2. **Bổ sung `delete_job`**:
   - Xóa vĩnh viễn bản ghi job khỏi CSDL `job_records` thông qua session `db.delete(job)`.
3. **Bổ sung `cleanup_jobs`**:
   - Nhận `collection_id` và danh sách trạng thái `statuses` (mặc định `completed,cancelled,failed`), thực thi câu lệnh bulk `delete(JobRecord).where(...)` và trả về `{"success": True, "deleted_count": count}`.
4. **FastAPI Router**:
   - Đăng ký route `DELETE /jobs/cleanup` trước `DELETE /jobs/{job_id}` để tránh router collision trong FastAPI.
5. **Bộ kiểm thử tự động**:
   - Bổ sung các test cases: `test_cancel_already_cancelled_is_idempotent`, `test_delete_job_success`, `test_cleanup_jobs_success`, `test_api_delete_job`, `test_api_cleanup_jobs`. Đạt 15/15 test passed cho module jobs và 122/122 test passed cho toàn bộ hệ thống.

### 2.2. Frontend (`api-client.ts` & `collection-detail-page.tsx`)
1. **Kiểu dữ liệu & Mapping chuẩn xác**:
   - Mở rộng kiểu `IngestionTask.status`: `"completed" | "processing" | "failed" | "cancelled"`.
   - Cập nhật `mapJobToIngestionTask` ánh xạ đúng `cancelled -> cancelled`.
2. **Triệt tiêu Mock Trap trong `getIngestionTasks`**:
   - Thay `if (mapped.length > 0) return mapped;` thành `if (Array.isArray(data)) return ...`. Khi backend trả về `[]`, hiển thị đúng Empty State, không fallback sang dữ liệu mock.
3. **Bổ sung phương thức API**:
   - `apiClient.deleteJob(jobId: string): Promise<void>` (hỗ trợ 404 idempotent).
   - `apiClient.cleanupJobs(collectionId?: string): Promise<{ deleted_count: number }>`.
4. **Cải tiến UI Tab Tiến trình & Lịch sử tác vụ**:
   - Thêm `TASK_STATUS_BADGE.cancelled`: nhãn "Đã hủy" với style badge muted tinh tế.
   - Hiển thị icon động theo từng trạng thái: `CheckCircle2` (Hoàn tất), `RefreshCw animate-spin` (Đang xử lý), `X` (Đã hủy), `CircleAlert` (Thất bại).
   - Bổ sung tùy chọn lọc trạng thái "Đã hủy" và "Thất bại" trong filter dropdown.
   - Thêm nút Xóa (`Trash2`) trên từng dòng tác vụ kèm `ConfirmDialog` xác nhận xóa.
   - Gắn handler cho nút "Dọn dẹp đã xong", vô hiệu hóa khi không có tác vụ kết thúc nào, mở `ConfirmDialog` xác nhận trước khi thực hiện dọn dẹp hàng loạt.
   - Hiển thị banner thông báo xanh `taskSuccessMessage` tự động ẩn sau khi thao tác thành công.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

```bash
# 1. Backend Lint & Tests
uv run ruff check .
# Output: All checks passed!

uv run --extra dev pytest tests/test_jobs.py -v
# Output: 15 passed in 2.94s (100%)

uv run --extra dev pytest tests/ -q
# Output: 122 passed in 33.13s (100%)

# 2. Frontend Lint & Build
npm run lint
# Output: Checked 77 files in 49ms. No fixes applied. (0 errors)

npm run typecheck
# Output: tsc --noEmit (0 errors)

npm run build
# Output: built in 13.59s (thành công)
```

## 4. Danh Sách Tệp Thay Đổi
- `backend/app/modules/jobs/service.py`
- `backend/app/modules/jobs/router.py`
- `backend/tests/test_jobs.py`
- `frontend/src/services/api-client.ts`
- `frontend/src/pages/collection-detail-page.tsx`
- `docs/memory/PROJECT_CONTEXT.md`
- `docs/memory/snapshots/2026-09-17_session_51.md`
- `docs/nhat_ky/2026-09-17_xoa_don_dep_tac_vu_va_fix_status_cancelled_409.md`
- `docs/WORK_LOG.md`
