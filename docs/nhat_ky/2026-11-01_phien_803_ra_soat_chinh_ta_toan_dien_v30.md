# Phiên 803 — Rà soát toàn diện chính tả và ngữ cảnh 32 trang Quy chế 363 (Text Version 30)

Ngày: 2026-11-01.
Yêu cầu của người dùng: "bạn hãy giúp tôi rà lại chính tả và ngữ cảnh của file md so với file pdf cho đúng giúp tôi".

## 1. Mục tiêu và phạm vi

- **Tài liệu nguồn**: `docs/tai_lieu/tuyen_sinh/Quy chế tuyển sinh đại học 2026 - 363.pdf` (32 trang scan ảnh 100%, không có text layer).
- **OCR Source Run**: `ocr_89d03deb881b` (176 DPI, Nemotron parser v2).
- **Phạm vi xử lý**:
  - Đối chiếu toàn bộ 601 units của tài liệu đối với ảnh scan gốc độ phân giải cao cắt trực tiếp từ file PDF bằng PyMuPDF (`fitz`).
  - Phát hiện và khắc phục triệt để các sai lệch ngữ cảnh do mô hình AI ở phiên 797 tự suy đoán thay thế từ (hallucinations/distortions) và các lỗi chính tả hệ thống của OCR chưa được nhận diện.
  - Cập nhật tài liệu text review qua API chính thức `POST /platform/v1alpha1/.../text-review` tạo **Text Version 30**.
  - Biên soạn lại tài liệu bằng Compiler run mới (`cmp_f5401a18cdcf`) từ Text Version 30.
  - Xuất đồng bộ toàn bộ artifacts trong thư mục `tmp/ocr799/`.

## 2. Các sai lệch ngữ cảnh & chính tả được phát hiện và xử lý

Qua việc so sánh từng unit với ảnh chụp trang PDF gốc và quét toàn bộ 140 diffs lịch sử:

### 2.1. Lỗi AI suy đoán sai nghĩa / làm méo mó ngữ cảnh (phiên 797)
1. **Trang 3 (`ev_p003_b009`, `ev_p003_b010`)**: OCR gốc đọc thiếu dấu nặng `thiết bị nối mang`, AI phiên 797 sửa nhầm `nối` thành `mạng` nhưng vẫn giữ `mang`, dẫn đến lỗi nghiêm trọng thành `thiết bị mạng mang hoặc trả lời phỏng vấn`.
   - *Chuẩn theo ảnh scan*: `thiết bị nối mạng hoặc trả lời phỏng vấn`.
2. **Trang 5 (`ev_p005_b009`)**: OCR gốc là `dụ tuyển`, AI phiên 797 suy đoán nhầm thành `tuyển sinh` làm biến dạng ngữ cảnh (*"Về cơ hội tuyển sinh: không thí sinh nào bị mất cơ hội tuyển sinh..."*).
   - *Chuẩn theo ảnh scan*: `Về cơ hội dự tuyển: không thí sinh nào bị mất cơ hội dự tuyển do những quy định không liên quan tới trình độ, năng lực...`.
   - Đồng thời sửa lỗi dấu `tổn kém` → `tốn kém` ở cuối câu.
3. **Trang 11 (`ev_p011_b003`)**: AI phiên 797 sửa `thị` thành `tay`, tạo thành cụm lặp `tay tay nghề quốc tế`.
   - *Chuẩn theo ảnh scan*: `và thi tay nghề quốc tế do Bộ GDĐT cử tham gia`.
4. **Trang 11 (`ev_p011_b013`)**: OCR gốc đọc `môn thì`, AI phiên 797 sửa nhầm `thì` thành `tế`, biến thành cụm từ vô nghĩa `môn tế`.
   - *Chuẩn theo ảnh scan*: `phù hợp với môn thi hoặc nội dung đề tài dự thi đã đạt giải`.
5. **Trang 13 (`ev_p013_b009`)**: AI phiên 797 chèn lặp từ `tương`, biến thành `vận động viên kiện tướng tương, vận động viên`.
   - *Chuẩn theo ảnh scan*: `vận động viên kiện tướng, vận động viên đã từng đạt huy chương`.
6. **Trang 17 (`ev_p017_b006`)**: AI phiên 797 chèn lặp từ do ngắt dòng: `(gọi tắt tất là Hệ thống)`.
   - *Chuẩn theo ảnh scan*: `(gọi tắt là Hệ thống)`.

### 2.2. Lỗi dấu hệ thống của OCR (`tuyến` → `tuyển`)
Do chất lượng mực scan, OCR thường xuyên nhận nhầm dấu hỏi thành dấu sắc ở cụm `tuyển` / `dự tuyển` / `xét tuyển`:
- **Trang 5 (`ev_p005_b003`)**: `tiêu chí xét tuyến` → `tiêu chí xét tuyển`.
- **Trang 7 (hệ thống Điều 6, 10 vị trí)**:
  - `ev_p007_b003`: `điều kiện dự tuyến... phương thức tuyến sinh` → `điều kiện dự tuyển... phương thức tuyển sinh`.
  - `ev_p007_b004`: `người dự tuyến... đăng ký dự tuyến` → `người dự tuyển... đăng ký dự tuyển`.
  - `ev_p007_b005`: `Điều 6. Phương thức tuyến sinh và nguồn tuyến` → `Điều 6. Phương thức tuyển sinh và nguồn tuyển`.
  - `ev_p007_b006`: `tuyến sinh... xét tuyến thẳng, xét tuyến đối tượng cử tuyến, xét tuyến đối tượng dự bị` → toàn bộ thành `tuyển`.
  - `ev_p007_b007`: `phương thức tuyến sinh... xét tuyến... trúng tuyến` → `tuyển sinh... xét tuyển... trúng tuyển`.
  - `ev_p007_b008`: `xét tuyến` → `xét tuyển`.
  - `ev_p007_b009`: `Phương thức xét tuyến... người dự tuyến... xét tuyến` → `xét tuyển... người dự tuyển... xét tuyển`.
  - `ev_p007_b010`: `thang điểm xét tuyến` → `thang điểm xét tuyển`.
  - `ev_p007_b011`: `tổ hợp xét tuyến` → `tổ hợp xét tuyển`.
  - `ev_p007_b012`: `Nguồn xét tuyến... tổ hợp xét tuyến` → `Nguồn xét tuyển... tổ hợp xét tuyển`.
- **Trang 8 (`ev_p008_b003`)**: `đăng ký xét tuyến đại học` → `đăng ký xét tuyển đại học`.
- **Trang 14 (`ev_p014_b003`, `b004`, `b005`, `b006`, `b011`, `b015`)**: 7 vị trí `xét tuyến`, `dự tuyến`, `trúng tuyến` đều được sửa thành `tuyển`.
- **Trang 19 (`ev_p019_b003`)**: `Điểm trúng tuyến... số lượng tuyến được... số lượng tuyến sinh` → `Điểm trúng tuyển... số lượng tuyển được... số lượng tuyển sinh`.
- **Trang 21 (`ev_p021_b003`)**: `Thí sinh chưa trúng tuyến` → `Thí sinh chưa trúng tuyển`.
- **Trang 28 (`ev_p028_b016`)**: `TUYẾN SINH CAO ĐẲNG` → `TUYỂN SINH CAO ĐẲNG`.

### 2.3. Lỗi thiếu dấu và sai dấu thuật ngữ
- **Trang 4 (`ev_p004_b005`)**: `_Tiêu chi xét tuyển_ là những tiêu chi... các tiêu chi... điểm công` → `_Tiêu chí xét tuyển_ là những tiêu chí... các tiêu chí... điểm cộng`.
- **Trang 5 (`ev_p005_b005`)**: `điểm ưu tiên và điểm công (nếu có)` → `điểm ưu tiên và điểm cộng (nếu có)`.
- **Trang 7 (`ev_p007_b012`)**: `03 môn thì kì thi tốt nghiệp THPT` → `03 môn thi kỳ thi tốt nghiệp THPT`.
- **Trang 9 (`ev_p009_b007`)**: `quy đối chứng chỉ ngoại ngữ` → `quy đổi chứng chỉ ngoại ngữ`.
- **Trang 10 (`ev_p010_b006`)**: `khi quy đối về điểm` → `khi quy đổi về điểm`.
- **Trang 11 (`ev_p011_b006`)**: `Hiệu\ntrường)` → `Hiệu\ntrưởng)`.
- **Trang 14 (`ev_p014_b011`)**: `Giáo dục Thể chat` → `Giáo dục Thể chất`.
- **Trang 16 (`ev_p016_b007`)**: `quy tắc quy đối tương đương` → `quy tắc quy đổi tương đương`.
- **Trang 19 (`ev_p019_b007`, `ev_p019_b011`)**: `tiêu chi phụ... tiêu chi phân loại... tiêu chi phụ` → `tiêu chí phụ... tiêu chí phân loại... tiêu chí phụ`.

## 3. Kết quả cập nhật Text Version 30

- **API Request**: `POST /platform/v1alpha1/.../text-review`
  - Idempotency key: `scan801-ocr_89d03deb881b-fix-spelling-context-v30`
  - Số units cập nhật: 36 units.
- **Kết quả trả về**:
  - **Version mới**: **Version 30**.
  - **Canonical SHA256**: `988fe0ae8b9b5c66675dbeef43c02cde575b5c4f72d99bcd137fb19603c89c5f`.
  - Cập nhật bền vững vào `tmp/v1-e2e/93faa11f0caf/checkpoint.json`.

## 4. Compilation Run từ Text Version 30

- **Run ID**: `cmp_f5401a18cdcf`
- **Idempotency Key**: `scan801-ocr_89d03deb881b-compiled-v30`
- **Gắn chặt với text_version**: `{"ocr_89d03deb881b": 30}`
- **Cấu hình**: Qwen `qwen3.8-27b-q4`, `structured_output=True`, `auto_review=False`, `reasoning off`.
- Toàn bộ kết quả draft và markdown được xuất ra `tmp/ocr799/compiled-draft.json` và `tmp/ocr799/compiled.md`.

## 5. Ranh giới kiểm chứng và cam kết tuân thủ

- **Chưa xuất bản** (draft status).
- **Chưa lập chỉ mục** (không re-index, không đưa vào vector store).
- **Không chạy lại benchmark F01–F19**.
- **Cảnh báo hình học bảng trang 32 (`column_spec_reconciled`)**: Giữ nguyên trạng 100%.
- **Chữ số, công thức, ngày tháng**: Đã xác nhận không có bất kỳ ký tự số nào bị thay đổi so với bản gốc.
