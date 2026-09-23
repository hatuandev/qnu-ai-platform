# NHẬT KÝ LÀM VIỆC — Phiên #207
**Ngày**: 2026-09-23 16:05 (UTC+7)
**Mục tiêu**: Tối ưu hóa bóc tách PDF OCR hơn mà không ảnh hưởng tới bóc tách của DOCX và PDF Text.

---

## 1. Hiện Trạng & Vấn Đề Kỹ Thuật

Khi bóc tách tài liệu hợp đồng quét scan nhiều trang (`Hợp đồng nâng cấp PM cổng thông tin điện tử_0001.pdf` 16 trang), kết quả OCR trước đó gặp 4 vấn đề lớn:
1. **Bảng biểu đa trang bị cắt vụn nát**: Bảng mô tả tính năng kỹ thuật (từ trang 2 đến trang 12) bị chen ngang bởi dấu gạch ngang phân trang `---` và nhãn trang, khiến bảng bị xé thành 11 bảng rời rạc, mất header và separator ở các trang sau.
2. **Từ ngữ bị chặt đôi qua ranh giới trang**: Ví dụ `banner, giới` ở cuối trang 3 và `thiệu, hình ảnh` ở đầu trang 4 khiến từ *"giới thiệu"* bị chặt đôi.
3. **Dòng trong cùng một ô bị bẻ thành nhiều hàng riêng biệt**: Các đoạn mô tả của một mục (1.1, 1.2, 2.1...) bị bẻ thành các hàng bảng riêng có cột STT rỗng, làm mất cấu trúc 1 bản ghi = 1 hàng và gây lỗi khi vector hóa/tra cứu.
4. **Ràng buộc người dùng**: Tuyệt đối không được gây ảnh hưởng tới bóc tách của DOCX (`DocxParser`) và PDF text (`PDFInspector` fast path, `PyMuPDFParser`).

---

## 2. Các Thay Đổi Kỹ Thuật

### 2.1. Nâng Cấp Prompt Chuyên Gia Trong `GeminiOCRAdapter`
- Tệp: [`backend/app/modules/ocr/adapters/gemini_adapter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/adapters/gemini_adapter.py)
- Bổ sung 4 chỉ đạo nghiệp vụ cốt lõi:
  - **Quy tắc Bảng Biểu Liên Trang (Multi-page Table Continuity)**: Duy trì liên tục cấu trúc bảng; cấm chèn ký tự phân cách `---` vào giữa các hàng của bảng.
  - **Quy tắc Chống Bẻ Đôi Từ Ngữ (No Word Splitting)**: Hoàn tất trọn vẹn từ ngữ bị ngắt dòng ở cuối trang (ví dụ *"giới thiệu"* thay vì *"banner, giới"* | *"thiệu, hình ảnh"*).
  - **Quy tắc Gộp Ô Mô Tả (Cell Content Integrity)**: Đặt toàn bộ các đoạn mô tả chi tiết của một mục vào ô mô tả của hàng đó (dùng `<br>`), không tạo thêm hàng rỗng STT.
  - **Quy tắc Từ Vựng Hành Chính & Hợp Đồng QNU**: Chuẩn hóa chính tả ("chỉ số", "ký kết", "kinh phí", "Trung tâm Số và Học liệu",...).

### 2.2. Xây Dựng Module Hậu Xử Lý OCR Độc Lập
- Tệp: [`backend/app/modules/ocr/cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/cleaner.py)
- Triển khai các thuật toán xử lý chuỗi:
  1. `repair_ocr_split_words_across_pages(markdown)`: Hàn gắn từ ghép tiếng Việt bị bẻ đôi qua ngắt trang / ngắt dòng.
  2. `stitch_ocr_multipage_tables(markdown)`: Hợp nhất các bảng bị ngắt quãng bởi `---` hoặc nhãn trang thành 1 Master Table hoàn chỉnh; loại bỏ các header lặp lại giữa chừng.
  3. `merge_ocr_orphan_table_rows(markdown)`: Gộp các hàng rỗng STT vào ô mô tả của hàng cha (chữ thường nối bằng dấu cách, câu mới nối bằng `<br>`).
  4. `clean_ocr_table_syntax(markdown)`: Xóa các separator thừa hoặc separator rác chèn giữa các hàng dữ liệu bảng; sửa lỗi chính tả OCR.
  5. `post_process_ocr_output(raw_text, pages)`: Hàm điều phối tổng thể cho kết quả OCR.

### 2.3. Tích Hợp Vào `OCRService` & Adapter
- Tệp: [`backend/app/modules/ocr/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/service.py)
- Tích hợp gọi `post_process_ocr_output` trong phương thức `_build_response` của `OCRService`.
- Luồng DOCX (`DocxParser`) và PDF text (`pdf_parser.py`) hoàn toàn độc lập, không đi qua hàm này, bảo đảm 100% Zero-Impact.

### 2.5. Chuyển Dịch Toàn Diện Sang Thuật Toán Tổng Quát (Zero-Hardcoded Vocabulary)
- Tệp: [`backend/app/modules/ocr/cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/cleaner.py)
- **Vấn đề trước đó**: Dùng mảng từ khóa cứng `_COMMON_SPLIT_WORD_PAIRS = [("giới", "thiệu"), ...]` để ghép từ bị ngắt trang. Cách làm này mang tính chắp vá, không bao quát được hàng nghìn thuật ngữ trong tiếng Việt và tiếng Anh.
- **Giải thuật thay thế**:
  - *Thuật toán Hình thái học Ranh giới Trang (Morphological Boundary Stitcher)*: Quét các cặp dòng liên tiếp qua ranh giới trang (`---`, `<!-- Trang X -->`).
  - *Bất biến cú pháp (Syntactic Invariant)*: Nếu hàng/dòng sau bắt đầu bằng ký tự thường (`islower()`) và cột định danh (STT/ID) rỗng, chứng tỏ đây 100% là token tiếp diễn từ hàng/dòng trước. Thuật toán tự động chuyển token đầu tiên sang nối vào đuôi ô tương ứng của hàng trước mà không phụ thuộc vào bất kỳ từ điển nào.
  - *Xử lý Hyphenation*: Chuẩn hóa gạch nối từ ngữ cuối dòng/trang bằng regex tổng quát `(\w+)-\s*\n+(\w+)`.
  - *Bảo toàn bảng Markdown*: Bổ sung cơ chế nhận diện `_RE_PAGE_MARKER` trong `merge_ocr_orphan_table_rows` giúp không làm đứt mạch hàng cha - hàng con khi có comment trang chèn giữa.

### 2.6. Bổ Sung Nguyên Tắc "Algorithmic-First & Propose-Before-Implement" Vào `AGENTS.md`
- Tệp: [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md)
- Bổ sung **Mục 1.7** (Tôn chỉ phát triển) và **Mục 8.12** (Quy chuẩn Clean Code khi Vibe Coding):
  - **Tôn chỉ Thuật toán Tổng quát (Algorithmic-First)**: Khi xử lý dữ liệu bóc tách (OCR, PDF, DOCX, Chunking, Ingestion, Text Cleaning, Table Reconstruction) hay bất kỳ xử lý dữ liệu nào, bắt buộc phải ưu tiên dùng thuật toán hình thái học, cấu trúc dữ liệu hoặc mô hình toán học / NLP tổng quát dựa trên các bất biến (Invariants). Tuyệt đối cấm hardcode từ điển, danh sách từ vựng gõ tay.
  - **Quy tắc Đề Xuất Trước - Thực Thi Sau (Propose Before Implementation)**: Khi đối mặt với bài toán xử lý dữ liệu phức tạp, AI Agent bắt buộc phải phân tích, xây dựng đề xuất phương pháp / thuật toán rõ ràng và báo cáo cho người dùng biết trước để thảo luận, thống nhất trước khi áp dụng vào codebase.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

1. **Bộ Test OCR & Cleaner mới**:
   - `uv run --extra dev pytest tests/test_ocr_cleaner.py tests/test_ocr.py -v`: 24/24 passed (100%).
2. **Kiểm tra hồi quy DOCX & PDF Text**:
   - `uv run --extra dev pytest tests/test_knowledge.py tests/test_table_reconstructor.py -v`: 51/51 passed (100%).
3. **Toàn bộ 75 tests OCR & Knowledge**:
   - 75/75 passed (100%).
4. **Linter & Code Style**:
   - `uv run ruff check .`: All checks passed (0 lỗi).
   - `npm run lint`: Checked 171 files, 0 errors.
   - `npm run typecheck`: 0 errors.
   - `npm run build`: Vite build thành công trong 4.67s.
