# Phiên 799 — Rà soát chính tả 32 trang và compiler lại Quy chế 363

Ngày: 2026-11-01. Yêu cầu: Chọn phương án 2. Rà soát đủ 32 trang, đối chiếu ảnh gốc và lưu bản sửa có truy vết; chỗ chưa chắc chắn thì giữ nguyên và ghi nhận. Sau đó tạo lượt compiler mới từ bản sửa mới nhất, giữ lịch sử cũ. Chưa xuất bản, chưa lập chỉ mục và chưa chạy lại F01–F19. Báo cáo các lỗi còn tồn tại cùng đường dẫn MD/JSON sau sửa và kết quả compiler.

## 1. Hiện trạng trước khi làm

- Tài liệu nguồn: `docs/tai_lieu/tuyen_sinh/Quy chế tuyển sinh đại học 2026 - 363.pdf` (32 trang ảnh scan, SHA256: `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`).
- OCR run: `ocr_89d03deb881b` (176 DPI, Nemotron parser v2).
- Phiên bản văn bản trước: Version 27, hash `35a43a367df4c037b03c98802228379c6024583f9981ca8bf328251602db1091`.
- Compiler cũ: `cmp_51223c447c59`.
- Vấn đề tồn tại từ phiên 797/798:
  - Trang 31 ảnh ghi `PHỤ LỤC IV` nhưng bản OCR lưu `PHỤ LỰC IV`.
  - Trang 27 trước đây model trả `{}` nên chưa có sửa đổi.
  - 40 đề xuất AI bị loại trong phiên 797 chưa được rà soát đối chiếu ảnh thực tế.
  - Bảng trang 32 có cảnh báo dư cột (OCR sinh 10 cột, ảnh có 8 cột).

## 2. Rà soát và sửa đổi có truy vết

- Đã trích xuất và kết xuất toàn bộ 32 trang PDF sang ảnh 150/200 DPI tại `tmp/ocr799/pages/` để đối chiếu từng chữ.
- Đã rà soát chi tiết 601 units văn bản:
  1. **Tiêu đề Phụ lục (Trang 26, 27, 28, 31)**: Cả 4 phụ lục đều bị OCR đọc nhầm `PHỤ LỰC` → Đã đối chiếu ảnh và sửa thành `PHỤ LỤC I`, `PHỤ LỤC II`, `PHỤ LỤC III`, `PHỤ LỤC IV`.
  2. **Trang 27 (Phụ lục II)**: Sửa `PHỤ LỰC II` → `PHỤ LỤC II`, `ƯU TIỀN` → `ƯU TIÊN`, `người được hướng chính sách` → `người được hưởng chính sách`.
  3. **Trang 31 (Phụ lục IV)**: Sửa `PHỤ LỰC IV` → `PHỤ LỤC IV`, `QUẢN LỶ` → `QUẢN LÝ`, `XÃ HỌI` → `XÃ HỘI`.
  4. **Hình thức thi (Trang 3)**: Sửa 6 vị trí `thi trục tiếp / trục tuyển` → `thi trực tiếp / trực tuyến`.
  5. **Quy định tính điểm & thưởng (Trang 4, 11)**: Sửa `tinh điểm xét` → `tính điểm xét`, `01 món` → `01 môn`, `điểm thường` → `điểm thưởng`.
  6. **Chứng chỉ ngoại ngữ & điều chỉnh (Trang 8, 9)**: Sửa 11 vị trí `chứng chi ngoại ngữ` → `chứng chỉ ngoại ngữ`, `điều chính` → `điều chỉnh`, `quy đối` → `quy đổi`.
  7. **Đối tượng y tế & kỹ thuật (Trang 13, 14)**: Sửa `trư` → `trừ`, `đối tương` → `đối tượng`, `Ky thuật` → `Kỹ thuật` (cho 4 ngành y tế: Kỹ thuật phục hình răng, Kỹ thuật xét nghiệm y học, Kỹ thuật hình ảnh y học, Kỹ thuật phục hồi chức năng).
  8. **Cơ sở đào tạo & cán bộ (Trang 14, 20, 24, 25)**: Sửa `co sở đào tạo` → `cơ sở đào tạo`, `cấp co bản` → `cấp cơ bản`, `can bộ` → `cán bộ`, `thi sinh` → `thí sinh`, `phân ánh` → `phản ánh`, `hiệu trường` → `hiệu trưởng`.
  9. **Thông tin liên hệ (Trang 32)**: Sửa `địa chi email` → `địa chỉ email`.
- Tổng cộng: **42 units** được cập nhật với **55 lỗi chính tả** được sửa dựa trên đối chiếu ảnh gốc.
- Bảo toàn 100% số liệu (18,00, 8,50, 16,50, 6,50, 3,00...), ngày tháng, mã điều khoản, bbox, table rows/cols và identity.
- Lưu qua API `POST /text-review` thành công:
  - Text version mới: **Version 28**.
  - Canonical hash mới: `b201f88c09b4db510a3f672ffe5032a55a14dce93f6398bf0fedc6515430df73`.
  - Đã cập nhật checkpoint phiên `93faa11f0caf`.

## 3. Compiler lượt mới

- Khởi tạo compilation run mới ghim đúng Version 28:
  - Run ID: `cmp_9d0b9f63f911` (giữ run cũ `cmp_51223c447c59` trong lịch sử).
  - Cấu hình: Chat provider Qwen, `max_output_tokens=16384`, `structured_output=True`, `auto_review=False`, `reasoning off` (`enable_thinking=false`).
  - Idempotency key: `scan799-ocr_89d03deb881b-compiled-corrected-v2`.
- Kết quả compiler:
  - Trạng thái: **completed** (hoàn tất 8/8 phần).
  - Thời gian biên soạn: **304.172s** (~5.07 phút).
  - Quy mô kết quả: **38 mục** (sections), **644 citations** gắn chặt với nguồn OCR text version 28.
  - Các phần chưa rõ và cảnh báo OCR được compiler giữ lại nguyên trạng.

## 4. Các điểm giữ nguyên / tồn tại chưa chắc chắn

1. **Bảng Phụ lục trang 32**: Cấu trúc OCR sinh 10 cột trong khi ảnh nguồn chỉ có 8 cột. Giữ nguyên cảnh báo `column_spec_reconciled` và cấu trúc bảng của OCR, không tự ý xóa cột hay gộp ô trái phép.
2. **Không xuất bản / lập chỉ mục / chạy RAG**: Giữ nguyên ranh giới, chưa xuất bản tài liệu này vào kho tri thức, chưa tạo index và chưa chạy lại bộ 19 câu F01–F19.

## 5. Artifacts được xuất

- Markdown văn bản sau sửa: `tmp/ocr799/corrected.md`
- JSON văn bản sau sửa: `tmp/ocr799/corrected.json`
- Markdown đối chiếu bôi đậm chữ sửa: `tmp/ocr799/quy-che-363-ocr-highlight.md`
- JSON đối chiếu bôi đậm chữ sửa: `tmp/ocr799/quy-che-363-ocr-highlight.json`
- Báo cáo chi tiết các vị trí sửa: `tmp/ocr799/changes_report.md` & `changes_report.json`
- Kết quả bản thảo compiler (Markdown): `tmp/ocr799/compiled.md`
- Kết quả bản thảo compiler (JSON): `tmp/ocr799/compiled-draft.json`
- Biên nhận lượt compiler: `tmp/ocr799/compiler.json`
