# Phiên 418 — Sao lưu thủ công và khôi phục thử, đợt 1

## Mục tiêu và phạm vi được người dùng duyệt

Triển khai đợt 1 của đề xuất: full backup bản cài đặt, password encryption, catalogue/progress/download, integrity verification và isolated restore drill. Không lập lịch, không reset/restore-to-live, không tự backup dữ liệu thật hay đổi provider/model. Không tiếp tục benchmark 82 câu hỏi trong phiên này.

## Thay đổi

- Module `backend/app/modules/backups/`: models/schemas/router/service và catalogue, capture, archive, encryption, coordination, processes, locks, errors, offload, runner, drill, CLI.
- `backend/app/core/config.py`: cấu hình thư mục/prefix/timeout/drain/min free space/drill; không thêm API key LLM vào env.
- `backend/app/main.py`: router và ASGI barrier giữ khóa đến hết SSE/background response.
- `backend/app/workers/arq_worker.py`: shared barrier toàn vòng đời các task và cron; cron skip maintenance, regular job retry hữu hạn.
- `backend/Dockerfile`, `docker-compose.yml`: pg_dump/pg_restore16 native production, cấu hình backup trên volume sẵn có; không gắn Docker socket.
- `frontend/src/features/backups/`: typed API/query, TanStack Form+Zod action dialog, TanStack Table history, detail/check/download/drill và audit history.
- Ba route `settings.backups*`, SettingsLayout, navigation config/types; route tree do plugin sinh, không sửa tay.
- Tests `test_backups.py`, `test_backups_integration.py`; hướng dẫn `docs/trien_khai/04_sao_luu_va_khoi_phuc_dot_1.md`.

## Thuật toán và an toàn

PG advisory shared/exclusive barrier, kết nối riêng độc lập Redis; filesystem locks serialise catalogue/process và vẫn dùng được khi DB live mất. Capture kiểm tra còn job/workflow active, exact storage references và namespace active; không báo full success nếu thiếu thành phần. pg_dump custom binary, version gate, Docker fallback kiểm tra PostgreSQL system identifier để không dump nhầm host.

Tar streaming gzip vào scrypt/AES-256-GCM framed encryption: salt/nonce ngẫu nhiên, authenticated sequence+header, EOF frame bắt buộc, bounded block memory. Không lưu passphrase vào DB/file/argv/log; key escrow chỉ nằm trong archive encrypted. Manifest exact entries/SHA-256/size/schema/row counts/models/dimensions/Qdrant version+aliases; path/link/duplicate/expansion checks; `.partial` không coi hoàn tất. Offloaded blocking I/O được drain khi hủy trước khi release barrier/delete scratch.

Backup API đòi phiên thực và AI.Admin; quyền whole-installation gồm mọi tenant. Download ticket HttpOnly scoped cookie90s/no URL token/no-store; browser stream file thay vì Blob RAM. Lịch sử thao tác actor/correlation/status ngoài DB. Runner không qua ARQ; heartbeat mất phải hiện failed, không fake success.

Restore drill chỉ tạo Docker container ID/label mới, localhost ports/no mounts live; đối soát PG schema/counts/file refs, key decryptability JSON+relational pool, Qdrant snapshot exact counts+aliases, S3 original key+checksum. Dọn đúng container ID+ownership label và anonymous volumes do phiên tạo. Không chạy chatbot/worker sandbox, không replay Redis, không gọi AI. CLI getpass cho verify/drill offline khi API/DB/Redis live không có.

## Kiểm thử

- Unit/security 24/24 đạt (mật khẩu sai, corruption/truncation/trailing ciphertext, link/traversal, giải nén budget, stream3MB, catalogue, auth, ticket, tool failure).
- Integration thật PG16/MinIO/Qdrant handoff đạt37.20s sau full runtime config/audit history: Unicode/đã duyệt, key pool, vector, shared lock xuyên SSE, worker failure unlock, job pending và thiếu file fail-closed. Một lần phát hiện CannotConnectNowError lúc sandbox startup; đã thêm readiness retry, các rerun đạt. Không còn runner/container thử đang chạy sau handoff.
- Ruff toàn backend đạt (có warnings Windows access denied ở các temp cũ; không sửa file khác).
- Full backend finalgate:1095 passed/11 baseline failures/10 skipped,108.49s; integration opt-in skipped trong full nhưng đã chạy riêng đạt. 11 lỗi cùng nhóm consulting exports, publishing/auth/canary/system GC/reconciliation/universal tool của phiên417, không sửa lan.
- Frontend final build Vite5105 modules/4.04s + TypeScript đạt; scoped Biome10files đạt. Full frontend lint13 lỗi ngoài scope (format của collection/add-documents/knowledge utils/types + schema version info), không apply fix toàn repo.
- Docker production image chưa build; integration dùng image/container local thật. Browser smoke chuyển về `/sign-in`, không tự đăng nhập/bypass auth; chưa UI E2E authenticated/mobile/dark. Không coi fixture restore thành corpus/app RAG đã nghiệm thu.

## Lưu ý tiếp quản

Đợt1 chưa schedule/remote transfer/retention/PITR/restore-to-live/import archive UI. Chỉ Qdrant single-node, S3 current object versions. ModelOps và nguồn/DAG giữ trong PG; Redis cache/leases không nằm backup, phải đối soát trước khi bật worker khi khôi phục thật. 9router/SSO/server AI ngoài app không nằm phạm vi.

Bắt buộc rollout/restart tất cả BE/worker để barrier có hiệu lực; không chạy CLI/direct writes lúc capture. Mật khẩu do người dùng tự giữ, không tạo backup thật trong phiên. Bản trên cùng disk không chống hỏng máy, cần tải/chép sang nơi độc lập. Fixture encrypted/catalogue giữ trong test scratch; container mẫu được dọn, không xóa vật liệu người dùng.

Thiết kế theo skills backend/clean-code/frontend/admin-design: domain riêng, error fail-closed, I/O offload, primitives dùng lại và tách list/detail; không tạo schema backup trong PG bị backup để tránh mất control plane khi DB down. Không đồng nghĩa production-ready/RPO/RTO đã đo.
