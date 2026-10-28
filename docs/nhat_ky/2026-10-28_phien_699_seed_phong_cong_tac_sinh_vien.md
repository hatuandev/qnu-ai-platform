# Context699 — Seed Phòng Công tác sinh viên

Ngày: 2026-10-28. Phạm vi: backendV1, dữ liệu thử nghiệm local và đăng nhập dev gate.

## Yêu cầu và cách thực hiện

Người dùng yêu cầu tạo phòng Công tác sinh viên và user để thử phân quyền cùng admin.
Tạo workspace mã `cong-tac-sinh-vien`, một kho trống và ba membership thử nghiệm:
quản trị workspace, biên tập và thành viên. Admin nền tảng dev hiện có được giữ nguyên.
Đây là danh tính dev để thử, không phải tài khoản SSO hoặc dữ liệu nhân sự thực.

Script `backendV1/scripts/seed_student_affairs.py` kiểm dev gate + DB loopback, dùng
service workspace/collection hiện có để kiểm quyền và ghi audit. Advisory lock cho
chạy lặp; không ghi đè vai trò/trạng thái hoặc đặt lại khóa. Registry local bị Git bỏ
qua, chỉ lưu hash của khóa ngẫu nhiên; danh tính cố định không có quyền admin toàn cục.
Login chạy đọc tệp trong thread riêng, token giữ tên hiển thị; quyền workspace lấy từ DB.

## Thay đổi

- `.gitignore`: bỏ qua riêng `backendV1/.local/` chứa thông tin đăng nhập dev.
- `backendV1/qnu/domains/identity/dev_accounts.py`, `dev_gate.py`, `router.py`.
- `backendV1/scripts/seed_student_affairs.py`.
- Hai test mới `tests/unit/test_dev_seed_accounts.py`, `tests/integration/test_student_affairs_seed.py`.
- `backendV1/README.md`: hướng dẫn seed và đổi tài khoản bằng màn hình Dev Access Key.
- Nhật ký/index/memory/snapshot của phiên này. Giữ nguyên các diff ModelOps/API tích hợp đang có.

## Kiểm chứng thực chạy

- Baseline test mới trước triển khai: FAIL tại import module chưa tồn tại (exit1).
- Ruff check sáu tệp Python: PASS (exit0); đã format đúng phạm vi.
- Unit đăng nhập mới + identity boundary: 8 PASS (exit0), gồm 401/403/503 và không kế thừa AI.Admin.
  Lượt đầu gặp quyền thư mục Temp Windows; chuyển basetemp vào artifact local.
- DB test cô lập: `uv run --frozen --env-file ../.env --extra dev python scripts/test_database.py tests/integration/test_student_affairs_seed.py -q`:
  1 PASS (exit0), DB `qnu_v1_test_886993154f72483a` đã dọn, legacy sentinel giữ nguyên.
- Seed DB local được phép qua `uv run --frozen --env-file ../.env python -X utf8 -m scripts.seed_student_affairs`:
  lần đầu tạo workspace + ba membership + kho; lần hai `created=[]`, không trùng.
- API qua HTTP ASGI stack với DB local thật: cả ba tài khoản đăng nhập/me/đọc kho đạt;
  chỉ thấy workspace CTSV, truy cập workspace khác 404, quản trị provider 403;
  admin phòng đọc audit 200, editor/member đọc audit 403; xác nhận đúng ba thành viên.
  Đây là ASGI trong tiến trình kiểm tra, không chứng minh trình duyệt hoặc dịch vụ HTTP đang chạy.
- Git ignore hai tệp credential local: PASS. UTF-8 không BOM/LF của các tệp thay đổi: PASS.
- Full suite đã khởi chạy qua harness DB cô lập, bị ngắt theo phiên ở hơn28%; không có exit code cuối, KHÔNG PASS. Có1FAIL quan sát tại `tests/integration/test_knowledge_regressions_639.py::test_failed_concurrent_writer_cannot_damage_committed_original`; chạy lại riêng qua harness đạt1PASS/exit0, DB `qnu_v1_test_4e8a8671c6ce46f7` đã dọn. Không kết luận lỗi nền khi chưa có traceback full. DB của lượt bị ngắt `qnu_v1_test_3fbba1c37183415f` đã được dọn sau kiểm sentinel; application DB giữ nguyên.

## Giới hạn và vận hành

Không sửa frontend, cấu hình môi trường hay SSO; không migrate, cấp provider/model,
gọi AI, upload corpus, reindex, publish, restart dịch vụ hoặc Git commit/push.
Không tạo dữ liệu tài liệu giả. Kho mới trống; thử AI cần cấp model và tài liệu hợp lệ riêng.
Cổng API8002/FE3001 không phản hồi lúc kiểm tra; chưa kiểm browser. Người dùng chạy
ứng dụng theo runner V1 hiện có rồi đăng xuất và chọn Dev Access Key để đổi danh tính.
