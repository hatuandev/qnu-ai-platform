# Phiên 782 — Nạp khóa E2E từ .env qua ModelOps

## Yêu cầu và ngoại lệ có phạm vi

Người dùng yêu cầu lưu khóa server QNU và 9router trong .env để không nhập lại mỗi phiên test. Theo ưu tiên chỉ dẫn người dùng, bổ sung ngoại lệ ngày 01/11/2026 trong security-and-git.md: chỉ bootstrap E2E qua API ModelOps local, không biến .env thành fallback/override credential runtime, không áp production.

## Thay đổi

- scripts/e2e_provider_setup.py: nếu connection đã có key active, dùng lại trước và không đọc .env/rotate. Nếu thiếu, đọc E2E_QNU_API_KEY hoặc E2E_9ROUTER_API_KEY từ .env ở root; trống/thiếu thì hỏi nhập ẩn như trước. Sau đó vẫn POST key qua API ModelOps, chỉ lưu key ID vào checkpoint.
- Parser dùng python-dotenv đã cài, đọc literal, không nội suy biến, không nạp vào os.environ hoặc truyền từ file sang API/worker/Vite/Playwright. Cú pháp sai, biến trùng, khóa nhiều dòng/control char hoặc quá ngắn báo lỗi không kèm giá trị. Chỉ đọc đúng hai tên E2E; endpoint/model/capacity vẫn theo profile/ModelOps.
- Bổ sung ô trống còn thiếu vào .env local và .env.example, giữ nguyên mọi giá trị cũ. Không trích khóa DB hoặc điền khóa thật thay người dùng; người dùng tự điền hai biến. .env vẫn Git ignored và không được stage. .env.example chỉ thêm hai giá trị trống.
- Giữ bước chọn model/capacity thiếu, guard phiên đã upload và quy trình hiện có. Không gọi provider-setup trên phiên đang có dữ liệu để vượt guard, không cleanup/init/restart hoặc gọi model.
- Cập nhật ba hướng dẫn test về ưu tiên key và cách dùng .env.

## Kiểm chứng

- Trước sửa implementation: 15 test provider chạy, 1 FAIL/2 ERROR đúng chức năng đọc .env còn thiếu; không gọi provider thật.
- Sau sửa: unittest discover scripts/test_*.py **33 PASS**, gồm 17 test provider và các test runner hiện có. Fake HTTP xác nhận hai key khác nhau vào đúng ModelOps connection, không hỏi key khi file đã điền, không có secret trong output/checkpoint/file phiên, ưu tiên key active, lỗi an toàn, thiếu file, literal interpolation, duplicate/multiline bị chặn. Các thông báo cleanup trong unittest là fixture giả, không dọn phiên live.
- Scoped Ruff format/check PASS. Diff whitespace, UTF-8/LF, liên kết tài liệu và Git ignore được kiểm tra.
- Live với khóa thật NOT_RUN: chưa được cung cấp khóa trong hai ô mới, không đọc/chép key trong DB để tạo .env. Không chạy full backend/frontend vì không đổi runtime/API/UI ứng dụng.

## Cách dùng

Điền E2E_QNU_API_KEY và E2E_9ROUTER_API_KEY trong .env ở root, mỗi key một dòng, có thể bọc nháy đơn. Không gửi key vào chat. Chạy provider-setup như cũ khi chuẩn bị một phiên chưa upload tài liệu. Nếu đang tiếp tục phiên cũ có key active, không cần chạy lại provider-setup. Sau cleanup/init có chủ đích, runner sẽ nạp lại từ file này. Đổi key trong file không tự rotate key đã active; dùng ModelOps cho việc xoay khóa.
