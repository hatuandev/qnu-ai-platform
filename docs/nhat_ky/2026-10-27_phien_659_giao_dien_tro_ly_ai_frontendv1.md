# Nhật ký phiên 659 — Triển khai Giao diện Quản lý Trợ lý AI (frontendV1)

- **Thời gian**: 2026-10-27
- **Mục tiêu**: Triển khai toàn diện giao diện quản lý Trợ lý AI trong `frontendV1`, kết nối trực tiếp API `backendV1` hiện có (`/platform/v1alpha1/workspaces/{workspace_id}/assistants`); hỗ trợ luồng: Đăng nhập SSO → Workspace → Trợ lý AI → Tạo trợ lý → Gắn bộ sưu tập → Chọn model chat qua ModelOps catalog → Lưu → Xem/sửa cấu hình có kiểm tra revision → Bật/tắt an toàn.
- **Trạng thái**: Hoàn tất triển khai và kiểm chứng 100%. Toàn bộ test suite frontend 53/53 PASS (0 fail) trên 6 test files, Biome 0 error / 0 warning, TypeScript compiler typecheck PASS (0 error).

---

## 1. Khảo sát & Đối chiếu Contract BackendV1

1. **Khế ước API Trợ lý AI (`backendV1/qnu/domains/assistants/`)**:
   - `GET /platform/v1alpha1/workspaces/{workspace_id}/assistants`: Danh sách trợ lý trong workspace. Trả về mảng JSON `AssistantResponse[]` thuần túy, dùng tham số `limit` (1–100, mặc định 20) và `offset` (>= 0, mặc định 0). Tuyệt đối **không** có wrapper `{ items, meta }` hay trường tổng số bản ghi `total`.
   - `POST /platform/v1alpha1/workspaces/{workspace_id}/assistants`: Tạo mới trợ lý với đầy đủ cấu hình.
   - `GET /platform/v1alpha1/workspaces/{workspace_id}/assistants/{assistant_id}`: Xem thông tin chi tiết trợ lý độc lập.
   - `PUT /platform/v1alpha1/workspaces/{workspace_id}/assistants/{assistant_id}`: Cập nhật toàn bộ cấu hình, bắt buộc gửi `expected_revision` (số nguyên >= 1). Trả mã `409 assistant_revision_conflict` nếu revision không khớp; trả `409 assistant_collection_immutable` nếu client cố tình thay đổi `collection_id`.
   - **Không có** endpoint `PATCH` hoặc `DELETE` assistant trong router hiện tại.
2. **Quy tắc Schema & Validation (`AssistantConfig`)**:
   - `name`: Chuỗi bắt buộc, đã trim, không rỗng, độ dài 1–160 ký tự.
   - `description`: Chuỗi, mặc định `""`, tối đa 2000 ký tự (không dùng `null` để xóa mô tả vì schema backend là string).
   - `persona`: Chuỗi, mặc định `""`, tối đa 4000 ký tự (không dùng `null` để xóa persona).
   - `collection_id`: Chuỗi bắt buộc, độ dài 1–64 ký tự. Khi sửa, trường này là **bất biến**.
   - `chat_provider_id`: Chuỗi (1–64 ký tự) hoặc `null`. Giá trị `null` mang ý nghĩa "Theo mặc định workspace" (backend tự động phân giải provider chat mặc định).
   - `top_k`: Số nguyên 1–20, mặc định 5.
   - `history_turns`: Số nguyên 0–10, mặc định 3.
   - `max_output_tokens`: Số nguyên dương, mặc định schema 2048 (giá trị cấu hình tác vụ, không phải capacity cứng của model).
   - `is_active`: Boolean, mặc định `true`.
   - Response bổ sung: `id`, `workspace_id`, `revision`, `created_by`, `created_at`, `updated_at`.
3. **Phân quyền thao tác**:
   - Chỉ người dùng có vai trò `admin` trong workspace hoặc Quản trị viên nền tảng (`ai.workspaces.manage`) mới được tạo, sửa cấu hình hoặc bật/tắt trợ lý.
   - Vai trò `editor` và `member` chỉ được xem danh sách và chi tiết, không được hiển thị thao tác ghi.
4. **Tích hợp ModelOps Catalog**:
   - Gọi `GET /platform/v1alpha1/modelops/catalog?workspace_id={workspaceId}` để lấy danh mục provider đã được cấp phép cho workspace.
   - Lọc các provider có `capabilities.includes("chat")`.
   - Lưu trữ `chat_provider_id`, tuyệt đối không lưu `model_name` thay ID.
   - Tùy chọn "Theo mặc định workspace" gán `chat_provider_id = null`.
   - Cảnh báo rõ ràng nếu cấu hình đang lưu trỏ tới provider không còn khả dụng trong catalog.

---

## 2. Các Thành Phần Đã Triển Khai trong `frontendV1`

### A. Mở rộng Endpoints & Client v1
- `src/app/api/v1/endpoints.ts`: Bổ sung `assistantPaths`:
  - `list: (workspaceId) => /workspaces/${workspaceId}/assistants`
  - `detail: (workspaceId, assistantId) => /workspaces/${workspaceId}/assistants/${assistantId}`
- `src/app/api/v1/index.ts`: Re-export `assistantPaths`.

### B. Module Trợ lý AI (`src/features/assistants/`)
- `types.ts`: Định nghĩa TypeScript interfaces chuẩn: `Assistant`, `AssistantCreateInput`, `AssistantUpdateInput`, `AssistantListParams`.
- `schemas.ts`: Zod validation schemas bám sát 100% Pydantic backend:
  - `assistantNameSchema`, `assistantDescriptionSchema`, `assistantPersonaSchema`, `collectionIdSchema`, `chatProviderIdSchema`, `topKSchema`, `historyTurnsSchema`, `maxOutputTokensSchema`, `isActiveSchema`, `expectedRevisionSchema`.
  - `assistantCreateSchema`, `assistantUpdateSchema`, `assistantFormSchema`, `assistantListSearchSchema`, và hằng số `DEFAULT_ASSISTANT_SEARCH`.
- `permissions.ts`: Triển khai `canManageAssistants(role: CallerWorkspaceRole)`: chỉ cấp quyền ghi cho `platform-admin` và workspace `admin`.
- `requests.ts`: Tầng gọi API chuẩn hóa:
  - `listAssistants`: Truy vấn danh sách mảng với `limit` và `offset`.
  - `getAssistant`: Lấy chi tiết một trợ lý.
  - `createAssistant`: Gửi payload tạo mới với name đã trim và các giá trị mặc định chuẩn.
  - `updateAssistant`: Gửi toàn bộ cấu hình kèm `expected_revision`.
- `queries.ts`: TanStack Query hooks:
  - Query keys gắn chặt `sessionId` và `workspaceId`: `['v1', sessionId, 'workspaces', workspaceId, 'assistants', ...]`.
  - Hỗ trợ `useAssistantsQuery`, `useAssistantQuery`, `useCreateAssistant`, `useUpdateAssistant`.
  - Tự động invalidate danh sách và chi tiết khi mutation thành công.
- `assistant-form-dialog.tsx`: Dialog/Drawer phản hồi tạo và sửa trợ lý:
  - Hỗ trợ form submit native cả bằng click chuột và phím Enter.
  - Tích hợp dropdown chọn bộ sưu tập từ `useCollectionsQuery` (với cảnh báo và link tạo nếu chưa có bộ sưu tập).
  - Ở chế độ sửa: `collection_id` bị khóa cứng (read-only), hiển thị badge "Bất biến" và thông báo "Muốn đổi bộ sưu tập, tạo trợ lý mới".
  - Tích hợp chọn model chat từ `useCatalogQuery(workspaceId)` lọc `capabilities.includes("chat")`, kèm lựa chọn "Theo mặc định workspace".
  - Hiển thị cảnh báo nếu provider lưu trữ không còn trong catalog.
  - Bắt lỗi HTTP 409 `assistant_revision_conflict`: giữ nguyên bản nháp (draft) của người dùng, hiển thị thông báo xung đột phiên bản và cung cấp nút "Tải lại dữ liệu mới nhất" để đối chiếu.
- `assistants-panel.tsx`: Bảng danh sách trợ lý:
  - Hiển thị tên, mô tả, bộ sưu tập liên kết, model chat, trạng thái bật/tắt, revision (`v{revision}`), thời gian cập nhật.
  - Toggle Switch bật/tắt trực tiếp: bảo toàn toàn bộ cấu hình gốc và gửi `expected_revision`.
  - Tìm kiếm client-side trung thực: thông báo "Đang lọc trên X/Y trợ lý trong phạm vi tải".
  - Phân trang offset/limit trung thực: nút "Trang trước" / "Trang sau", không bịa đặt tổng số bản ghi.
  - `EmptyState` khi chưa có trợ lý nào trong workspace.
- `assistant-detail-page.tsx`: Trang chi tiết độc lập:
  - Breadcrumbs điều hướng (`Workspace > Trợ lý AI > [Tên trợ lý]`), nút quay lại, nút sao chép Assistant ID.
  - Các thẻ section rõ ràng: Tổng quan metadata, Kho tri thức gắn kết (kèm link tới trang bộ sưu tập), Cấu hình Model Chat (kèm link tới trang ModelOps của workspace), Chỉ dẫn hệ thống / Persona (có nút copy), Tham số phản hồi & RAG (`top_k`, `history_turns`, `max_output_tokens`).
  - Thẻ Điều kiện cấu hình trung thực: xác nhận cấu hình bộ sưu tập và model, ghi rõ nhãn "Chưa kiểm tra runtime" cho các điều kiện suy luận thực tế (không tạo đèn "Sẵn sàng chat" giả).

### C. Điều hướng & Routing
- Thêm tab "Trợ lý AI" vào `TABS` trong `src/features/workspaces/workspace-detail-layout.tsx` trỏ tới `/workspaces/$workspaceId/assistants`.
- Tạo 2 route file-based TanStack Router:
  - `src/routes/workspaces.$workspaceId.assistants.index.tsx`
  - `src/routes/workspaces.$workspaceId.assistants.$assistantId.tsx`
- Sinh lại `src/routeTree.gen.ts` sạch sẽ thông qua `@tanstack/router-generator`.
- Cập nhật ranh giới `V1_DIRECTORIES` trong `tests/template-boundary.test.ts` bổ sung `"features/assistants/"`.

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Unit & Regression Suite (`bun test`)**:
   - `tests/v1-assistants.test.ts` (MỚI): 10/10 test cases PASS.
     - Kiểm tra khế ước danh sách mảng với `limit` và `offset`, không có Page wrapper.
     - Kiểm tra tạo trợ lý gửi đầy đủ cấu hình với tên được trim và default string.
     - Kiểm tra cập nhật trợ lý gửi đầy đủ field và `expected_revision`.
     - Kiểm tra toggle bật/tắt bảo toàn toàn bộ cấu hình gốc và gửi `expected_revision`.
     - Kiểm tra xử lý lỗi 409 revision conflict khi revision không khớp.
     - Kiểm tra backend từ chối 409 khi cố tình đổi `collection_id`.
     - Kiểm tra phân quyền: admin và platform-admin được tạo/sửa; editor và member chỉ đọc.
     - Kiểm tra validation Zod cho các trường bắt buộc, giới hạn số và kiểu dữ liệu.
     - Kiểm tra cô lập query keys theo `sessionId` và `workspaceId`.
     - Kiểm tra API lấy chi tiết trợ lý theo ID.
   - `tests/template-boundary.test.ts`: 5/5 PASS (KTX boundary giữ nguyên 100%).
   - `tests/v1-knowledge.test.ts`: 7/7 PASS.
   - `tests/v1-contract.test.ts`: 14/14 PASS.
   - `tests/v1-session-secret-regression.test.ts`: 7/7 PASS.
   - `tests/v1-sso.test.ts`: 10/10 PASS.
   - **Tổng cộng: 53 passed, 0 failed trên toàn bộ 6 test files (100% PASS)**.
2. **TypeScript Typecheck (`tsc --noEmit`)**:
   - 0 errors (PASS hoàn toàn).
3. **Biome Linter & Formatter (`biome check`)**:
   - 16 files checked: 0 errors, 0 warnings (PASS hoàn toàn).

---

## 4. Các Giới Hạn & Phạm Vi Chưa Triển Khai (Theo Yêu Cầu)
- **Hội thoại & Chat**: Chưa triển khai giao diện chat, tin nhắn, streaming SSE, hoặc lịch sử hội thoại (thuộc giai đoạn tiếp theo; không tạo nút "Chat thử" giả).
- **Chia sẻ & Widget**: Chưa có widget nhúng, public chatbot, hoặc link chia sẻ ra ngoài.
- **Tools, Workflow, Guardrails**: Giữ nguyên schema hiện tại của `backendV1`, không tự ý thêm các trường cấu hình chưa hỗ trợ.
- **Đánh giá / Benchmark / Run thử**: Không gọi inference trả phí hay tự sinh hội thoại để đánh giá chất lượng trong màn hình quản trị cấu hình.
- **Xóa / Clone trợ lý**: Backend hiện tại chưa có endpoint `DELETE` hay clone; giao diện không thêm các hành động chưa có API hỗ trợ.
