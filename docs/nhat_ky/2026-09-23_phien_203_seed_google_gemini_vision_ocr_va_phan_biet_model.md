# NHẬT KÝ CÔNG VIỆC — PHIÊN #203 (2026-09-23)

## Tiêu Đề: Seed Dữ Liệu Google Gemini Vision OCR, Phân Biệt Rõ Model OCR vs Text, Thiết Lập OCR Mặc Định Cho Kho Tri Thức

---

### 1. Thời Gian & Bối Cảnh
- **Thời gian**: 2026-09-23 11:20 (UTC+7).
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist.
- **Yêu cầu từ người dùng**:
  > *"seed data provider google với các model này giúp tôi nhé, phải có nhận biết cái nào là OCR nhé chứ ko là sẽ nhầm, tôi cần phân biệt để làm ocr mặc định cho kho tri thức"*.

---

### 2. Các Vấn Đề Kỹ Thuật Đã Giải Quyết

#### 2.1. Cập Nhật Danh Mục Mô Hình Google Gemini & Model Specs Chi Tiết
- Bổ sung đầy đủ danh mục mô hình thế hệ 2.5 và 3.x vào `STANDARD_QNU_PROVIDERS` (`provider_service.py`) và CSDL PostgreSQL (`model_provider_configs` - `prov_ace0d9fe`):
  - **Mô hình OCR / Vision (Thị giác & Bóc tách đa phương thức)**:
    - `gemini-2.5-flash`: Bóc tách văn bản, bảng biểu PDF scan & hình ảnh siêu tốc (Được chọn làm OCR mặc định hệ thống).
    - `gemini-2.5-flash-lite`: Vision OCR siêu nhẹ, phản hồi nhanh, tối ưu chi phí.
    - `gemini-2.5-pro`: OCR tài liệu phức tạp, phân tích cấu trúc bảng biểu nhiều tầng.
    - `gemini-3.1-flash-lite`: Google 3.1 Flash Vision OCR thế hệ mới siêu tốc.
    - `gemini-3.1-flash-image`: Chuyên biệt xử lý hình ảnh và tài liệu scan.
    - `gemini-3.1-pro-preview`: Google 3.1 Pro Đa phương thức cao cấp preview.
  - **Mô hình Thuần Text (Không hỗ trợ OCR/Vision)**:
    - `gemma-4-26b-a4b-it`: Mô hình ngôn ngữ mở, chỉ xử lý văn bản thuần.
    - `gemma-4-31b-it`: Mô hình ngôn ngữ mở, chỉ xử lý văn bản thuần.
- Khai báo tường minh `model_specs` với các thuộc tính `can_ocr: bool`, `can_vision: bool`, `type: "vision_ocr" | "text"`, và mô tả nghiệp vụ tiếng Việt chi tiết.

#### 2.2. Nhận Biết Trực Quan & Bộ Lọc Trên Giao Diện ModelOps (Frontend)
- Cập nhật `frontend/src/components/modelops/modelops-helpers.ts`:
  - Mở rộng hàm `getModelCapabilities` trả về `{ hasVision, hasReasoning, isOcr, capabilityLabel }`.
  - Phân tách rạch ròi giữa mô hình có năng lực OCR (`isOcr = true`) và mô hình thuần text như dòng `gemma-*`.
- Cập nhật `frontend/src/components/modelops/models-grid.tsx`:
  - Bổ sung tùy chọn lọc **`OCR & Bóc tách (Vision OCR)`** vào thanh công cụ lọc `modelFilter`.
  - Gắn huy hiệu (Badge) nổi bật `OCR` (icon `ScanText`, màu sky/cyan) cho các mô hình có năng lực OCR.
  - Gắn huy hiệu `Text` (icon `Type`, màu muted) cho các mô hình thuần text.
  - Hiển thị tooltip mô tả chức năng bóc tách tài liệu khi người dùng hover.

#### 2.3. Hỗ Trợ Chọn Google Gemini Làm OCR Mặc Định Hệ Thống
- Cập nhật `backend/app/modules/modelops/services/model_catalog_service.py`:
  - Nhận diện các mô hình có `can_ocr` hoặc `vision` từ Google Gemini đưa vào danh sách `available_ocrs`.
  - Loại trừ các mô hình thuần text `gemma-*` khỏi danh sách OCR để tránh người dùng chọn nhầm.
  - Cập nhật CSDL `system_model_defaults` thiết lập `default_ocr_provider_id = "prov_ace0d9fe"` và `default_ocr_model = "gemini-2.5-flash"`.
- Cập nhật `frontend/src/components/modelops/system-defaults-card.tsx`:
  - Hiển thị trạng thái khi người dùng chọn Google Gemini Vision OCR làm mặc định hệ thống.

#### 2.4. Triển Khai `GeminiOCRAdapter` Cho Module OCR Backend
- Khởi tạo adapter mới `backend/app/modules/ocr/adapters/gemini_adapter.py`:
  - Kế thừa `BaseOCRAdapter`.
  - Gửi payload chuẩn REST lên Google Generative Language API (`gemini-2.5-flash:generateContent`).
  - Hỗ trợ cả tài liệu PDF (`application/pdf`) và tệp ảnh (`image/png`, `image/jpeg`).
  - Tự động bóc tách cú pháp Markdown GFM và phân trang `<!-- Trang X -->`.
  - Tích hợp `SmartLayoutDetector` nhận diện tọa độ bounding boxes cho bảng biểu, con dấu và chữ ký phục vụ Scan Studio.
- Đăng ký `gemini_ocr` vào `OCRService` (`backend/app/modules/ocr/service.py`) với vai trò cloud OCR engine ưu tiên hàng đầu, tự động fallback an toàn sang `mistral_ocr`, `easyocr` hoặc `docling` khi thiếu API key.
- Cập nhật `frontend/src/pages/document-ingest-page.tsx` hỗ trợ engine `gemini: "gemini_ocr"`.

---

### 3. Kết Quả Kiểm Thử (Verification)

1. **Backend Tests**:
   - `uv run ruff check .`: 0 lỗi.
   - `uv run --extra dev pytest tests/test_ocr.py tests/test_modelops.py`: 34/34 passed (100%).
   - `uv run --extra dev pytest`: 414/414 passed (100%) trong 84.00s.
2. **Frontend Tests**:
   - `npm run lint`: Biome check 170 files, 0 lỗi.
   - `npm run typecheck`: TypeScript tsc `--noEmit` 0 lỗi.
   - `npm run build`: Vite v6.4.3 build thành công đóng gói 44 chunks trong 10.96s.
3. **Độ Sạch Dữ Liệu**:
   - 100% tệp tuân thủ Zero Mojibake, UTF-8 tiếng Việt sạch, không có ký tự rác.
