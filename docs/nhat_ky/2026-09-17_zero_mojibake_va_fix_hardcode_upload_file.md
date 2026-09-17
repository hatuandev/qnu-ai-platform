# Nhật Ký Làm Việc: Phòng Chống Lỗi Mojibake Tiếng Việt & Sửa Dứt Điểm Lỗi Hardcode Upload File

- **Thời gian**: 2026-09-17 10:10 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  1. Thêm quy chuẩn bắt buộc chống lỗi Mojibake (vỡ font tiếng Việt, ký tự thay thế `\ufffd`, byte rác CP1252) vào `AGENTS.md` và các skill hệ thống.
  2. Tạo công cụ tự động kiểm tra Zero Mojibake trên toàn bộ codebase (`scripts/check_mojibake.py`, `npm run check:mojibake`).
  3. Sửa dứt điểm lỗi hardcode khi nạp tài liệu: Không còn mặc định tệp *"Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)"*, tiếp nhận tệp động thực tế gửi lên API Backend, hiển thị đúng dữ liệu bóc tách của tài liệu đó.

---

## 1. Vấn Đề Kỹ Thuật Đã Nhận Diện

1. **Lỗi Hardcode Form & Mock Data**:
   - Trong `document-ingest-page.tsx`, ô tiêu đề được gán sẵn giá trị `useState("Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)")`.
   - Hàm `handleSubmit` sử dụng `setTimeout` giả lập rồi gọi cứng `onStartVerification("doc_ts_2026")`.
   - Trong `api-client.ts`, hàm `getDocumentVerification(docId)` clone nguyên mẫu 14 trang scan tuyển sinh cho mọi document ID mới (`{ ...MOCK_VERIFICATION_DOCUMENT, document_id: docId }`).
   - Trong `document-bounding-visualizer.tsx`, thuộc tính `currentImageSrc` tự fallback cứng về `/ocr-cache/doc_ts_2026/page_N.jpg` khiến bất kỳ tệp nào được mở cũng hiện ảnh scan của đề án tuyển sinh.
2. **Nguy cơ Lỗi Mã Hóa Ký Tự (Mojibake)**:
   - Hệ điều hành Windows thường sử dụng bảng mã `cp1252` thay vì `utf-8` khi đọc/ghi file hoặc xuất console.
   - Khi xử lý tài liệu OCR/scan, nếu không chuẩn hóa Unicode NFC, văn bản tiếng Việt rất dễ bị vỡ font, sinh ký tự `\ufffd` hoặc các chuỗi byte decode nhầm.

---

## 2. Các Thay Đổi Kỹ Thuật Cốt Lõi

### 2.1. Cập Nhật AGENTS.md & Hệ Thống Kỹ Năng (Skills)
- **`AGENTS.md`**:
  - Bổ sung **Tôn chỉ 1.5**: *Zero Mojibake & Chuẩn Hóa UTF-8 Tiếng Việt*.
  - Nâng cấp Mục 8 thành **10 điều răn Clean Code khi Vibe Coding**:
    - **Điều răn 8.9**: *Tuyệt Đối Không Hardcode Logic & Dữ Liệu Khi Vibe Coding (Zero Hardcoded Data & Zero Mock Traps)* — Cấm gán cứng form state, cấm fake submit `setTimeout`, cấm clone-overwriting dữ liệu cũ lên file mới, tách bạch rõ ràng giữa chế độ mẫu thử và luồng nạp tệp thật.
    - **Điều răn 8.10**: *Triệt Tiêu Lỗi Mã Hóa Ký Tự & Vỡ Font Tiếng Việt (Zero Mojibake & Strict UTF-8 Enforcement)* — 100% tệp UTF-8 không BOM, chuẩn hóa `unicodedata.normalize("NFC", text)` cho toàn bộ chuỗi tiếp nhận từ OCR/PDF, cấm đưa ký tự rác vào codebase, charset trong Blob khi export.
- **Skill `qnu-clean-code-architect`**: Cập nhật bảng 10 điều răn, Anti-Patterns tra cứu và danh mục 7 câu hỏi tự kiểm toán Clean Code.
- **Skill `qnu-knowledge-ingestion`**: Bổ sung quy định khử Mojibake và chuẩn hóa Unicode NFC ở bước 4 (cleaner).

### 2.2. Xây Dựng Công Cụ Tự Động Quét Lỗi Mojibake
- Tạo script [`scripts/check_mojibake.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/scripts/check_mojibake.py):
  - Tự động cấu hình stdout/stderr UTF-8 trên Windows.
  - Quét toàn bộ tệp `.ts`, `.tsx`, `.py`, `.json`, `.md`, `.css` trong dự án.
  - Phát hiện ký tự thay thế `\ufffd`, chuỗi byte UTF-8 bị decode nhầm theo CP1252 (`Ã¡`, `á»`,...), ký tự rác OCR và dấu hỏi bất thường trong từ tiếng Việt.
- Tích hợp lệnh `npm run check:mojibake` vào `frontend/package.json`.

### 2.3. Sửa Dứt Điểm Lỗi Hardcode Khi Upload File
1. **`frontend/src/pages/document-ingest-page.tsx`**:
   - `docTitle`: Khởi tạo rỗng `useState("")`.
   - `handleFileChange`: Khi người dùng chọn tệp, tự động điền tiêu đề từ tên file sạch (`file.name.replace(...)`) nếu ô tiêu đề đang trống.
   - `handleSubmit`: Gọi trực tiếp `await apiClient.uploadDocument(collection.id, selectedFile, docTitle)` bất đồng bộ, tiếp nhận `newDoc.id` thực tế từ hệ thống rồi chuyển sang màn hình Studio đối soát.
   - Nếu chỉ nhập tiêu đề mà không đính kèm file, tạo file văn bản động từ tiêu đề.
   - Bổ sung nút **"Xem tài liệu mẫu (Tuyển sinh 2026)"** tách biệt hoàn toàn để cán bộ có thể mở nhanh 14 trang scan Docling mẫu khi cần demo mà không làm ảnh hưởng luồng tải file thật.
   - Bổ sung Banner cảnh báo lỗi rõ ràng nếu tiến trình nạp tệp gặp sự cố.
2. **`frontend/src/services/api-client.ts`**:
   - Cập nhật hàm `getDocumentVerification(docId)`:
     - Nếu `docId === "doc_ts_2026"`: Trả về tài liệu mẫu 14 trang scan Docling tuyển sinh.
     - Nếu là `docId` khác: Tìm trong danh sách `MOCK_DOCUMENTS` (chứa các tài liệu thật vừa upload hoặc đã lưu) để sinh động cấu trúc trang, tiêu đề thật, tên file thật, số trang thật và nội dung Markdown bóc tách tương ứng.
     - Triệt tiêu hoàn toàn bẫy clone đè `MOCK_VERIFICATION_DOCUMENT`.
3. **`frontend/src/components/admin/document-bounding-visualizer.tsx`**:
   - Xóa bỏ fallback cứng `/ocr-cache/doc_ts_2026/page_N.jpg`.
   - Khi không có ảnh scan tĩnh (đối với các tệp văn bản / PDF mới tải lên), giao diện hiển thị khung canvas tài liệu số hóa trực quan, sạch sẽ, không tải nhầm ảnh scan của đề án tuyển sinh.
4. **`frontend/src/pages/document-verification-studio-page.tsx`**:
   - Chỉ truyền đường dẫn ảnh scan tuyển sinh khi `documentId === "doc_ts_2026"`.
5. **`frontend/src/pages/collection-detail-page.tsx` & `knowledge-page.tsx`**:
   - Xóa bỏ fallback mặc định `doc_ts_2026`, truyền động ID tài liệu người dùng click hoặc tài liệu đầu tiên trong danh sách kho tri thức.

### 2.4. Bổ Sung Kiểm Thử Tự Động Chống Tái Diễn (E2E Regression Test)
- Thêm test case `TC-INGEST-04` vào [`frontend/tests/e2e/09_knowledge_ingestion_studio.spec.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/tests/e2e/09_knowledge_ingestion_studio.spec.ts):
  - Kiểm tra ô tiêu đề khởi tạo rỗng 100%.
  - Nạp tệp giả lập động `Quy_dinh_Cong_tac_Hoc_sinh_Sinh_vien_2026.pdf`.
  - Kiểm tra tiêu đề tự động điền từ tên tệp.
  - Bấm submit và kiểm tra Studio mở ra với tiêu đề động và tên file động thực tế.
  - Khẳng định tiêu đề tuyển sinh cũ hoàn toàn KHÔNG xuất hiện.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

```text
==================================================
🔍 QNU AI Platform — Bộ Kiểm Toán Zero Mojibake
==================================================
Tổng số tệp đã quét: 182
✅ TUYỆT VỜI: Không phát hiện bất kỳ lỗi Mojibake hay vỡ font tiếng Việt nào!
==================================================

Backend Ruff:
All checks passed! (0 lỗi)

Backend Pytest:
tests/test_knowledge.py: 8 passed
tests/test_ocr.py: 4 passed
Tổng cộng: 12/12 passed (100%)

Frontend Biome:
Checked 73 files. 0 errors, 0 warnings.

Frontend Typecheck:
tsc --noEmit: 0 errors.

Frontend Build:
Vite v6.4.3: built in 8.79s (thành công)

Playwright E2E Suite 09 (4 tests):
  ok 1 TC-INGEST-01: Verifies Knowledge Master View (4.3s)
  ok 2 TC-INGEST-02: Verifies Dedicated Detail View (2.9s)
  ok 3 TC-INGEST-03: Full-Screen Split-Pane Studio (6.8s)
  ok 4 TC-INGEST-04: Verifies Dynamic File Ingestion and Zero-Hardcoded Title (2.1s)
  4 passed (17.4s)
```
