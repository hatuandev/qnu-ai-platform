# NHẬT KÝ LÀM VIỆC — PHIÊN #285
**Thời gian**: 2026-10-07 | **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Mục tiêu chính**: Tối ưu UI Nạp Tài Liệu Kho Tập Trung (`/documents`): Hỗ trợ Kéo Thả Nhiều File (Multi-file Drag & Drop Batch Upload), Loại Bỏ Bắt Buộc Nhập Thủ Công (Ngày Ban Hành, Số Hiệu, Trích Yếu), Tự Động Bóc Tách Metadata Hành Chính Theo Nghị Định 30/2020/NĐ-CP.

---

## 1. Bối Cảnh & Vấn Đề Cần Giải Quyết

Người dùng phản ánh chính xác các điểm nghẽn trải nghiệm người dùng trên Modal "Tải Tài Liệu Vào Kho Tập Trung" (`DocumentUploadModal`):
1. **Bất cập ở trường "Ngày ban hành" & các ô nhập metadata thủ công**:
   - Giao diện trước đó bắt người dùng nhập tay 6 trường: `Tiêu đề / Trích yếu`, `Loại văn bản`, `Số hiệu văn bản`, `Cơ quan ban hành`, `Ngày ban hành`, `Người ký`.
   - Về mặt bản chất nghiệp vụ: Khi văn bản hành chính (Quyết định, Thông báo, Kế hoạch, Quy chế...) được tải lên, hệ thống/AI Parser hoàn toàn có thể tự động bóc tách ngày ban hành, số hiệu, trích yếu từ thể thức văn bản chuẩn (Nghị định 30/2020/NĐ-CP). Bắt nhập thủ công vừa gây phiền hà vừa vô lý, đặc biệt khi người dùng nạp một lô nhiều tài liệu khác nhau.
2. **Thiếu tính năng nạp hàng loạt (Multi-file Batch Drag & Drop)**:
   - Component trước đó bị khóa cứng `multiple={false}`, `maxFiles={1}`, chỉ cho phép tải từng file đơn lẻ.
   - Khi có nhiều tài liệu đào tạo, quy chế, người dùng muốn kéo thả 5-20 tệp cùng lúc từ máy tính vào modal.

---

## 2. Các Thay Đổi & Giải Pháp Kiến Trúc

### 2.1. Backend: Tự Động Nhận Diện Metadata Hành Chính NĐ 30 (`backend/app/modules/knowledge/cleaner.py` & `service.py`)
- **Tuân thủ Tôn chỉ 7 (`AGENTS.md`) — Bất biến cú pháp (Syntactic Invariants), Zero Hardcoded Vocabulary**:
  - Xây dựng hàm `extract_administrative_metadata(text: str) -> dict[str, object]`:
    - **Ngày ban hành (`issued_date`)**: Nhận diện regex thể thức chuẩn góc trên bên phải: `r'(?:ngày|ng\u00e0y)\s+0?([1-9]|[12][0-9]|3[01])\s+th\u00e1ng\s+0?([1-9]|1[0-2])\s+n\u0103m\s+(19\d{2}|20\d{2})'` $\rightarrow$ chuyển đổi thành `datetime.date(YYYY, MM, DD)`.
    - **Số hiệu văn bản (`document_number`)**: Nhận diện thể thức chuẩn góc trên bên trái: `r'(?:Số|S\u1ed1)\s*:\s*([0-9]+/[A-Z\u0110\u0111a-z0-9\-_/]+)'`.
    - **Mã loại văn bản (`document_type_code`)**: Phân tích ký hiệu chữ viết tắt loại văn bản trong số hiệu (`_ND30_ABBREV_MAP`: `QĐ` $\rightarrow$ `quyet_dinh`, `TB` $\rightarrow$ `thong_bao`, `KH` $\rightarrow$ `ke_hoach`, `QC` $\rightarrow$ `quy_che`, `HD` $\rightarrow$ `huong_dan`, v.v.) hoặc tiêu đề loại văn bản viết hoa ở phần mở đầu. Chuẩn hóa qua `normalize_document_type_code`.
    - **Trích yếu tiêu đề (`title`)**: Nhận diện sau cú pháp `V/v:` hoặc `Về việc:` chuẩn NĐ 30.
    - **Cơ quan ban hành (`issuing_authority`)**: Tự động nhận diện `Trường Đại học Quy Nhơn` / Bộ GD&ĐT.
    - **Người ký (`signer`)**: Nhận diện chức danh và họ tên người ký ở cuối văn bản.
- **Tích hợp Service Layer (`backend/app/modules/documents/service.py`)**:
  - Trong `parse_and_cache_document`, tự động điền các trường còn thiếu (`doc.issued_date`, `doc.document_number`, `doc.document_type_code`, `doc.title`, `doc.issuing_authority`) ngay khi bóc tách văn bản.
  - Lưu chi tiết vào `doc_metadata["auto_detected_metadata"]` để người dùng đối soát minh bạch.

### 2.2. Frontend: Tái Thiết Kế UI Modal Nạp Tài Liệu Tập Trung (`DocumentUploadModal`)
- **Kéo thả nhiều tệp (`multiple={true}`)**:
  - Hỗ trợ kéo thả tối đa 50 tệp cùng lúc (`maxFiles={50}`, `maxSize={50MB}`).
  - Thêm thanh tóm tắt thông tin: `Đã chọn X tệp (Tổng Y MB)` kèm nút `Xóa tất cả`.
  - Cải tiến container danh sách tệp trong `FileUpload` với `max-h-48 overflow-y-auto` để cuộn gọn gàng khi chọn nhiều tệp, không làm tràn modal.
- **Loại bỏ form nhập liệu thủ công rườm rà**:
  - Xóa bỏ toàn bộ các ô nhập tay bắt buộc `issuedDate`, `documentNumber`, `signer`, `title`.
  - Thay bằng **Card Thông Tin Bóc Tách Tự Động (Smart Recognition Banner)** phong cách Academic Teal với icon `Sparkles`:
    *Giải thích rõ AI & Parser NĐ 30 sẽ tự động nhận diện ngày ban hành, số hiệu, trích yếu và người ký từ nội dung từng văn bản sau khi tải lên.*
- **Cấu hình chung tùy chọn cho lô tải lên (`Collapsible`)**:
  - Cung cấp mục tùy chọn rút gọn: cho phép người dùng chỉ định loại văn bản chung hoặc cơ quan ban hành chung nếu cần gán nhãn hàng loạt cho cả lô tệp.
- **Tiến trình tải lên hàng loạt trực quan (Batch Upload Progress)**:
  - Hiển thị thanh `<Progress />` theo thời gian thực (`Đang tải lên tệp 2/5 (40%): thong_bao.pdf...`).
  - Disable các nút điều khiển trong khi đang tải để chống race condition.
  - Toast thông báo tổng kết chi tiết số tệp thành công khi hoàn tất và tự động làm mới kho tài liệu.

---

## 3. Kết Quả Kiểm Thử

1. **Backend Tests**:
   - Chạy toàn bộ test suite `tests/test_document_repository.py`: **6/6 PASSED 100%**.
   - Bổ sung test case `test_document_repository_auto_detect_nd30_metadata`: xác nhận nhận diện chính xác 100% Ngày ban hành `2025-08-15`, Số hiệu `2139/QĐ-ĐHQN`, Loại văn bản `quyet_dinh`, Tiêu đề `Ban hành quy chế tổ chức đào tạo đại học năm học 2025 - 2026`, Cơ quan `Trường Đại học Quy Nhơn`.
   - **Ruff linter**: `0 errors` trên toàn bộ codebase backend.
2. **Frontend Typecheck & Linting**:
   - **TypeScript Typecheck (`tsc --noEmit`)**: **0 errors (Pass 100%)**.
   - **Biome Linter (`biome check`)**: **0 errors (Pass 100%)**.
   - **Hot Module Replacement (HMR)**: Giao diện cập nhật tức thì trên trình duyệt tại `http://localhost:3000/documents`.

---

## 4. Danh Sách Tệp Đã Sửa Đổi / Bổ Sung

1. [`backend/app/modules/knowledge/cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/cleaner.py) — Bổ sung hàm `extract_administrative_metadata` bóc tách ngày ban hành, số hiệu, trích yếu, người ký theo Nghị định 30.
2. [`backend/app/modules/documents/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/service.py) — Tự động điền metadata hành chính vào `RepositoryDocument` khi bóc tách.
3. [`backend/tests/test_document_repository.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_document_repository.py) — Bổ sung test case kiểm thử tự động nhận diện metadata NĐ 30.
4. [`frontend/src/components/admin/file-upload.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/file-upload.tsx) — Thêm thanh cuộn `max-h-48 overflow-y-auto` cho danh sách tệp tải lên nhiều file.
5. [`frontend/src/features/documents/components/document-upload-modal.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/documents/components/document-upload-modal.tsx) — Tái thiết kế toàn diện modal nạp tài liệu: kéo thả nhiều file, bỏ nhập tay ngày ban hành, banner AI Smart Recognition, batch upload progress.
