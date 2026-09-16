# NHẬT KÝ LÀM VIỆC — PHIÊN #29
# Ngày: 2026-09-16 | Mục tiêu: Tích Hợp Smart Auto-Recommendation Engine Cho Kho Tri Thức QNU (Kế Thừa QNU AI Core)

---

## 1. Bối Cảnh & Yêu Cầu Kỹ Thuật

- **Vấn đề trước đó**: Khi người dùng tải lên tài liệu vào Kho Tri Thức, họ phải tự suy đoán và lựa chọn thủ công mô hình OCR và thuật toán phân mảnh (Chunking strategy). Việc này dễ dẫn đến chọn sai (ví dụ gửi tệp Word chứa bảng sang Cloud Vision OCR gây tốn token và vỡ bảng biểu).
- **Giải pháp kế thừa từ `qnu-ai-core`**:
  - Tệp Word (`.docx`, `.doc`) và Excel (`.xlsx`): Tự động nhận diện lớp văn bản XML & bảng số liệu ➔ Đề xuất **Docling TableFormer Local** (bảo toàn 100% bảng & Điều/Khoản, 0 tốn token Cloud OCR) + `ClauseBasedChunker`.
  - Tệp PDF (`.pdf`): Kích hoạt **Fast-path PDF Inspector (10-30ms)** cho các trang số hóa + đề xuất **Mistral OCR Cloud** cho trang scan ảnh.
  - Tệp Văn bản thuần (`.txt`, `.md`): Bóc tách native tức thì ➔ `SemanticChunker`.
  - Hiển thị **Smart Recommendation Banner** màu Academic Teal (`oklch(0.46 0.13 160)`), biểu tượng `Sparkles`, huy hiệu badge, giải thích kỹ thuật minh bạch và hỗ trợ Manual Override.

---

## 2. Chi Tiết Các Tệp Tin Thay Đổi (Key Changes)

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật |
| :--- | :---: | :--- |
| [`frontend/src/lib/file-inspector.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/lib/file-inspector.ts) | **Tạo mới** | Module độc lập nhận diện loại tệp (.docx, .pdf, .xlsx, .txt) và đề xuất cấu hình bóc tách chuẩn xác theo nguyên tắc Clean Architecture. |
| [`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx) | **Chỉnh sửa** | Tích hợp Auto-Recommendation vào `onFileSelect`: tự động điền tiêu đề văn bản, tự động chọn mô hình OCR khớp từ khóa, tự động chọn thuật toán phân mảnh, hiển thị Smart Recommendation Banner. |
| [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx) | **Chỉnh sửa** | Đồng bộ hóa hoàn toàn tính năng Auto-Recommendation và Banner thông minh vào Tab Ingest Wizard toàn cục `/knowledge`. |
| [`frontend/tests/e2e/05_smart_auto_recommendation.spec.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/tests/e2e/05_smart_auto_recommendation.spec.ts) | **Tạo mới** | Bộ kiểm thử E2E Playwright với 3 test cases: Word (.docx), PDF (.pdf), và quy trình nạp hoàn chỉnh. |

---

## 3. Kết Quả Kiểm Thử (Verification)

### 3.1 Kiểm Tra Tĩnh
- `npm run lint`: `Checked 60 files in 77ms. No fixes applied.` (0 lỗi Biome).
- `npm run typecheck`: `tsc --noEmit` (0 lỗi TypeScript).
- `npm run build`: `✓ built in 8.20s` (Đóng gói production thành công).

### 3.2 Kiểm Thử Trình Duyệt Tự Động Playwright (Google Chrome)
```text
Running 3 tests using 1 worker
  ok 1 [Google Chrome] TC-SMART-01: Auto-recommends Docling TableFormer and ClauseBasedChunker for Word .docx files (3.5s)
  ok 2 [Google Chrome] TC-SMART-02: Auto-recommends Mistral OCR and Fast-path Inspector for PDF files (2.6s)
  ok 3 [Google Chrome] TC-SMART-03: Full Ingestion workflow with Smart Recommendation (7.2s)
  3 passed (14.7s)
```
- Ảnh bằng chứng nghiệm thu:
  - `smart_recommendation_word.png`: Giao diện đề xuất Docling TableFormer cho tệp Word.
  - `smart_recommendation_pdf.png`: Giao diện đề xuất Mistral OCR Cloud + Fast-path cho PDF.
  - `smart_ingestion_success.png`: Tài liệu nạp thành công vào bảng danh mục bộ sưu tập.
