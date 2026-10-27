# Phiên651 — Rà soát và sửa văn bản hậu OCR

Người dùng muốn thấy đoạn văn có lỗi, sửa theo gợi ý hoặc tự sửa, rồi lưu cập nhật
MD/JSON. Đã triển khai backendV1: units có text/text gốc/trang/ô, model suggestions
qua ModelOps, save version/hash/idempotency và hai artifact kiểm hash trước commit.
OCR gốc giữ nguyên. Người dùng đã chọn chỉ backendV1 trước; giao diện làm sau.

Migration0011 thêm `ocr_text_versions`, `ocr_spelling_runs`; đăng ký route/ownership/
fixture. Không thay auth/ModelOps/config hoặc quy tắc workspace của backend cũ.
Không chuyển Compiler/publication/index ngầm sang bản sửa mới nhất.

Baseline API1FAIL404 → smoke2PASS → focused18PASS → concurrent4PASS.
Review thêm phát hiện commit quota mở race cùng key: baseline1FAIL → sửa thứ tự
persist request trước reserve → 1PASS/1model/1reservation. Full đầu dừng, không
PASS. Lượt tuần tự sau có434PASS/1FAIL do thông báo downgrade, rồi kẹt khi đóng
Windows TestClient sau100%; dừng đúng pytest child, không PASS. Sửa thông báo,
regression1PASS; full cuối qua sáu nhóm đủ435PASS/0FAIL/0SKIP/exit0,22ca mới/0mất.
Ba nhóm integration + unit/migration chạy293,28s; tổng thời gian case849,62s.
Ruff/format14file PASS;475legacy hash giữ theo649. Chưa sửa gốc lỗi shutdown.

OpenAPI70path/95operation,65path cũ giữ. UTF-8 không BOM/LF và local links PASS.
16DBtest kiểm lại0còn,0vector v1 quan sát; sentinel/version legacy giữ. Artifact
và lệnh thật ở `backendV1/storage/context651/`, không đưa secret hoặc dữ liệu thật
vào docs. Full dùng4nhóm đầu, thêm contract/invariant; union435case không trùng.

Kiểm tra dùng dữ liệu tổng hợp và model/OCR loopback; chưa quality/live, UI/browser,
Compiler binding, migrate DB phục vụ, restart, publish/index hoặc Git. Blob ghi
dở có thể mồ côi; không tự GC. Gợi ý rỗng không chứng minh không có lỗi chính tả.

[Báo cáo651](../bao_cao/context651/REVIEW.md) ·
[API/UX](../../backendV1/docs/ocr-text-review.md) ·
[Quy trình27](../quy_trinh/27_ra_soat_van_ban_hau_ocr_backendv1.md).
