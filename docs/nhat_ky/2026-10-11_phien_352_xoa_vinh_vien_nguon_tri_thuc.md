# Phiên #352 — Xóa vĩnh viễn nguồn trong Kho tri thức

## Yêu cầu và ranh giới

Người dùng chốt Xóa vĩnh viễn dọn dữ liệu thuộc nguồn ở Kho tri thức, giữ tệp và phiên bản trong Kho tài liệu. Không reset DB, không xóa hai tài liệu người dùng đang thử, không đụng qnu-sso hay thay đổi thuật toán RAG/DAG. Chỉ bổ sung cleanup vector cần thiết cho purge.

Áp dụng backend/clean-code/frontend/admin-design: đề xuất quy trình ngừng truy xuất -> worker cleanup external -> DB commit trước khi code; tái sử dụng ConfirmDialog/Button, phản hồi theo job thật. Đọc skill RAG để đối chiếu bộ lọc namespace/scope, không tuning retrieval/model.

## Thiết kế / thay đổi

- `source_purge.py`: request khóa collection rồi binding; chặn OCR/import/index đang xử lý; dedup job queued/running, retry failed. Chuyển binding deleting + clear active index pointer + tăng epochs, tạo JobRecord và commit trước dispatch Redis. Redis offline giữ pending để cron dispatch lại.
- Endpoint DELETE `/knowledge/bindings/{id}/purge` trả202/JobResponse; GET progress dưới cùng nguồn dùng quyền ai.knowledge.delete và tenant/workspace job. API detach legacy giữ semantics gỡ riêng; nút Xóa FE chuyển sang purge.
- Worker `task_knowledge_source_purge` đăng ký ARQ + durable dispatch mapping; job chỉ completed sau cleanup/DB final commit. Lỗi rollback DB plan, ghi failed/purge_failed và error, có thể retry. Không cho cancel purge vì external deletion có thể đã thực hiện một phần.
- VectorIndexer.delete_source_points: namespace động từ mọi vector generation của kho + default legacy; filter source/collection/tenant/workspace, wait=True rồi count exact phải0; không drop namespace. Lỗi không che bằng warning/success.
- Storage.delete_confirmed: local unlink missing_ok, S3 delete_object lỗi propagate; khác delete boolean legacy để retry không nhầm object đã xóa là thất bại hoặc nuốt lỗi mạng.
- Worker xóa snapshot đúng prefix snapshots/{collection}/{binding}/, giữ snapshot còn nguồn khác tham chiếu, từ chối path ngoài phạm vi. Xóa chunks/facts/index revisions/chunk sets/source revisions/binding của nguồn sau external cleanup. Chặn tham chiếu source/chunkset/active pointers chéo bất thường để không cascade phá nguồn khác.
- Import items giữ audit trạng thái skipped/purged/SOURCE_PURGED nhưng bỏ các link source/index; batch counters tính lại. Job giữ audit đếm. Không giữ cache markdown/OCR/layout thuộc nguồn đã purge; không sửa Repository/file path documents/.
- Chặn nạp nguồn đang deleting ngay khi create batch dưới collection lock; process ingestion cũng chặn và không reuse deleting artifact. Source detail và list không cung cấp nguồn đang deleting. Index build đặt collection/binding locks + status guard trước build reservation để không tranh purge.
- FE API + DeleteSourceButton: xác nhận vĩnh viễn, poll job, pending/error/retry; chỉ toast thành công khi completed, invalidate danh sách/KPI. Jobs API thêm nhãn Xóa nguồn tri thức. Không tạo UI primitives mới.

## Kiểm chứng

- `test_knowledge_source_purge.py`: 6 tests với PostgreSQL transaction/savepoint tách fixture khỏi worker; phủ purge và replay, giữ Repository, chunks/facts nguồn khác, snapshot shared, cả2model namespaces, lỗi storage rồi retry, Qdrant failure không xóa snapshot/báo success, filter4scope/wait/count, khác tenant, chống nạp khi deleting, cấm cancel. External failure tests dùng mocks chủ đích để mô phỏng lỗi, không mock production adapter.
- Cập nhật fixtures tests_jobs để có job_type theo model; tests vector-generation thêm collection lock result; tests import mock scalar None cho guard mới. Không bỏ assertions hay ép fallback.
- 57 tests trọng tâm đạt. Ruff toàn backend đạt (cảnh báo các thư mục test cũ bị access denied). Full backend: **828 passed /13 failed /2 skipped**,24.79s. 13 lỗi nhóm cũ #347/#349 (RBAC6, reconciliation1, auth role1, live-seed consulting/tools5), không sửa ngoài phạm vi.
- Biome3files FE sửa đạt; typecheck và Vite build đạt (build3.98s). Lint toàn FE vẫn16errors/3infos ở tệp ngoài phạm vi và config schema mismatch; không auto-fix lan. Chưa browser-click E2E của nút Xóa.
- API dev OpenAPI có cả purge và progress routes.
- **Worker + Redis + DB + MinIO + Qdrant thật**: tạo fixture mới col_purge_e2e_7c45b264fe56, snapshot OCR/chunkset/chunk, namespace2D purge_e2e_7c45b264fe56 chứa1point nguồn xóa +1point khác. Job_d52ea7f94f7a dispatched rồi completed bởi ARQ thật. Kiểm chứng nguồn/revision/chunk/chunkset/snapshot biến mất, Repository row/bytes giữ nguyên, point khác còn đúng1. Sau test dọn chính xác collection/namespace/doc/object/job fixture mới tạo; không thể/không cần khôi phục các fixture này, không đụng user files. Không giả embedding fixture vector là inference thật.
- Worker được restart lúc rảnh để nhận task mới; không migration. Đối chiếu cuối bảo toàn2Repository documents user và các nguồn user (chưa chủ động purge).

## Giới hạn / vận hành

Đây là deletion workflow nhiều hệ thống, không phải distributed transaction: khi external cleanup dở, nguồn không phục vụ RAG, DB plan giữ để retry; một số snapshot/vector có thể đã mất. Không cho cancel như undo. Tệp gốc chỉ còn ở Repository, không phục hồi dữ liệu OCR vừa xóa bằng rollback.

Nạp lại sau purge sẽ parse mới nếu không còn source artifact hợp lệ ở nguồn khác. Nếu cùng file còn dùng ở kho khác, cache đó thuộc nguồn khác và được giữ theo ranh giới người dùng. Không xóa backup/log lịch sử hạ tầng. Chưa benchmark purge nhiều người dùng hay kiểm thử browser end-to-end.

Đồng bộ quy trình02, journal index, PROJECT_CONTEXT, memory snapshot và WORK_LOG. Không commit, không dọn thay đổi cũ của người dùng.
