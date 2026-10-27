# Vòng đời ngược backendV1 — Kết quả kiểm chứng

Kết quả cuối hợp các nhóm không trùng và regression sau sửa: **563 PASS / 0 FAIL / 0 SKIP**,
23ca mới, không mất540ca trước. Full đầu có2lỗi review nguồn,1lỗi teardown TestClient
và2queue NOT RUN; lượt đó vẫn là FAIL. Chạy lại trọn nhóm lỗi và37ca boundary sau sửa,
bao gồm Redis/ARQ thật trên queue thử riêng. Không thay assertion để bỏ qua lỗi.

Ruff/format49file, UTF-8/LF, migration parity/legacy sentinel và OpenAPI96path/123operation
đạt;92path cũ giữ.475file backend legacy khớp byte snapshot trước batch.

Luồng đã kiểm: archive/delete/restore nguồn và kho; pause/resume/delete chatbot;
owned conversation; private trash; quyền/hash/expiry/idempotency/concurrent acceptance;
hủy index/Compiler/lượt hỏi trong khi gọi; auto-review cancel trước tạo con;
retrieval/history loại nguồn đã thu hồi; staged replacement thành công/thất bại;
rollback publication khi lỗi manifest và tái dùng embedding; cleanup retry và rebuild
sau restore. PostgreSQL/Qdrant/Redis thật cục bộ; AI HTTP tổng hợp, không đo chất lượng model.

Chỉ dọn DB/queue/vector thử được xác định bởi receipt hoặc DB thử; không tác động
môi trường phục vụ. Giữ file gốc/raw và artifact dẫn xuất; chưa purge vĩnh viễn,
batch nhiều document dùng nguồn chung, UI hay deploy/migrate/restart phục vụ.

[Receipt máy đọc](verification.json) ·
[Hợp đồng API](../../../backendV1/docs/resource-lifecycle.md) ·
[Nhật ký](../../nhat_ky/2026-10-27_phien_660_vong_doi_nguoc_backendv1.md).
