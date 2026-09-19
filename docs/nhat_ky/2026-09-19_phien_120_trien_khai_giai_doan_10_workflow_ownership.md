# NHẬT KÝ PHIÊN LÀM VIỆC #120
**Thời gian:** 2026-09-19 19:15  
**Mục tiêu:** Hoàn thiện Giai đoạn 10: Workflow Ownership & Publish Consistency (Đợt 3 Kế hoạch 06).

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Trước Giai đoạn 10, các Trợ lý AI (như Tuyển sinh, Quy chế, Khảo thí,...) cùng trỏ chung vào các `WorkflowDefinition` mẫu mutable (ví dụ `admissions-assistant`). Khi một cán bộ chỉnh sửa node hoặc xuất bản một phiên bản workflow mới, tất cả các trợ lý khác đang dùng chung workflow đó đều bị ảnh hưởng ngay lập tức mà không có sự cô lập, đồng thời không có cơ chế ghim bất biến phiên bản workflow đã xuất bản của từng trợ lý.

Giai đoạn 10 giải quyết triệt để vấn đề này với 5 trụ cột:
1. **Private Workflow Binding**: Khi tạo mới Assistant (`workflow_ownership == "private"` mặc định), hệ thống tự động fork một Workflow riêng biệt (`wf_ast_{code}`) với `ownership="private"` và `assistant_id=record.id`.
2. **Clone Assistant Fork Workflow**: Khi nhân bản Assistant, checkbox `fork_workflow` (mặc định `true`) tự động fork workflow của source thành một workflow riêng cho bản sao.
3. **Pin Bất Biến Khi Publish**: Khi xuất bản Assistant (`POST /assistants/{ref}/publish`), hệ thống tự động ghim `published_workflow_version_id` bất biến vào bản ghi của Assistant và lưu vào snapshot version.
4. **Rollback Toàn Vẹn**: Khôi phục phiên bản Assistant sẽ khôi phục chính xác cả cấu hình 7 lớp lẫn DAG version tương ứng trong snapshot.
5. **Cảnh Báo Shared Workflow & Tách Riêng**: Bổ sung API audit usage (`GET /workflows/definitions/{id}/assistants`) và endpoint fork (`POST /assistants/{id}/fork-workflow`); trên UI hiển thị cảnh báo khi workflow có $>1$ Assistant và cung cấp nút **[Tách thành quy trình riêng]**.

---

## 2. Các Tệp Tin Đã Chỉnh Sửa / Tạo Mới

| Tệp | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- |
| `backend/app/modules/assistants/models.py` | Cập nhật | Bổ sung `published_workflow_version_id` (String 120, nullable) và `workflow_ownership` (String 30, default "private"). |
| `backend/app/modules/workflows/models.py` | Cập nhật | Bổ sung `ownership` (String 30, default "shared") và `assistant_id` (String 120, nullable, foreign key logical). |
| `backend/app/modules/assistants/schemas.py` | Cập nhật | Cập nhật DTO `AssistantCreateRequest`, `AssistantUpdateRequest`, `AssistantResponse`, `AssistantCloneRequest`, và bổ sung `AssistantForkWorkflowResponse`. |
| `backend/app/modules/workflows/schemas.py` | Cập nhật | Bổ sung `workflow_version_id` vào `WorkflowExecuteRequest`, `ownership` + `assistant_id` vào `WorkflowDefinitionResponse`, và thêm `WorkflowAssistantsUsageResponse`. |
| `backend/app/modules/workflows/service.py` | Cập nhật | Bổ sung `get_workflow_assistants`, `fork_workflow`, và cập nhật `execute` ưu tiên phân giải `req.workflow_version_id` trước khi fallback. |
| `backend/app/modules/workflows/router.py` | Cập nhật | Thêm endpoint `GET /definitions/{workflow_id}/assistants` trả về danh sách và số lượng trợ lý đang gắn kết. |
| `backend/app/modules/assistants/service.py` | Cập nhật | Cập nhật `create_assistant` (tự động fork private workflow), `clone_assistant` (hỗ trợ fork_workflow), `publish_assistant` (pin version vào assistant & snapshot), `rollback_version` (khôi phục workflow version & ownership), thêm `fork_workflow`, và cập nhật `chat`/`chat_stream` truyền `workflow_version_id`. |
| `backend/app/modules/assistants/router.py` | Cập nhật | Thêm endpoint `POST /platform/v1alpha1/assistants/{reference}/fork-workflow`. |
| `backend/tests/test_assistant_workflow_ownership.py` | Tạo mới | Suite kiểm thử 7 test cases bao phủ toàn bộ luồng sở hữu, nhân bản, ghim version, rollback, audit usage, và runtime execution. |
| `frontend/src/types/assistants.ts` | Cập nhật | Bổ sung các trường `published_workflow_version_id`, `workflow_ownership`, `fork_workflow`, và `AssistantForkWorkflowResponse`. |
| `frontend/src/types/workflows.ts` | Cập nhật | Bổ sung `WorkflowAssistantsUsageItem` và `WorkflowAssistantsUsageResponse`. |
| `frontend/src/services/assistants-api.ts` | Cập nhật | Bổ sung API method `forkAssistantWorkflow(reference)`. |
| `frontend/src/services/workflows-api.ts` | Cập nhật | Bổ sung trường `ownership` + `assistant_id` vào `WorkflowDefinition` và method `getWorkflowAssistants(workflowId)`. |
| `frontend/src/services/api-client.ts` | Cập nhật | Re-export `workflowsApi` trong facade `apiClient`. |
| `frontend/src/components/assistants/sections/assistant-tools-section.tsx` | Cập nhật | Hiển thị badge quyền sở hữu (Riêng tư/Dùng chung), thông tin phiên bản ghim, và nút [Tách thành quy trình riêng]. |
| `frontend/src/components/assistants/dialogs/assistant-clone-dialog.tsx` | Cập nhật | Thêm checkbox toggle cho phép chọn tách riêng quy trình xử lý khi nhân bản trợ lý. |
| `frontend/src/pages/assistant-detail-page.tsx` | Cập nhật | Tích hợp mutation tách quy trình `forkWorkflowMutation` và truyền xuống form/dialog. |
| `frontend/src/pages/dag-canvas-page.tsx` | Cập nhật | Hiển thị badge quyền sở hữu trên Topbar và Banner cảnh báo màu hổ phách khi workflow dùng chung cho nhiều trợ lý. |

---

## 3. Kết Quả Kiểm Thử (Verification)

- **Backend Pytest**:
  - `tests/test_assistant_workflow_ownership.py`: 7/7 passed (100%).
  - Toàn bộ suite assistants & workflows: 54/54 passed (100%).
- **Backend Ruff Linter**:
  - `uv run ruff check .`: 0 lỗi, All checks passed.
- **Frontend Biome Linter**:
  - `npm run lint`: 0 lỗi trên 157 files.
- **Frontend Typecheck**:
  - `npm run typecheck`: 0 lỗi (`tsc --noEmit`).
- **Zero Mojibake Check**:
  - `python scripts/check_mojibake.py`: 313/313 tệp sạch 100%, không phát hiện bất kỳ ký tự rác nào.
