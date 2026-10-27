# Context632 — Hạ tầng local mới đã sẵn sàng

## Kết quả

Cả 5 container running/healthy, đủ 4 named volume mới theo xác nhận của người dùng. Khởi động bằng cấu hình docker-compose.infra.yml hiện tại.

| Dịch vụ | Cổng local | Kiểm chứng |
|---|---|---|
| PostgreSQL 16 | 5432 | SELECT 1 trả 1 |
| Redis 7 | 6379 | PONG |
| Qdrant | 6333/6334 | /readyz HTTP200 |
| MinIO PGSTY 2026-06-18 | 9000/9001 | live/ready/console200 và S3 ListBuckets có xác thực200 |
| Gotenberg 8 | 3005 | /health HTTP200 |

## Thay đổi

- Chỉ đổi image MinIO trong docker-compose.infra.yml sang pgsty/minio:RELEASE.2026-06-18T00-00-00Z theo user chỉ định. Không đổi credential, command, port, volume hoặc docker-compose.yml.
- Digest image tải thực tế: sha256:dacff8306a6e0a734518533992dbdcca26bc1ca47f77cf47cb9945725f92b29b. Binary xác nhận release/commit đúng.
- Giữ nguyên 4 container đã chạy; chỉ up minio với --no-deps.

## Bằng chứng và giới hạn

- [Kiểm tra cuối](infra-startup-final.json): tất cả 8 probe PASS, exit0. Compose validator và up/wait exit0. Không ghi mật khẩu vào report.
- [Kiểm tra tag gốc](minio-tag-check.json) giữ lịch sử fail404/401. Lệnh mirror GHCR từng bị auto-review chặn không được thực thi; người dùng sau đó cho phép một image PGSTY cụ thể khác. Không tự build hoặc retag giả image gốc.
- Đây là dữ liệu mới, S3 chưa có bucket. Backend/frontend/worker/migration/seed NOT RUN; chưa kiểm chứng toàn ứng dụng, không claim phục hồi dữ liệu cũ.
- Backend tests và FE build NOT RUN vì không đổi logic ứng dụng; thay image được kiểm tra bằng Compose và kết nối thật.
- [Nguồn phát hành PGSTY](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-06-18T00-00-00Z).
