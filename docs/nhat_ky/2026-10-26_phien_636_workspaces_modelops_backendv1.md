# Phiên636 — Workspace và ModelOps backendV1

Người dùng yêu cầu triển khai workspace và ModelOps trước theo ERD mới. Áp dụng ngoại lệ workspace là biên giới quyền riêng backendV1; không đổi backend cũ. Đã kiểm tra scaffold và giữ các thay đổi đang có.

Hoàn thiện CRUD/membership/audit và resolver, bảo vệ token dev/SSO, provider/key/rotation/defaults, grant tập trung và default theo capability, catalog đúng workspace, quota/usage ledger nội bộ có khóa và idempotency. Thêm migration0004; sửa index scaffold trước khi có version table v1 trong DB ứng dụng. Bỏ package marker che thư viện Alembic; tạo lockfile/venv riêng. Repository tiếp tục bỏ; chưa inference/OCR/UI/upload/RAG.

Baseline21PASS; auth trước sửa4FAIL/1PASS. Regression PostgreSQL12PASS, focused31PASS. Full cuối60PASS/0FAIL/0SKIP/12,39s/exit0; Ruff, migration/ORM, OpenAPI và lockfile PASS. Full58PASS trước đó là lượt trung gian, trước hai test thu hồi membership/subject case. Các lỗi test/migration trung gian và lệnh thực tại [báo cáo636](../bao_cao/context636/REVIEW.md).

Docker được bật để dùng PostgreSQL test;5container hạ tầng tự khởi động theo policy có sẵn. DB tạm dọn hết; sentinel legacy giữ. Hash475 file backend/app khớp đầu batch; DB ứng dụng chưa có version table v1, không migrate dữ liệu phục vụ. Không restart API/worker, đổi provider/key/default legacy, index/publish/Compiler hoặc Git.

SSO mới kiểm chứng bằng RSA/JWKS có kiểm soát; chưa live QNU. ModelOps control plane và metering đã có, adapter inference/key lease/cooldown/fallback runtime chưa nối. Bước tiếp theo theo luồng: collection/upload trực tiếp và nối Jobs/OCR qua ModelOps sau khi được giao.
