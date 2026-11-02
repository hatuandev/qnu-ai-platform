# Phiên 800 — Sửa lỗi chính tả bệnh viện cấp cơ bản và compiler lại Quy chế 363 (Version 29)

Ngày: 2026-11-01. Phản hồi người dùng: "chỗ này chưa đúng sai 'Bị bệnh nặng hoặc bị tai nạn nghiêm trọng không thể nhập học đúng hạn, có hồ sơ y tế và xác nhận của bệnh viện cấp cơ huyên trở lên.', sai chỗ bán → huyên (AI sửa phiên 797). Phải là bán → bản".

## 1. Xác minh nguyên nhân

- **OCR gốc** (`ocr_89d03deb881b`, trang 15, `ev_p015_b007`):
  `b) Bị bệnh nặng hoặc bị tai nạn nghiêm trọng không thể nhập học đúng hạn, có hồ so y tế và xác nhận của bệnh viện cấp cơ bán trở lên.`
  OCR đã đọc nhầm dấu hỏi thành dấu sắc ở chữ `bản` (`bán`) và `hồ so` (`hồ sơ`).
- **Lỗi phát sinh ở phiên 797**:
  Prompt sửa chính tả tự động bằng AI đã suy đoán nhầm `cơ bán` thành `cơ huyên` (nghĩ là cấp huyện nhưng lại giữ chữ "cơ" và gõ thiếu dấu nặng), dẫn đến cụm từ sai ngữ nghĩa `cấp cơ huyên trở lên`.
- **Căn cứ đối chiếu ảnh gốc & pháp lý**:
  - Đối chiếu ảnh gốc và Điều 16 khoản 4 điểm b (Trang 20 của chính Quy chế 363): đã ghi rõ chuẩn xác *"có giấy xác nhận của bệnh viện cấp cơ bản trở lên"*.
  - Theo Luật Khám bệnh, chữa bệnh 2023 (phân cấp kỹ thuật y tế thành 3 cấp: ban đầu, cơ bản, chuyên sâu), thuật ngữ chuẩn là **"bệnh viện cấp cơ bản trở lên"**.
  - Nhận xét của người dùng chính xác 100%: Lỗi của OCR chỉ là sai dấu `bán` → `bản`.

## 2. Triển khai sửa đổi và cập nhật Text Version 29

- Đã gửi request `POST /platform/v1alpha1/.../text-review` cập nhật `ev_p015_b007`:
  - Before: `b) Bị bệnh nặng hoặc bị tai nạn nghiêm trọng không thể nhập học đúng hạn, có hồ sơ y tế và xác nhận của bệnh viện cấp cơ huyên trở lên.`
  - After: `b) Bị bệnh nặng hoặc bị tai nạn nghiêm trọng không thể nhập học đúng hạn, có hồ sơ y tế và xác nhận của bệnh viện cấp cơ bản trở lên.`
- Kết quả:
  - **Text Version mới**: **Version 29**.
  - **Canonical SHA256**: `102a200441d5c986fc5dd7194ff37e0b1a5945ae1f0374282a61468600670876`.
  - Cập nhật bền vững vào `tmp/v1-e2e/93faa11f0caf/checkpoint.json`.

## 3. Chạy lại Compiler mới từ Version 29

- Tạo Compilation Run:
  - Run ID: **`cmp_5b8a2375d0d9`** (vẫn lưu giữ lịch sử các run `cmp_9d0b9f63f911` và `cmp_51223c447c59`).
  - Gắn chặt với `text_versions: {"ocr_89d03deb881b": 29}`.
  - Cấu hình: Qwen `qwen3.8-27b-q4`, `structured_output=True`, `auto_review=False`, `reasoning off` (`enable_thinking=false`).
- Kết quả:
  - Trạng thái: **completed** (8/8 parts hoàn tất).
  - Thời gian: **252.297s** (~4.2 phút).
  - Quy mô: **35 sections**, **644 citations**.
  - Kiểm tra kết quả tổng hợp của Điều 10 trong draft:
    > *"1. Thí sinh đã có giấy báo trúng tuyển được bảo lưu kết quả trúng tuyển trong những trường hợp sau: ... b) Bị bệnh nặng hoặc bị tai nạn nghiêm trọng không thể nhập học đúng hạn, có hồ sơ y tế và xác nhận của bệnh viện cấp cơ bản trở lên."*
    Trích dẫn chính xác: `ocr_89d03deb881b:ev_p015_b005`, `ocr_89d03deb881b:ev_p015_b006`, `ocr_89d03deb881b:ev_p015_b007`.

## 4. Ranh giới kiểm thử

- Tiếp tục tuân thủ yêu cầu: **Chưa xuất bản** (draft), **chưa lập chỉ mục** (un-indexed) và **chưa chạy lại** bộ 19 câu F01–F19.
- Cảnh báo hình học bảng trang 32 (`column_spec_reconciled`) được giữ nguyên trạng.

## 5. Artifacts được cập nhật

- `tmp/ocr799/corrected.md` & `corrected.json` (Văn bản sau sửa chính tả Version 29).
- `tmp/ocr799/quy-che-363-ocr-highlight.md` & `quy-che-363-ocr-highlight.json` (Bản xem đối chiếu bôi đậm).
- `tmp/ocr799/changes_report.md` & `changes_report.json` (Báo cáo chi tiết các lỗi sửa).
- `tmp/ocr799/compiled.md` & `compiled-draft.json` (Kết quả draft compiler mới nhất).
- `tmp/ocr799/compiler.json` (Biên nhận compiler run `cmp_5b8a2375d0d9`).
