# Phiên 424 — Sao lưu đợt 2

## Phạm vi và quyết định

Người dùng duyệt đợt 2: nhập file/khôi phục sandbox, nơi lưu ngoài, lịch, quản lý bản cũ và tiến độ. Người dùng chọn **kho bí mật bên ngoài** và **S3/MinIO**. Triển khai contract file secret mount được cấp bên ngoài, không tích hợp Vault/KMS API hoặc giữ mật khẩu lịch trong DB. Mật khẩu thủ công vẫn chỉ truyền stdin.

Không restore-to-live, không bật lịch/S3/retention thật, không chuyển hay khôi phục archive thật. Read-only metadata xác nhận bản thật `bkp_0748d2ca73254460bfe2ab4a4cb6599e` vẫn completed, 1.097.107.244 byte/verified_at14:37:25UTC; `.policy.json` thật chưa tồn tại, nên các chức năng tự động mặc định tắt. Không reset DB/Redis, không đổi AI/provider/knowledge/published pointers, không tự restart BE/worker.

## Kiến trúc và hành vi

- `policy.py`: Pydantic extra-forbid, non-secret JSON atomic control plane; default off. Endpoint không chứa credential/query/fragment, bucket khác nguồn. File secret absolute/regular/no symlink/outside capture roots, max16KiB; POSIX owner-only, Windows ACL do quản trị cấp. Không trả nội dung bí mật/log exception thô.
- `importing.py`: authenticated raw streaming upload, ID do server tạo, magic/size/disk gates; `.partial` chỉ rename khi receive hoàn tất; header/hash không phải integrity. Uploaded record unverified + pinned; chỉ verify/drill có mật khẩu mới giải mã. Upload heartbeat/throttle và drain blocking write khi cancellation.
- `remote.py`: only encrypted verified archive, multipart bounded memory, readback full SHA-256/size, version ID hoặc If-Match. Local integrity corruption fail-closed, không fake completed. Remote failure giữ local và field remote_error/status độc lập.
- `scheduler.py`: daily/weekly timezone-aware UTC offset, next occurrence future/no past backfill; ARQ tick10/40 giây, filesystem reservation serializes ticks. Preflight pending/running/retryable jobs/workflows hoãn không hủy/replay. Runner child độc lập, cron không bị bọc shared maintenance guard dẫn tới tự deadlock. Secret đọc bên ngoài tại dispatch, không persisted.
- `management.py`: exact-ID move archive/metadata vào `.trash/<id>` với actor/correlation audit; pinned/active/last-good gates. Retention hợp nhất các calendar buckets, giữ newest/latest drilled/pinned, không gỡ uncopied khi S3 bật và không dọn sau create/remote thất bại. **Soft removal chưa giải phóng disk**, không purge remote/local; điều này được ghi trên UI/runbook.
- `compatibility.py`: manifest/schema/PG major/vector metadata gates và production release match trước target creation; không tự migrate/seed/re-embed.
- `drill.py` + `relay.py`: target vào Docker internal network/no published ports, no live mounts; relay riêng secret-free/unprivileged/read-only/fixed IP+port/localhost publication. Separate target_ids và cleanup IDs, ownership-checked cleanup cả network. Không có default route ở target mẫu. Relay image bắt buộc pinned ID, thiếu thì fail-closed.
- `catalogue.py`: Windows atomic replace retry<=0,5s cho reader sharing denial, không nuốt lỗi quyền kéo dài; POSIX unchanged. Service kiểm tra active toàn catalogue, không chỉ100 bản mới nhất.
- UI: giữ primitives/admin/TanStack Form+Zod/Query/Table, page policy độc lập; Nhập file, pin/delete/copy, record-detail endpoint không phụ thuộc100 list; lỗi tại list/detail, stage elapsed/byte thực, phân biệt remote/local, split encryption và verification. Không giả ETA.

## Tệp thay đổi

- Backend backup module: models/router/service/catalogue/runner/drill và mới policy/management/importing/remote/scheduler/compatibility/relay.
- `backend/app/core/config.py`: import limit + external secret paths + relay image.
- `backend/app/workers/arq_worker.py`, `backend/tests/test_workers.py`: cron contract.
- `backend/tests/test_backup_phase2.py`, `backend/tests/test_backups_integration.py`, `backend/tests/docker/backup_launcher.Dockerfile`, `backend/tests/docker/backup_relay.Dockerfile`.
- `docker-compose.yml`: chuyển tiếp path/limit/relay ID; không tự mount secrets/Docker socket.
- Frontend backups feature files, new `settings.backups.policy.tsx`; route tree do plugin sinh, không sửa tay. Không đụng UI primitives.
- Runbook [đợt 2](../trien_khai/05_sao_luu_dot_2.md), liên kết runbook đợt1 và 3 tài liệu memory/log.

## Kiểm thử và các lỗi phát hiện

Regression mới ban đầu thiếu module -> collection fail đúng chức năng chưa có. Windows open-reader test tái hiện PermissionError trước retry; sau sửa đạt. Một batch lúc đang triển khai runner có syntax lỗi, sau sửa mới nghiệm thu; không coi lần đó là pass.

Thử internal network trực tiếp ban đầu không có port binding (Docker internal không publish); không fallback mở mạng. Đã thêm relay cố định. Sau đó phát hiện fixture/run_drill lấy `ids[-1]` trỏ relay thay PG (`docker exec` exit127), đã tách `target_ids` và kiểm chứng lại toàn pipeline. Worker test thêm cron expectation đúng contract mới, không sửa 11 baseline ngoài phạm vi.

- Scoped Windows backups: **42 passed**, 18.71s; cuối thêm worker suite **49 passed**, 22.31s.
- Ubuntu24.04 container phiên bản cuối: **38 passed / 4 skipped**, 12.05s; chỉ các ca riêng Windows được skip. Không phải full app/image production test trên Ubuntu.
- Integration thật PG16/MinIO/Qdrant: S3 copy/hash, import+drill, wrong password, pending jobs, missing source, scheduler defer/concurrent -> **1 passed**, 126.24s với mạng internal/relay cuối.
- Probe isolation độc lập -> **1 passed**, 11.26s: target không IPv4 default route, một network internal, không published ports; host vẫn kết nối qua relay. Tài nguyên mẫu được dọn, docker ps/network label không còn resources test.
- Ruff đạt. Frontend scoped Biome9files đạt; build5111modules + TypeScript đạt. Full FE lint vẫn13 lỗi format/schema version ngoài backups như baseline418; không auto-fix toàn repo.
- Full backend final gate với code đã chốt/network test bổ sung: **1113 passed / 11 baseline failed / 11 skipped**, 150.20s. Hai ca Docker opt-in đã chạy riêng đạt; 11 lỗi vẫn consulting/export, publishing permissions, reconciliation và auth role như trước, không có lỗi backup/worker mới.
- Browser smoke chỉ tới `/sign-in`; không bypass đăng nhập, chưa authenticated/mobile/dark E2E. Không thử khôi phục bản thật1GB hoặc đo RPO/RTO.

## Giới hạn và bàn giao

Khởi động lại BE/worker, F5. Lịch/S3 cần operator cấp external secret files và bucket/endpoint, rồi bật trên Chính sách. Drill cần relay image pinned và môi trường Docker vận hành; không gắn socket backend production. Tuân thủ runbook phiên bản nguồn/major/Qdrant tương ứng.

Soft delete/retention không purge nên chưa reclaim dung lượng; chưa UI restore-trash, retention remote, PITR, S3 version history, distributed Qdrant, fully restored chatbot RAG evaluation hoặc live cutover. Đây là ranh giới an toàn được hiển thị, không khẳng định disaster recovery production-ready.

Skills backend/clean-code định hình fail-closed/regression/async boundaries; frontend/admin-design giữ primitives, scope và trang cấu hình riêng. Không delegation/sub-agent. Đã lưu runbook, nhật ký README, PROJECT_CONTEXT và WORK_LOG, chốt final gate. Git diff whitespace check đạt. Docker compatibility cuối giữ38pass/4skip12.05s; các image test/relay giữ local để tái lập. Không còn container/network test chạy sau kiểm tra.
