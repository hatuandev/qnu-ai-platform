# Phiên 732 — Hướng dẫn test lại và giải thích review hình ảnh

## Yêu cầu và đối chiếu

Người dùng hỏi thứ tự test từ đầu mỗi khi mở máy và ý nghĩa3nhận xét thiếu OCR. Đọc runner, hướng dẫn, fixture, review/material.py và report.py; API chỉ đọc canonical document của PDF scan xác nhận block figure text rỗng với bbox gần cả trang. Không gọi inference hoặc thay cấu hình/runtime.

Ba finding thuộc cùng một vùng ảnh: heading Hình ảnh, paragraph mô tả Picture chưa có text OCR và unknown ghi chưa biết nội dung. source_units hiện chỉ thêm block thường có text; block figure rỗng không được chuyển thành source unit, còn messages_for bỏ pages/evidence khỏi context. Vì vậy reviewer không có source unit tương ứng. Không kết luận3ảnh hỏng, không nói OCR chính xác hay tự bỏ finding. Cần đối chiếu OCR trang gốc và nối metadata block rỗng nếu xử lý tiếp; chưa sửa backend trong phiên này.

## Tài liệu

- `docs/quy_trinh/V1_QUY_TRINH_TEST_LAI.md`: resume giữ DB khác với cleanup/init phiên mới; đủ14chặng, cấu hình Qwen128K/16K/timeout300, Compiler8192 và các model đã xác nhận; hash OCR lấy từ mã. Làm rõ cleanup xóa cấu hình/key của DB thử, lifecycle xóa nguồn thử và cached replay không phải inference mới.
- Index quy trình và đầu hướng dẫn đầy đủ trỏ bản ngắn mới.
- Không chạy cleanup/init/serve/test/model mới; giữ phiên đang phục vụ và mọi diff trước.

## Kiểm chứng

Chỉ tài liệu: đối chiếu thứ tự với MODEL_STAGES/STAGES và API read-only đã nêu. Kiểm UTF8 không BOM/LF, link local và diff. App test/build NOT RUN theo gate tài liệu; kết quả731 là lịch sử, không nghiệm thu mới. Full pipeline vẫn chưa PASS vì còn nội dung cần xem trước publication.
