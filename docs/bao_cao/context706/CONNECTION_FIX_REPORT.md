# Context706 — Sửa kiểm tra API Key/kết nối

Ngày: 2026-10-29. Phạm vi: ModelOps V1, kiểm tra kết nối/khóa tại trang provider.
Đã sửa các nhóm lỗi Context705, kiểm chứng trọng tâm và live; backend tổng **FAIL: 787 passed / 4 failed / 3 skipped**.

## Hành vi sau sửa

| Vấn đề705 | Bản sửa |
|---|---|
| Chọn khóa2nhưng dùng khóa1 | API nhận key_id, kiểm thuộc connection/active, chỉ dùng khóa đó; không fallback |
| Kiểm lần lượt chỉ1request | FE duyệt khóa active lần lượt, giữ kết quả riêng, tiếp tục sau lỗi và tổng hợp đạt/lỗi/bỏ qua |
| HTTP lỗi/HTML200vẫn thành công | Tái dùng diagnostic adapter, HTTP lỗi/schema sai là failed, có code/status an toàn |
| TLS verification bị tắt | Loại bỏ nhánh HTTP riêng; adapter xác minh TLS mặc định, không redirect/env proxy |
| Timeout10giây cố định | Dùng timeout connection/deadline tổng; client310giây bao phủ cấu hình tối đa300giây |
| RoundRobin giả | Bỏ công tắc state local; ghi rõ xoay khóa theo policy ModelOps từng model; không đổi policy runtime |
| Badge active cố định | Text/màu theo status, inactive không được chọn để kiểm; bật khóa khác với kiểm tra đạt |
| Thiếu history | Diagnostic theo key_id/config fingerprint và audit; UI đọc lại lịch sử, invalidate cả khi request lỗi |
| Connection tắt vẫn gọi network | Chặn trước network; kiểm lại connection/key/config trước khi lưu kết quả |

Khóa nhập thử trước khi lưu vẫn kiểm được nhưng không gán kết quả cho các khóa đã lưu.
Không log secret hoặc raw provider body. Discovery có header Anthropic theo api_type/
family; không tuyên bố runtime Anthropic inference đã được triển khai. Discovery không
chứng minh chat/OCR/embedding/rerank của từng model đã chạy đạt.

## Tham khảo 9router

Ghim commit `1fe586bb1cf35e1ed0cb2150a8ef7d1db040b21d`:

- [Route theo ID](https://github.com/decolua/9router/blob/1fe586bb1cf35e1ed0cb2150a8ef7d1db040b21d/src/app/api/providers/%5Bid%5D/test/route.js).
- [testSingleConnection và lưu kết quả](https://github.com/decolua/9router/blob/1fe586bb1cf35e1ed0cb2150a8ef7d1db040b21d/src/app/api/providers/%5Bid%5D/test/testUtils.js#L973).
- [Kiểm model riêng](https://github.com/decolua/9router/blob/1fe586bb1cf35e1ed0cb2150a8ef7d1db040b21d/src/app/api/models/test/route.js).

Học cách kiểm đúng đối tượng và lưu kết quả; không sao chép provider đặc thù, soft-success
hoặc code Node sang Python. Giữ quyền/adapter/history QNU. Không chạy mã upstream.

## Kiểm chứng

- Baseline lịch sử705: FE4FAIL/BE8FAIL; các control cơ bản đạt.
- Sau sửa BE unit adapter+HTTP boundary: **36PASS/exit0**.
- DB integration mới: **9PASS/exit0**. Bao gồm key2chính xác, cross-connection404,
  revoked không fallback, temporary không xác nhận saved keys, lưu failed401/429/500,
  revoke giữa network không lưu success và non-admin403.
- Batch connection/diagnostics trước đó27PASS/1FAIL vì test mới dùng DELETE(xóa thật)
  thay cho POSTrevoke. Đã sửa setup sang revoke, giữ assertion409,9test mới đều đạt.
 19test cũ của batch đạt; không sửa assertion để che lỗi.
- FE trọng tâm: **22PASS/exit0**. Payload/timeout/invalidate, tiếp tục batch sau lỗi,
  bỏ inactive, đọc history riêng và bỏ control chưa hoạt động.
- FE full cuối `npm test -- --maxWorkers=2`: **422PASS/exit0**.
  Lượt trước415PASS/1FAIL timeout5giây tại
  `maintenance-evaluation-ui-679.test.tsx::evaluation caps the editable question list at twenty`;
  chạy riêng1PASS rồi full cuối422PASS, không tăng timeout hay sửa test đó.
- Vite build+TypeScript: **PASS/exit0**; còn cảnh báo bundle lớn.
- Ruff/Biome đúng phạm vi: **PASS**.
- Backend full `uv run --frozen --env-file ../.env --extra dev python scripts/test_database.py tests -q`:
  **FAIL/exit1: 787 passed / 4 failed / 3 skipped**, 2035.37 giây. Các lỗi:
  - `test_integration_gateway_pipeline.py::test_external_key_calls_real_rag_and_preserves_assistant_config`:
    thiếu `TEST_REDIS_URL`; chạy riêng với Redis test tách biệt: **1PASS**.
  - `test_readiness_666.py::test_worker_heartbeat_is_queue_scoped_and_removed_on_shutdown`:
    cùng lỗi biến môi trường; chạy riêng với Redis test tách biệt: **1PASS**.
  - `test_knowledge_regressions_639.py::test_downgrade_cannot_mark_success_and_block_next_upgrade`:
    assertion vẫn kỳ vọng `0005_provider_connections`, schema hiện tại là `0006_kb_folders`.
    Chạy riêng tái hiện cùng lỗi.
  - `tests/migrations/test_workspace_model_schema.py::test_migrations_match_models_and_exclude_legacy`:
    cùng kỳ vọng revision cũ; so sánh metadata và giữ legacy sentinel đã đi qua trước assertion này.
  Không sửa các assertion migration ngoài phạm vi để làm bộ tổng xanh. Hai lượt Redis chạy lại
  dùng DB15 loopback được kiểm trống và khác Redis ứng dụng, chỉ truyền biến môi trường cho
  tiến trình test, không sửa `.env`. DB full `qnu_v1_test_6ccfdf90058a47a8` và các DB chạy riêng
  đã được harness dọn; receipt `db_dropped=true`, `legacy_sentinel_preserved=true`.
  Full tổng vẫn là **FAIL**; kết quả chạy riêng không đổi trạng thái lượt full.

Lượt DB đầu28ERROR vì fixture chưa dọn `kb_folders` từ tính năng thư mục. Bổ sung đúng
một bảng vào TABLES, không CASCADE vào DB phục vụ. DB lỗi/focused đã dọn, legacy sentinel
giữ nguyên. Regression dùng database `qnu_v1_test_*` và upstream tổng hợp/loopback.

Artifact log/receipt local: `storage/artifacts/connection-fix-706/` và receipt harness
trong `backendV1/storage/context636/`. Không đưa credential vào báo cáo.

## Thử thật và thay đổi đồng thời của người dùng

API ASGI bản sửa với DB/provider thật đã kiểm đúng2ID và lưu history current:

| Khóa | HTTP | Kết quả | Latency |
|---|---|---|---|
| `key_5ce458a3bab8` |200| đạt discovery |406ms|
| `key_87c766cc3039` |200| đạt discovery |186ms|

Browser bản sửa kiểm riêng khóa2đạt483ms. Sau đó audit ghi key.deleted lúc03:46:49Z và
03:47:02Z; người dùng xác nhận đang tự thay đổi khóa. Lượt batch browser sau đó báo
0đạt/2lỗi không tìm thấy khóa. Không dùng lượt này làm bằng chứng batch live2khóa cùng
đạt, không khôi phục/thêm lại khóa người dùng. Batch được kiểm bằng fixture riêng.

Sau reload, trang3001hiện đúng0khóa và vô hiệu nút kiểm tra lần lượt. Ảnh xác minh:
`storage/artifacts/connection-fix-706/provider-page-after.png`.

## Nạp bản sửa local

Người dùng xác nhận **Khởi động lại phiên V1 ngay**. Preflight Redis/PostgreSQL/schema/
Qdrant/storage/FEđạt. PID runner cũ đã thay đổi nên kiểm an toàn từ chối dừng; lượt start
khi chưa dừng phiên mới gặp cổng3001bận và tự dọn lượt đó. Đọc lại process tree, chỉ
dừng đúng runner/children đã xác minh rồi chạy lại v1-dev.

API8002/worker/FE3001đang chạy. Health live200/ready200/FE200; OpenAPI có key_id mới.
Không migration/seed, không đổi.env/model/grants/quota hoặc secret.

Thao tác mở helper nền bị auto-review chặn, không có lý do chi tiết. Đã dùng phương án
foreground được công cụ giám sát ở38002/38001; kiểm xong dừng riêng helper, giữ V1chính.

## Tệp và ranh giới

Backend: connections schemas/router/service/testing; diagnostics schema/history/summary;
port/adapter; fixture TABLES và test705/706/adapter. Frontend: connection detail, API hook,
DiagnosticCheck type và test705/706. Không sửa model-test-modal hay các diff knowledge,
storage/startup đang được phiên khác thực hiện. Đồng bộ báo cáo/journal/index/snapshot.

Không benchmark chất lượng, inference tài liệu nội bộ, reindex/publish/deploy hoặc Git
commit/push. Kiểm tra kết nối không thay thế kiểm thử model đúng capability.
