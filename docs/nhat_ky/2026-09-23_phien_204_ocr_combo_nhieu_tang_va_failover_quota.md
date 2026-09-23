# NHẬT KÝ LÀM VIỆC — PHIÊN #204
**Ngày**: 2026-09-23 | **Thời gian**: 12:30 (UTC+7)
**Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Chủ đề**: Combo OCR Dự Phòng Linh Hoạt & Tự Động Failover Khi Hết Quota (Zero-Quota-Failure Policy)

---

## 1. Mục Tiêu & Bối Cảnh Nghiệp Vụ
- **Yêu cầu người dùng**: Bổ sung tính năng OCR dự phòng linh hoạt theo hình thức "Combo OCR". Cho phép người quản trị cấu hình một combo gồm nhiều mô hình OCR theo thứ tự ưu tiên (Step 1 -> Step 2 -> Step 3...), sau đó gắn combo OCR đó làm OCR mặc định của toàn hệ thống / Kho Tri Thức. Khi tiến hành bóc tách tài liệu, nếu bất kỳ model nào trong combo bị hết hạn ngạch (429 Rate Limit / Quota Exceeded), timeout hoặc gặp sự cố mạng thì hệ thống sẽ tự động chuyển tiếp sang model tiếp theo trong chuỗi mà không gây đứt quãng tác vụ ingestion.
- **Tiêu chuẩn áp dụng**: Tuân thủ quy định `AGENTS.md` (Zero Big-Ball-of-Mud, Thin Controller, Zero Emoji, chuẩn màu OKLCH Academic Teal, 100% test suite pass).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Backend Architecture (FastAPI & Modular Monolith)
1. **Schema DTOs (`backend/app/modules/modelops/schemas.py`)**:
   - Thêm schema `OCRComboItem` định nghĩa cấu trúc một bước trong chuỗi Combo OCR: `provider_id`, `provider_name`, `model_name`, `provider_type`, `timeout_seconds`, `is_active`, `description`.
   - Bổ sung `default_ocr_mode: Literal["combo", "single"]` và `ocr_combo_chain: list[OCRComboItem]` vào `SystemModelDefaults` và `SystemModelDefaultsUpdate`.
   - Mở rộng vai trò trong `SetDefaultModelRequest` cho phép `fallback_ocr` và `ocr_combo`.

2. **Cấu Hình Mặc Định Chuẩn QNU (`backend/app/modules/modelops/services/model_catalog_service.py`)**:
   - Khởi tạo chuỗi chuẩn QNU 5 bước `DEFAULT_QNU_OCR_COMBO_CHAIN`:
     - **Bước 1 (Chính)**: `gemini-2.5-flash` (`Google Gemini Cloud`) — tốc độ cao, xử lý đa phương thức và bảng biểu phức tạp.
     - **Bước 2 (Dự phòng 1)**: `gemini-2.5-flash-lite` (`Google Gemini Cloud`) — chi phí tối ưu khi Step 1 chạm quota.
     - **Bước 3 (Dự phòng 2)**: `mistral-ocr-2503` (`Mistral Cloud`) — chuyên văn bản scan tiếng Việt và con dấu đỏ.
     - **Bước 4 (Dự phòng 3)**: `docling-tableformer` (`Local Edge Engine`) — phân tích bảng biểu cục bộ không phụ thuộc mạng ngoài.
     - **Bước 5 (Cứu sinh cuối cùng)**: `easyocr-vie` (`Local Edge Engine`) — OCR offline trên CPU/CUDA bảo đảm không đứt đoạn.
   - Hỗ trợ lưu trữ và cập nhật cấu hình combo vào metadata JSON của bảng `model_provider_configs` trong PostgreSQL.

3. **OCR Engine & Sequential Failover (`backend/app/modules/ocr/`)**:
   - `schemas.py`: Bổ sung `fallback_engine: str | None = None` và `cascade_trace: list[str] = Field(default_factory=list)` vào `OCRExtractResponse`.
   - `service.py`:
     - Triển khai `_get_active_combo_chain(session)`: nạp chuỗi combo đang kích hoạt từ cấu hình hệ thống hoặc trả về chuỗi 5 bước tiêu chuẩn.
     - Triển khai `_extract_combo_chain(request, session, raw_bytes)`: vòng lặp duyệt tuần tự từng model theo thứ tự ưu tiên trong combo chain.
     - Tự động bắt mã lỗi HTTP `429` (Quota Exceeded / Rate Limit), lỗi `503`, lỗi timeout và các ngoại lệ mạng, ghi vết vào `cascade_trace`, tự động chuyển sang model tiếp theo.
     - Ném exception RFC 7807 (`AppException`) với mã lỗi `OCR_ALL_CHAIN_ENGINES_FAILED` và đầy đủ `cascade_trace` chỉ khi toàn bộ các model trong chuỗi đều thất bại.
     - Cập nhật `_resolve_adapter(engine)` ưu tiên tra cứu trong mock registry `self._adapters` trước khi khởi tạo instance mới, tương thích 100% với test suite.

4. **Kiểm Thử Backend (`backend/tests/test_ocr.py`, `backend/tests/test_modelops.py`)**:
   - Thêm test case `test_ocr_combo_chain_sequential_failover_on_quota`: giả lập Step 1 bị lỗi 429 Quota Exceeded, xác nhận hệ thống tự động fallback tức thì sang Step 2, kết quả trả về có `fallback_engine` và `cascade_trace` ghi nhận đầy đủ.
   - Thêm test case `test_ocr_combo_explicit_engine_failure_triggers_combo_fallback`: xác nhận khi gọi một engine cố định bị lỗi thì hệ thống tự động cứu sinh qua chuỗi combo.
   - Cập nhật assert trong `test_system_model_defaults_api` kiểm tra `ocr_combo_chain` và `default_ocr_mode`.

### 2.2. Frontend Architecture (React 19, TypeScript, OKLCH Tokens)
1. **Types (`frontend/src/types/modelops.ts`)**:
   - Khai báo interface `OCRComboItem`.
   - Mở rộng `SystemModelDefaults` với `default_ocr_mode` và `ocr_combo_chain`.

2. **Component Quản Trị Combo OCR (`frontend/src/components/modelops/system-defaults-card.tsx`)**:
   - Cung cấp toggle switch chuyển đổi chế độ giữa `Combo Dự Phòng` (khuyên dùng) và `Mô Hình Đơn`.
   - Sơ đồ **Visual Pipeline Flow**: dải các bước trực quan với mũi tên `ArrowRight`, số thứ tự `#1, #2, #3...`, tên model, nhà cung cấp và trạng thái kích hoạt.
   - Bảng quản trị danh sách bước tương tác linh hoạt:
     - Bật/tắt bước bất kỳ bằng `Switch` mà không cần xóa.
     - Di chuyển tăng/giảm thứ tự ưu tiên bằng nút `ArrowUp` / `ArrowDown`.
     - Xóa bước khỏi combo bằng nút `Trash2`.
   - Form thêm model mới từ danh mục `availableOcrs` vào chuỗi.
   - Nút "Khôi phục Chuỗi Chuẩn QNU" đưa cấu hình về lại 5 bước tiêu chuẩn của nhà trường.
   - Bảng cảnh báo chính sách Zero Quota Failure Policy.

3. **Cập Nhật Màn Hình Ingest Văn Bản (`frontend/src/pages/document-ingest-page.tsx`)**:
   - Cập nhật `OCR_ENGINE_PARAM` bổ sung `combo: "combo"`.
   - Đặt `combo` làm giá trị mặc định của `ocrEngine`.
   - Bổ sung tùy chọn `Combo OCR Mặc Định Hệ Thống (Tự động chuyển mô hình khi hết Quota)` trên Dropdown Select.
   - Tuân thủ 100% chuẩn Zero-Emoji Standard (loại bỏ emoji ký tự trong dropdown và text mô tả).

---

## 3. Kết Quả Kiểm Thử (Verification)

| Suite | Lệnh | Kết Quả |
| :--- | :--- | :--- |
| **Backend Linter** | `uv run ruff check .` | **All checks passed (0 lỗi)** |
| **Backend Pytest** | `uv run --extra dev pytest tests/test_ocr.py tests/test_modelops.py -v` | **36/36 passed (100%)** |
| **Frontend Linter** | `npm run lint` (`biome check src`) | **170 files checked, 0 errors** |
| **Frontend Typecheck** | `npm run typecheck` (`tsc --noEmit`) | **0 errors** |
| **Frontend Production Build** | `npm run build` (`tsc -b && vite build`) | **Thành công trong 6.49s** |

---

## 4. Kế Hoạch Tiếp Theo
- Nạp thêm tài liệu mẫu dạng PDF scan phức tạp vào Kho Tri Thức để kiểm thử live trên giao diện Ingest với chuỗi Combo OCR.
- Tiếp tục theo dõi hạn ngạch API keys Gemini và Mistral trên widget quota.
