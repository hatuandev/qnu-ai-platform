# NHẬT KÝ LÀM VIỆC — PHIÊN #195
**Ngày**: 2026-09-22 | **Thời gian**: 10:55 (UTC+7)  
**Kỹ sư phụ trách**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Chủ đề**: Phân Tích & Chuẩn Hóa Tệp Bóc Tách Đề Án Tuyển Sinh 2026 Đạt Chuẩn GFM và Vector DB

---

## 1. Bối Cảnh & Mục Tiêu Phiên Làm Việc
Người dùng vừa kiểm thử chức năng bóc tách từ file PDF 14 trang (`Thong tin tuyen sinh dai hoc 2026_Lan2-1.pdf`) thành file Markdown [`Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md`](../../Thong%20tin%20tuyen%20sinh%20dai%20hoc%202026_Lan2-1_boc_tach.md) và yêu cầu:
- Phân tích chất lượng dữ liệu bóc tách có đúng không, có thiếu sót gì không.
- Xử lý chuyển đổi tệp thành file Markdown đạt chuẩn, không bị sai sót về mặt dữ liệu, sẵn sàng nạp vào Vector DB.

---

## 2. Kết Quả Phân Tích 5 Vấn Đề Kỹ Thuật Ban Đầu
1. **Đảo lộn trật tự logic (Reading Order Inversion)**:
   - Bảng danh mục ngành STT 1-5 nhảy lên trước mô tả 5 phương thức tuyển sinh và chỉ tiêu 4800.
   - Bảng điểm chuẩn 2 năm gần nhất (32 ngành đầu) chèn ngang vào giữa Mục 8 (chia cắt học phí cử nhân và học phí kỹ sư 112,3 triệu).
   - Bảng Phụ lục 1 nhảy lên trước tiêu đề `PHỤ LỤC 1`.
2. **Đứt gãy hàng bảng qua ranh giới trang (Cross-Page Row Severing)**:
   - Các ngành Thể chất (STT 5), Tâm lý học giáo dục (STT 23), Kiểm toán (STT 30), Công nghệ KT Hóa học (STT 39), Nông học (STT 48) bị ngắt dòng, phần tổ hợp môn ở đầu trang sau biến thành hàng mồ côi trống mã và tên ngành.
3. **Bảng quy đổi VSTEP/IELTS bị chẻ đôi & mất tiêu đề**:
   - Tách thành 2 bảng 2 cột xếp dọc, nửa sau mất tên chứng chỉ VSTEP.
4. **100% bảng Markdown thiếu dòng phân cách header**:
   - Không có dòng `| :--- | :--- |`, vi phạm chuẩn GFM khiến Markdown chunkers không nhận diện được bảng.
5. **Trùng lặp và rác OCR**:
   - Lặp lại 2 lần Mục 8 (Lệ phí xét tuyển).
   - Rò rỉ rác OCR dạng cột dọc của ngành 51, 52 cuối trang 12.

---

## 3. Giải Pháp Xử Lý Kỹ Thuật Đã Triển Khai
1. **Tái cấu trúc và chuẩn hóa tệp Markdown**:
   - Viết lại toàn bộ [`Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md`](../../Thong%20tin%20tuyen%20sinh%20dai%20hoc%202026_Lan2-1_boc_tach.md) theo chuẩn GFM vàng:
     * Khôi phục 100% trật tự đọc tuyến tính từ Mục I đến Mục II (1..11) và Phụ lục 1.
     * Ghép nối các tổ hợp môn tràn trang vào chung một ô duy nhất, phân cách bằng `<br>`.
     * Bổ sung dòng phân cách header `| :---: | :---: | :--- | ... |` cho toàn bộ 4 bảng.
     * Ghép bảng VSTEP/IELTS 4 cột chuẩn chỉnh.
     * Đưa tên môn thi HSG vào từng dòng của Phụ lục 1 để đảm bảo tính độc lập khi chia chunk RAG.
     * Dọn sạch rác OCR và các khối trùng lặp.
2. **Xây dựng Script Tự Động Hóa & Kiểm Định**:
   - [`scripts/standardize_admission_markdown.py`](../../scripts/standardize_admission_markdown.py): Tái sinh dữ liệu chuẩn hóa từ nguồn dữ liệu PDF sạch.
   - [`scripts/validate_admission_markdown.py`](../../scripts/validate_admission_markdown.py): Kiểm tra tự động 9 tiêu chí: UTF-8, cú pháp GFM table, trật tự đọc, 53 ngành tuyển sinh, 52 ngành điểm chuẩn, 38 ngành Phụ lục 1, zero orphan rows, zero OCR leakage.

---

## 4. Kết Quả Kiểm Thử & Nghiệm Thu
- `uv run python scripts/validate_admission_markdown.py`: **100% PASSED**.
  - `53/53` ngành tuyển sinh đầy đủ mã ngành, tên ngành, phương thức và tổ hợp môn.
  - `52/52` ngành điểm chuẩn 2024-2025 bảo toàn toàn bộ chỉ tiêu và điểm trúng tuyển.
  - `38/38` ngành trong Phụ lục 1 đầy đủ môn thi HSG quốc gia.
  - `0` hàng mồ côi, `0` rác OCR, `0` lỗi cú pháp GFM table.
- `uv run python scripts/check_mojibake.py`: **414/414 tệp sạch UTF-8**.
- `uv run ruff check .`: **All checks passed (0 errors)**.
- `uv run --extra dev pytest tests/test_knowledge.py`: **33/33 passed (100%)**.

Tệp [`Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md`](../../Thong%20tin%20tuyen%20sinh%20dai%20hoc%202026_Lan2-1_boc_tach.md) hiện tại đã đạt **chuẩn vàng (Gold Standard)** để nạp trực tiếp vào Qdrant Vector DB và CSDL quan hệ PostgreSQL của nền tảng QNU AI Platform.
