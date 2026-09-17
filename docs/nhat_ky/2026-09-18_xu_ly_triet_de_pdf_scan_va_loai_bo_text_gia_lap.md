# Nhật Ký Làm Việc: Xử Lý Triệt Để Lỗi Chuẩn Hóa PDF Scan & Xóa Bỏ Hoàn Toàn Text Giả Lập

- **Thời gian**: 2026-09-18 01:25 (UTC+7)
- **Phiên làm việc**: #77
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Điều tra và xử lý triệt để hiện tượng tệp PDF scan 9 trang (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`) hiển thị chuỗi văn bản giả lập (`### Tiêu đề đầu trang`, `## Tên loại văn bản / Trích yếu nội dung`, `Đoạn văn bản quy định`, `Bảng biểu số liệu`, `Con dấu & Chữ ký xác thực`), khôi phục 100% văn bản và bảng biểu thật của Quyết định 4740, đồng thời hoàn thiện cơ chế xử lý cho toàn bộ các định dạng tệp.

---

## 1. Các Thay Đổi Kỹ Thuật (Key Changes)

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/ocr/layout_detector.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/layout_detector.py) | Sửa đổi | Triệt tiêu hoàn toàn việc gán chuỗi giả lập (`"Đoạn văn bản quy định"`, `"Tiêu đề đầu trang"`, `"Bảng biểu số liệu"`, `"Con dấu & Chữ ký xác thực"`) vào thuộc tính `text` của box. Nếu không có OCR text, gán `text: ""` và `content_snippet: ""`. Gộp nhánh `title` theo chuẩn Ruff `SIM114`. |
| [`backend/app/modules/knowledge/chunker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/chunker.py) | Sửa đổi | Bổ sung `_RE_PAGE_MARKER` và theo dõi `sec_start_page` / `sub_page` trong `ClauseBasedChunker` và `SemanticChunker`. Gán đúng `page_number` cho từng `ChunkDraft` (1 đến 9), triệt tiêu lỗi `is_clumped` giả mạo. |
| [`backend/app/modules/ocr/adapters/mistral_adapter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/adapters/mistral_adapter.py) | Sửa đổi | Trích xuất `raw_pages_text` từ kết quả Mistral OCR và truyền trực tiếp markdown THẬT của từng trang vào `SmartLayoutDetector.detect_layout_regions` thay vì `page.get_text()` rỗng. |
| [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) | Sửa đổi | (1) Import `re` và trích xuất `page_markdowns` trong `prepare_ingestion`. (2) Lưu `page_markdowns` vào `doc_metadata` trong `replace_document_content` và `ingest_document`. (3) Bổ sung lọc `_SYNTHESIS_PLACEHOLDERS` trong `_synthesize_page_markdown_from_blocks` và bảo vệ chunks thật trong `build_studio_pages`. (4) Kích hoạt **Auto-Rescue** trong `get_studio_view` khi tài liệu có 0 chunks hoặc khi người dùng bấm `[Quét lại]`. |
| [`backend/tests/test_knowledge.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_knowledge.py) | Sửa đổi | Bổ sung 2 test case: `test_chunkers_track_page_number_from_page_markers` và `test_build_studio_pages_rejects_synthetic_placeholders`. |

---

## 2. Kết Quả Xác Minh & Kiểm Thử (Verification)

1. **Reprocess Thực Tế Quyết Định 4740**:
   - Tài liệu `doc_e5b93255b9ab` trong PostgreSQL đã được nạp đầy đủ **9 chunks thật (14.194 ký tự)**.
   - `get_studio_view` trả về đầy đủ 9 trang:
     * Trang 1: Quốc hiệu, Tiêu ngữ, Số hiệu 4740/QĐ-BGDĐT, Trích yếu, Căn cứ pháp lý, Điều 1.
     * Trang 2: Mục 4, Mục 5, Mục 6.
     * Trang 3: Mục 7, Điều 2, Điều 3, Con dấu và Chữ ký của Thứ trưởng Hoàng Minh Sơn.
     * Trang 4 - 9: Toàn bộ bảng Markdown ma trận Bộ chỉ số Chuyển đổi số.
     * 0 dòng văn bản giả lập.
2. **Backend Python Suite**:
   - `uv run ruff check .`: **All checks passed (0 lỗi)**.
   - `uv run --extra dev pytest tests/test_ocr.py tests/test_knowledge.py tests/test_smart_layout.py`: **44/44 tests passed 100%** trong 46.65s.
3. **Zero Mojibake**:
   - `uv run python scripts/check_mojibake.py`: **225/225 tệp sạch 100%**, 0 lỗi encoding.
4. **Frontend Suite**:
   - `npm run lint`: Biome check 91 files sạch **0 lỗi**.
   - `npm run typecheck`: TypeScript `tsc --noEmit` **0 lỗi**.
   - `npm run build`: Vite build đóng gói thành công trong 12.04s.
