# Context707 — Sửa v1-infra-up và kiểm tra storage

Ngày: 2026-10-29. Phạm vi: runner hạ tầng V1 và preflight; người dùng yêu cầu khắc phục toàn bộ phần thiếu liên quan `v1-infra-up`, giữ image MinIO đã chỉ định.

## Nguyên nhân và thay đổi

- Trước sửa, runner chỉ khởi động PostgreSQL/Redis/Qdrant. Cấu hình hiện dùng S3 local nhưng MinIO chưa chạy. Preflight cũ không kiểm tra storage nên không chặn API/worker/FE khi upload chắc chắn lỗi.
- `scripts/run_v1.py`: kiểm tra cấu hình storage, truyền đúng `.env` root/backend cho Compose, khởi động bốn dịch vụ có `--wait`, rồi chuẩn bị storage. Lỗi ở bước trước dừng các bước sau và giữ exit code. Các wrapper hiện có dùng chung runner, không cần nhân bản lệnh.
- `scripts/v1_storage.py`: chỉ tự tạo bucket ở endpoint MinIO loopback HTTP cổng9000. Tạo khi thiếu, không tạo khi403; không thay policy/tệp cũ. Probe object ngẫu nhiên ghi/đọc rồi xóa; nếu có VersionId thì xóa đúng phiên bản probe. Lỗi thao tác/dọn probe trả thất bại. Local filesystem giữ đường dẫn cấu hình và kiểm tra bằng tệp tạm. Endpoint khác chỉ kiểm tra đọc bucket, không tự ghi/khởi tạo bucket ở đó. Thông báo lỗi không in credential hay nội dung exception.
- `scripts/check_v1_runtime.py`: thêm storage vào preflight, S3 dùng HeadBucket; local kiểm tra đường dẫn/quyền filesystem mà không tạo tệp. Kết quả mô tả rõ đây là phép kiểm chỉ đọc, không khẳng định quyền ghi object.
- Compose đã ghim đúng `pgsty/minio:RELEASE.2026-06-18T00-00-00Z` từ trước; giữ nguyên và thêm kiểm tra chống đổi nhầm. Gotenberg không được backendV1 gọi; model AI quản lý qua ModelOps nên không thêm hai thành phần này vào stack V1.
- Cập nhật hướng dẫn38: hạ tầng, bucket, selected env, kiểm tra storage và xử lý lỗi upload.

## Kiểm chứng thực chạy

Tất cả lệnh chạy từ root repo, trừ container dùng để kiểm tra image.

| Kiểm tra | Kết quả |
| --- | --- |
| Regression trước sửa: `uv run --project backendV1 --frozen --extra dev --no-sync python -m unittest discover -s scripts/tests -v` | FAIL exit1: 26PASS,1FAIL,1ERROR; thiếu MinIO/setup trong plan và thiếu kết quả storage |
| Sau sửa, cùng lệnh trên | PASS exit0:44test, bao gồm read-only, thiếu bucket,403, mạng lỗi, dọn probe, version, remote không ghi, bảo toàn local, env selection và dừng chuỗi khi lỗi |
| Scoped Ruff check +format --check cho3script và scripts/tests | PASS exit0,6file |
| `docker compose -f docker-compose.infra.yml --env-file .env config --quiet` | PASS exit0; không in cấu hình chứa secret |
| Image tạm `docker run --rm --entrypoint /bin/sh pgsty/minio:RELEASE.2026-06-18T00-00-00Z -c 'command -v curl && command -v mc'` | PASS exit0; curl cho healthcheck có sẵn, container thử tự dọn |
| `make.ps1 v1-check` trước bật MinIO | FAIL exit1 đúng nguyên nhân storage, bốn mục khácOK |
| `make.ps1 v1-infra-up` lần đầu | PASS exit0; ba dịch vụ cũ giữ chạy, tạo volume/container MinIO, health đạt, bucket local và write/read/delete probe đạt |
| `make.ps1 v1-infra-up` chạy lặp | PASS exit0; không tạo lại bucket, bốn container healthy, probe đạt |
| `make.ps1 v1-check` sau setup | PASS exit0: Redis/PostgreSQL schema/Qdrant/storage/frontend đềuOK |
| `make.ps1 v1-infra-up --dry-run --env-dir backend` | PASS exit0; argv có selected backendV1/.env, đủ bốn dịch vụ và setup storage |
| `docker inspect qnu_minio --format '{{.Config.Image}} {{.State.Health.Status}}'` | PASS exit0; đúng image yêu cầu và healthy |
| Diff/link/UTF-8/LF các tệp task | PASS |

Một lượt gọi unittest theo tên module `scripts.tests...` ban đầu lỗi import do trùng namespace `scripts` của môi trường; đổi sang discovery đúng thư mục. Một lượt lint trong khi sửa báo B018 đã sửa; kết quả cuối như bảng trên.

## Trạng thái và giới hạn

MinIO/bucket local đang được giữ chạy để người dùng upload lại. Không sửa `.env`, không khởi động lại API/worker/FE, không migration/reset/reindex, không gọi model hoặc upload corpus thử vào ứng dụng, không Git push. Full backend/FE suite NOT RUN vì không sửa domain/API/FE; kiểm tra toàn bộ bộ test runner/storage44ca và kiểm tra hạ tầng thật trong phạm vi này. Không suy phép thử storage thành bảo đảm chất lượng OCR/RAG.

Các thay đổi ModelOps/Knowledge/FE của phiên khác đang diễn ra được giữ nguyên; chúng nằm ngoài phạm vi task này. Không dùng kết quả preflight để xác nhận các thay đổi đó đã đạt.
