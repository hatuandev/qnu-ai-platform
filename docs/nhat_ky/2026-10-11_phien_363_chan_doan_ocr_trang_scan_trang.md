# Phiên #363 — Chẩn đoán OCR lỗi trên trang scan trắng

## Mục tiêu và phạm vi

Chẩn đoán lỗi `EMPTY_OCR_PAGE: Không nhận dạng được trang 48` của batch `imp_batch_6d1321f05898`. Chỉ đọc PDF, code, log và DB; chưa sửa runtime, retry, gọi OCR mới, reset hoặc restart. Không tác động qnu-sso hoặc credential.

## Bằng chứng

- Tệp QĐ 2705 người dùng gửi có 48 trang, không mã hóa, 18.507.242 bytes. SHA-256 `4dfc6601de8d9b6a773c705dccb9ec52743fe4024ae53546f684f1ef085003a3` khớp `origin_file_hash` của item `imp_item_140f96e391e5` trong batch.
- Render trực quan: trang 47 có nội dung đề cương luận văn; trang 48 trắng, chỉ vài đốm nhiễu. Grayscale render 2x của trang 48: mean 254,999099, không pixel dưới 128, tỷ lệ pixel dưới 200 khoảng 0,0002%. Đây là phép đo chẩn đoán, không phải ngưỡng runtime tổng quát.
- Log worker `backend/storage/worker_logs/ba5d59cc762f4e8a9b9e8648911b48bf.stdout.log`: Inspector phân loại scanned/48 trang, gọi Paddle thật; task đầu thất bại sau khoảng 27,92s, retry cũng lỗi trang 48. Stack trace ở `source_extraction.py:112`.
- DB read-only: item failed, phase failed, failure_code EMPTY_OCR_PAGE, chưa có knowledge_source_revision_id. Không phải lỗi embedding/Qdrant hoặc kết nối Paddle của batch này.

## Nguyên nhân

`source_extraction.py` chọn trang có full-page image/no native text để OCR, kể cả ảnh scan trắng. Sau khi Paddle trả thành công và page count khớp, guard dòng 110–112 từ phiên #360 từ chối mọi trang có extracted_text rỗng. Trang trắng hợp lệ do đó làm hỏng toàn tài liệu. Adapter Paddle chỉ từ chối khi toàn kết quả không có text; lỗi ở guard per-page mới. Chưa kiểm định độ chính xác hoặc đầy đủ của nội dung 47 trang trước.

## Đề xuất, chưa triển khai

Phân loại blank theo bằng chứng ảnh/hình thái học tổng quát: nền thích nghi, nhiễu và connected components; ưu tiên bảo thủ để không bỏ chữ mờ. Giữ trang trắng trong manifest/đánh số, ghi trạng thái no-content, không sinh chunks/facts. Trang có dấu hiệu nội dung nhưng OCR rỗng vẫn phải báo lỗi/cần duyệt. Không hardcode trang 48/trang cuối và không bỏ qua tất cả OCR rỗng. Cần regression blank-scan, faint-text, mixed-PDF và OCR failure trước nghiệm thu.

## Tệp và kiểm chứng

Chỉ thêm nhật ký/snapshot và cập nhật PROJECT_CONTEXT, WORK_LOG, index nhật ký. Ảnh render chẩn đoán tại tmp/pdfs/ocr363. Đọc DB bằng transaction read-only; không gọi Paddle mới hoặc nạp lại nguồn. Không chạy Ruff/Pytest/build vì không sửa mã nguồn. Kiểm tra UTF-8 và whitespace của tài liệu.

## Bài học

Đếm trang đúng không đồng nghĩa mỗi trang phải có chữ. Quality gate phải phân biệt trang trắng thực sự và mất nội dung OCR, không dùng guard text-empty làm thay thế cho kiểm tra ảnh.
