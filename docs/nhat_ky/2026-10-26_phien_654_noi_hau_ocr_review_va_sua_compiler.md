# Phiên654 — Nối hậu OCR, review tự động và sửa Compiler

Ngày26/10/2026. Người dùng yêu cầu làm mục1→2→3, giữ phạm vi chỉ backendV1.
Đã đọc PROJECT_CONTEXT, Git/diff, mã thật và skill backend/clean-code/ingestion/
ModelOps/RAG. Không tạo subagent. Không sửa FE hoặc triển khai dữ liệu phục vụ.

## Phương pháp và thay đổi

1. `CompilationRequest.text_versions` chọn chính xác phiên bản đã lưu của từng OCR.
   Binding ghim text-version ID/hash và canonical/manifest gốc; loader dùng chung
   cho worker và publication. Citation phân biệt nguồn dẫn xuất. Index/review dùng
   snapshot cùng nguồn đó; version mới không làm bản cũ tự đổi căn cứ.
2. Completion tạo intent review trong cùng transaction; worker/cron ARQ v1 giao
   việc và khôi phục việc thiếu. Idempotency cố định, lease và review durable chống
   gọi model trùng. Lỗi review không đổi Compiler completed; không retry uncertain.
3. API edit-context, edit-previews và edits kiểm quyền/actor/hash/expiry/cạnh tranh,
   bảo vệ bảng/citation/nguồn. Lưu thành run con origin=user_edit, parent giữ nguyên,
   MD/JSON readback trước commit, audit/provenance và review mới; không recompile.

Files: compilation schemas/models/service/evidence/execution; workflow mới gồm
models/schemas/router/automatic/edits; review router; publication evidence;
OCR TextVersion composite scope; route/worker/ownership/fixture/migration0013.
Thêm5file test cùng helper, cập nhật test queue và schema. Tổng29file Python kiểm Ruff.
Docs workflow mới, các contract và quy trình27/28/29 cập nhật; hình653 gắn nhãn lịch sử.

## Kiểm chứng thật

[Báo cáo chi tiết](../bao_cao/context654/REVIEW.md) và
[kết quả có cấu trúc](../bao_cao/context654/validation.json).

Baseline3FAIL→first4PASS→workflow22PASS; queue1FAIL do cách tiêu thụ burst→1PASS;
E2E1PASS; extra18PASS; recovery2PASS. Full4nhóm đầu489PASS/1FAIL/0SKIP, đủ52file,
484,53giây wall. Lỗi thông báo downgrade của migration0013, đã sửa giữ guard;
target1PASS và chạy lại nhóm3 đầy đủ86PASS. Hợp cuối490PASS/0FAIL/0SKIP,
30ca mới/0ca mất so với652, tổng1161,47giây test. Không đổi/bỏ assertion để che lỗi.

Lệnh ở backendV1: `python storage/context654/run_checks.py ...`,
`python storage/context654/full.py`, `python storage/context654/recheck.py`,
`python storage/context654/lint.py`, `python storage/context654/finish.py`.
Wrapper/harness dùng DB riêng và HTTP tổng hợp; Redis/ARQ/Qdrant thật, không gọi
server model hoặc corpus thật. Ruff/format29file PASS; format từng1FAIL đã sửa.
OpenAPI79path/105operation,75path cũ giữ.14DB thử0còn,0Qdrantcollection v1 quan sát.
Tài liệu19tệp UTF8/noBOM/LF và82liên kết local PASS qua package.py; đọc lại tiếng Việt đúng.

Đối chiếu bảo toàn byte legacy **FAIL**: 413/475khớp;62khác hash, trong đó48chỉ
khác CRLF/LF và14chưa giải thích được byte. Cả62khớp Git index về nội dung khi
chuẩn hóa EOL; chưa đủ bằng chứng quy nguồn thay đổi. Không ghi/restore legacy.
Không dùng kiểm tra này để tuyên bố475file giữ nguyên byte.

## Giới hạn và bước sau

Chỉ nghiệm thu chức năng bằng fixture; chất lượng model/corpus, UI và full legacy
NOT RUN. Chưa migrate/restart/config ModelOps/reindex/pub dữ liệu phục vụ hoặc Git
commit/push. Khi được triển khai môi trường phục vụ cần migration0013 và worker
v1 có task review/reconcile; quyền/provider/quota cấu hình qua ModelOps hiện có.
Review không tự sửa/approve; blob ghi dở chưa có GC. Cần điều tra byte legacy riêng
nếu muốn chứng nhận bảo toàn tuyệt đối các tệp cũ.
