# Nhật ký phiên 661 — Triển khai Chức năng Chat với Trợ lý AI (frontendV1)

- **Thời gian**: 2026-10-27
- **Mục tiêu**: Triển khai chức năng Chat với Trợ lý AI trong `frontendV1`, kết nối API thật của `backendV1` qua prefix `/platform/v1alpha1/workspaces/{workspace_id}/conversations`; hoàn thành trọn vẹn luồng: Chọn trợ lý → tạo hội thoại → gửi câu hỏi → nhận kết quả đồng bộ → xem dẫn nguồn trích đoạn → mở lại lịch sử.
- **Trạng thái**: Hoàn tất triển khai và kiểm chứng 100%. Toàn bộ test suite frontend 64/64 PASS (0 fail) trên 7 test files, Biome 0 error / 0 warning trên 20 tệp v1, TypeScript compiler `tsc --noEmit` PASS (0 error).

---

## 1. Khảo sát & Đối chiếu Contract BackendV1

1. **Khế ước API Hội thoại & Lượt hỏi (`backendV1/qnu/domains/conversations/`)**:
   - `POST /platform/v1alpha1/workspaces/{workspace_id}/conversations`: Mở cuộc trò chuyện mới (`assistant_id`, `title`). Backend tự xác định `owner_ref`, `assistant_snapshot`, `collection_id` và gán `last_turn_no = 0`.
   - `GET /platform/v1alpha1/workspaces/{workspace_id}/conversations`: Danh sách hội thoại của chính actor đăng nhập trong workspace (mảng thuần `ConversationResponse[]`, limit/offset, sắp xếp `updated_at` giảm dần). Tuyệt đối **không** có wrapper `{ items, meta }` hay trường `total`.
   - `GET /platform/v1alpha1/workspaces/{workspace_id}/conversations/{conversation_id}`: Chi tiết hội thoại (lấy `last_turn_no`, `status`, `assistant_revision`).
   - `PUT /platform/v1alpha1/workspaces/{workspace_id}/conversations/{conversation_id}`: Cập nhật tiêu đề và trạng thái (`title` 1–160 ký tự, `status` "active" | "archived"). Khi đổi tên giữ nguyên status; khi lưu trữ/mở lại giữ nguyên title.
   - `POST /platform/v1alpha1/workspaces/{workspace_id}/conversations/{conversation_id}/turns`: Gửi lượt hỏi. Bắt buộc header `Idempotency-Key` (1–128 ký tự, regex `^[A-Za-z0-9_.:-]+$`). Body: `{ question, expected_turn_no }` (câu hỏi trim 1–8000 ký tự; `expected_turn_no` lấy từ `conversation.last_turn_no`).
   - `GET /platform/v1alpha1/workspaces/{workspace_id}/conversations/{conversation_id}/turns`: Lịch sử các lượt hỏi (mảng thuần `TurnResponse[]`, limit/offset, sắp xếp `turn_no` tăng dần).
   - `GET /platform/v1alpha1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}`: Trạng thái và kết quả của một lượt hỏi.
2. **Quy tắc Nghiệp vụ, Sequence & Idempotency**:
   - **Quyền Chat**: Khác với quyền quản lý trợ lý (cần admin), bất kỳ thành viên hợp lệ nào trong workspace đều có quyền chat với trợ lý đang hoạt động (`is_active: true`). Hội thoại chỉ thuộc chính actor; platform admin cũng không tự đọc chat của người khác.
   - **Xác định lượt hỏi**: `expected_turn_no` bắt buộc lấy từ `conversation.last_turn_no`, tuyệt đối không suy đoán từ số lượng turn đang nạp ở client.
   - **Quản lý Khóa Idempotency**: Mỗi thao tác gửi mới tạo một UUID v4. Nếu thử lại cùng một thao tác do lỗi mạng, **giữ nguyên** key, question và `expected_turn_no`.
   - **Chặn Double Submit**: Khóa form khi đang gửi (`isPending`), mutation không tự động retry ngầm. Chỉ cho phép duy nhất một lượt hỏi chạy trên mỗi hội thoại.
   - **Xử lý Đồng bộ (NO Streaming)**: Backend hiện trả JSON đồng bộ; không thêm SSE/WebSocket hay hiệu ứng gõ chữ giả. Khi turn `status === "running"`, thực hiện polling có giới hạn (khoảng 2s/lần, tối đa 15 lần) và dọn sạch timer khi rời trang hoặc đổi phiên.
   - **Dẫn nguồn Bằng chứng (`CitationSheet`)**: Trích xuất mệnh đề `statements` kèm nút dẫn nguồn mở Sheet hiển thị chi tiết `EvidenceSource` (`chunk_id`, `document_id`, `version_id`, tọa độ trang/bảng/mục, score). Nếu metadata thiếu, hiển thị "Không có thông tin", không tự suy đoán.
   - **Xử lý Nguồn Thu hồi**: Khi `source_status === "unavailable"` hoặc `result === null`, loại bỏ kết quả cũ khỏi màn hình và hiển thị cảnh báo nguồn không còn khả dụng.
   - **Kết quả `insufficient_evidence`**: Xử lý riêng biệt với các lý do `no_eligible_content`, `no_match`, `model_abstained`; không coi lỗi hạ tầng/provider là "không có dữ liệu".

---

## 2. Các Thành Phần Đã Triển Khai trong `frontendV1`

### A. Mở rộng Endpoints & Client v1
- `src/app/api/v1/endpoints.ts`: Bổ sung `conversationPaths`:
  - `list: (workspaceId) => /workspaces/${workspaceId}/conversations`
  - `detail: (workspaceId, conversationId) => /workspaces/${workspaceId}/conversations/${conversationId}`
  - `turns: (workspaceId, conversationId) => /workspaces/${workspaceId}/conversations/${conversationId}/turns`
  - `turn: (workspaceId, conversationId, turnId) => /workspaces/${workspaceId}/conversations/${conversationId}/turns/${turnId}`
- `src/app/api/v1/index.ts`: Re-export `conversationPaths`.

### B. Module Hội thoại & Chat (`src/features/conversations/`)
- `types.ts`: Định nghĩa TypeScript interfaces chuẩn: `Conversation`, `ConversationCreateInput`, `ConversationUpdateInput`, `TurnResponse`, `TurnRequestInput`, `Statement`, `EvidenceSource`, `AnswerResponse`, `AnswerTrace`, `SourceStatus`.
- `schemas.ts`: Zod validation schemas bám sát Pydantic backend:
  - `conversationTitleSchema`: trim, 1–160 ký tự.
  - `conversationStatusSchema`: "active" | "archived".
  - `conversationCreateSchema`, `conversationUpdateSchema`.
  - `turnQuestionSchema`: trim, 1–8000 ký tự.
  - `expectedTurnNoSchema`: số nguyên >= 0.
  - `turnRequestSchema`: `{ question, expected_turn_no }`.
  - `conversationListSearchSchema`: limit/offset pagination.
  - `generateIdempotencyKey()`: sinh UUID v4 chuẩn.
  - `formatConversationError()`: ánh xạ trung thực các mã lỗi RFC 7807 (`conversation_busy`, `conversation_sequence_conflict`, `idempotency_conflict`, `conversation_assistant_changed`, `assistant_inactive`, `conversation_archived`, `answer_evidence_changed`,...).
- `requests.ts`: Tầng gọi API chuẩn hóa: `listConversations`, `getConversation`, `createConversation`, `updateConversation`, `listTurns`, `getTurn`, `sendTurn` (truyền `Idempotency-Key` qua header).
- `queries.ts`: TanStack Query hooks với query keys cô lập theo `['v1', sessionId, 'workspaces', workspaceId, 'conversations', ...]`:
  - `useConversationsQuery`, `useConversationQuery`, `useTurnsQuery`, `useTurnQuery`, `useCreateConversation`, `useUpdateConversation`, `useSendTurn`.
  - Invalidate và refresh metadata chính xác sau khi gửi turn để `last_turn_no` luôn đồng bộ.
- `conversation-create-dialog.tsx`: Dialog tạo cuộc trò chuyện mới, cho phép chọn trợ lý AI đang hoạt động (hoặc tự động nhận trợ lý được ghim trước), nhập tiêu đề, tự động điều hướng vào trang chat sau khi tạo.
- `conversation-rename-dialog.tsx`: Dialog đổi tên cuộc trò chuyện, bảo toàn nguyên vẹn trường `status`.
- `citation-sheet.tsx`: Radix Sheet hiển thị chi tiết bằng chứng dẫn nguồn: mệnh đề trích xuất, danh sách các nguồn liên kết (`evidence_id`, `chunk_id`, `document_id`, `version_id`), tọa độ trang/bảng biểu ("Không có thông tin" nếu thiếu), điểm tương đồng (score), và khối đọc nội dung trích đoạn rõ ràng.
- `chat-message-item.tsx`: Component hiển thị một lượt hỏi-đáp:
  - Phía người dùng: bong bóng câu hỏi, số thứ tự lượt `#turn_no`, thời điểm gửi, thông tin làm rõ câu hỏi nếu có.
  - Phía trợ lý:
    - `running`: spinner trung thực "Trợ lý đang tìm kiếm tài liệu và tổng hợp câu trả lời..." (không fake gõ chữ).
    - `completed`: hiển thị các mệnh đề `statements` kèm nút dẫn nguồn bấm mở `CitationSheet`, thông tin trace (model, token) nếu có.
    - `insufficient_evidence`: banner màu cảnh báo giải thích rõ lý do (`no_eligible_content`, `no_match`, `model_abstained`).
    - `failed`: banner báo lỗi kèm mã lỗi và nút "Thử lại với cùng khóa".
    - `uncertain`: cảnh báo lượt hỏi quá hạn lease.
    - `source_status === "unavailable"`: cảnh báo nguồn đã thay đổi hoặc không còn khả dụng, ẩn câu trả lời cũ.
- `chat-view.tsx`: Giao diện trò chuyện chính:
  - Header: tiêu đề, liên kết tới trợ lý AI, badge trạng thái, menu hành động (đổi tên, lưu trữ / mở lại).
  - Khung tin nhắn cuộn tự động chỉ khi người dùng đang ở gần đáy (không kéo giật màn hình khi đang đọc lịch sử).
  - Nút "Tải các lượt trước đó" hỗ trợ phân trang đúng chiều lịch sử.
  - Ô nhập câu hỏi: `Textarea` tự động co giãn, Enter để gửi, Shift+Enter xuống dòng, kiểm tra IME composition; vô hiệu hóa khi hội thoại đã lưu trữ hoặc trợ lý tạm dừng; hiển thị bộ đếm ký tự.
  - Quản lý `expected_turn_no` và `Idempotency-Key` chặt chẽ, hỗ trợ thử lại đúng lượt hỏi cũ.
- `conversations-sidebar.tsx`: Thanh danh sách hội thoại bên trái:
  - Ô tìm kiếm client-side nhanh theo tiêu đề.
  - Lọc theo tab "Tất cả", "Đang mở", "Lưu trữ".
  - Phân trang offset/limit trung thực.
  - Thao tác nhanh đổi tên, lưu trữ / mở lại.
- `conversations-page.tsx`: Khung Master-Detail liên kết Sidebar và ChatView; tự động co giãn hiển thị danh sách trên mobile khi chưa chọn hội thoại và hiển thị toàn màn hình chat khi có `conversationId`.
- `assistant-detail-page.tsx`: Bổ sung nút **"Trò chuyện"** nổi bật trong header chi tiết trợ lý, cho phép mở nhanh `ConversationCreateDialog` với trợ lý đã chọn.
- `workspace-detail-layout.tsx`: Thêm tab **"Hội thoại"** vào thanh điều hướng workspace.

### C. Điều hướng & Routing
- Thêm 2 route file-based TanStack Router:
  - `src/routes/workspaces.$workspaceId.conversations.index.tsx` -> `/workspaces/$workspaceId/conversations`
  - `src/routes/workspaces.$workspaceId.conversations.$conversationId.tsx` -> `/workspaces/$workspaceId/conversations/$conversationId`
- Sinh lại `src/routeTree.gen.ts` sạch sẽ thông qua `@tanstack/router-generator`.
- Cập nhật ranh giới `V1_DIRECTORIES` trong `tests/template-boundary.test.ts` bổ sung `"features/conversations/"`.

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Unit & Regression Suite (`bun test`)**:
   - `tests/v1-conversations.test.ts` (MỚI): 11/11 test cases PASS.
     - `listConversations`: Kiểm tra gọi GET với limit/offset, trả về mảng thuần `Conversation[]`.
     - `getConversation`: Kiểm tra gọi GET chi tiết hội thoại.
     - `createConversation`: Kiểm tra gọi POST với assistant_id và title, không gửi thừa trường.
     - `updateConversation`: Kiểm tra gọi PUT gửi đầy đủ title và status.
     - `listTurns`: Kiểm tra gọi GET turns mảng thuần theo thứ tự turn_no tăng dần.
     - `getTurn`: Kiểm tra gọi GET chi tiết một turn.
     - `sendTurn`: Kiểm tra gửi question, `expected_turn_no`, và header `Idempotency-Key`.
     - `Sequence conflict (409)`: Kiểm tra xử lý lỗi `conversation_sequence_conflict`.
     - `formatConversationError`: Kiểm tra ánh xạ toàn bộ mã lỗi backend sang thông điệp trung thực.
     - `Schemas`: Kiểm tra validation cho tiêu đề, câu hỏi, số thứ tự, tìm kiếm và sinh key.
     - `Queries`: Kiểm tra cô lập query keys theo `sessionId` và `workspaceId`.
   - `tests/template-boundary.test.ts`: 5/5 PASS (KTX boundary giữ nguyên 100%).
   - `tests/v1-assistants.test.ts`: 10/10 PASS.
   - `tests/v1-contract.test.ts`: 14/14 PASS.
   - `tests/v1-knowledge.test.ts`: 7/7 PASS.
   - `tests/v1-session-secret-regression.test.ts`: 7/7 PASS.
   - `tests/v1-sso.test.ts`: 10/10 PASS.
   - **Tổng cộng: 64 passed, 0 failed trên toàn bộ 7 test files (100% PASS)**.
2. **TypeScript Typecheck (`tsc --noEmit`)**:
   - 0 errors (PASS hoàn toàn).
3. **Biome Linter & Formatter (`biome check`)**:
   - 20 files checked: 0 errors, 0 warnings (PASS hoàn toàn).

---

## 4. Các Giới Hạn & Phạm Vi Chưa Triển Khai (Theo Yêu Cầu)
- **Streaming & Websocket**: Backend hiện trả JSON đồng bộ; giao diện giữ nguyên xử lý đồng bộ, không dùng streaming giả lập.
- **Tải tệp trong Chat**: Chưa hỗ trợ upload file trực tiếp trong cửa sổ chat (việc tải tài liệu được thực hiện ở Kho tri thức).
- **Tools, Function Calling, Workflow**: Chưa hỗ trợ theo schema backend hiện tại.
- **Chia sẻ / Public / Widget Embed**: Chưa triển khai chatbot công khai hoặc nhúng widget ngoài workspace.
- **Xóa hội thoại, sửa câu hỏi cũ hoặc Regenerate**: Backend chưa có endpoint xóa hoặc sinh lại lượt hỏi cũ; giao diện không thêm các hành động chưa có contract hỗ trợ.
