# Phiên792 — Frontend ModelOps: thêm model không bắt nhập giới hạn token và hiển thị ngân sách vận hành

Ngày 01/11/2026. Người dùng yêu cầu triển khai FE ModelOps trong `frontendV1/` theo `docs/ke_hoach/PROMPT_FE_MODELOPS_TU_DONG_791.md` (tiếp nối BE phiên791). Không sửa backend, DB hoặc phiên E2E đang chạy.

## 1. Mục tiêu và Phương pháp

Người dùng có thể thêm nhà cung cấp bằng tên, URL, API key được bảo vệ, chọn từ danh sách khám phá hoặc tự nhập tên model và năng lực (`chat`, `embedding`, `rerank`, `ocr`) mà không bắt buộc nhập `context_window_tokens`, `max_input_tokens`, `max_output_tokens`. Model chưa công bố thông số vẫn được lưu và dùng ngân sách vận hành tạm tính (`operational_budgets`) do backend quyết định.

Phân biệt rạch ròi giữa **Giới hạn đã biết của model** (`token_limits`, `capacity_status`, `capacity_basis`) và **Ngân sách đang áp dụng** (`operational_budgets`):
- Không gửi `0`, `null` giả hay biến ngân sách tạm tính (`provisional`) thành khai báo tay (`token_limits`) khi chỉnh sửa.
- Không hiển thị `"Đã kiểm chứng"` khi chỉ mới khám phá hoặc khai báo tay chưa có bằng chứng thực thi.
- Gom các trường giới hạn token thủ công vào mục `"Nâng cao"` mặc định thu gọn; thêm hành động `"Xóa khai báo giới hạn"` có `ConfirmDialog` gửi `PATCH { token_limits: null }`.
- Với `import-models-dialog`, chỉ gửi `discovery_check_id` khi dòng model thực sự có thông số khám phá (`context_window_tokens`, `max_output_tokens` hoặc `embedding_dimension`); model chỉ có tên vẫn cho chọn và tạo với ngân sách tự động; hỗ trợ thêm model tùy chỉnh ngay trong hộp thoại.
- Tuân thủ UI standards: gom thao tác phụ từng model con vào 1 menu `⋯` (`DropdownMenu`), thay `window.confirm` bằng `ConfirmDialog`, bỏ double-border, ẩn ID kỹ thuật nội bộ (`prv_...`) khỏi thẻ/subtitle/select.

## 2. Các File Đã Sửa / Tạo Mới (`frontendV1/`)

1. `src/features/modelops/types.ts`: Thêm `CapacityBasis`, `BudgetSource`, `OperationalBudgetStatus`, `OperationalBudget` và `operational_budgets?: Partial<Record<Capability, OperationalBudget>>` trên `Provider` và `CatalogItem`.
2. `src/features/modelops/capacity-badge.tsx`: Thêm `BUDGET_STATUS_LABELS`, `BUDGET_SOURCE_LABELS`, `formatTokenLimitValue` (hiển thị `"Chưa công bố"` hoặc `${n} token`), `describeBudgetReason`, `resolveCapabilityBudgetState`, `OperationalBudgetBadge`, `ProviderOperationalBudgetsSummary`, `ConsumerModelBudgetNotice` và `describeDiagnosticFailure` (phân loại lỗi 429/Quota, vượt ngân sách token, sai định dạng phản hồi, timeout, xác thực).
3. `src/features/modelops/connections/api.ts`: Thêm `model_metadata?: DiscoveredModel[]` vào `ConnectionTestResult`, `ConnectionModelCreateInput` và `buildConnectionModelPayload` (chặn gửi đồng thời `discovery_check_id` và `token_limits`/`embedding_dimension` thủ công; lược bỏ trường `null`/`undefined`).
4. `src/features/modelops/capacity-patch.ts`: Thêm `hasManualCapacityDraft` và `buildClearTokenLimitsPatch` (`{ token_limits: null }`); đảm bảo `draftFromProvider` chỉ đọc `provider.token_limits`, không chép `operational_budgets`.
5. `src/features/modelops/connections/model-form.tsx`: Thu gọn phần nhập thông số vào mục `"Nâng cao"` (`aria-expanded`), hỗ trợ chọn model từ kết quả khám phá hoặc tự nhập tên model khi khám phá lỗi, kiểm tra hợp lệ qua `validateCapacityDraft`.
6. `src/features/modelops/provider-form-dialog.tsx`: Thu gọn giới hạn token vào mục `"Nâng cao"`, đổi placeholder sang `"Chưa công bố"`, thêm nút `"Xóa khai báo giới hạn"` kèm `ConfirmDialog` gửi `{ token_limits: null }`.
7. `src/features/modelops/connections/import-models-dialog.tsx`: Thêm `hasDiscoveredCapacity(row)` để chỉ đính kèm `discovery_check_id` khi server thực sự trả thông số; cho phép chọn model không kèm metadata để lưu với ngân sách tạm tính; thêm khu vực nhập model tùy chỉnh.
8. `src/features/modelops/provider-detail.tsx`: Cập nhật `CapacityPanel` tách rõ 2 khối **"Giới hạn đã biết của model"** và **"Ngân sách đang áp dụng"**, hiển thị nguồn từng trường (`sources`), đơn vị `token`, và nút `"Xóa khai báo giới hạn"` có `ConfirmDialog`; bỏ `provider.id` nội bộ ở subtitle.
9. `src/features/modelops/connections/model-test-modal.tsx` & `src/features/modelops/diagnostics-panel.tsx`: Tích hợp `describeDiagnosticFailure`, hiển thị cảnh báo `configuration_status === "stale"`, và làm rõ khi probe `"ok"` rằng lượt thử ngắn không xác minh trần token tối đa hay nâng ngân sách tạm tính thành đã kiểm chứng.
10. `src/features/modelops/connections/connection-detail.tsx`, `src/features/modelops/providers-table.tsx`, `src/features/modelops/provider-card-grid.tsx`: Hiển thị `CapacityBadge` + `ProviderOperationalBudgetsSummary`, gom hành động phụ vào menu `⋯`, mở modal xem/đồng bộ `CapacityPanel`, dùng `ConfirmDialog` khi xóa, bỏ viền lồng nhau và ẩn `provider.id`.
11. Consumers (`src/features/modelops/defaults-page.tsx`, `src/features/assistants/assistant-form-dialog.tsx`, `src/features/compilation/compilation-dialog.tsx`, `src/features/compilation/compilation-schemas.ts`, `src/features/sources/ocr-request-dialog.tsx`, `src/features/sources/ocr-schemas.ts`, `src/features/indexing/index-panel.tsx`): Hiển thị `ConsumerModelBudgetNotice` theo capability, ẩn `p.id` trong select OCR, và bổ sung thông điệp lỗi thân thiện cho lỗi ngân sách/kích thước/trạng thái model.
12. `tests/modelops-auto-budget-792.test.tsx`: Thêm 10 bài test bao phủ toàn bộ 15 nhóm yêu cầu trong prompt FE.

## 3. Kiểm Chứng Thực Chạy

Thực hiện tại `frontendV1/`:

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Bộ test mới (10 kịch bản) | `npm test -- --run tests/modelops-auto-budget-792.test.tsx` | **PASS** (10/10 passed) |
| Toàn bộ 10 file test ModelOps (53 tests) | `npm test -- --run tests/modelops-diagnostics-694.test.tsx tests/modelops-auto-budget-792.test.tsx tests/connection-model-capacity-727.test.tsx tests/capacity-discovery-733.test.tsx tests/test_connection_review_705.test.tsx tests/modelops-resilience-695.test.tsx tests/test_provider_connections_702.test.tsx tests/connection-key-modal-payload.test.tsx tests/test_modelops_endpoints.test.tsx tests/connection-test-request-706.test.tsx` | **PASS** (10 files, 53/53 passed; đã khắc phục luôn 7 lỗi cũ ở `test_connection_review_705.test.tsx`) |
| Typecheck & Production Build | `npm run build` (`vite build && tsc --noEmit`) | **PASS** (exit 0, 5.04s) |
| Biome Format & Lint (21 file chạm tới) | `npx biome check ...` | **PASS** (21 files checked, 0 errors, 0 warnings) |
| Full Vitest suite toàn `frontendV1` | `npm test -- --run` | **FAIL nền** (`611 PASS / 26 FAIL`, giảm 7 lỗi so với baseline `594 PASS / 33 FAIL` của phiên790 do `test_connection_review_705.test.tsx` đã xanh) |

26 lỗi còn lại trong full suite thuộc các cụm UI/fixture ngoài phạm vi ModelOps (`test_knowledge_703`, `test_ui_standards_706`, `workspace-Access-640`, `document-viewer-bounding-box`, `pdf-bounding-box`, `chunk-navigator`, `status-cell-badge`, `sidebar-navigation-badges`, `error-state-retry`).

## 4. Giới Hạn và Bàn Giao

- Không sửa `backendV1/`, DB, cấu hình ModelOps đang chạy hoặc phiên E2E `93faa11f0caf`.
- Không restart dịch vụ, không gọi model thật, không thêm thư viện UI hay sửa `routeTree.gen.ts`.
- Về yêu cầu người dùng gửi kèm ảnh chụp màn hình liên quan đến 3 điểm sửa RAG/E2E và chạy lại 19 câu: đã đối chiếu lịch sử dự án (Phiên762–764 và Phiên788–791) để báo cáo rõ trạng thái từng điểm và xác nhận trước khi chạy bất kỳ lượt live model nào.
