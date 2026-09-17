# NHẬT KÝ LÀM VIỆC — Phiên #66
# Ngày: 2026-09-17 | Tiêu đề: Tích Hợp Smart Auto-Recommendation Cho Trang Nạp Tài Liệu Kho Tri Thức

## 1. Bối Cảnh & Yêu Cầu
- **Yêu cầu từ người dùng**: Tìm hiểu tính năng tự động đề xuất cấu hình bóc tách khi chọn tệp tin (kế thừa từ `qnu-ai-core`) và triển khai tích hợp hoàn thiện vào ứng dụng `qnu-ai-platform`.
- **Khảo sát hiện trạng**: Module giải thuật `file-inspector.ts` đã có sẵn nhưng trang nạp tài liệu độc lập `DocumentIngestPage` (`document-ingest-page.tsx`) chưa được kết nối, khi người dùng chọn file chỉ tự điền tiêu đề mà không tự nhận diện loại văn bản, năm hiệu lực, OCR engine hay hiển thị banner đề xuất.

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

1. **[`frontend/src/lib/file-inspector.ts`](../../frontend/src/lib/file-inspector.ts)**:
   - Bổ sung `detectDocumentTypeFromFilename`: Tự động nhận diện 18 mẫu loại văn bản tiếng Việt đối chiếu với danh mục 37 loại trong Taxonomy QNU (`quyet_dinh`, `quy_che`, `thong_bao`, `ke_hoach`, `to_trinh`, `cong_van`, `bao_cao`, `de_cuong_mon_hoc`, `giao_trinh`, `ngan_hang_cau_hoi`,...).
   - Bổ sung `extractYearFromFilename`: Tự động trích xuất năm hiệu lực 4 chữ số (`20\d{2}`) từ tên file.
   - Bổ sung `cleanTitleFromFilename`: Làm sạch tên tệp loại bỏ đuôi mở rộng, thay ký tự gạch chân/gạch ngang thành khoảng trắng chuẩn.
   - Bổ sung `getPriorityForDocumentType`: Phân cấp mức ưu tiên pháp lý động (Cốt lõi 10/10, Tiêu chuẩn 8/10, Tham khảo 6/10).
   - Chuẩn hóa Unicode Regex với `\p{M}/gu` tương thích 100% với Biome linter.

2. **[`frontend/src/pages/document-ingest-page.tsx`](../../frontend/src/pages/document-ingest-page.tsx)**:
   - Trong `handleFileChange`:
     * Tự động làm sạch tiêu đề và điền vào ô "Tiêu đề / Số hiệu Văn bản".
     * Tự động chọn Bộ máy OCR tối ưu (Word/Excel -> Docling TableFormer để bảo toàn 100% bảng biểu; Text/MD -> PyMuPDF Fast; PDF -> Auto / Docling).
     * Tự động chọn đúng option Loại văn bản trong Taxonomy dropdown.
     * Tự động điền Năm ban hành / hiệu lực.
     * Lưu `recommendation` để kích hoạt giao diện trực quan.
   - Giao diện:
     * Hiển thị **Smart Recommendation Banner** màu Academic Teal (`bg-primary/5 border-primary/25`) với icon `Sparkles`, huy hiệu `badgeText`, lý giải kỹ thuật và bảng tóm tắt cấu hình tự động đã áp dụng kèm lưu ý Manual Override.
     * Mức độ ưu tiên pháp lý tự động cập nhật động theo loại văn bản được chọn.
     * Hộp thông tin chính sách phân đoạn cập nhật theo `recommendedChunking` (`ClauseBasedChunker` vs `SemanticChunker`).

## 3. Kết Quả Kiểm Thử Toàn Diện
- **Frontend**:
  - `npm run lint`: Biome check 86 files — 0 lỗi.
  - `npm run typecheck`: TypeScript tsc --noEmit — 0 lỗi.
  - `npm run build`: Vite build hoàn tất thành công trong 12.59s.
- **Backend**:
  - 136/136 tests passed (100%), Ruff check 0 lỗi.
- **Kiểm thử logic tự động (TSX/Node)**:
  - `Thong_tin_tuyen_sinh_dai_hoc_2026_Lan2-1 (1).docx` -> Tiêu đề sạch: `Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)`, Năm: `2026`, OCR Engine: `docling` (TableFormer).
  - `Quyet_dinh_2705_QD_DHQN.pdf` -> Loại văn bản: `quyet_dinh`, Ưu tiên: `Điểm: 10/10 (Cốt lõi)`.
  - `Thong_bao_tuyen_sinh_2026.docx` -> Loại văn bản: `thong_bao`, Ưu tiên: `Điểm: 8/10 (Tiêu chuẩn)`.
