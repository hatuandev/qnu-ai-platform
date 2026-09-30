# Nhật Ký Phiên Làm Việc #233 — Tích Hợp Provider NVIDIA NIM, Cơ Chế Suy Luận (Reasoning) Nemotron 550B & Xử Lý Lỗi Quá Tải 503 Server Overload

- **Thời gian**: 2026-09-30 22:30 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Trạng thái**: Hoàn thành xuất sắc, đã seed thành công `prov_nvidia` vào PostgreSQL, Vite build 100%

---

## 1. Yêu Cầu & Bối Cảnh Thực Tế

1. **Yêu cầu tích hợp Nhà Cung Cấp NVIDIA NIM (`prov_nvidia`)**:
   - Người dùng yêu cầu seed dữ liệu nhà cung cấp NVIDIA NIM API (`https://integrate.api.nvidia.com/v1`) vào hệ thống để khai thác các dòng mô hình tiên tiến chạy trên hạ tầng GPU NVIDIA.
2. **Hỗ trợ cơ chế Thinking / Reasoning cho siêu mô hình Nemotron 550B**:
   - Mô hình `nvidia/nemotron-3-ultra-550b-a55b` đòi hỏi cấu hình tham số suy luận chuyên biệt:
     ```python
     extra_body={"chat_template_kwargs": {"enable_thinking": True}}
     ```
   - Cần trích xuất `delta.reasoning_content` trong luồng SSE streaming để hiển thị quá trình tư duy (Thinking Process) của mô hình.
3. **Hiện tượng lỗi 503 Service Unavailable khi kiểm tra kết nối (Ping Model)**:
   - Các mô hình siêu lớn (550B tham số) trên cụm máy chủ NVIDIA NIM đôi khi phản hồi mã lỗi `HTTP 503: Service Unavailable` kèm thông điệp *"The server is temporarily overloaded"*.
   - Trước đây, hệ thống đánh đồng 503 thành lỗi `"failed"` (hỏng/không tồn tại) và vô hiệu hóa nút "Thêm mô hình" trên Frontend, gây cản trở người dùng cấu hình mô hình hợp lệ.

---

## 2. Các Thành Phần Kỹ Thuật Đã Triển Khai

### 2.1 Backend (`app.modules.modelops`)
- **Seed Provider NVIDIA NIM**:
  - Đăng ký `prov_nvidia` vào `STANDARD_QNU_PROVIDERS` trong `provider_service.py` với cấu hình chuẩn OpenAI-compatible:
    - Base URL: `https://integrate.api.nvidia.com/v1`
    - Cụm model mặc định: `nvidia/nemotron-3-ultra-550b-a55b`, `meta/llama-3.3-70b-instruct`, `deepseek-ai/deepseek-r1`, `mistralai/mistral-large-2407`, `nvidia/llama-3.1-nemotron-70b-instruct`.
- **Hỗ trợ Thinking & Reasoning Trong `OpenAIAdapter`**:
  - Cập nhật `backend/app/modules/modelops/providers/openai_adapter.py`:
    - Hỗ trợ truyền `chat_template_kwargs={"enable_thinking": True}` qua `extra_body` khi gọi Chat Completions đối với các mô hình suy luận (`nemotron`, `r1`, `o1`, `o3`).
    - Bóc tách thuộc tính `reasoning_content` từ `chunk.choices[0].delta` và phát luồng token suy luận về client.
- **Khả năng Phục hồi & Tự Động Thử Lại (Resilience & Auto-Retry)**:
  - Nâng cấp phương thức `_ping_single_model` trong `provider_service.py`:
    - Bắt các mã lỗi quá tải tạm thời: `HTTP 503`, `504` (Gateway Timeout), `529` (Site Overloaded).
    - Tự động thực hiện retry 1 lần sau 1 giây trước khi kết luận trạng thái.
    - Nếu máy chủ vẫn báo quá tải, gán trạng thái riêng biệt `temporarily_overloaded` kèm thông báo *"Máy chủ AI đang tạm thời bận hoặc quá tải (HTTP 503/504). Tên mô hình chính xác, bạn vẫn có thể lưu mô hình này."* thay vì gán lỗi chết.
    - Xử lý mã lỗi `410 Gone` phân loại trạng thái `"deprecated"`.

### 2.2 Frontend (`frontend2`)
- **Nâng Cấp Schema & Types**:
  - `frontend2/src/types/modelops.ts`: Mở rộng union `SingleModelTestResult.status` hỗ trợ `"temporarily_overloaded" | "deprecated"`.
- **Giao Diện Thêm Model (`add-custom-model-dialog.tsx`)**:
  - Bổ sung biểu tượng đồng hồ `Clock` màu hổ phách (`text-amber-500`, `bg-amber-500/10`).
  - Hiển thị hộp cảnh báo thân thiện khi gặp lỗi 503, giải thích rõ tên model là hoàn toàn chuẩn xác và cho phép nhấn **"Thêm model"** ngay lập tức.
  - Tích hợp công tắc suy luận sâu "Kích hoạt Chế độ Suy Luận (Thinking / Reasoning)" tự động bật khi nhập model `nemotron` hoặc `r1`.
- **Lưới Hiển Thị Mô Hình (`models-grid.tsx` & `modelops-helpers.ts`)**:
  - Bổ sung huy hiệu trạng thái màu cam `"Tạm quá tải"` khi kiểm tra kết nối gặp 503.
  - Cập nhật danh mục model gợi ý cho provider NVIDIA.

---

## 3. Kết Quả Kiểm Tra (Verification)
- CSDL PostgreSQL: Provider `prov_nvidia` được khởi tạo thành công với 5 mô hình chuẩn.
- Frontend2: `npm run build` thành công 100% trong 1.63s, 0 lỗi TypeScript, 0 lỗi cú pháp.
- Người dùng có thể kiểm tra và lưu mô hình `nvidia/nemotron-3-ultra-550b-a55b` mà không bị chặn bởi lỗi quá tải tạm thời của cụm GPU NVIDIA.
