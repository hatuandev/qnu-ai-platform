# Phiên826 — Docker và runner mặc định chuyển V1

## Phạm vi

User yêu cầu chuyển hẳn đường chạy mặc định sang V1, từ Docker đến Make. Không yêu cầu xóa thư mục legacy, restart app, migration DB thật, đổi ModelOps hoặc push/deploy. Giữ các thay đổi BE/FE chưa commit của các phiên trước.

## Thay đổi

- `scripts/run_v1.py` là runner chung cho lệnh ngắn và `v1-*`; thêm infra status/down/logs, test tổng hợp dừng khi BE lỗi và lint-fix tường minh. `db-ready` là kiểm tra readonly; seed/reset/reseed/reconcile/reindex legacy trả2, không chạy subprocess.
- Root Makefile/make Bash/make.bat/make.ps1/run.ps1 và start-dev/start-worker/start-dev-service chuyển V1 foreground API8002/FE3001/worker riêng. Ctrl+C dừng đúng phiên; không tự restart app hay migrate/seed.
- Root Compose build backendV1 và frontendV1, bootstrap chỉ `alembic upgrade head` chuỗi V1. Queue/cache V1 riêng; volume qnu_platform_storage giữ tên. Backend image dùng Python3.12 + uv0.11.16 + frozen uv.lock, không cần mã backend cũ.
- FrontendV1 có Dockerfile/.dockerignore/Nginx: SPA deep links, giữ nguyên API prefix/query/body/error, bufferingoff/readwait86400s cho xử lý dài; dev login false khi build production. SSO thật vẫn cần cấu hình và nghiệm thu riêng.
- Entry Compose backendV1 include root để không lệch hai cấu hình. Templates local/Dokploy mới dùng CSV origins, giữ ModelOps trongDB, không LLMkeyenv. `.env` thật không thay đổi.
- Cập nhật README, local/deployment/runbook, hướng dẫn V1, AGENTS ngữ cảnh, READMEbackend và mojibake scan V1. Không đổi bất biến quyền/schema giữa legacy/V1.

## Kiểm chứng thực chạy

1. Test mới6ca trước sửa FAIL đúng thiếu alias, còn đường legacy/Docker cũ và chưa có NginxV1. Lần gọi unittest theo module ban đầu không tìm được scripts.tests, sau đó chạy trực tiếp file để tái hiện.
2. Sau batch cuối: `python -m unittest discover -s scripts/tests -p 'test_*v1*.py'`:52testsPASS/exit0/3,574s. Có8ca cutover và tests cũ giữ guard subprocess/process ownership/env/migrationplan.
3. Ruff check runner/test mới PASS; format2file. PowerShell `scripts/test-dev-processes.ps1` PASS; mocks giữ guard PID cũ, phần launcher giờ kiểm thực dry-run V1.
4. Thực chạy PowerShell make/run, CMDmake.bat ở cwd có khoảng trắng: builddryrun đúngfrontendV1, reset-db trả2. BashmakebuilddryrunPASS. GNU Make binary riêng NOT RUN; Makefile delegate cùngrunner, đã đọc tĩnh.
5. `docker compose --env-file .env.dokploy.example build backend frontend` PASS; frontend tag riêng được build lại sau thêm image name. `config --quiet` và configJSON root/include đạt, không log secret.
6. Smokeimage cô lập:7/7PASS gồm importapp/worker/head0011, Nginxsyntax/health/SPAdeep-link/asset404 và upstream giả trả418/409 giữpathquery/body. Đây là proxycontract, không phải fullapp hoặc LLM thật.
7. API image chạy riêng production/dev_authfalse/networknone:GETlocalhosthealth200/qnu-backend-v1. Không DB/model request. Đã dọn đúng container/network smoke vừa tạo, không còn qnu-cutover826 container.
8. `make.ps1 check` thật:Redis/PostgreSQL schema current/Qdrant/S3readonly/frontend đềuOK/exit0. Không migrate/seed hoặc kiểm model.
9. UTF-8/LF/source docs links/diff--check đạt. Sửa lỗi quoting của lệnh kiểm image ban đầu bằng script argv chuẩn; sửa cách đọc encoding artifact Bash, không thay app để làm kết quả xanh.

Full backend domain suite và liveOCR/RAG NOT RUN vì batch chỉ thay orchestration/build/templates/docs, không sửa domain logic. FE production build đã gồm TypeScript trong Docker; không tuyên bố đã kiểm SSO/login bằng nhà cung cấp thật hoặc fullE2E.

## Bàn giao

Máy hiện có: dừng đúng phiên app cũ nếu còn nghe cổng, chạy `make.ps1 check`, rồi `make.ps1 dev`. Schema hiện đãcurrent nên không cần tự migrate lại. Máy mới dùng install/config/infra/migrate tường minh trong guide. Server mới cầnSSO/URL/quyềnstorage/backup thật trước deploy.

Legacy backend/frontend và mọi rawOCR/report/storage vẫn giữ. Chưa push/deploy/restartchính. ProfileE2ENemotron và Nemotroncatalogactive là tồn đọng825 cần batch ModelOps/E2E riêng trước chạy lại provider-setup; đợt826 không đổi lựa chọn provider/model của user.

Artifact: `tmp/cutover826/` có before/final tests, buildlogs, proxy/APIhealth, wrappers/preflight và receipt; không secrets/nguồn corpus.
