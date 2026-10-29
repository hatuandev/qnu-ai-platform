# Context706 — Sửa kiểm tra API Key/kết nối

Ngày: 2026-10-29. Người dùng yêu cầu sửa ngay các lỗi705và tham khảo9router.

## Phạm vi và quyết định

Đọc context/Git/source và skill clean-code/backend/frontend/ModelOps. Tham khảo9router
commit1fe586b, kiểm connection theo ID và lưu kết quả. Tái dùng adapter/history QNU;
không chuyển code Node hay các trạng thái soft-success vào Python.

API nhận key_id, không fallback khi kiểm khóa riêng. Batch FE duyệt từng khóa active,
giữ kết quả riêng/tiếp tục sau lỗi. TLS/schema/status/timeout theo diagnostic adapter;
history có key_id/fingerprint, audit và kiểm lại sau network. Temporary key không ghi
xác nhận cho saved keys. Bỏ fake RoundRobin switch, giữ chính sách runtime hiện có.

## Kiểm chứng đã chạy

- Backend adapter/HTTP regression36PASS. Integration mới9PASS,19test cũ trong batch đạt.
- FE focused22PASS; full cuối422PASS sau khi chạy lại một timeout5giây ngoài phạm vi.
- Build+TypeScript/Ruff/Biome có phạm vi PASS.
- Backend full FAIL: 787 passed / 4 failed / 3 skipped; 2 lỗi thiếu TEST_REDIS_URL chạy riêng đạt, 2 assertion migration vẫn kỳ vọng 0005 thay vì 0006. DB test đã dọn, sentinel giữ nguyên.
- Lượt fixture đầu28ERROR do thiếu kb_folders trong TABLES; thêm bảng vào test harness.
  Lượt integration sau27PASS/1FAIL vì test dùng DELETE thay revoke; sửa setup đúng API,
  giữ assertion409;9test mới đạt. DB focused/lỗi đã dọn, legacy sentinel giữ.

## Live và thay đổi đồng thời

Hai khóa thật ban đầu được kiểm đúng ID qua ASGI: đạt406ms/186ms, history current.
Browser kiểm khóa2đạt483ms. Người dùng sau đó tự xóa/thay khóa và đã xác nhận trong
chat; giữ nguyên thao tác đó, không khôi phục hay tạo khóa thay thế. Browser batch sau
thay đổi báo lỗi không tìm thấy khóa, không dùng làm bằng chứng batch2khóa live đạt.
Đã thêm invalidate cả khi request lỗi để danh sách cập nhật sau thay đổi ở phiên khác.

Người dùng cho phép khởi động lại phiên V1 ngay. Kiểm preflight5mụcđạt; runner PID cũ
đã thay đổi nên từ chối dừng; lượt start bị cổng3001bận tự dọn; đọc lại và chỉ dừng đúng
phiênV1/children đã xác minh. Chạy lại v1-dev: API8002/worker/FE3001hoạt động,
health live/ready/FE200, OpenAPI có key_id. Không migration/env/grants/model/key writes
ngoài diagnostic history/audit đã được yêu cầu kiểm thử.

Thử helper nền bị auto-review chặn; dùng foreground do công cụ giám sát thay thế,
đã dọn helper38002/38001sau kiểm browser. Giữ phiên V1chính đang chạy.

## Bàn giao

[Báo cáo](../bao_cao/context706/CONNECTION_FIX_REPORT.md), artifact local
`storage/artifacts/connection-fix-706/`. Sửa đúng module connection/diagnostics,
FE detail/API/type và tests. Không sửa model-test-modal/knowledge/storage/startup đang
được phiên khác làm. Giữ lịch sử context707và các diff đồng thời.

Không benchmark/inference corpus nội bộ/reindex/publish/deploy/Git commit/push.
