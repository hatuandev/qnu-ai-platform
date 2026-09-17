# NHẬT KÝ LÀM VIỆC — Phiên #67
# Ngày: 2026-09-17 | Tiêu đề: Tối Ưu Tự Động Nhận Diện Loại Văn Bản (Taxonomy) Cho Mọi Mẫu Tệp Tin

## 1. Phản Hồi Từ Người Dùng
- Người dùng thử nghiệm tải lên tệp: `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`.
- Kết quả quan sát trên giao diện:
  * Tiêu đề: Đã tự động điền `Thong tin tuyen sinh dai hoc 2026 Lan2 1 (1)`.
  * Năm hiệu lực: Đã tự động điền `2026`.
  * Bộ máy OCR: Đã tự động chọn `IBM Docling TableFormer`.
  * Smart Recommendation Banner: Đã hiển thị sắc nét.
  * **Vấn đề còn tồn tại**: Ô "Loại văn bản" vẫn hiển thị `Chọn loại văn bản` và trong banner báo `Loại văn bản: Chưa xác định`.
- **Yêu cầu**: Cấu hình để tự động nhận diện và chọn luôn Loại văn bản trong trường hợp này cũng như các mẫu tệp tương tự.

## 2. Phân Tích Kỹ Thuật
1. Tệp tin có tên `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` chứa cụm từ `thông tin tuyển sinh` và `tuyển sinh`.
2. Trong danh mục Taxonomy 37 loại của QNU (theo Nghị định 30 và quy chế ĐH Quy Nhơn):
   - Mã `de_an` (Đề án) có mô tả nghiệp vụ chính thức: *"Đề án tuyển sinh trình độ đại học/sau đại học, đề án mở ngành mới..."*.
   - Mã `thong_bao` (Thông báo) truyền đạt thông tin tuyển sinh.
3. Bộ regex trước đó chỉ bắt các từ khóa cứng `quy_che`, `quyet_dinh`, `thong_bao`, `ke_hoach` mà chưa bao quát các từ khóa tuyển sinh (`de an`, `tuyen sinh`, `thong tin tuyen sinh`) và chưa hỗ trợ cơ chế dự phòng thông minh theo ngữ cảnh Kho Tri Thức (`collectionId`).

## 3. Các Thay Đổi Đã Triển Khai
1. **[`frontend/src/lib/file-inspector.ts`](../../frontend/src/lib/file-inspector.ts)**:
   - Mở rộng mẫu regex trong `detectDocumentTypeFromFilename`:
     * Bổ sung nhận diện `de_an`: `/(?:de\s*an|tuyen\s*sinh|thong\s*tin\s*tuyen\s*sinh)/` -> tự động chọn `de_an` (Đề án tuyển sinh).
     * Bổ sung nhận diện `thong_bao`: `/(?:thong\s*bao|\btb\b|thong\s*tin|\btin\s*tuc\b)/`.
     * Khớp mã ma trận đề thi/khảo thí vào `de_cuong_mon_hoc` (mã chuẩn 37 loại của catalog).
   - Nâng cấp cơ chế **Collection Context Default Fallback** chấp nhận `collectionContext` đa hình (`id`, `name`, `code`):
     * Nhận diện cụm từ trong tên kho/mã kho:
       - Tuyển sinh / Admissions -> mặc định `de_an`.
       - Quy chế / Học vụ / Regulations -> mặc định `quy_che`.
       - Thư viện / Giáo trình / Library -> mặc định `giao_trinh`.
       - Soạn thảo / Drafting -> mặc định `cong_van`.
       - Khảo thí / Ngân hàng / Đề thi -> mặc định `de_cuong_mon_hoc`.
   - Cập nhật hàm `getPriorityForDocumentType`:
     * Đưa `de_an` vào `standardTypes` (Điểm: 8/10, Ưu tiên Tiêu chuẩn x50) khớp 100% catalog backend.
     * Cập nhật toàn diện nhóm `coreTypes` (10/10) và `standardTypes` (8/10).
2. **[`frontend/src/pages/document-ingest-page.tsx`](../../frontend/src/pages/document-ingest-page.tsx)**:
   - Tách hàm `processFile(f: File)` dùng chung cho cả sự kiện click duyệt chọn file và kéo thả file (`onDrop` / `onDragOver`).
   - Bổ sung `useEffect` tự động khởi tạo Loại văn bản mặc định theo Kho tri thức khi vừa mở trang (không cần đợi upload file).
   - Tối ưu hiển thị Loại văn bản trong Smart Recommendation Banner (`Đề án`, `Quy chế`,...).

## 4. Kết Quả Kiểm Thử
- **Kiểm thử trực tiếp trên tệp của người dùng**:
  * `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` -> Loại văn bản tự động nhận diện: **`de_an` (Đề án)** ✓
  * Mức độ ưu tiên pháp lý: **`Điểm: 8/10 (Tiêu chuẩn) (x50)`** ✓
  * Banner Smart Recommendation hiển thị: `• Loại văn bản: Đề án` ✓
  * Dropdown "Loại văn bản" tự động chọn giá trị `Đề án` ✓
- **Linter & Types & Tests**:
  * `npm run lint`: 0 lỗi (Biome check 86 files).
  * `npm run typecheck`: 0 lỗi (tsc --noEmit).
  * `npm run build`: Vite build thành công (10.81s).
  * Backend: 25/25 test `test_knowledge.py` pass (100%), Ruff 0 lỗi.
