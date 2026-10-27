# Phiên 632 — Khởi tạo lại hạ tầng local

> Trạng thái cuối: **PASS 5/5 hạ tầng healthy**. MinIO dùng image PGSTY do người dùng chỉ định; S3 có xác thực và console HTTP200. Dữ liệu được khởi tạo mới theo xác nhận, tầng ứng dụng/migration/seed chưa chạy.

## Yêu cầu và phạm vi

- Người dùng kết thúc dọn ổ đĩa, yêu cầu chạy lại hạ tầng dự án trước.
- Docker ban đầu báo 0 image, 0 container và 0 volume. Đã dừng trước thao tác tạo dữ liệu mới; người dùng xác nhận: đã xóa dữ liệu cũ, yêu cầu khởi tạo hạ tầng mới.
- Phạm vi là 5 dịch vụ trong docker-compose.infra.yml. Backend, frontend, worker, migration, seed, compiler và inference chưa được khởi động/chạy trong phiên này.
- Mã ứng dụng và các chỉnh sửa đồng thời được giữ. Giai đoạn đầu chưa sửa compose; khi user chỉ định image PGSTY, đổi đúng 1 dòng image MinIO trong docker-compose.infra.yml. Không đổi credential, cổng, volume hoặc compose triển khai khác.

## Thực hiện và bằng chứng

Cwd các lệnh Docker Compose: D:/DuAnPhanMem/qnu-ai-platform.

| Lệnh/kiểm tra | Exit/kết quả | Trạng thái |
|---|---|---|
| docker compose -f docker-compose.infra.yml config --quiet | exit 0 | PASS |
| Kiểm tra 7 cổng trước startup | không có cổng bị chiếm | PASS |
| docker compose -f docker-compose.infra.yml up -d --wait --wait-timeout 180 | exit 1: image MinIO bị Docker Hub từ chối | FAIL |
| docker compose -f docker-compose.infra.yml pull postgres qdrant redis gotenberg | exit 0 | PASS |
| docker pull quay.io/minio/minio@sha256:a1ea29fa28355559ef137d71fc570e508a214ec84ff8083e39bc5428980b015e | exit 1: HTTP 401 | FAIL |
| Tải mirror ghcr.io/l33tlamer/minio-backup theo digest cũ | auto-review từ chối trước thực thi | NOT RUN |
| docker compose -f docker-compose.infra.yml up -d --pull never --wait --wait-timeout 180 postgres redis qdrant gotenberg | exit 0; 4 container healthy | PASS |
| PostgreSQL SELECT 1 qua psql trong container | exit 0; trả 1 | PASS |
| Redis redis-cli ping | exit 0; PONG | PASS |
| Qdrant /readyz cổng 6333 | HTTP 200 | PASS |
| Gotenberg /health cổng 3005 | HTTP 200 | PASS |
| MinIO startup/health | chờ quyết định nguồn image | NOT RUN |
| Build/test ứng dụng | không thay mã; ngoài phạm vi startup infra | NOT RUN |

Bằng chứng không chứa credential: [infra-startup-evidence.json](../bao_cao/context632/infra-startup-evidence.json).

## Trạng thái trung gian trước khi người dùng chọn PGSTY

- PARTIAL: PostgreSQL, Redis, Qdrant và Gotenberg chạy healthy. Ba volume mới qnu_postgres_data, qnu_redis_data, qnu_qdrant_data được tạo theo xác nhận. MinIO và volume tương ứng chưa được tạo.
- Cổng: PostgreSQL 5432; Redis 6379; Qdrant 6333/6334; Gotenberg 3005.
- Theo tag hiện tại của compose, Qdrant là v1.20.0 và Gotenberg là 8.38.1. Chưa kiểm chứng tương thích toàn ứng dụng; không khẳng định nền tảng hoàn chỉnh đã sẵn sàng.
- Hai kho image chính thức MinIO không tải được. Kênh archive binary chính thức trả HTTP 410 khi kiểm tra. Không thay MinIO bằng bản latest hay fork.
- Auto-review chặn import mirror GHCR vì kho bên thứ ba chưa được xác minh đủ và phạm vi cho phép chưa bao gồm nguồn đó. Không thực thi lệnh bị chặn hoặc lách bằng công cụ khác. Đã hỏi người dùng: build từ mã nguồn chính thức, cho phép mirror đúng digest cũ, hoặc để MinIO chờ. Đang chờ lựa chọn.
- Đây là hạ tầng dữ liệu mới, không phục hồi dữ liệu cũ, không tự seed/migrate hoặc đưa LLM key vào .env.

## Tiếp tục

Hoàn tất MinIO theo lựa chọn người dùng, chạy healthcheck 5/5 và cập nhật trạng thái phiên. Chỉ khởi động tầng ứng dụng theo phạm vi người dùng giao tiếp theo. Các kết quả compiler/nghiệp vụ trong lịch sử không phải bằng chứng dữ liệu hiện vẫn tồn tại sau lần xóa chủ động của người dùng.

## Tiếp tục 25/10 — người dùng chỉ định lại đúng image gốc

- User yêu cầu minio/minio:RELEASE.2025-04-22T22-12-26Z. Đây chính là image đã có trong compose; không hiểu câu trả lời này thành cho phép mirror GHCR.
- Tải lại Docker Hub vẫn báo pull access denied. Kiểm tra trực tiếp: Docker Hub tag API HTTP404, token ẩn danh không có scope pull, manifest registry chính thức HTTP401. Không có registry mirror cấu hình; không sửa đăng nhập hay credential helper.
- Bốn dịch vụ khác vẫn running/healthy ở lần kiểm tra mới. MinIO chưa có container hoặc volume.
- Không thể suy từ HTTP404/401 rằng tag chắc chắn bị xóa với mọi tài khoản; chỉ xác nhận không truy cập được với quyền hiện tại.
- Đã hỏi riêng việc build đúng release từ mã nguồn chính thức; nếu được phép, bản build cục bộ phải được ghi rõ khác digest image phát hành. Chưa build, chưa đổi nguồn image hoặc phiên bản.
- [Bằng chứng kiểm tra tag](../bao_cao/context632/minio-tag-check.json).

## Hoàn tất — image PGSTY được người dùng chỉ định

- User yêu cầu thử chính xác `pgsty/minio:RELEASE.2026-06-18T00-00-00Z`. Đây là phép dùng nguồn và phiên bản cụ thể mới, không phải quyền dùng mirror GHCR đã bị chặn. Không tải mirror bị chặn và không tự build image.
- Áp dụng qnu-clean-code-architect; sửa duy nhất dòng image MinIO tại docker-compose.infra.yml. Diff cấu hình: 1 dòng thêm/1 dòng xóa. Không đổi docker-compose.yml hoặc .env.
- Pull PGSTY exit0, digest `sha256:dacff8306a6e0a734518533992dbdcca26bc1ca47f77cf47cb9945725f92b29b`; `minio --version` trả đúng release 2026-06-18, commit 3e61b1d3a55c67340214ed6dc4612a7e2abc877d, Go1.26.4.
- `docker compose -f docker-compose.infra.yml config --quiet`: exit0/PASS.
- `docker compose -f docker-compose.infra.yml up -d --no-deps --pull never --wait --wait-timeout 120 minio`: exit0/PASS, tạo qnu_minio_data mới và container qnu_minio. Bốn dịch vụ đang chạy được giữ nguyên.
- Kiểm tra cuối qua Python trong backend/.venv: exit0; 5/5 container healthy. PostgreSQL SELECT1, Redis PONG, Qdrant ready HTTP200, Gotenberg health HTTP200, MinIO live/ready/console đều HTTP200; boto3 ListBuckets có xác thực HTTP200/0bucket. Chỉ đọc trạng thái, không tạo test bucket/object.
- Có đủ 4 named volume mới. Hạ tầng sẵn sàng theo scope này; chưa backend/frontend/worker/migration/seed, chưa khôi phục dữ liệu hoặc cấu hình ModelOps cũ, chưa nghiệm thu ứng dụng xuyên tầng.
- `git diff --check`, UTF-8 không BOM/LF và local links: PASS. Full Pytest/FE build NOT RUN vì chỉ đổi image hạ tầng và docs; dùng Compose validator và runtime checks theo rủi ro.
- [Bằng chứng cuối](../bao_cao/context632/infra-startup-final.json), [báo cáo](../bao_cao/context632/REVIEW.md).
