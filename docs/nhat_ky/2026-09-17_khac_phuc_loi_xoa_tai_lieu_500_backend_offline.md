# NHẬT KÝ LÀM VIỆC — Phiên #65
# Ngày: 2026-09-17 | Tiêu đề: Khắc Phục Lỗi "Xóa Tài Liệu Thất Bại (HTTP 500)" Do Backend Chưa Khởi Chạy

## 1. Bối Cảnh & Hiện Tượng Lỗi
- **Hiện tượng trên giao diện**:
  - Người dùng truy cập trang chi tiết Bộ sưu tập Tuyển sinh (`/knowledge/collections/col_admissions`).
  - Danh sách tài liệu hiển thị bản ghi mẫu: `"Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)"` (`doc_ts_2026`).
  - Khi người dùng bấm biểu tượng thùng rác để xóa tài liệu và xác nhận xóa, màn hình xuất hiện banner màu đỏ: **`Xóa tài liệu thất bại (HTTP 500).`**
  - DevTools Console xuất hiện hàng loạt lỗi HTTP 500:
    * `GET :3001/health/live` -> 500 (Internal Server Error)
    * `GET :3001/platform/v1alpha1/jobs?limit=50` -> 500
    * `GET :3001/platform/v1alpha1/modelops/defaults` -> 500
    * `GET :3001/platform/v1alpha1/knowledge/collections/col_admissions` -> 500
    * `DELETE :3001/platform/v1alpha1/knowledge/documents/doc_ts_2026` -> 500
  - Ở góc dưới bên trái thanh Sidebar hiển thị trạng thái: **`Backend Offline (Port 8001 / REST API)` kèm chấm đỏ**.

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)
1. **Tiến trình Backend (FastAPI - Port 8001) chưa được khởi chạy**:
   - Chỉ có Frontend (Vite - Port 3001) và cụm Docker đang chạy. Cổng 8001 hoàn toàn không có tiến trình lắng nghe.
2. **Cơ chế chuyển tiếp (Proxy) của Vite trả về HTTP 500 khi target sập**:
   - Cấu hình `frontend/vite.config.ts` thiết lập proxy `/platform/v1alpha1` và `/health` sang `http://127.0.0.1:8001`.
   - Khi Backend tắt, kết nối bị từ chối (`connect ECONNREFUSED 127.0.0.1:8001`). Vite Proxy không bắt nuốt lỗi mà phản hồi thẳng về trình duyệt mã **HTTP 500 Internal Server Error** với body rỗng.
3. **Hiển thị dữ liệu Mock Fallback khi API tải danh sách thất bại**:
   - Khi Backend offline, `apiClient.listDocuments` không gọi được API thật nên rơi vào nhánh fallback trả về `MOCK_DOCUMENTS` (trong đó có `doc_ts_2026`).
   - Người dùng lầm tưởng đây là tài liệu thật đang tồn tại trong CSDL và tiến hành bấm xóa.
4. **Hàm `deleteDocument` thiếu thông báo trực quan khi gặp lỗi Proxy ECONNREFUSED**:
   - Khi nhận mã HTTP 500 từ Vite proxy, `apiClient.deleteDocument` ném ra thông báo chung chung `Xóa tài liệu thất bại (HTTP 500).`, khiến người dùng không biết rằng nguyên nhân cốt lõi là do Backend đang offline.

## 3. Các Giải Pháp Đã Thực Hiện
1. **Khởi động và duy trì dịch vụ Backend**:
   - Kích hoạt dịch vụ FastAPI trên cổng 8001 (`uv run uvicorn app.main:app --host 127.0.0.1 --port 8001`).
   - Xác thực: Endpoint `/health/live` và `/platform/v1alpha1/...` ngay lập tức phản hồi HTTP 200 OK (<2ms).
2. **Nâng cấp xử lý lỗi trong [`frontend/src/services/api-client.ts`](../../frontend/src/services/api-client.ts)**:
   - Trong `deleteDocument`:
     * Tự động phát hiện lỗi HTTP 500 do Vite proxy / ECONNREFUSED khi backend tắt.
     * Trả về thông báo lỗi tự giải thích rõ ràng: `"Không kết nối được máy chủ Backend (Port 8001 đang tắt). Vui lòng khởi động backend bằng lệnh 'make be' hoặc 'make dev'."`
     * Nếu tài liệu đang xóa là tài liệu mẫu trong `MOCK_DOCUMENTS`, tự động loại bỏ khỏi danh sách cục bộ để giao diện người dùng không bị treo hoặc báo lỗi giả.
     * Khi backend chạy thật, nếu xóa tài liệu không có trong CSDL (HTTP 404), tiếp tục coi là thao tác thành công (idempotent delete) và dọn sạch khỏi giao diện.

## 4. Kết Quả Kiểm Thử Toàn Diện
- **Frontend**:
  - `npm run lint`: Biome check 83 files — 0 lỗi.
  - `npm run typecheck`: TypeScript tsc --noEmit — 0 lỗi.
- **Backend**:
  - `uv run ruff check .`: 0 lỗi.
  - `uv run --extra dev pytest`: 136/136 tests passed (100%).
- **Xác thực trực tiếp qua Vite Proxy**:
  - `GET http://127.0.0.1:3001/health/live` -> HTTP 200 `{"status":"ok","service":"qnu-ai-platform","version":"0.1.0"}`.
  - `GET http://127.0.0.1:3001/platform/v1alpha1/knowledge/collections/col_admissions` -> HTTP 200 OK.
  - `GET http://127.0.0.1:3001/platform/v1alpha1/knowledge/documents?collection_id=col_admissions` -> HTTP 200 OK.
  - `DELETE http://127.0.0.1:3001/platform/v1alpha1/knowledge/documents/doc_ts_2026` -> HTTP 404 (được xử lý idempotent thành công).
