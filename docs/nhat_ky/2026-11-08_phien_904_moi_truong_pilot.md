# Nhật ký phiên 904 — Chuẩn bị môi trường pilot P7

- Ngày: 2026-11-08.
- Nhánh: `feat/v1-user-workflow`, baseline `09a173a2`.
- Kế hoạch nguồn: [15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md), gói P7; runbook [46 — Pilot QNU V1](../quy_trinh/46_pilot_qnu_v1_va_dong_pham_vi.md).
- Trạng thái: môi trường dev đã backup, áp migration `0015`–`0017`, chạy được API/worker/giao diện và smoke qua trình duyệt; **phiên pilot với người thật NOT RUN** vì chưa có đơn vị/người tham gia và workspace pilot chưa có thành viên/trợ lý/tài liệu xuất bản.

## 1. Yêu cầu và giả định

Người dùng chọn **“Chạy pilot P7 trước”**: áp migration `0015`–`0017` trên môi trường được phép, chọn đơn vị và 3–5 người, chạy T1–T6 và ma trận lỗi theo runbook 46. Phiên này chuẩn bị phần kỹ thuật của môi trường trước; không thay người dùng thực hiện nghiệp vụ, không tuyên bố pilot đã đạt.

Giả định:

- DB phát triển là môi trường được phép cho bước chuẩn bị; vẫn phải backup trước migrate và không dùng kết quả dev thay cho staging/production.
- Ba migration `0015`–`0017` là additive: `upgrade()` chỉ `create_table`/index; `drop_table` chỉ nằm trong `downgrade()`. Đã đọc cả ba tệp trước khi áp.
- Không tạo dữ liệu nghiệp vụ giả, không tạo thành viên/trợ lý thay đơn vị, không gọi model thật.

## 2. Các bước đã thực hiện và kết quả

### 2.1. Backup trước migrate

```bash
docker exec qnu_postgres sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/qnu_pre_pilot.dump'
docker cp qnu_postgres:/tmp/qnu_pre_pilot.dump storage/backups/qnu_pre_pilot_20261108_170941.dump
docker exec qnu_postgres rm -f /tmp/qnu_pre_pilot.dump
cat storage/backups/qnu_pre_pilot_20261108_170941.dump | docker exec -i qnu_postgres pg_restore -l | wc -l
```

Kết quả: `storage/backups/qnu_pre_pilot_20261108_170941.dump`, 221.855 byte (217K), PostgreSQL custom dump v1.15-0, **382 mục** khi liệt kê qua stdin. Lần kiểm tra đầu dùng `pg_restore -l /tmp/...` trong `docker exec` bị Docker Desktop dịch đường dẫn container sang đường dẫn Windows nên trả 0 mục; đã kiểm lại bằng stdin như trên.

### 2.2. Áp migration trên DB phát triển

Từ `backendV1`:

```bash
export DATABASE_URL="$(grep -m1 '^DATABASE_URL=' ../.env | cut -d= -f2-)"
uv run alembic upgrade head
uv run alembic current
```

Kết quả: `0015_preparation_intent` → `0016_review_submission` → `0017_answer_review` chạy thành công; `alembic current` = `0017_answer_review (head)`. Không seed, không reset, không reindex.

### 2.3. Khởi động dịch vụ

| Thành phần | Lệnh | Kết quả |
| --- | --- | --- |
| API V1 | `uv run --project ./backendV1 --frozen --extra dev uvicorn qnu.main:app --host 127.0.0.1 --port 8002` | chạy tại `127.0.0.1:8002`; `/health` 200, `/docs` 200 |
| Worker V1 | `uv run --project ./backendV1 --frozen --extra dev arq qnu.workers.settings.WorkerSettings` | 24 function đăng ký; Redis 7.4.11; cron chạy |
| Giao diện V1 | `npm run dev` trong `frontendV1` | Vite sẵn sàng tại `127.0.0.1:3001`; trang chủ 200; cầu auto-login dev trỏ `127.0.0.1:8002` |

Kiểm lại lúc ghi nhật ký: API 200, web 200.

### 2.4. Smoke qua trình duyệt (chỉ đọc)

| Trang | Kết quả |
| --- | --- |
| `/workspaces` | Auto-login dev hoạt động; 1 workspace “Trung Tâm Số & Học Liệu” (`shl`, `ws_31a7278f42e7`); **0 thành viên** |
| `/shl/overview` | Tổng quan workspace tải được |
| `/workspaces/ws_31a7278f42e7/assistants` | Trạng thái trống trung thực “Chưa có trợ lý AI nào” |
| `/shl/knowledge` | 1 collection “Demo1” (`col_7987fde7015e`) với 2 tài liệu |
| Collection → tab “Tài liệu” | 2 nguồn DOCX, OCR 100% |
| Collection → tab “Xuất bản” (`stage=publication`) | Trạng thái trống trung thực “Chưa có tài liệu xuất bản nào”, CTA “Bắt đầu chuẩn bị nội dung” |
| Nguồn `src_d750fde2180f` | Tiêu đề, phiên bản v1, “Chuẩn bị nội dung”, menu thao tác, vùng “Dẫn xuất & phục vụ 0 dẫn xuất — Chưa có bản phục vụ”, trình xem OCR 74 khối |

Console trình duyệt: không có lỗi; chỉ có log debug của Vite/React DevTools và cảnh báo code-split có sẵn của `signin-oidc.tsx`. Không bấm nút có thể ghi dữ liệu (không tạo preparation intent, không tạo trợ lý, không gửi duyệt).

## 3. Phát hiện và khoảng trống

- Workspace pilot hiện có **0 thành viên**, **0 trợ lý**, **0 tài liệu đã xuất bản**. Không thể chạy T1–T6 hoặc ma trận lỗi §4 runbook 46 nếu chưa có đơn vị cử người và dữ liệu được phép.
- Cần cấu hình ModelOps provider/model được phép trước T5 (hỏi đáp) và kiểm thử trả lời.
- Chưa có người điều phối/người ghi biên bản/verifier cho phiên pilot.

## 4. NOT RUN

- P7.1 chọn đơn vị/người tham gia: **NOT RUN** — cần quyết định của đơn vị.
- P7.2 kịch bản T1–T6 và bảng đo thời gian: **NOT RUN**.
- P7.3 ma trận 12 tình huống lỗi/thiếu quyền/thiếu cấu hình/xung đột nguồn/sync chưa xong: **NOT RUN**.
- Kiểm thị giác desktop/mobile có so sánh ảnh cho P5/P6: **NOT RUN** — smoke chỉ xác nhận trang tải và trạng thái trống trung thực.
- Full backend suite: **NOT COMPLETED** — giữ lỗi nền Redis751 đã biết; gate pilot 43 ca đã đạt ở phiên 903.
- Deploy production, reindex, gọi model thật: **NOT RUN** và ngoài phạm vi phiên này.

## 5. Rủi ro và bước sau

- Cần đơn vị pilot, 3–5 người theo vai trò editor/reviewer/admin/người tra cứu, đồng ý ghi biên bản ẩn danh; sau đó tạo membership, trợ lý và corpus đã xuất bản trong workspace riêng.
- Chạy theo runbook 46 §3–§4 với người điều phối không hướng dẫn thay; ghi thời gian thao tác/thời gian chờ/số lần dev hỗ trợ.
- Backup `qnu_pre_pilot_20261108_170941.dump` giữ lại đến khi kết thúc pilot; không xóa hay ghi đè.
- Chưa commit/push. Không mở backlog E1–E6 khi chưa có yêu cầu mới.
