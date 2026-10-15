# Phiên 463 — Rà Git ngoài docs/tai_lieu

## Giới hạn bắt buộc

User yêu cầu giữ nguyên docs/tai_lieu, chỉ xem các chỗ khác. Không xóa, di chuyển, bỏ theo dõi, thêm ignore cho thư mục này. Chỉ audit theo skill qnu-clean-code-architect; chưa thực hiện dọn repo hoặc thay đổi index.

## Kiểm kê tại HEAD 40c8c65

Số đo là tổng nội dung chưa nén trong cây HEAD, không phải dung lượng truyền push hay lịch sử.

| Nhóm | File | MiB | Đánh giá |
| --- | ---: | ---: | --- |
| backend/storage/pytest*/ | 1929 | 76,36 | Output sinh bởi test, ưu tiên bỏ tracking giữ local |
| Log toàn repo ngoài docs/tai_lieu | 86 | 4,23 | Output chạy lệnh, không phải mã test; có overlap nhóm khác |
| tmp/ | 14 | 1,44 | Phần lớn ảnh render/PDF/DOCX; giữ helper qa_drafting_render.py khi cần |
| backend/storage/e2e_fixtures | 24 | 13,43 | Có fixture còn được script sử dụng, không dọn nguyên thư mục |
| storage còn lại | 219 | 40,14 | Report JSON/log/eval, cần phân loại trước khi dọn |
| legacy/ | 217 | 4,89 | Mã nguồn cũ, chưa xác minh hết dependency; không tự xóa |
| data/ | 8 | 8,89 | Tài liệu nghiệp vụ và ảnh; không xem là rác hoặc tự xóa |
| browser_tester/ | 9 | 0,87 | Mã công cụ test/lock, giữ |
| storage/ gốc | 7 | 0,22 | Có documents và fixture, giữ dữ liệu/placeholder |

Tập ứng viên ưu tiên là hợp không trùng của backend/storage/pytest*/, *.log ngoài thư mục được bảo vệ, tmp/ trừ *.py: **2028 file, 82,03 MiB**, không chứa file docs/tai_lieu. Đây là danh sách để duyệt bước bỏ tracking, không phải xác nhận được phép xóa vật lý.

Script create_e2e_341_fixtures.py sinh PDF scan; prepare_e2e_studio_source.py đọc lại e2e341_scan_2pages.pdf. Vì vậy E2E fixture cần có đường tái tạo rõ ràng trước khi bỏ khỏi Git. configs_locked nhỏ, browser_tester/lock, tests/conftest cần giữ. Có 52 file đang tracked dù match ignore hiện hành; kiểm tra ignore toàn cục cảnh báo quyền đọc, chưa kết luận bao phủ mọi global rule.

## Đề xuất và trạng thái

Đợt đầu chỉ cập nhật ignore có phạm vi và gỡ tracking tập artifact đã duyệt, giữ nguyên local, source tests, báo cáo tóm tắt và docs/tai_lieu. Không blanket-ignore/xóa cả backend/storage vì fixture/harness và dữ liệu runtime. Không rewrite lịch sử/force-push; blob lịch sử vẫn tồn tại sau untrack. Giữ docs/tai_lieu đồng nghĩa PDF lớn vẫn còn, không hứa GitHub push hết lỗi dung lượng.

Không test/build, không commit/push/cleanup/index mutation, không truy cập DB/server. Chỉ cập nhật nhật ký và memory theo yêu cầu dự án.
