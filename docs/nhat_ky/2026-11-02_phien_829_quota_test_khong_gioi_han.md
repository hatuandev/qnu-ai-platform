# Phiên 829 — Quota test không giới hạn

Người dùng yêu cầu cấu hình không giới hạn token sau lỗi `quota_not_configured` trên kho Tuyển sinh. Áp dụng skill ModelOps; đọc quota router/service/model và cấu hình thực tế trước khi ghi.

## Thay đổi được phép

- App local development; workspace Trung Tâm Số & Học Liệu chứa collection Tuyển sinh. Tháng UTC hiện tại 2026-11-01 trước ghi `configured=false`.
- Đăng nhập bằng cơ chế development hiện có, actor thật; PUT quota qua handler có quyền ModelOps + workspace, commit và audit `quota.updated` của service hiện hành.
- Payload `monthly_token_limit=null`, `is_blocked=false`: không giới hạn, không dùng số cực lớn hoặc xóa kiểm tra quota.
- GET đọc lại HTTP 200 xác nhận `configured=true`, limit null, không khóa. `tokens_used` và `tokens_reserved` giữ nguyên; không reset usage, không gọi inference hay tự chạy lại OCR.
- Chỉ workspace này/tháng hiện tại. Không đổi hai workspace còn lại, quota E2E profile, code ứng dụng, provider/capacity, worker hoặc dịch vụ đang chạy.

## Kiểm chứng và giới hạn

Root command `backendV1/.venv/Scripts/python.exe tmp/quota829/manage.py --apply`: exit0. PUT200/GET200, counter-preservation assertions đạt. Preview và receipt trong `tmp/quota829/`, không chứa credential.

Backend sẵn hỗ trợ null là unlimited; đây là thay đổi cấu hình DB bằng API, không đổi code. Full BE/FE NOT RUN. Không reset job cũ, inference/retry/reindex/restart/push/deploy.

Quota hiện tại được lưu từng tháng UTC; chưa có chính sách tự gia hạn. Đã thông báo rõ cấu hình này không tự áp dụng tháng sau. Không tuyên bố không giới hạn context/output của model hay quota upstream. Phiên hiện tại có thể chạy lại bước bóc tách từ UI.
