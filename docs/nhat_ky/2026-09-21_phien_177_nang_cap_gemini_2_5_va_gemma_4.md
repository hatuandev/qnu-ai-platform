# Nhật Ký Làm Việc — Phiên #177
**Ngày thực hiện**: 2026-09-21
**Mục tiêu chính**: Nâng cấp danh mục mô hình Google Provider lên thế hệ mới Gemini 2.5+, Gemma 4 26B/31B, loại bỏ hoàn toàn các mô hình đã ngừng hoạt động 1.5 & 2.0, tối ưu hóa fallback tự động và đồng bộ CSDL.

---

## 1. Bối Cảnh & Yêu Cầu Của Người Dùng

Người dùng yêu cầu:
> *"ok bạn cứ tập trung vào gemini từ 2.5 trở lên di, bổ sung thêm Gemma 4 26B, Gemma 4 31B nữa, bạn hãy bổ sung vào provider google nhé, bỏ 2.0, 1.5 đi giúp tôi"*

Khảo sát và kiểm toán thực tế:
1. **Google AI Studio Model Retirement**:
   - Google đã chính thức ngừng hỗ trợ (deprecated & shutdown) các endpoint của thế hệ cũ 1.5 (`gemini-1.5-flash`, `gemini-1.5-pro`) và 2.0. Khi gửi request tới các mô hình này, API trả về mã lỗi 404 hoặc không tìm thấy model.
2. **Khám phá mô hình hoạt động thực tế qua Google API Key của hệ thống**:
   - Truy vấn trực tiếp endpoint `https://generativelanguage.googleapis.com/v1beta/models?key=...` phát hiện 50 mô hình đang hoạt động trên dự án của người dùng, trong đó nổi bật là:
     * `gemini-2.5-flash-lite`: Thời gian phản hồi ~2.4s, định mức miễn phí cao (1,500 RPD, 15-30 RPM), tối ưu nhất cho bài toán RAG chat trợ lý.
     * `gemini-2.5-flash`: Thời gian phản hồi ~2.1s, 1,500 RPD.
     * `gemini-2.5-pro`: Dòng cao cấp cho tác vụ suy luận sâu và viết văn bản phức tạp.
     * `gemini-flash-lite-latest`: Bản tự động cập nhật nhẹ nhất.
     * `gemini-3.1-flash-lite`: Thế hệ 3.x siêu tốc.
     * `gemma-4-26b-a4b-it`: Dòng Gemma mã nguồn mở thế hệ 4 (26B mixture-of-experts/attention).
     * `gemma-4-31b-it`: Dòng Gemma 4 dense 31B instruction-tuned.
3. **Phát hiện bug luồng Fallback trong RAG Generation**:
   - Tệp `backend/app/modules/rag/service.py` khi khởi tạo `LLMGenerateRequest` đã quên truyền tham số `fallback_model_name=req.fallback_model`. Do đó khi mô hình chính gặp sự cố mạng (503/429), ModelOps không biết model dự phòng đích danh mà rơi tự do xuống cấu hình mặc định hệ thống.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Technical Changes)

### 2.1. Cập Nhật Provider Service & Model List (`backend/app/modules/modelops/services/provider_service.py`)
- Cập nhật cấu hình khởi tạo của `prov_gemini`:
  * Đặt `model_name` mặc định: `"gemini-2.5-flash-lite"`.
  * Cập nhật danh sách `models` hỗ trợ đầy đủ 7 mô hình:
    `"gemini-2.5-flash-lite"`, `"gemini-2.5-flash"`, `"gemini-2.5-pro"`, `"gemini-flash-lite-latest"`, `"gemini-3.1-flash-lite"`, `"gemma-4-26b-a4b-it"`, `"gemma-4-31b-it"`.
  * Xóa bỏ triệt để mọi tham chiếu tới `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`.

### 2.2. Cập Nhật Mặc Định Cấu Hình Nền Tảng (`backend/app/core/config.py`)
- Cập nhật `GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"`.

### 2.3. Cập Nhật Bảng Giá & Theo Dõi Chi Phí (`pricing.py` & `cost_tracker.py`)
- Bổ sung định mức USD / 1K tokens cho:
  * `gemini-2.5-flash-lite`: $0.000075 input / $0.0003 output.
  * `gemini-2.5-flash`: $0.000075 input / $0.0003 output.
  * `gemini-2.5-pro`: $0.00125 input / $0.005 output.
  * `gemini-flash-lite-latest`: $0.000075 input / $0.0003 output.
  * `gemini-3.1-flash-lite`: $0.0001 input / $0.0004 output.
  * `gemma-4-26b-a4b-it`: $0.0001 input / $0.0003 output.
  * `gemma-4-31b-it`: $0.00015 input / $0.00045 output.

### 2.4. Khắc Phục Luồng RAG LLM Fallback Cascade (`backend/app/modules/rag/service.py`)
- Bổ sung `fallback_model_name=req.fallback_model` vào lệnh khởi tạo `LLMGenerateRequest` trong `RAGService.generate_answer`.
- Điều này đảm bảo khi mô hình chính gặp sự cố kết nối, ModelOps sẽ ưu tiên kích hoạt ngay mô hình dự phòng được cấu hình riêng cho từng Trợ lý (ví dụ `@cf/meta/llama-3.1-8b-instruct` của Cloudflare).

### 2.5. Đồng Bộ Schemas & Readiness Check Của Trợ Lý (`backend/app/modules/assistants/`)
- `schemas.py`: Đặt `fallback_model: str = "gemini-2.5-flash-lite"` (hoặc model tùy biến).
- `readiness.py`: Cập nhật khuyến nghị fallback sang `gemini-2.5-flash-lite`.
- `seeder.py`: Cập nhật cấu hình mặc định cho Trợ lý.

### 2.6. Nâng Cấp Giao Diện Quản Trị Frontend (`frontend/src/`)
- `components/modelops/modelops-helpers.ts`:
  * Cập nhật `PRESET_SUGGESTED_MODELS.gemini`:
    `["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-flash-lite", "gemma-4-26b-a4b-it", "gemma-4-31b-it"]`.
  * Bổ sung `@cf/meta/llama-3.1-8b-instruct` vào gợi ý Cloudflare.
- `pages/assistant-create-page.tsx` & `assistant-detail-page.tsx`:
  * Thay thế toàn bộ options dropdown Google:
    `Gemini 2.5 Flash-Lite (Khuyến nghị RAG - 1500 RPD)`, `Gemini 2.5 Flash`, `Gemma 4 26B IT`, `Gemma 4 31B IT`.
  * Loại bỏ hoàn toàn các lựa chọn cũ 1.5 và 2.0.

### 2.7. Đồng Bộ CSDL PostgreSQL
- Chạy script cập nhật bản ghi `model_provider_configs` cho `prov_gemini` với danh sách model mới và default model `gemini-2.5-flash-lite`.
- Cập nhật Trợ lý Tuyển sinh `ast_admissions`:
  * `primary_model`: `"gemini-2.5-flash-lite"`
  * `fallback_model`: `"@cf/meta/llama-3.1-8b-instruct"`

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Kiểm thử chat thực tế đầu cuối**:
   - Gửi câu hỏi: `"xin chào cho tôi biết phương thức tuyển sinh 2026"`.
   - Kết quả: `status=success`, `groundedness=grounded`, `confidence_score=0.96`, trả lời chi tiết 4 phương thức tuyển sinh 2026 của ĐH Quy Nhơn kèm 5 trích dẫn từ Đề án tuyển sinh chính thức.
2. **Backend**:
   - `uv run ruff check .`: **0 lỗi linter**.
   - `uv run --extra dev pytest tests/test_modelops.py tests/test_assistants.py tests/test_rag.py -v`: **48/48 passed (100%)**.
3. **Frontend**:
   - `npm run lint`: **Biome check 168 files: 0 lỗi**.
   - `npm run typecheck`: **0 lỗi TypeScript**.
   - `npm run build`: **Vite build thành công trong 8.89s**.
