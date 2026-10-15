# Phiên 486 — Migration glossary, khởi động dịch vụ và Git

Ngày: 2026-10-16. User cho phép push, restart và apply migration glossary.
Phạm vi: máy local và remote Gitea; không deploy server, không push GitHub,
không reset DB, không thay publication/vector/ModelOps hoặc bật glossary tự động.

## Vận hành đã thực hiện

- Alembic `current` và `heads` cùng là `20261015_glossary_terms` ngay trước thao tác.
  Đã chạy `python -X utf8 -m alembic upgrade 20261015_glossary_terms`, exit 0;
  đây là xác nhận idempotent, không tạo lại hay xóa bảng.
- DB local `qnu_ai_platform` có đủ `knowledge_glossary_terms`,
  `knowledge_glossary_audits`, `knowledge_glossary_settings`; cả ba 0 dòng,
  số cấu hình bật bằng 0. Không tự thêm thuật ngữ hoặc phê duyệt.
- Trước khởi động: 54 job completed, không có queued/running; không thấy BE/worker
  hay listener 8001/3000 trong inventory. Đã khởi động BE và ARQ worker ẩn bằng
  virtualenv của checkout hiện tại, không dừng tiến trình ứng dụng khác.
- BE `/health` và `/health/ready`: HTTP 200, PostgreSQL/Redis connected.
  Worker log xác nhận 12 hàm, kết nối Redis và cron hoàn tất; không gọi model.
- Log vận hành nằm trong `backend/storage/service_logs` và `worker_logs`,
  không đưa vào Git. Không khởi động frontend hoặc triển khai Dokploy trong phiên này.

## Git và kiểm chứng

- Gitea `main` trước push trùng local HEAD `fc3edfa`; không cần merge/force-push.
- Batch gồm các sửa mã/kiểm thử/tài liệu kỹ thuật đang chờ từ phiên 475–485.
  Loại trừ corpus `docs/tai_lieu`, runtime storage, ảnh/PDF/DOCX nguồn và
  các deletion artifact pytest không liên quan. Giữ các file đó trên máy.
- Kết quả test phiên 485 là lịch sử: backend 1666 pass/11 lỗi nền/17 skip,
  frontend build và 46 auth test pass; không chạy lại full suite cho thao tác vận hành.
- Commit/push chỉ được xác nhận bằng kết quả Git và đối chiếu remote sau thao tác;
  chưa coi việc tạo commit local là đã đồng bộ Gitea.
