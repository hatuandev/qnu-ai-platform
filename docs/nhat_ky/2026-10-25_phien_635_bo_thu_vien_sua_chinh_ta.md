# Phiên635 — Bỏ thư viện sửa chính tả hậu OCR

Người dùng chọn bỏ thư viện, chỉ dùng kết quả Nemotron sau khi thấy khả năng sửa sai chữ. Đã gỡ dependency, từ điển và toàn bộ hook thử nghiệm; giữ các sửa Nemotron của Context634. Bỏ thêm ba phép thay từ có sẵn trong cleaner. Giữ xử lý cấu trúc bảng/trang và raw OCR; không sửa dữ liệu cũ.

Thay đổi cuối: `backend/app/modules/ocr/cleaner.py`, version extraction trong `backend/app/modules/knowledge/services/source_extraction.py`, cập nhật `backend/tests/test_ocr_cleaner.py`, thêm `backend/tests/test_ocr_literal_635.py`. pyproject/lock không còn thư viện thử nghiệm, giữ tiktoken có trước. Các file hook thử nghiệm được xóa đúng phạm vi.

Tái hiện 2 FAIL trước sửa; focused cuối 128 PASS + 23 subtest PASS/55,04 giây/exit0; Ruff4 PASS. Package metadata và hash các sửa634 xác nhận gỡ sạch mà giữ chức năng trước. API OpenAPI200 không còn trường hậu sửa chữ. Full gate NOT RUN: harness exit1 trước pytest vì PostgreSQL từ chối kết nối, Docker không chạy; readiness503 và không có worker. Chưa test live OCR lại sau thay đổi cuối, không tuyên bố full PASS. Database test từ lượt thử thư viện bị gián đoạn đã dọn đúng phạm vi; không tạo DB mới ở lượt kết nối thất bại.

Không bật lại hạ tầng, không đổi ModelOps/key/defaults, không backfill, index, publish hoặc Compiler. Rủi ro còn lại: lỗi OCR của Nemotron được giữ để đối chiếu thay vì tự sửa bằng thư viện; cần chạy full gate và live khi hạ tầng trở lại. Lệnh, giới hạn và bằng chứng tại [báo cáo635](../bao_cao/context635/REVIEW.md).
