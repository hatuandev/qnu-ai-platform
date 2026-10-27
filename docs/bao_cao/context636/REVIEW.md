# Context636 — Workspace và ModelOps trong backendV1

Yêu cầu: bắt đầu triển khai workspace và ModelOps theo ERD đơn vị, kho tri thức và chatbot. Phạm vi là backendV1; giữ backend cũ và các thay đổi chưa commit. Không triển khai frontend hoặc Repository. Đã hoàn thiện bản đầu có sẵn thay vì ghi đè scaffold.

## Kết quả

- Workspace CRUD có trạng thái, membership role/status, thu hồi/khôi phục và audit. Mỗi tài nguyên đi qua workspace resolver; danh sách chỉ trả workspace được phép. Opaque SSO subject giữ hoa/thường. Workspace admin không thành platform admin. Row lock chặn hai admin đồng thời tự bỏ admin cuối; platform có quyền phục hồi quản trị.
- ModelOps control plane: đăng ký/sửa/tắt provider; capability; default hệ thống cập nhật từng phần và model phải khớp provider. Key lưu mã hóa, đọc dạng che, rotate/revoke/audit; revoke lặp không tạo tác dụng phụ mới. Audit cấu hình chỉ lưu ID và tên trường thay đổi.
- Platform cấp grant; admin đơn vị chỉ chọn defaults theo capability trong grant. Catalog và public resolver bắt buộc workspace cho người dùng đơn vị, không hợp quyền nhiều đơn vị. Provider inactive, sai capability, workspace suspended và membership revoked bị chặn. Catalog đơn vị không lộ endpoint/key.
- Quota/usage ledger nội bộ: tháng UTC, cấu hình tường minh, request hash, khóa đồng thời, settlement idempotent và unknown token/cost giữ NULL. Reservation unknown không tự được hoàn tiền. API không cho client tự ghi usage/counters. Runtime inference sẽ gọi các giao diện này khi được nối sau.
- Sửa lỗi dev auth: thiếu token không tự thành admin, dev token bị chặn khi gate tắt/production, thiếu roles không được bổ sung admin. SSO xác minh RS256/JWKS/issuer/audience/expiry, lỗi hạ tầng giữ503. Không live SSO QNU.
- Migration sở hữu 12 bảng riêng; version table v1, allowlist bảng và advisory lock. Bỏ alembic/__init__.py vì che khuất thư viện Alembic. Sửa index của hai migration scaffold chưa áp dụng để khớp ORM; thêm0004 cho policy/quota/usage/audit. Không tự nhận ownership của bảng trùng tên có trước ngoài lịch sử v1. Không stamp legacy.
- Có uv.lock và môi trường Python riêng; OpenAPI35 HTTP operations toàn ứng dụng v1 tại backendV1/docs/openapi-v1.json.

## Kiểm chứng thật

| Kiểm tra | Kết quả |
|---|---|
| Baseline unit/contract/invariants có sẵn | 21 PASS, exit0 |
| Tái hiện lỗi xác thực trước sửa | 4 FAIL / 1 PASS, exit1 |
| API regression đầu với PostgreSQL thật | 12 PASS, exit0 |
| Focused auth/API/migration sau sửa | 31 PASS, exit0 |
| Full v1 trước hai regression cuối | 58 PASS, exit0 |
| Full v1 cuối, đúng venv/lockfile v1 | **60 PASS / 0 FAIL / 0 SKIP**, 12,39 giây, exit0 |
| Ruff qnu/tests/scripts/alembic | PASS, exit0 |
| Migration thật + ORM diff | PASS; không còn schema diff |
| Legacy sentinel/version trong DB test | Giữ nguyên |
| Lockfile check + OpenAPI export | PASS, exit0 |
| Hash475 file backend/app so với đầu batch | Khớp toàn bộ |

Lệnh cuối, cwd backendV1: `.venv\Scripts\python.exe scripts/run_isolated_tests.py` (DATABASE_URL được truyền trong bộ nhớ từ cấu hình kết nối hạ tầng hiện có, không in/lưu credential). Harness tạo DB mới, chạy Alembic upgrade head rồi `pytest tests -v`, lưu XML/log và dọn đúng DB đó. Runtime60test cuối: backendV1/storage/context636/qnu_v1_test_94f3b3d63e9b4c2a. Receipt ghi db_dropped=true và legacy_sentinel_preserved=true, tổng16,88 giây gồm migration/cleanup. Có2 warning deprecation TestClient, không phải failure.

Các lỗi trung gian đã sửa: kết nối test dùng credential mặc định không đúng (chưa tạo DB), package migration che Alembic, fixture tái dùng async pool khác event loop,20 index/constraint diff từ scaffold. Các DB test đã tạo ở những lượt này đều có receipt dọn; PostgreSQL hiện không còn namespace qnu_v1_test_*. Full được chạy lại sau thay đổi cuối để kiểm thu hồi membership và subject phân biệt hoa/thường; không dùng kết quả lượt cũ thay gate cuối.

Docker Desktop ban đầu tắt; đã bật để kiểm thử PostgreSQL. Hạ tầng5container tự khởi động theo cấu hình hiện có. Không khởi động/restart API/worker v1, không sửa cấu hình provider/default/key của backend cũ. Kiểm tra chỉ đọc DB ứng dụng cuối batch: chưa có alembic_version_backendv1. Không apply migration v1 lên DB phục vụ.

## Giới hạn

Đây là phần quản trị và hợp đồng metering, chưa phải runtime AI đầu-cuối. Discovery/probe, inference, OCR, embedding/rerank thật, streaming và key lease/cooldown/fallback chưa nối. SSO dùng RSA JWT và JWKS kiểm soát trong test, không chứng minh SSO QNU thật hoạt động. Chưa UI, upload, Knowledge, RAG, publish, vector hoặc Compiler. Không chạy suite legacy vì mã legacy giữ nguyên; không gộp60test v1 với kết quả legacy cũ.

Quota chỉ bảo vệ reservation do caller tin cậy tính; khi nối inference phải tính budget phù hợp model/protocol và quan sát usage/cost thật. Không tính unknown thành0. Audit/usage history không tự drop khi downgrade; rollback dữ liệu cần kế hoạch riêng. Legacy autogenerate cần review ownership khi vận hành chung DB.

[API và luồng dùng](../../../backendV1/docs/workspaces-modelops.md). [Kết quả JSON](result.json). Logs, DB receipt và source seal ở storage/context636 được Git ignore; không lưu corpus, credential hoặc prompt riêng trong báo cáo. Không commit/push.
