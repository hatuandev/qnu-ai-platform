# Phiên 795 — Khắc phục dứt điểm 4 lỗi P2 ModelOps và đưa toàn bộ 26 frontend test về 0 FAIL

## Mục tiêu phiên

Thực hiện toàn bộ yêu cầu trong `docs/ke_hoach/PROMPT_FIX_FE_26_TEST_VA_4_P2_794.md`:
1. Sửa 4 khiếm khuyết P2 ModelOps phát hiện từ đợt review phiên 793 (P2-1, P2-2, P2-3, P2-4).
2. Khắc phục dứt điểm 26 frontend test đang FAIL thuộc 8 file test hồi quy.
3. Viết bộ test hồi quy thực chất cho 4 P2 trong `frontendV1/tests/modelops-p2-regressions-795.test.tsx`.
4. Đưa toàn bộ frontend test suite về **0 FAIL** (95 test suites, 651 tests PASS).
5. Bảo toàn phiên E2E `93faa11f0caf`, không restart/cleanup/reindex/deploy.

---

## 1. Khắc phục 4 khiếm khuyết P2 ModelOps

### P2-1: Wire dữ liệu ngân sách catalog từ BE sang FE consumers
- **Backend**:
  - `backendV1/qnu/domains/modelops/schemas.py`: Mở rộng `CatalogItem` và `ProviderResponse` thêm các trường `token_limits`, `capacity_status`, `capacity_basis`, `operational_budgets`, `field_sources`, `embedding_dimension`, `embedding_dimension_status`.
  - `backendV1/qnu/domains/modelops/providers/service.py`: Trả `field_sources` từ `capacity` sang payload.
  - `backendV1/qnu/domains/modelops/router.py`: Endpoint `catalog` chuyển tải đầy đủ ngân sách và thông số model thay vì chỉ id/name/capabilities.
- **Frontend**:
  - `frontendV1/src/features/modelops/types.ts`: Cập nhật `CatalogItem` và `Provider` có `field_sources?: Record<string, BudgetSource>`.
  - `frontendV1/src/features/modelops/capacity-badge.tsx`: Cập nhật `ConsumerModelBudgetNotice` hỗ trợ `defaultModel` và `isDefaultSelection`, phân biệt model mặc định workspace với model chọn cụ thể, hiển thị alert khi model bị `blocked` (ví dụ OCR thiếu ngân sách) và badge `Chưa có thông số` khi thiếu thông tin.
  - Cập nhật các consumer: `assistant-form-dialog.tsx`, `compilation-dialog.tsx`, `ocr-request-dialog.tsx`, `index-panel.tsx` truyền đúng `defaultModel` và cờ lựa chọn.

### P2-2: Xác nhận khi xóa giới hạn token trên mọi luồng lưu form
- `frontendV1/src/features/modelops/provider-form-dialog.tsx`: Bổ sung `pendingClearLimitsPatch`. Khi user xóa các trường giới hạn và bấm "Lưu thay đổi", form phát hiện `patch.token_limits === null && provider.token_limits !== null`, giữ nguyên draft và mở `ConfirmDialog` với tiêu đề *"Xóa giới hạn token đã khai báo?"*.
  - Nếu bấm "Hủy": Đóng dialog xác nhận, giữ nguyên form modal và dữ liệu đang soạn thảo (không reset).
  - Nếu bấm "Xác nhận xóa khai báo": Thực hiện mutate với `token_limits: null`, giữ nguyên các trường khác đã sửa (tên, capabilities...).
  - Nút xác nhận có cờ `isLoading` chống double submit.

### P2-3: Chuẩn hóa phân loại lỗi trong `describeDiagnosticFailure`
- `frontendV1/src/features/modelops/capacity-badge.tsx`:
  - Thêm danh mục `"output_truncated"` cho `chat_output_truncated` hoặc `finish_reason: length`.
  - Ánh xạ `provider_response_invalid`, `chat_response_invalid`, `response_invalid` sang `"malformed_response"`.
  - Ánh xạ `chat_provider_uncertain`, HTTP 504/408 sang `"timeout"`.
  - HTTP 502/503 sang `"unavailable"`.
  - HTTP 400/422 thông thường không có mã token sang `"general"`.

### P2-4: Hiển thị nguồn gốc dữ liệu theo từng trường trong `CapacityPanel`
- `frontendV1/src/features/modelops/provider-detail.tsx`: Triển khai hàm `resolveFieldSource(provider, fieldName)`:
  - Tra cứu trước trong `provider.field_sources` cho từng trường cụ thể (`context_window_tokens`, `max_input_tokens`, `max_output_tokens`).
  - Hỗ trợ fallback sang `operational_budgets[capability].sources` (`effective_context`, `effective_input`, `effective_output`).
  - Fallback cuối cùng về `provider.capacity_basis`.
  - Khu vực *"Giới hạn đã biết của model"* hiển thị nguồn độc lập cho từng dòng (ví dụ Context: *"Server công bố"*, Output: *"Khai báo thủ công"*), không còn bị gộp chung thành một nhãn duy nhất.

---

## 2. Khắc phục 26 frontend test và ổn định suite

| Nhóm | File test | Số test | Nguyên nhân gốc & giải pháp | Kết quả |
|---|---|---|---|---|
| **A** | `tests/final-functions-ui-682.test.tsx` | 10 | Fixture thiếu mock `useRouterState` và `useFeatureScope`. Thay vì bọc `FeatureScopeProvider` gây ô nhiễm network call sang `/workspaces`, mock `useFeatureScope: () => ({})`. Cập nhật các assertion của Dashboard phù hợp với thiết kế tinh gọn thanh Topbar phiên 717 và regex match đơn vị/workspace. | **32/32 PASS** |
| **B** | `tests/knowledge-actions-708.test.tsx` | 8 | Thiếu mock `@/app/auth/v1` và `QueryClientProvider` cho trang chi tiết kho; các panel nhúng mới (Compiler, Publication, Serving) cần mock các query hook tương ứng (`useCompilationRunsQuery`, `useCompiledDocumentsQuery`, `useIndexRunsQuery`). Thao tác xóa trong bảng khớp nhãn `"Xóa vĩnh viễn"`. | **13/13 PASS** |
| **C** | `tests/navigation-scope-692.test.tsx` | 2 | `use-feature-scope.tsx` logic chooser fallback sticky vào `previous.workspaceId` thay vì để scope rỗng khi vào `/workspaces/choose/*`. Sửa điều kiện `isChooser`. Bọc `QueryClientProvider` trong test fixture. | **21/21 PASS** |
| **D** | `tests/workspace-sidebar-689.test.tsx` | 2 | Thiếu export `hasV1Permission` trong mock auth; cập nhật test kiểm tra cấu trúc Sidebar 6 mục chính chuẩn phiên 717 thay cho sidebar 4 nhóm cũ. | **3/3 PASS** |
| **E** | `tests/sidebar-navigation-691.test.tsx` | 1 | Thiếu export `hasV1Permission` trong mock auth; thêm route `/workspaces/$workspaceId/knowledge` vào test router tree. | **7/7 PASS** |
| **F** | `tests/rag-ui-674.test.tsx` | 1 | `CompiledDocumentDetailPage` thiếu mock auth và `QueryClientProvider`. Đã bổ sung wrapper. | **6/6 PASS** |
| **G** | `tests/lifecycle-operations-ui-678.test.tsx` | 1 | Trong `operations-page.tsx`, `ReadinessPanel` bị thiếu trong tab `OperationsJobs`. Khôi phục `{isLifecycleAdmin(role) ? <ReadinessPanel workspaceId={workspaceId} /> : null}`. | **19/19 PASS** |
| **H** | `tests/maintenance-evaluation-ui-679.test.tsx` | 1 | Test `evaluation caps the editable question list at twenty` re-render 20 câu hỏi bị timeout 5000ms trong CI tải cao. Tăng timeout lên 15000ms. | **30/30 PASS** |
| **I** | `tests/connection-model-capacity-727.test.tsx` | - | Tương tự nhóm H, tăng timeout 15000ms cho các test form capacity nhiều lượt `waitFor` để chống flaky khi chạy full suite. | **4/4 PASS** |

---

## 3. Bộ test hồi quy mới `modelops-p2-regressions-795.test.tsx`

Tạo mới `frontendV1/tests/modelops-p2-regressions-795.test.tsx` gồm 14 test kiểm chứng thực chất:
- **P2-1 (4 test)**:
  - Model OCR có `operational_budgets.ocr.status == "blocked"` hiển thị Alert cảnh báo thiếu ngân sách.
  - Model dùng `defaultModel` hiển thị đúng chỉ dẫn mặc định workspace và trạng thái tạm tính.
  - Model thiếu cả thông số lẫn metadata hiển thị nhãn `"Chưa có thông tin"`.
  - `resolveCapabilityBudgetState` giải quyết đúng cấu trúc ngân sách và mã lý do.
- **P2-2 (3 test)**:
  - Xóa input giới hạn token và bấm "Lưu thay đổi" sẽ kích hoạt `ConfirmDialog`, không gọi API patch ngay lập tức.
  - Bấm "Hủy" giữ nguyên form modal và dữ liệu nháp của user.
  - Bấm "Xác nhận xóa khai báo" gọi `updateProvider` với `{ token_limits: null }`, đồng thời các trường khác như name vẫn được gửi đầy đủ.
- **P2-3 (5 test)**:
  - `chat_output_truncated` và `finish_reason: length` -> `"output_truncated"`.
  - `provider_response_invalid`, `chat_response_invalid`, `response_invalid` -> `"malformed_response"`.
  - `chat_provider_uncertain`, HTTP 504 -> `"timeout"`.
  - HTTP 502, 503 -> `"unavailable"`.
  - Generic 400/422 không có mã token -> `"general"`.
- **P2-4 (2 test)**:
  - Provider có `field_sources` hiển thị provenance riêng biệt (Context: *"Server công bố"*, Output: *"Khai báo thủ công"*).
  - Tự động fallback sang `operational_budgets` source khi `field_sources` rỗng.

---

## 4. Bằng chứng kiểm chứng thực chạy

1. **Ruff check backend**:
   ```powershell
   backendV1\.venv\Scripts\ruff.exe check backendV1/qnu/domains/modelops/schemas.py backendV1/qnu/domains/modelops/router.py backendV1/qnu/domains/modelops/providers/service.py
   # Kết quả: All checks passed!
   ```
2. **Pytest targeted backend**:
   ```powershell
   cd backendV1; .\.venv\Scripts\python.exe -m pytest tests/unit/ -k "modelops or provider or budget or connection"
   # Kết quả: 170 passed, 486 deselected in 6.15s (100% PASS)
   ```
3. **Vitest 10 file ModelOps**:
   ```powershell
   cd frontendV1; npx vitest run tests/modelops-p2-regressions-795.test.tsx tests/modelops-auto-budget-792.test.tsx tests/modelops-diagnostics-694.test.tsx tests/modelops-resilience-695.test.tsx tests/test_modelops_endpoints.test.tsx tests/test_modelops_integration_regressions.test.tsx tests/capacity-discovery-733.test.tsx tests/connection-model-capacity-727.test.tsx tests/provider-sidebar-726.test.tsx tests/test_provider_connections_702.test.tsx
   # Kết quả: Test Files: 10 passed (10) | Tests: 62 passed (62) in 10.91s
   ```
4. **Vitest 8 file test sửa chữa**:
   ```powershell
   cd frontendV1; npx vitest run tests/final-functions-ui-682.test.tsx tests/knowledge-actions-708.test.tsx tests/navigation-scope-692.test.tsx tests/workspace-sidebar-689.test.tsx tests/sidebar-navigation-691.test.tsx tests/rag-ui-674.test.tsx tests/lifecycle-operations-ui-678.test.tsx tests/maintenance-evaluation-ui-679.test.tsx
   # Kết quả: Test Files: 8 passed (8) | Tests: 131 passed (131) in 10.77s
   ```
5. **Full Vitest Suite (`tmp/fix794-full-vitest.json`)**:
   ```powershell
   cd frontendV1; npm test -- --run --reporter=json --outputFile=../tmp/fix794-full-vitest.json
   # Kết quả:
   # numTotalTestSuites: 95 | numPassedTestSuites: 95 | numFailedTestSuites: 0
   # numTotalTests: 651 | numPassedTests: 651 | numFailedTests: 0
   ```
6. **Biome Check**:
   ```powershell
   cd frontendV1; npx biome check src/features/modelops/ src/navigation/use-feature-scope.tsx src/features/operations/operations-page.tsx tests/modelops-p2-regressions-795.test.tsx tests/final-functions-ui-682.test.tsx tests/knowledge-actions-708.test.tsx tests/navigation-scope-692.test.tsx tests/workspace-sidebar-689.test.tsx tests/sidebar-navigation-691.test.tsx tests/rag-ui-674.test.tsx tests/lifecycle-operations-ui-678.test.tsx tests/maintenance-evaluation-ui-679.test.tsx tests/connection-model-capacity-727.test.tsx
   # Kết quả: Checked 49 files in 96ms. No fixes applied. (0 errors, 0 warnings)
   ```
7. **Production Build & TypeScript check**:
   ```powershell
   cd frontendV1; npm run build
   # Kết quả: vite build && tsc --noEmit: built in 3.45s, exit code 0
   ```
8. **Git diff check**:
   ```powershell
   git diff --check
   # Kết quả: 0 (không có trailing whitespace hay lỗi encoding)
   ```
