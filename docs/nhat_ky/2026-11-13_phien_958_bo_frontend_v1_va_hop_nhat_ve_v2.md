# Phiên 958 — Bỏ frontendV1, hợp nhất về Frontend V2 và bỏ service frontend khỏi Docker

## 1. Yêu cầu và phạm vi

- Người dùng yêu cầu: **"chắc bỏ luôn FE v1 đi nhé, nó sẽ làm rối, tôi muốn tập trung hết vào Fe v2 luôn để phát triển"**.
- Hai quyết định người dùng chốt qua lựa chọn:
  1. **Xóa hẳn + dọn tham chiếu** — xóa `frontendV1/` khỏi repo, cập nhật Makefile/runner/README/AGENTS/tài liệu vận hành hiện hành; lịch sử Git giữ khả năng khôi phục; khoảng 20 thay đổi cục bộ chỉ thuộc V1 từ phiên 957 bị bỏ theo lựa chọn này.
  2. **Tạm bỏ frontend khỏi compose** — repo chỉ còn backend/worker trong Docker; website trên server giữ nguyên bản cũ cho tới khi `frontendV2` có SSO production.
- Phạm vi đã thực hiện: xóa `frontendV1/` và harness E2E V1; sửa `Makefile`, `scripts/run_v1.py`; bỏ service frontend khỏi `docker-compose.yml` và `.env.dokploy.example`; cập nhật toàn bộ tài liệu sống mô tả cổng 3001/Frontend V1; dán nhãn lịch sử cho tài liệu mô tả `frontendV1` hoặc harness đã gỡ.
- Giữ nguyên: `backendV1/` (FastAPI, worker ARQ, cổng 8002), API prefix `/platform/v1alpha1`, migration chain `0025→0026→0027→0028` (dev DB vẫn `0026`, 0027+0028 chờ duyệt), toàn bộ diff chưa commit của người dùng ở các tệp được bảo vệ.
- Ràng buộc: không commit/push/deploy; không re-index; không đổi dữ liệu ngoài phạm vi; không chạy pytest (người dùng đã yêu cầu dừng test); không in secret/corpus.

## 2. Hợp đồng sau thay đổi

1. **Một giao diện duy nhất:** `frontendV2/` (Vite + TanStack Router/Query) là frontend hiện hành, dev tại cổng 3002, proxy `/platform/v1alpha1` về API 8002. `frontendV1/` không còn trong checkout.
2. **Runner:** `make dev`/`dev2` chạy Backend V1 + worker V1 + Frontend V2 (3002); `v1-dev`/`v1-be`/`v1-worker` chỉ backend; `v2-dev`/`v2-fe`/`v2-install-fe`/`v2-typecheck`/`v2-build` cho FE V2; `v1-test` chỉ backend, *"Frontend V2 has no test suite"*; lint = Ruff + Biome V2.
3. **Docker/Dokploy:** `docker-compose.yml` chỉ còn `storage-init`, `bootstrap`, `backend`, `worker`. Không còn service frontend, không còn build `frontendV1`. Website trên server tạm giữ bản cũ cho tới khi V2 có SSO; local không phụ thuộc dịch vụ này.
4. **Auth dev V2:** cầu nối chỉ tồn tại khi chạy Vite dev (`frontendV2/dev/dev-auto-login.ts`), cần `QNU_DEV_AUTO_LOGIN=true`, `QNU_DEV_ACCESS_KEY` khớp `DEV_ACCESS_PASSWORD` của backend và `QNU_DEV_WORKSPACE_CODE`; không có màn nhập khóa thủ công nên build production không thể đăng nhập.
5. **Tài liệu:** mọi tài liệu sống mô tả checkout V2-only; tài liệu mô tả `frontendV1`/harness E2E đã gỡ được dán nhãn **"TÀI LIỆU LỊCH SỬ (từ 2026-11-13)"**, nội dung giữ nguyên.

## 3. Thay đổi

### 3.1 Xóa `frontendV1/`

- `git rm -r -f -q frontendV1`: **816 tệp tracked** bị xóa (81 route, SSO, nginx proxy, cổng 3001, bộ test vitest/playwright, e2e data).
- Khoảng 20 thay đổi cục bộ chỉ thuộc V1 của phiên 957 (nhãn microcopy, trang Model được phép dùng) bị bỏ cùng thư mục theo quyết định "xóa hẳn"; các thay đổi đó vốn đã vô nghĩa sau khi bãi bỏ cấu hình model theo đơn vị.
- Lịch sử Git còn nguyên để khôi phục khi cần truy vết.

### 3.2 Xóa harness E2E V1 (16 tệp tracked ngoài `frontendV1/`)

- Gốc: `test-v1-e2e.ps1`.
- `scripts/`: `v1_e2e_runner.py`, `v1_e2e_session.py`, `e2e_data_probe.py`, `e2e_fixtures.py`, `e2e_mock_server.py`, `e2e_provider_setup.py`, `e2e_profiles/qnu-server.json`, `run_admissions_retest.py`, `verify_admissions_benchmark.py`, `test_e2e_provider_setup.py`, `test_v1_e2e_cleanup.py`, `test_v1_e2e_draft_778.py`, `test_v1_e2e_runtime_741.py`, `test_v1_e2e_scan_797.py`.
- `frontendV2/tests/studio-browser.mjs`: xóa vì không còn dùng được — môi trường `frontendV2` không có playwright, giữ lại chỉ tạo lệnh hỏng.
- Giữ `backendV1/scripts/run_sharded_tests.py` (untracked, chỉ chạy test backend) — chờ người dùng quyết định giữ hay bỏ.

### 3.3 Runner và Makefile

- `Makefile`: bỏ các đích `dev1`/`v1-dev` cũ gắn Frontend V1, `v1-fe`, `v1-test-fe`, `install-fe`, `typecheck`, `build` của V1; thêm `V2_TASKS := v2-dev v2-fe v2-check v2-install-fe v2-typecheck v2-build`; `dev`/`dev2` → `v2-dev`; `fe`/`fe2` → `v2-fe`; `v1-*` chỉ còn backend; `lint` chạy Ruff rồi Biome trên `frontendV2`.
- `scripts/run_v1.py`: dựng lại bảng tác vụ theo hợp đồng mục 2; preflight `check`/`v2-check` chỉ kiểm API/schema/Redis/Qdrant/storage và Vite V2; `v2-typecheck`/`v2-build` chạy npm trong `frontendV2`; `v1-test` ghi rõ backend-only.
- `make.ps1`/`make.bat` chỉ là wrapper gọi `scripts/run_v1.py`, không cần sửa logic.

### 3.4 Docker và mẫu cấu hình

- `docker-compose.yml`: xóa service `frontend` (build `frontendV1`, nginx, cổng 80); giữ `storage-init` → `bootstrap` → `backend`/`worker`, healthcheck `/health/ready`, log xoay vòng, grace period như phiên 956.
- `.env.dokploy.example`: bỏ biến chỉ phục vụ frontend; giữ cấu hình backend/worker (SSO, storage, Gotenberg, ModelOps).
- `backendV1/.env.example` và root `.env.example`: `ALLOWED_ORIGINS=http://localhost:3002,http://127.0.0.1:3002`.

### 3.5 Tài liệu sống cập nhật

- Gốc: `README.md`, `AGENTS.md`, `HUONG_DAN_CHAY_LOCAL.md`.
- `docs/`: `README.md` (nguồn sự thật + phân loại), `architecture.md`, `deployment.md`, `huong_dan_chay_local.md`.
- `docs/quy_trinh/`: `38_huong_dan_chay_qnu_v1.md` (viết lại phần chạy/cấu hình/xử lý lỗi cho V2 3002, env `FRONTEND_V2_PORT`, `QNU_API_PROXY_TARGET`, `QNU_DEV_*`), `README.md` (mục 1 ghi chú tài liệu đã dán nhãn lịch sử), 41/42/43 (ghi chú `frontendV1` đã gỡ).
- `docs/trien_khai/`: `README.md`, `02_quy_trinh_trien_khai_dokploy.md` (bỏ hàng frontend, bỏ build frontend, ghi rõ server tạm giữ website cũ).
- `backendV1/README.md` (đăng nhập dev qua cầu nối V2), `backendV1/docs/ocr-text-review.md` (bỏ nhắc role demo của frontendV1).
- `.agents/rules/verification.md` (gate frontend từ `frontendV2`: Biome + `npm run build`, không có bộ test riêng), `.agents/rules/ui-standards.md`, `.agents/skills/qnu-frontend-architect/SKILL.md` (cây thư mục thật của `frontendV2`, `routeTree.gen.ts` sinh tự động, token tại `frontendV2/src/styles/tokens.css`).

### 3.6 Tài liệu lịch sử dán nhãn (không viết lại nội dung)

- Nhãn harness: `V1_E2E_TUNG_BUOC.md`, `V1_QUY_TRINH_TEST_LAI.md`, `V1_TEST_TOAN_LUONG_MODEL_QNU.md`, `V1_TEST_MODEL_QNU.md`, `V1_TEST_TB_DIEM_SAN_26.md`, `V1_TEST_OCR_QUY_CHE_363.md`, `V1_COMPILER_TAI_LIEU_LON.md`, `V1_RAG_NGU_CANH_VA_PHAM_VI.md` — "frontendV1, `test-v1-e2e.ps1` và bộ `scripts/v1_e2e_*` đã được gỡ khỏi repo. Các lệnh dưới đây không còn chạy được; giữ để truy vết."
- Nhãn giao diện cũ: `34`, `35`, `36`, `37`, `45` — "`frontendV1` đã được gỡ khỏi repo; giao diện duy nhất hiện hành là `frontendV2`."
- `46_pilot_qnu_v1_va_dong_pham_vi.md`: thêm ghi chú lịch sử ngay sau ma trận trình duyệt 3001 và sau khối lệnh vitest V1; không sửa số liệu đã ghi.
- `docs/README.md` §2/§3 và `docs/quy_trinh/README.md` §1: bổ sung quy ước nhãn ngày 2026-11-13 và danh sách tệp đã dán nhãn.

## 4. Kiểm chứng (chỉ ghi kết quả thực chạy)

- **Runner:** `python scripts/run_v1.py help` → exit 0, liệt kê đúng bộ tác vụ mới (`v2-dev`…`v2-build`, `v1-dev` backend-only, `v1-test` "Frontend V2 has no test suite").
- **Dry-run:** `python scripts/run_v1.py dev --dry-run` → exit 0; kế hoạch gồm preflight, uvicorn `qnu.main:app`, ARQ `qnu.workers.settings.WorkerSettings` và Vite trong `frontendV2`; **không** còn mục nào trỏ `frontendV1` hay cổng 3001.
- **Compose:** `docker compose --env-file .env.dokploy.example config --quiet` → **OK** (chỉ `storage-init`, `bootstrap`, `backend`, `worker`).
- **Ruff:** `uv run --project backendV1 --frozen ruff check scripts/run_v1.py` → **All checks passed**.
- **Encoding:** kiểm 19 tệp tài liệu vừa sửa — UTF-8 không BOM, không CRLF, không ký tự thay thế; đọc lại tiêu đề/banner tiếng Việt đúng.
- **Grep tham chiếu sống:** không còn tệp không phải `.md` nào nhắc `frontendV1`/`test-v1-e2e`/`scripts/v1_e2e_*`; các tệp `.md` còn nhắc đều thuộc nhóm đã dán nhãn lịch sử hoặc thư mục lịch sử (`nhat_ky/`, `bao_cao/`, `ke_hoach/`, `kiem_thu/`, `adr/`, `quy_trinh/` 01–18).
- **NOT RUN:** pytest (người dùng yêu cầu dừng test — `NOT RUN ≠ PASS`); Biome/typecheck/build FE V2 (phiên này không sửa mã ứng dụng V2, chỉ xóa một tệp test trình duyệt không chạy được); build image Docker; deploy Dokploy; kiểm trình duyệt 390/1280.

## 5. Giới hạn và bước tiếp

- **`frontendV2` chưa có SSO production** — đây là lý do website trên server tiếp tục dùng bản cũ; không tuyên bố V2 sẵn sàng thay thế website cho tới khi có luồng đăng nhập production.
- **Dev DB vẫn ở `0026_ollama_llamacpp`**; migration `0027_drop_ws_model_policy` + `0028_drop_index_system_default_authorized` chưa áp dụng (chờ duyệt, như phiên 957).
- **Chưa commit/push** toàn bộ batch 957+958; working tree còn 832 tệp xóa (816 `frontendV1` + 16 harness) và các thay đổi của các phiên 954–957.
- Build image Docker/Dokploy deploy, E2E live upload→OCR→publish→RAG, re-index, demo corpus và bộ câu hỏi vẫn **NOT RUN**.
- `backendV1/scripts/run_sharded_tests.py` (untracked) giữ nguyên, chờ người dùng quyết định.
