# Phiên 687 — Đồng bộ đăng nhập local

Người dùng báo access key local không đúng sau khi bật tự đăng nhập.
Đối chiếu Settings thực tế: backendV1 đang đọc `.env` gốc, development/dev gate
đã bật và signing key hợp lệ; frontendV1/.env.local có auto-login=true nhưng
khóa khác backend. Không có biến môi trường tiến trình ghi đè hai khóa.

Chỉ cập nhật hai dòng QNU_DEV_AUTO_LOGIN/QNU_DEV_ACCESS_KEY trong tệp cấu hình
FE local đã Git ignore, giữ nguyên mọi dòng khác; dùng mật khẩu backend hiện
có làm nguồn để không xoay mật khẩu hay sửa backend.env. Không ghi secret,
hash secret, token hay nội dung tệp cấu hình vào log/docs/artifact. Không thay
mã ứng dụng, không thay ModelOps/provider credential hoặc SSO.

Kiểm chứng thực chạy từ gốc repo bằng Python backendV1/.venv:

- So sánh khóa trong bộ nhớ sau ghi: khớp, auto-login bật, không in giá trị.
- POST cầu nối loopback `/__qnu_dev/auto-login` với Origin cùng FE: HTTP200,
  token nhận trong bộ nhớ; GET backend `/platform/v1alpha1/auth/me`: HTTP200,
  username dev.admin và role AI.Admin đúng. Không lưu/công bố token.
- Dev server đã nạp cấu hình mà không cần dừng/restart backend hoặc tiến trình
  của người dùng. Không tự điều khiển trình duyệt hoặc khẳng định phiên tab
  người dùng đã cập nhật; cần tải lại và Thử lại nếu còn màn hình lỗi cũ.
- Tệp local được Git ignore. Link/UTF8/LF cho nhật ký/snapshot và chèn index
  có kiểm bytes lịch sử giữ nguyên. Test/build ứng dụng, DDL, inference,
  reindex, deploy hoặc commit/push: NOT RUN.

Không áp dụng thay đổi auth source hoặc bypass gate bảo vệ. Mật khẩu do người
dùng vừa nhập khác giá trị backend đang dùng; FE đã đồng bộ theo backend.

[Snapshot687](../memory/snapshots/2026-10-28_session_687.md).
