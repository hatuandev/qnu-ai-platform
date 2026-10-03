# NHẬT KÝ LÀM VIỆC: CHUẨN HÓA ADAPTER OPENAI VISION ĐA MÔ HÌNH, THUẬT TOÁN LÀM SẠCH BẢNG OCR & KHẮC PHỤC OCR COMBO FAILOVER

- **Thời gian**: 2026-10-03 23:15
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên (Goals)**:
  - Đánh giá chất lượng bóc tách tài liệu scan `QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf` bằng mô hình `gemini-3.5-flash` và đối soát 1-1 với ảnh gốc.
  - Xây dựng thuật toán hậu xử lý trong `cleaner.py` để khử triệt để mã HTML thô (`<table>`, `<tr>`, `<td>`, `<hr>`, `<br>`), hàn gắn bảng ngắt tiếp nối qua trang (Multi-page Table Stitching) và khắc phục hàng mồ côi.
  - Chuẩn hóa kiến trúc Adapter theo Phương án B (Protocol-Based Separation): phân tách độc lập giữa Google Multimodal Protocol (`GeminiOCRAdapter`) và OpenAI Vision Protocol (`OpenAIVisionOCRAdapter`), đồng thời dọn dẹp sạch sẽ tệp thừa `qwen_adapter.py`.
  - Điều tra và giải quyết sự cố cấu hình tính năng OCR Combo trên UI ModelOps (`localhost:3000/models`): sửa lỗi gán nhầm sang `LLM Chat`, loại bỏ model text-only của Groq và bổ sung nhận diện model Vision-Language (`-vl`, `pixtral`) trong `modelops-helpers.ts`.

---

## 1. Các Thay Đổi Mã Nguồn & Kiến Trúc (Key Changes)

### 1.1. Backend — Thuật Toán Làm Sạch Bảng & Khử HTML Thô (`cleaner.py`)
- **Tệp**: `backend/app/modules/ocr/cleaner.py`
- **Chi tiết**:
  - `clean_html_layout_tables`: Tự động nhận diện và chuyển đổi 100% các khối HTML layout dạng `<table><tr><td>...</td></tr></table>` ở phần Quốc hiệu, tiêu ngữ và chữ ký con dấu thành văn bản Markdown GFM thuần khiết (`**...**`, `*...*`, `-`).
  - `stitch_ocr_multipage_tables`: Thuật toán hàn gắn bảng biểu tiếp nối qua trang. Tự động nhận diện ranh giới phân trang (`---` hoặc `<!-- Trang X -->`), phát hiện hàng bảng bị ngắt và khử bỏ dòng kẻ ngang, hợp nhất liền mạch hoặc lặp lại tiêu đề hợp lệ để đảm bảo cú pháp GFM Markdown không bị vỡ thành 2 bảng riêng lẻ.
  - `merge_ocr_orphan_table_rows`: Tự động phát hiện các hàng bảng mồ côi (thiếu ô STT do thuộc về ô gộp của trang trước) để bảo toàn 100% dữ liệu hàng, giải quyết dứt điểm lỗi Gemini bỏ quên hàng học phí đầu tiên của trang 2 (ngành Kế toán 3 năm - 37.440.000 VNĐ).

### 1.2. Backend — Kiến Trúc Protocol-Based Adapters (`openai_vision_adapter.py`)
- **Tệp**:
  - `backend/app/modules/ocr/adapters/openai_vision_adapter.py` (Tạo mới)
  - `backend/app/modules/ocr/adapters/gemini_adapter.py` (Cập nhật prompt và quy chuẩn)
  - `backend/app/modules/ocr/adapters/qwen_adapter.py` (Xóa bỏ để đạt chuẩn Clean Code)
  - `backend/app/modules/ocr/adapters/__init__.py` (Cập nhật exports)
  - `backend/app/modules/ocr/service.py` (Cập nhật điều phối `_resolve_adapter`)
- **Chi tiết**:
  - `GeminiOCRAdapter`: Chuyên trách trực tiếp Google Multimodal Protocol, gửi trực tiếp tệp PDF đa trang hoặc ảnh scan dạng base64 qua Google Gemini Vision API (`gemini-3.5-flash`, `gemini-3.1-flash-lite`, `gemini-2.5-flash`).
  - `OpenAIVisionOCRAdapter`: Bộ adapter tổng quát theo chuẩn OpenAI Vision API (`/chat/completions` với `image_url`). Tự động render PDF thành các trang ảnh độ phân giải cao qua PyMuPDF và hỗ trợ mọi mô hình tương thích: Qwen-2.5-VL-72B/7B (OpenRouter / SiliconFlow), GPT-4o Vision, Claude 3.5 Sonnet, DeepSeek-VL, Pixtral hoặc mô hình tự host qua vLLM/Ollama.
  - Định nghĩa class kế thừa `QwenOCRAdapter(OpenAIVisionOCRAdapter)` để bảo đảm tính tương thích ngược 100%.
  - Xóa bỏ hoàn toàn tệp `qwen_adapter.py` thừa thãi, không để tồn tại wrapper rỗng hay dead code.

### 1.3. Frontend & ModelOps — Khắc Phục Sự Cố Nhận Diện OCR Combo
- **Tệp**: `frontend2/src/components/modelops/modelops-helpers.ts`
- **Nguyên nhân phát hiện**:
  - Trên màn hình `localhost:3000/models` (Tab Combos), thẻ `qnu-ocr-master` bị gán nhãn `LLM Chat` và chọn nhầm mô hình text-only `qwen/qwen3.8-27b (Groq Cloud LPU)`.
  - Nguyên nhân do hàm `getModelCapabilities` trước đó chỉ tìm từ khóa `vision`, `ocr` mà bỏ sót hậu tố `-vl` (Vision-Language). Khi người dùng lọc `Vision OCR`, Qwen-2.5-VL không xuất hiện nên đã chuyển sang `LLM Chat` để tìm kiếm.
- **Xử lý**:
  - Bổ sung `mLower.includes("-vl")`, `mLower.includes("_vl")` và `mLower.includes("pixtral")` vào `isOcr` và `hasVision`.
  - Hướng dẫn cấu hình đúng chuỗi 3 tầng Vision OCR chuẩn:
    1. Ưu tiên 1: `gemini-3.5-flash` (Google Gemini)
    2. Ưu tiên 2: `gemini-2.5-flash` (Google Gemini)
    3. Ưu tiên 3: `qwen/qwen-2.5-vl-72b-instruct` (OpenRouter / Qwen Vision)

---

## 2. Kết Quả Kiểm Thử & Xác Minh (Verification)

1. **Linter & Code Format**:
   - `python -m ruff check backend/app/modules/ocr/ backend/tests/`: **All checks passed! (0 lỗi)**.
2. **Kiểm Thử Đơn Vị (Test Suite)**:
   - `pytest backend/tests/test_ocr_cleaner.py backend/tests/test_ocr.py -v`:
   - **24/24 tests PASSED (100%) in 1.46s**.
   - Bao gồm kiểm thử tính năng của `OpenAIVisionOCRAdapter`, `GeminiOCRAdapter`, `MistralOCRAdapter`, khử bảng HTML, ghép bảng nối tiếp qua trang, xoay vòng khóa API và failover tuần tự OCR Combo.
3. **Kiểm tra tham chiếu toàn dự án**:
   - Đảm bảo 0 tàn dư hay tham chiếu gãy sau khi xóa `qwen_adapter.py`.

---

## 3. Trạng Thái & Công Việc Tiếp Theo (Next Steps)
- **Trạng thái**: HOÀN THÀNH 100% (Backend Adapters, Cleaner, Linter, Pytest & Frontend Helper).
- **Việc tiếp theo**:
  - Cập nhật quy tắc bắt buộc vào `AGENTS.md` về việc tự động ghi nhận Memory & Nhật ký làm việc sau mỗi phiên Vibe Coding.
  - Người dùng bấm sửa trên giao diện `localhost:3000/models` để chuyển `qnu-ocr-master` về `Vision OCR` và lưu lại chuỗi 3 tầng.
