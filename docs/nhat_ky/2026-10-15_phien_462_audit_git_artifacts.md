# Phiên 462 — Rà file test và artifact trong Git

## Yêu cầu và phạm vi

Người dùng hỏi nhiều file test khi push có ổn không, có cần dọn không. Chỉ kiểm tra chỉ mục/cây Git và ignore rules; chưa được yêu cầu thực hiện dọn. Áp dụng skill qnu-clean-code-architect, không xóa file hoặc chỉnh code/runtime.

## Kết quả tại HEAD 40c8c65

Dung lượng dưới đây là tổng byte nội dung file trong cây HEAD, chưa nén, không phải dung lượng .git hoặc số byte phải truyền khi push.

| Nhóm | File | MiB |
| --- | ---: | ---: |
| Toàn cây HEAD | 4389 | 443,34 |
| Mã Python backend/tests | 141 | 1,50 |
| backend/storage | 2172 | 129,93 |
| docs/tai_lieu | 36 | 274,17 |
| tmp gốc | 14 | 1,44 |

PDF Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1).pdf đang nằm trong cây Git thường, 170295266 byte (~162,41 MiB). Có các artifact PDF scan, JSON evaluation, pytest output và backup test trong storage; chưa phân loại đầy đủ file cần thiết cho fixture hay xác minh có bí mật thật. Không mở nội dung credentials để tránh lộ dữ liệu.

.gitignore chưa bao phủ toàn bộ backend/storage và các biến thể thư mục pytest. Thêm ignore không gỡ các file đã được theo dõi. .dockerignore đã loại backend/storage, storage, tmp, docs/tai_lieu khỏi build context gốc, nhưng không giảm clone/push Git.

## Đề xuất

Giữ source test, conftest, fixture nhỏ cần cho regression và lock/config. Phân loại artifact sinh tự động rồi bỏ theo dõi có phạm vi, giữ file local; bổ sung ignore. Đưa tài liệu nặng lên MinIO/S3 theo quy định dự án, hoặc LFS nếu thật sự cần version. Kiểm tra tham chiếu harness trước khi bỏ theo dõi fixture. Lịch sử Git vẫn chứa blob cũ; muốn giảm cả lịch sử cần phương án riêng có bản sao và đồng thuận trước khi rewrite/force-push. GitHub chặn file Git thường >100 MiB: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github . Chưa xác nhận thông báo lỗi push thực tế của GitHub.

Không chạy test/build vì chỉ audit metadata. Không cleanup/index mutation/commit/push/rewrite hoặc tác động DB/server. Nhật ký và bộ nhớ được cập nhật riêng; chưa nghiệm thu độ sạch repo.
