# NHẬT KÝ LÀM VIỆC — PHIÊN #206
# Ngày: 2026-09-23 | Mục tiêu: Đồng Bộ Động Model OCR & Tự Động Điều Hướng Auto Router Sang Chuỗi Combo Từ Cấu Hình Hệ Thống

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật

- **Vấn đề**: Người dùng cấu hình lại mô hình OCR trong ModelOps (chọn mô hình mới trong Combo hoặc chọn mô hình OCR đơn lẻ), nhưng khi nạp tệp tài liệu PDF scan từ trang Kho Tri Thức (`/collections/.../upload`), log terminal vẫn luôn ghi nhận:
  `Gửi tài liệu ... tới Google Gemini Vision OCR (gemini-2.5-flash) [app.modules.ocr.adapters.gemini_adapter]`
- **Nguyên nhân cốt lõi**:
  1. Trong `backend/app/modules/ocr/service.py`, hàm `_extract_auto` có tuple ứng viên tĩnh `candidate_order = ("gemini_ocr", "mistral_ocr", "easyocr", "docling")` và bốc trực tiếp `self._adapters["gemini_ocr"]` vốn được khởi tạo tĩnh lúc khởi động server với giá trị mặc định là `"gemini-2.5-flash"`.
  2. `_extract_auto` và `_resolve_adapter` chưa tra cứu bảng `system_model_defaults` trong CSDL PostgreSQL, nên không nắm bắt được sự thay đổi của `default_ocr_model` hay `default_ocr_mode`.
  3. Khi nạp tệp ở trang Ingest, nếu form để chế độ "Auto Router", backend gọi vào `_extract_auto` và bỏ qua chuỗi Combo được kích hoạt trong hệ thống.

---

## 2. Giải Pháp Kỹ Thuật Triển Khai

1. **Bổ sung `_get_system_defaults` trong `OCRService`**:
   - Truy vấn CSDL PostgreSQL (`system_model_defaults`) để lấy toàn bộ từ điển `defaults` chứa `default_ocr_model`, `default_ocr_mode`, `ocr_combo_chain`, và `model_combos`.
2. **Tự động điều hướng Auto Router sang Combo Chain**:
   - Trong `extract_document`: Nếu yêu cầu là `requested in ("auto", "none", "")`, kiểm tra nếu `default_ocr_mode == "combo"` thì tự động chuyển tiếp sang `self._extract_combo_chain(session, content, filename, tenant_id, start_time)`.
3. **Phân giải Adapter động theo cấu hình hệ thống**:
   - Trong `_resolve_adapter(name_or_model, default_gemini_model, **kwargs)`: Nếu `gemini_ocr`, `gemini`, hoặc `gemini_vision` được yêu cầu, ưu tiên khởi tạo `GeminiOCRAdapter(model_name=default_gemini_model)` khi có `default_gemini_model`.
   - Trong `_extract_auto`: Nhận tham số `default_ocr_model`. Khi duyệt ứng viên `"gemini_ocr"`, khởi tạo `GeminiOCRAdapter(model_name=default_ocr_model)` để gửi đúng model người dùng đã cấu hình.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Backend Tests**:
   - `uv run ruff check app/modules/ocr tests/test_ocr.py`: **0 lỗi linter**.
   - `uv run --extra dev pytest tests/test_ocr.py -v`: **18/18 passed (100%)**.
     - `test_resolve_adapter_dynamically_respects_default_ocr_model`: PASSED.
     - `test_auto_routing_routes_to_combo_when_combo_mode_enabled`: PASSED.
2. **Frontend Quality**:
   - `npm run lint`: **171 files, 0 lỗi**.
   - `npm run typecheck`: **0 lỗi compiler**.
