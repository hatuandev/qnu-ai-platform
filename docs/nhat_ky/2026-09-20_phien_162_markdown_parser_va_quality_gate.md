# NHẬT KÝ PHIÊN LÀM VIỆC #162

## Thời gian và mục tiêu

- **Thời gian:** 2026-09-20 22:08 (UTC+7)
- **Mục tiêu:** Tiếp tục xử lý hai file Markdown đã bóc tách để bảo đảm chúng đi qua đúng pipeline chuẩn hóa, Quality Gate, record-aware chunking và Structured Facts trước khi nạp Qdrant.

## Tóm tắt thay đổi

| Tệp | Hành động | Mô tả |
|---|---|---|
| [`backend/app/modules/knowledge/parsers/markdown_parser.py`](../../backend/app/modules/knowledge/parsers/markdown_parser.py) | Tạo mới | Bổ sung parser Markdown UTF-8, nhận diện/tái dựng bảng GFM nhiều block và chuyển các block kế hoạch nhiệm vụ thành record có cấu trúc. |
| [`backend/app/modules/knowledge/parsers/__init__.py`](../../backend/app/modules/knowledge/parsers/__init__.py) | Cập nhật | Định tuyến `.md` sang `MarkdownParser` thay cho `PlainTextParser`. |
| [`backend/tests/test_domain_records_and_quality_gate.py`](../../backend/tests/test_domain_records_and_quality_gate.py) | Cập nhật | Bổ sung kiểm thử parser kế hoạch nhiệm vụ và bảng tuyển sinh bị tách block. |
| [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](../quy_trinh/02_nap_tri_thuc_minio.md) | Cập nhật | Đồng bộ quy trình tiếp nhận Markdown trực tiếp và chính sách chặn dữ liệu mâu thuẫn trước Qdrant. |

## Kết quả kiểm tra dữ liệu thực tế

### Kế hoạch triển khai nhiệm vụ 2025-2026

- 1 bảng canonical, 76 dòng nhiệm vụ.
- 76/76 mã nhiệm vụ duy nhất và hợp lệ.
- Quality Gate: **đạt**.
- Chuẩn bị được 76 record, 76 atomic chunks và 152 Facts.

### Thông tin tuyển sinh đại học 2026

- 5 block bảng GFM, nhận diện 53 ngành.
- Quality Gate: **không đạt do lỗi blocking**.
- Mâu thuẫn cần đối chiếu: ngành Trí tuệ nhân tạo xuất hiện với cả mã `7480207` và `7480107` ở các bảng khác nhau.
- Hệ thống chủ động không tạo chunks/Facts và không nạp Qdrant cho đến khi có xác nhận từ PDF/văn bản chính thức.

## Kiểm thử kỹ thuật

- `uv run ruff check .`: đạt, không có lỗi.
- `uv run --extra dev pytest -v`: **328 passed**.
- Hai file Markdown gốc trong thư mục Downloads không bị ghi đè; chỉ cập nhật Backend parser, test và tài liệu quy trình.

## Việc còn lại

1. Đối chiếu mã ngành Trí tuệ nhân tạo trong file tuyển sinh với PDF/văn bản chính thức và hiệu đính qua Verification Studio.
2. Sau khi xác nhận, chạy lại Quality Gate rồi mới approve/index Qdrant.
3. Có thể làm sạch thêm các dấu OCR nhỏ như `,;` và ký tự đầu dòng bị thiếu trong tài liệu kế hoạch; đây là cải thiện chất lượng văn bản, không phải lỗi an toàn dữ liệu.
