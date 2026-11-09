# Nhật ký phiên 905 — Seed đơn vị Trung tâm Số & Học liệu và kiểm chứng vai trò

- Ngày: 2026-11-08.
- Nhánh: `feat/v1-user-workflow`, baseline `09a173a2`.
- Kế hoạch nguồn: [15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md), gói P7; runbook [46 — Pilot QNU V1](../quy_trinh/46_pilot_qnu_v1_va_dong_pham_vi.md).
- Trạng thái: workspace dev `shl` đã có 4 thành viên dev theo vai trò; quyền được kiểm qua HTTP in-process, HTTP thật sau restart (21/21) và trình duyệt (32/32); **full backend suite đang chạy**, **phiên pilot với người thật NOT RUN**.

## 1. Yêu cầu

Người dùng yêu cầu seed đơn vị **“Trung tâm Số & Học liệu”** và thêm người để kiểm thử vai trò ngay trên môi trường dev. Phiên này tiếp tục thứ tự đã chốt: hoàn tất full backend suite trên DB cô lập, ma trận trình duyệt P1–P6 (đã xong trong phiên này), rồi chuẩn bị điều kiện pilot.

Không tạo dữ liệu nghiệp vụ giả, không dùng tài khoản dev thay cho người tham gia pilot, không gọi model thật, không deploy/reindex/push.

## 2. Việc đã làm

### 2.1. Seed idempotent workspace và membership

- `backendV1/qnu/domains/identity/dev_accounts.py`: thêm `SHL_PILOT_PROFILES` gồm bốn actor dev (`act_dev_shl_admin`, `act_dev_shl_editor`, `act_dev_shl_reviewer`, `act_dev_shl_reader`); `resolve_seed_actor` tra cứu trên hợp của `SEED_PROFILES` và `SHL_PILOT_PROFILES`. Vai trò trong hồ sơ chỉ là nhãn; quyền thực tế vẫn do membership trong DB quyết định.
- `backendV1/scripts/seed_shl_pilot.py` (mới): kiểm dev-gate và DB loopback; dùng `workspace_service.create_workspace`/`add_member` để tạo dữ liệu có audit; advisory lock chống chạy song song; tạo khóa dev ngẫu nhiên một lần vào `backendV1/.local/shl-pilot-accounts.json` (đã Git ignore) và ghi SHA-256 vào `.local/dev-accounts.json`; chạy lại chỉ kiểm trạng thái, không tạo thêm, không đổi vai trò/trạng thái, không reset khóa.
- `backendV1/scripts/seed_student_affairs.py`: kiểm registry chỉ trong phạm vi khóa CTSV để registry có thêm người vẫn chạy được.

Lệnh đã chạy từ `backendV1` (không in khóa):

```bash
uv run --frozen --env-file ../.env python -X utf8 -m scripts.seed_shl_pilot
```

Kết quả: workspace `ws_31a7278f42e7`, code `shl`, tên “Trung Tâm Số & Học Liệu”; bốn membership `active` với vai trò `admin`, `editor`, `reviewer`, `member`. Chạy lại in `created: []`. Ruff và `ruff format --check` trên ba tệp đã sửa đều đạt.

### 2.2. Kiểm chứng quyền qua HTTP in-process

Dùng `TestClient` trên DB dev (chỉ đọc, không tạo thành viên), đăng nhập từng khóa seed và gọi các endpoint thật:

| Trường hợp | Kỳ vọng | Kết quả |
|---|---|---|
| Đăng nhập 4 tài khoản | 200, `/auth/me` đúng `actor_id`, không có permission nền tảng | 4/4 đạt |
| `GET /workspaces` và `GET /workspaces/{id}` | 200, thấy workspace `shl` | 4/4 đạt |
| `GET /workspaces/{id}/members` | 200, đủ 4 vai trò | 4/4 đạt |
| `PATCH /workspaces/{id}/members/wm_missing` | editor/reviewer/member 403; admin 404 | 4/4 đạt |
| Platform admin | thấy 4 thành viên, PATCH thành viên không tồn tại 404 | đạt |

Tổng 27/28 kiểm tra đạt. Kiểm tra còn lại do kỳ vọng của người viết sai: platform admin mang vai trò `AI.Admin` với danh sách `permissions` rỗng, còn `has_permission` cấp mọi quyền `ai.*` cho vai trò này; các bằng chứng HTTP (đọc đủ 4 thành viên, PATCH trả 404 thay vì 403) xác nhận quyền admin hoạt động, không phải lỗi sản phẩm.

### 2.3. Khởi động lại API dev và kiểm trình duyệt

Sau khi người dùng yêu cầu, API dev `127.0.0.1:8002` được dừng và khởi động lại bằng đúng lệnh cũ từ thư mục gốc repo: `uv run --project ./backendV1 --frozen --extra dev uvicorn qnu.main:app --host 127.0.0.1 --port 8002`; log ghi tại `backendV1/storage/context636/dev-api.out.log` và `.err.log` (đã Git ignore). `/health` trả 200, database và Redis `connected`.

Kiểm HTTP thật trên tiến trình mới: **21/21 đạt** — 4/4 khóa seed đăng nhập 200, `/auth/me` đúng `actor_id`, workspace hiển thị 200, danh sách thành viên 200, biên quyền PATCH trả 403 cho editor/reviewer/member và 404 cho admin, platform admin đăng nhập 200.

Kiểm trình duyệt 1280px bằng Playwright với dev-key form (auto-login bị vô hiệu trong phiên kiểm): **32/32 đạt** — 4/4 vai trò đăng nhập được; trang Thành viên hiển thị đủ 4 dòng cho mọi vai trò; admin có nút “Thêm thành viên” bật và 4 ô chọn vai trò, các vai trò khác chỉ đọc; điều hướng theo vai trò đúng (admin/editor thấy Cần xử lý + Chuẩn bị nội dung + Xuất bản; reviewer không thấy Chuẩn bị nội dung; reader chỉ thấy nhóm tra cứu); 0 lỗi console.

### 2.4. Ma trận trình duyệt và full suite

Ma trận P1–P6 đã hoàn tất trong phiên này: 11 route × 390/768/1280 × sáng/tối = 66 lượt, 0 lỗi console; ba lỗi UI/deep-link được sửa và commit `f3f47284`; link cũ `?tab=`, `?sourceAction=ocr`, `?stage=publication` giữ đúng stage.

Full backend suite chạy trên DB cô lập `qnu_v1_test_c095edcd1391408d`. Một lượt chạy trùng lặp trước đó (mở cùng lúc, dùng chung Redis) đã được dừng để tránh nhiễu; DB sót `qnu_v1_test_16585e2e95f24896` đã được dọn sau khi ngắt backend. Lượt này kết thúc **FAIL: 16 failed, 1521 passed, 3 skipped** trong 3477,21s; receipt `pytest_exit: 1`, `db_dropped: true`, `legacy_sentinel_preserved: true`, 3489,31s. Không dùng kết quả này làm gate vì lượt chạy chồng với seed/restart và harness chưa cô lập Redis (mục 2.5).

### 2.5. Phân loại 16 FAIL và sửa nền trước lượt chạy sạch

| Nhóm | Test ID | Nguyên nhân | Xử lý |
|---|---|---|---|
| Schema head lệch | `test_recovery_666` (4 ca), `test_readiness_666::test_readiness_is_independent...`, `test_workspace_model_schema::test_migrations_match_models...`, `test_knowledge_regressions_639::test_downgrade_cannot...` | `qnu/platform/schema.py` vẫn ghi `0016_review_submission` trong khi migration head là `0017_answer_review` | Nâng `SCHEMA_HEAD` lên `0017_answer_review` |
| Test baseline lỗi thời | `test_migration_baseline_661` (2 ca) | Test đếm 16 revision/tệp và chuỗi dừng ở 0016 | Cập nhật 17 revision và chuỗi `0017 → 0016 → 0015` |
| Chunker lỗi thời | `test_table_grounding_770::test_ingestion_quality...` | Test còn kỳ vọng `qnu.published-chunks/v4`, mã đã là `v5` | Cập nhật kỳ vọng `v5` |
| Window-zero lỗi thời | `test_rag_modelops_budgets_767::test_window_zero...` | Từ `ef8a7c6f`, window 0 chỉ dừng sớm khi không có hit paragraph; test dùng hit paragraph nhưng truyền DB/actor `None` | Dùng hit bảng cho nhánh không DB; nhánh paragraph được kiểm ở integration |
| Harness thiếu Redis cô lập | `test_chat_shared_admission_751`, `test_integration_gateway_pipeline` (2 ca), `test_readiness_666::test_worker_heartbeat...` | Harness không đặt `TEST_REDIS_URL`/namespace test, nên test bảo vệ dừng trước khi chạy | Harness dùng Redis logical DB 15 (cho phép override `TEST_REDIS_URL`) và `CACHE_NAMESPACE=qnu:test:<db>:` |
| Nhiễu do chạy chồng seed | `test_identity_boundary::test_login_and_authenticated_identity` | Suite bắt đầu 17:46, registry SHL được ghi 17:56 trong khi tiến trình pytest đã nạp danh sách profile CTSV cũ; registry có khóa lạ nên trả 503 thay vì 401 | Chạy lại riêng đạt; không chạy seed song song với suite |

Sau khi Redis thật sự chạy, một deadlock Windows Proactor xuất hiện ở teardown `TestClient`: client Redis async toàn cục chưa bao giờ được đóng (`close_redis` không có nơi gọi). Đã nối `close_redis()` vào shutdown của lifespan và cho phép bỏ qua an toàn khi client thuộc event loop khác (test dùng nhiều `TestClient`). Kết quả kiểm lại nhóm 21 ca từng FAIL: **21/21 PASS** trong 99,42s, không treo; các tệp Redis còn lại **35/35 PASS**; Ruff/format 7 tệp đã sửa đạt.

Lượt full suite sạch trên DB `qnu_v1_test_9caa1233fba44b4c` đã hoàn tất ngày 2026-11-08: **PASS — 1540 passed, 0 failed, 0 skipped** (5 warning) trong 3460,19s; receipt `pytest_exit: 0`, `seconds: 3478,95`, `db_dropped: true`, `legacy_sentinel_preserved: true`. Log: `backendV1/storage/context636/qnu_v1_test_9caa1233fba44b4c/pytest.log`, `result.xml`, `receipt.json`. Không có FAIL nền nào còn lại; đây là gate xanh của KH15.


## 3. Phát hiện và chặn

- API dev trước restart giữ module `dev_accounts` cũ nên đăng nhập bằng khóa seed trả 503 `dev_accounts_unavailable`; đã xử lý bằng restart có sự đồng ý của người dùng và kiểm lại đạt (mục 2.3).
- Hai full suite chạy song song dùng chung Redis có thể gây nhiễu kết quả; chỉ giữ một lượt chạy.

## 4. NOT RUN

- P7.1 chọn người tham gia thật, P7.2 T1–T6, P7.3 ma trận 12 tình huống lỗi, kiểm thử trả lời có nhãn người.
- Gọi model thật trong benchmark KH16, deploy production, reindex, push.

## 5. Bước sau

- Full suite sạch đã đạt (mục 2.5); chuyển sang triển khai KH16 G1–G6 trong phạm vi được cấp.
- Đăng nhập UI bằng khóa trong `backendV1/.local/shl-pilot-accounts.json` khi cần kiểm vai trò; không dán khóa vào tài liệu hay log.
- Pilot thật vẫn cần điều phối viên/thư ký, trợ lý, kho tài liệu đã xuất bản và ModelOps provider/model được phép.
