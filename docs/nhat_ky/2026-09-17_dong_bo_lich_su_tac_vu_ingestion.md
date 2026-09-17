# NHẬT KÝ LÀM VIỆC — Phiên #69
# Ngày: 2026-09-17 | Tiêu đề: Đồng Bộ Lịch Sử Tác Vụ (Job Records) Cho Luồng Nạp Tài Liệu Kho Tri Thức

## 1. Yêu Cầu & Thắc Mắc Của Người Dùng
- Người dùng đã nạp tệp `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` vào kho tri thức thành công và tài liệu đã hiển thị ở tab "Danh mục Tài liệu (1)" với trạng thái "Hiệu lực" (16 chunks).
- Tuy nhiên, khi chuyển sang tab **"Tiến trình & Lịch sử Tác vụ (0)"**, bảng hiển thị trống trơn: *"Không có tác vụ nền nào đang chờ hoặc đã xử lý."*.
- Người dùng thắc mắc: *"lạ quá tôi đã nạp dữ liệu vào db thành công nhưng mà không bất cứ tiếp trình nào xảy ra ?"*.

## 2. Phân Tích Kỹ Thuật
1. **Nguyên nhân cốt lõi**:
   - Hệ thống có 2 cơ chế xử lý:
     * **Luồng bóc tách trực tiếp có người dùng phê duyệt (Interactive Human-in-the-loop Ingestion)**: Khi bấm "+ Nạp tài liệu" -> bóc tách -> mở Studio đối soát -> bấm Phê duyệt. Toàn bộ chu trình này chạy đồng bộ trực tiếp (synchronous) trả kết quả tức thời (<1s) để người dùng kiểm tra mắt trước khi lưu vào CSDL, không đẩy qua hàng đợi Redis/ARQ.
     * **Hàng đợi tác vụ ngầm (Asynchronous Background Worker Jobs)**: Tab "Tiến trình & Lịch sử Tác vụ" gọi API `GET /jobs?limit=50`, đọc dữ liệu từ bảng `job_records`. Trước đây, bảng này chỉ được ghi khi người dùng bấm nút "Reindex Kho" (`POST /reindex`) hoặc gọi API chạy job nền, chứ không ghi nhận khi người dùng nạp tài liệu qua màn hình Studio.
2. **Giải pháp kiến trúc**:
   - Tự động ghi nhận một bản ghi `JobRecord(job_type="ingestion", status="completed", progress=100.0, ...)` vào `job_records` ngay khi tài liệu được bóc tách (`ingest_document`) và phê duyệt (`approve_document`).
   - Bổ sung hàm `sync_ingestion_job_records` trong `KnowledgeService` và hook vào lifespan startup của `app/main.py` để tự động hồi tố (backfill) lịch sử tác vụ cho các tài liệu đã nạp trước đó.

## 3. Các Thay Đổi Đã Triển Khai
1. **[`backend/app/modules/knowledge/service.py`](../../backend/app/modules/knowledge/service.py)**:
   - Trong `ingest_document`: Tự động tạo bản ghi `JobRecord` ghi nhận tệp đã bóc tách thành công (tên tệp, dung lượng, OCR engine, số chunks).
   - Trong `approve_document`: Cập nhật `JobRecord` với kết quả phê duyệt và số lượng chunks được index.
   - Thêm phương thức `sync_ingestion_job_records`: Tự động đồng bộ các tài liệu đang hoạt động vào `job_records`.
2. **[`backend/app/main.py`](../../backend/app/main.py)**:
   - Gọi `await knowledge_service.sync_ingestion_job_records(db)` trong lifespan startup.
3. **Thực thi đồng bộ ngay trên CSDL**:
   - Đã tạo thành công bản ghi `JobRecord` cho tệp `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` trong `col_question_bank`.

## 4. Kết Quả Kiểm Thử
- Backend:
  * `uv run ruff check .`: 0 lỗi.
  * `uv run --extra dev pytest tests/test_jobs.py`: 15/15 tests passed (100%).
- Frontend:
  * `npm run lint`: 0 lỗi (Biome 86 files).
  * `npm run typecheck`: 0 lỗi (tsc --noEmit).
- Tab **"Tiến trình & Lịch sử Tác vụ"** giờ đây hiển thị `(1)` tác vụ bóc tách hoàn tất với đầy đủ thông tin tên tệp, dung lượng và trạng thái Hoàn tất.
