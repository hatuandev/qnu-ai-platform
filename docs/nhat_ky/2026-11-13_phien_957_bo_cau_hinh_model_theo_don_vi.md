# Phiên 957 — Bỏ cấu hình model theo đơn vị: allowlist provider và model mặc định workspace

## 1. Yêu cầu và phạm vi

- Người dùng yêu cầu bỏ chức năng "model được sử dụng theo đơn vị"; sau khi nghe phân tích hai lớp cấu hình, người dùng chốt: **"bỏ luôn cả hai, tôi đồng ý với phương án bỏ sạch"** — tức bỏ cả `workspace_allowed_providers` (allowlist provider theo workspace) lẫn `workspace_model_defaults` (model mặc định theo workspace).
- Phạm vi đã thực hiện: enforcement/phân giải trong `backendV1/qnu/domains/modelops`, hai nhóm endpoint `/workspaces/{id}/allowed-providers` và `/workspaces/{id}/model-defaults`, ORM/schema/DTO, guard xóa provider/model, phân loại bảng sở hữu, migration `0027`; FE V1 (trang "Model được phép dùng", panel, API client, quyền, điều hướng); FE V2 (client/hook/type không còn dùng); test backend; artifact OpenAPI; ADR và tài liệu trạng thái hiện hành.
- Giữ nguyên: bản ghi **model mặc định hệ thống** (`model_defaults`, id `system`) làm nguồn phân giải duy nhất; workspace vẫn là biên giới **quyền** (membership/role), không phải phân vùng dữ liệu; quota/usage tháng UTC không đổi.
- Ràng buộc: không commit/push/deploy; không re-index; không đổi dữ liệu ngoài phạm vi; giữ nguyên diff chưa commit của người dùng (`chunking.py`, `hybrid.py`, `table_layout.py` và các test được bảo vệ); chỉ sửa khối setup provider tối thiểu trong `test_answers_api_648.py` và `test_hybrid_655.py` (đã được duyệt), có ghi nhận bên dưới.

## 2. Hợp đồng sau khi bỏ

1. **Một nguồn cấu hình model:** `PUT /modelops/defaults` (quyền `ai.models.manage`) chọn provider/model mặc định hệ thống theo capability chat/embedding/rerank/ocr; không còn cấu hình model theo từng workspace.
2. **Phân giải runtime:** sau khi kiểm quyền workspace (`resolve_workspace_access`), resolver chỉ đọc default hệ thống; chưa cấu hình → `model_not_configured`; provider ghim không tồn tại → `provider_not_found`; provider tắt/sai capability → lỗi tương ứng; fallback theo resilience policy không còn bước lọc allowlist.
3. **Catalog:** thành viên đang hoạt động đọc catalog trong workspace cụ thể; không trả endpoint/base_url; provider bị tắt không được phân giải.
4. **Admin đơn vị** vẫn xem được defaults và catalog nhưng **không** đổi được chính sách hệ thống (403); không còn thao tác mở rộng allowlist hay đặt default đơn vị.
5. **Guard xóa provider/model:** chỉ còn kiểm tham chiếu từ `model_defaults` (cùng trợ lý, lịch sử…); xóa connection cũng kiểm default trỏ tới provider cha/con.
6. **Schema:** migration `0027_drop_ws_model_policy` drop hai bảng; migration `0028_drop_index_system_default_authorized` bỏ cột chết trên `kb_index_runs`; `SCHEMA_HEAD = "0028_drop_index_system_default_authorized"` và `V1_TABLES` cập nhật tương ứng.

## 3. Thay đổi

### 3.1 Backend

- `qnu/domains/modelops/router.py`: xóa `workspace_router` cùng hai endpoint `GET/PUT /workspaces/{workspace_id}/allowed-providers` và `PUT /workspaces/{workspace_id}/model-defaults`; xóa DTO liên quan trong `schemas.py`.
- `qnu/api/routes.py`: bỏ đăng ký `workspace_router`.
- `qnu/domains/modelops/models.py`: xóa ORM `WorkspaceAllowedProvider`, `WorkspaceModelDefault`.
- `qnu/domains/modelops/catalog/service.py`: bỏ toàn bộ nhánh allowlist/`workspace_defaults`; `resolve_provider`/`resolve_workspace_provider`/`resolve_workspace_target` chỉ dùng default hệ thống sau khi caller đã kiểm quyền workspace; giữ `model_not_configured`, `provider_inactive`, `provider_capability_mismatch`, `model_mismatch`.
- `qnu/domains/modelops/resilience/routing.py`: `choose_target` lấy primary từ default hệ thống; fallback chỉ kiểm provider active/capability/transport; bỏ lọc `candidate_not_granted`.
- `qnu/domains/modelops/connections/service.py`: guard xóa connection/provider/model kiểm tham chiếu `model_defaults` thay cho hai bảng đã bỏ.
- `qnu/domains/modelops/public_api.py`: cập nhật docstring/hợp đồng phân giải (không còn allowlist).
- `qnu/platform/ownership.py`, `qnu/platform/schema.py`: bỏ hai bảng khỏi `V1_TABLES`; `SCHEMA_HEAD = "0028_drop_index_system_default_authorized"`.

### 3.2 Migration `backendV1/alembic/versions/0027_drop_ws_model_policy.py` (mới)

- `revision = "0027_drop_ws_model_policy"` (25 ký tự, vừa giới hạn `varchar(32)` của `alembic_version_backendv1`), `down_revision = "0026_ollama_llamacpp"`.
- `upgrade()`: drop `workspace_model_defaults` trước, sau đó `workspace_allowed_providers`.
- `downgrade()`: tạo lại cả hai bảng kèm index để có thể quay lui cấu trúc (không phục hồi dữ liệu đã xóa).

### 3.3 Frontend V1

- Xóa trang/route `workspaces.$workspaceId.models.tsx`, panel `models-panel.tsx`, helper `allowlist-patch.ts`; bỏ hook/request/type allowlist trong `features/workspaces`; bỏ mục "Model" khỏi điều hướng workspace và thẻ mô tả trong `qnu-settings-hub.tsx`; bỏ quyền `canChooseWorkspaceDefaults`; bỏ link "Xem Model workspace" và đổi nhãn "Theo mặc định workspace" → "Theo mặc định hệ thống" ở `assistant-detail-page.tsx`; bỏ invalidate query allowlist trong `features/modelops/queries.ts`; cập nhật `tests/v1-contract.test.ts`.
- Chỉnh này kéo theo lỗi type do nav key `models` bị bỏ; đã sửa cùng lượt và build lại.
- Đổi nhãn còn sót "Theo mặc định workspace" → "Theo mặc định hệ thống" ở 6 lựa chọn provider mặc định: `assistant-form-dialog.tsx`, `knowledge/answer-settings.tsx`, `knowledge/compilation-dialog.tsx`, `knowledge/index-panel.tsx`, `knowledge/ocr-request-dialog.tsx`, `knowledge/ocr-review-dialogs.tsx` (chỉ đổi microcopy, không đổi value/logic).

### 3.4 Frontend V2

- Bỏ endpoint/type/hook/request allowlist trong `src/api/workspaces/{endpoints,queries,requests,types}.ts` (không còn nơi dùng).

### 3.5 Test backend (25 tệp, trong đó 2 tệp support)

- Hai tệp support `compiler_support.py`, `ocr_support.py` và `conftest.py` bỏ helper/khai báo allowlist.
- Các tệp còn lại chuyển setup từ `PUT /workspaces/{id}/allowed-providers` sang `PUT /modelops/defaults`, bỏ khẳng định allowlist không còn nghĩa, thay bằng khẳng định mạnh hơn: default hệ thống áp dụng cho mọi workspace; catalog/runtime vẫn kiểm quyền membership (outsider 404); admin đơn vị đọc được defaults nhưng PUT bị 403; provider tắt/sai capability bị từ chối; fallback không "hồi sinh" provider inactive (`fallback_exhausted`).
- **Hai tệp được bảo vệ, sửa tối thiểu đã được duyệt:** `test_answers_api_648.py` (2 khối setup provider) và `test_hybrid_655.py` (1 khối setup rerank) chỉ thay payload allowlist bằng `PUT /modelops/defaults`; không đụng phần còn lại của tệp. Diff: 6 dòng thêm / 39 dòng bớt trên cả hai tệp.

### 3.6 OpenAPI và tài liệu

- `backendV1/docs/openapi-v1.json`: gỡ đúng 6 mục (2 path + 4 schema `AllowedProviderItem`, `AllowlistResponse`, `AllowlistUpdateRequest`, `WorkspaceDefaultsRequest`), **giữ nguyên định dạng LF và các byte còn lại** (diff 281 dòng xóa, 0 dòng thêm; JSON hợp lệ).
- Cập nhật trạng thái hiện hành: `ADR-007`, `ADR-008` (thêm mục "Cập nhật batch957 — bãi bỏ cấu hình model theo đơn vị"), `workspaces-modelops.md`, `migration-ownership.yaml`, `resource-lifecycle.md`, `modelops-resilience.md`, `ocr-processing.md`, `dense-indexing.md`, `model-capacity.md`, `modelops-diagnostics.md`, `module-boundaries.md`, `compiler-review.md`, `compiler-v1.md`, `compiler-workflow.md`, `ADR-010`, `feature-port-matrix.md`, `hybrid-evaluation.md`, `ocr-acceptance.md`, `ocr-text-review.md`, `docs/quy_trinh/19`, `docs/quy_trinh/37`, `docs/quy_trinh/47`.
- Không sửa nhật ký/báo cáo cũ đã đóng (mang tính lịch sử).

### 3.7 Dọn 7 điểm tồn đọng sau bãi bỏ (yêu cầu tiếp theo trong phiên)

Người dùng yêu cầu "dọn 7 điểm comment và thông báo lỗi" đã báo cáo sau khi kiểm chức năng model mặc định hệ thống:

1. `qnu/domains/modelops/catalog/service.py`: docstring module "workspace-scoped resolution" → `"""System capability defaults and provider catalog resolution."""`; docstring `resolve_workspace_target` đổi thành "Return the active provider, preferring an explicit target over the system default."
2. `qnu/domains/modelops/rerank.py`: docstring "through grants" → `"""Resolve rerank through encrypted keys and configured model capacity."""`.
3. `qnu/domains/modelops/resilience/key_pool.py`: comment "Revalidate grants..." → "Revalidate the provider's active/capability state immediately before dispatch."; lời gọi rút gọn còn `resolve_workspace_provider(db, scope.workspace_id, capability, scope.provider_id)`.
4. **Tham số chết `index_run_id`:** gỡ end-to-end khỏi chuỗi `EmbeddingRuntime.request()` → `ProviderExecution` → `key_pool.acquire` → `resolve_workspace_target` và `usage_service.reserve` → `resolve_provider` (không còn nơi đọc sau khi bỏ grant). Sửa 8 tệp backend: `modelops/embedding/runtime.py`, `ports/provider_execution.py`, `modelops/resilience/key_pool.py`, `modelops/catalog/service.py`, `modelops/usage/service.py`, `knowledge/index/{execution,validation,search}.py`.
5. **`system_default_authorized`:** cột ghi-only trên `kb_index_runs` (migration 0021), không có reader/test/schema nào đọc; bỏ field khỏi ORM `IndexRun`, bỏ gán trong `knowledge/index/service.py`, thêm migration **`0028_drop_index_system_default_authorized`** (`down_revision = "0027_drop_ws_model_policy"`, có downgrade) và dâng `SCHEMA_HEAD`.
6. `frontendV1/src/features/knowledge/ocr-schemas.ts`: message `model_not_configured` → "Chưa cấu hình model mặc định hệ thống cho chức năng đang thực hiện. Hãy cấu hình trong ModelOps."
7. `frontendV1/src/features/knowledge/preparation-schemas.ts`: message `model_not_configured` → "Chưa cấu hình model mặc định hệ thống cho chức năng này. Hãy cấu hình trong ModelOps."

Ghi chú phạm vi: `workspace_id` trong `resolve_workspace_target` nay cũng không được đọc bên trong hàm, nhưng **giữ nguyên** để không mở rộng phạm vi ngoài 7 điểm đã duyệt; `preparation-schemas.ts` còn nhãn `provider_not_found: "Model đã chọn chưa được cấp cho workspace này."` (dòng 55, ngoài 7 điểm) — chờ người dùng quyết định.

## 4. Kiểm chứng (chỉ ghi kết quả thực chạy)

- **Ruff check** trên 35 tệp Python thay đổi + migration `0027`: **All checks passed** (exit 0).
- **Ruff format --check** trên cùng phạm vi: 12 tệp "would be reformatted". Đã đối chiếu bản `HEAD` của đúng 12 tệp này: **cả 12 tệp đã không đạt format từ trước** (nền cũ, ngoài diff phiên); không chạy format toàn tệp để tránh churn ngoài phạm vi.
- **Pytest cô lập, phạm vi trọng tâm** (11 module: workspaces/modelops/defaults/boundaries/resilience/answers/hybrid/index/readiness/rag verification): **156 passed, 0 failed, 2 warnings — 933,43 s**; receipt `pytest_exit: 0`, `db_dropped: true`, `legacy_sentinel_preserved: true`, DB tạm `qnu_v1_test_33977fda29174fd4`.
- **Full backend suite (một lần cuối batch, DB cô lập):** **NOT RUN** — người dùng yêu cầu dừng để tập trung vào tính năng chọn đơn vị. Lần chạy serial đã dừng ở khoảng 522/~2.000 test (~26%), có 1 lỗi sớm chưa xác định được ID vì chưa có `result.xml`/receipt; pilot chia 4 chặng song song cũng đã hủy theo yêu cầu. Mọi DB tạm và thư mục runtime của hai lần chạy đã được dọn sạch; không có tiến trình pytest/alembic nào còn sống. `NOT RUN ≠ PASS`.
- **Frontend V1:** Biome sạch trên 12 tệp thay đổi; `npm run build` (Vite + `tsc --noEmit`) **PASS**; `npm run typecheck` **exit 0** (chạy lại sau khi đổi 6 nhãn microcopy, vẫn exit 0).
- **Frontend V2:** `npm run typecheck` **exit 0**.
- **Vitest V1:** `tests/v1-contract.test.ts` **13/13 PASS**. Full vitest: **896 passed / 27 failed trên 6 tệp** — các tệp lỗi (`admissions-cohort-775`, `admissions-integrity-775`, `admissions-multi-docs-773`, `admissions-pipeline-777`, `e2e-capacity-735`, `modelops-diagnostics-694.test.tsx`) **sạch trong git và không import module nào của thay đổi này**; nguyên nhân nền: fixture `frontendV1/e2e/data/admissions-multi-docs.json` đã 77 ca/7 tài liệu trong khi test ghim 53 ca/3 tài liệu, test pipeline bị chặn vì thiếu extraction page counts, mock capacity thiếu `policy`, mock diagnostics thiếu `observed_output_limits`. Không nới assertion, không sửa test để xanh.
- **OpenAPI artifact:** JSON hợp lệ; so sánh cấu trúc với `HEAD` chỉ còn đúng 6 mục bị gỡ; không đổi CRLF/LF (0 ký tự `\r`).
- **Kiểm chứng mục 3.7 (dọn 7 điểm, không chạy pytest theo yêu cầu dừng test):** `uv run ruff check` trên **13 tệp backend** liên quan + migration 0028 → **All checks passed**; `uv run alembic heads` → **đúng một head** `0028_drop_index_system_default_authorized`; import smoke các module đã sửa (`catalog/service`, `embedding/runtime`, `ports/provider_execution`, `usage/service`, `index/{execution,validation,search,service,models}`, `resilience/key_pool`) → **imports ok**; Biome check 2 tệp FE V1 → **Checked 2 files. No fixes applied**. **Pytest: NOT RUN** cho phần dọn này (`NOT RUN ≠ PASS`).

## 5. Giới hạn và bước tiếp

- **Dev DB chưa migrate** sang `0027`/`0028` (vẫn ở `0026_ollama_llamacpp`; kiểm tra đọc ngày 2026-11-13: `workspace_allowed_providers` và `workspace_model_defaults` vẫn tồn tại, `kb_index_runs.system_default_authorized` vẫn còn, `model_defaults` chỉ còn 1 dòng `id='system'`). Do full suite bị dừng theo yêu cầu, điều kiện "chạy migration sau khi full suite đạt" chưa thỏa — cần người dùng quyết định trước khi áp migration.
- **Xác minh tĩnh bãi bỏ cấu hình model theo đơn vị (sau khi dừng test):** grep toàn `backendV1` và `frontendV1/src`, `frontendV2/src` không còn tham chiếu sống tới `allowed-providers`/`model-defaults`/các model-schema đã bỏ; chỉ còn DDL lịch sử trong `0001_initial_schema.py`, migration `0027` và mục ghi chú bãi bỏ trong `ADR-008`. `backendV1/docs/openapi-v1.json` không còn 2 path và 4 schema đã gỡ. `SCHEMA_HEAD = "0028_drop_index_system_default_authorized"`; chuỗi alembic 0025→0026→0027→0028 liên tục, một head. Router workspace còn nguyên (list/tạo/sửa, `resolve-route`, members, events) và vẫn dùng `resolve_workspace_access`.
- Chưa chạy: E2E live upload→OCR→publish→RAG, rebuild Docker, re-index; `NOT RUN ≠ PASS`.
- Chưa commit/push; working tree còn các thay đổi chưa commit của các phiên 954–956 đang chờ duyệt.
- 27 lỗi vitest nền và 12 tệp format nền là vấn đề đã có trước phiên, được ghi nhận thay vì che giấu.
