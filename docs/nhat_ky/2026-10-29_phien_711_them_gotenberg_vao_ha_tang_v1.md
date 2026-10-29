# Context711 — Bật Gotenberg trong hạ tầng Docker V1

Ngày 2026-10-29. Người dùng yêu cầu thêm Gotenberg vào Docker. Đối chiếu thực tế:
`docker-compose.infra.yml` đã có service nhưng `v1-infra-up` chỉ chọn bốn service
khác, nên container Gotenberg chưa chạy. Không tạo Compose/service trùng.

## Thay đổi và vận hành

- `scripts/run_v1.py`: thêm `gotenberg` vào danh sách `v1-infra-up` và mô tả help;
  giữ chọn env, validation trước Docker, `--wait` và chuẩn bị storage sau Docker.
- `scripts/tests/test_run_v1.py`: kiểm đúng năm service cho cả hai chế độ env.
- `docker-compose.infra.yml`: giữ image `gotenberg/gotenberg:8`, restart/healthcheck
  có sẵn; bind cổng host `127.0.0.1:3005` tới container3000, chỉ phục vụ local.
- Cập nhật [hướng dẫn38](../quy_trinh/38_huong_dan_chay_qnu_v1.md) về năm service,
  địa chỉ và lệnh bật riêng. V1 vẫn dùng PyMuPDF, chưa tự gọi LibreOffice/Chromium.

Đã thực thi từ gốc repo:

```text
docker compose -f docker-compose.infra.yml --env-file .env config --quiet
docker compose -f docker-compose.infra.yml --env-file .env up -d --no-deps --wait gotenberg
```

Cả hai exit0. Container `qnu_gotenberg` running/healthy, image local có version
label8.38.1; không pull/đổi image PostgreSQL/MinIO. Bốn container hiện hữu có ID
và StartedAt khớp trước/sau; không recreate/restart. Không sửa `.env`, model,
quota, backend/FE, schema, pipeline xử lý tài liệu hoặc production Compose.

## Kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `python -m unittest discover -s scripts/tests -p 'test_*v1*.py' -q` |44PASS/exit0, không gọi DB/model |
| `python -m unittest discover -s scripts/tests -p 'test_v1_storage.py' -q` |14PASS/exit0, là chạy lại subset, không cộng thành58ca |
| Ruff check/format hai file Python sửa |PASS/exit0 |
| Runner dry-run `v1-infra-up --env-dir root` |Đủ5service, validation/storage sequence giữ nguyên |
| Compose config và startup chọn riêng gotenberg |PASS/exit0, healthy |
| `GET http://127.0.0.1:3005/health` |200; Chromium và LibreOffice đềuup |
| DOCX tổng hợp → `/forms/libreoffice/convert` |200, PDF1trang/15559byte; đọc lại đúng tiếng Việt, năm và số0 |
| HTML tổng hợp → `/forms/chromium/convert/html` |200, PDF1trang/15853byte; nội dung đọc được |
| Diff/local links/UTF-8 khôngBOM/LF |PASS theo kiểm chứng cuối |
| Backend/full FE/live model/corpus phòng ban |NOT RUN: ngoài phạm vi hạ tầng này |

Artifact local: `storage/artifacts/gotenberg-711/`: smoke.py, input.docx, hai PDF,
smoke-result.json, container IDs/StartedAt trước/sau. Chỉ tài liệu thử tự tạo,
không dùng tệp người dùng hoặc nội dung phòng ban. Không đưa artifact vào Git.

## Bàn giao

Gotenberg sẵn sàng trên host `http://127.0.0.1:3005`; trong mạng Compose là
`http://gotenberg:3000`. Service chạy nền theo restart policy có sẵn. Không có
giao diện riêng; health và conversion là HTTP API. Tích hợp V1 để thay bộ render
DOCX cần task riêng, giữ raw/revision/hash và kiểm layout; việc bật container
không chứng minh pipeline ứng dụng đã dùng Gotenberg.

Nguồn chính thức đã đối chiếu: [cài Docker/Compose](https://gotenberg.dev/docs/getting-started/installation),
[LibreOffice conversion](https://gotenberg.dev/docs/convert-with-libreoffice/convert-to-pdf),
[health](https://gotenberg.dev/docs/system/get-health-check).
Không restart API/worker/FE, migrate/reindex/deploy/push. Các sửa FE đồng thời giữ nguyên.
