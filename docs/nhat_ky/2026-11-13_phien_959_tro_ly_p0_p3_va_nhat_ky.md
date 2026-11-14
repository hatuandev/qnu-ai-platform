# Phiên 959 — Trang Trợ lý V2: xóa thật, cấu hình cơ bản/nâng cao, Hỏi thử, Kiểm thử và Nhật ký (P0–P3)

## 1. Yêu cầu và phạm vi

- Người dùng giao làm tiếp trang **Trợ lý** trên `frontendV2` theo từng chặng P0 → P3, chốt "P0 thì cứ xóa thật luôn nhé ko xóa mềm", sau đó "làm tiếp P2", "làm tiếp P3" và "tiếp tục theo lộ trình".
- Mục tiêu P0–P3: thay trang trợ lý tĩnh bằng luồng thật gồm danh sách + tạo/sửa cấu hình, xóa vĩnh viễn có kiểm soát, tab Hỏi thử (gửi lượt hỏi thật), tab Kiểm thử (duyệt câu trả lời) và tab Nhật ký (hội thoại + lượt hỏi của trợ lý).
- Phạm vi backend: một endpoint xóa thật trợ lý; một tham số lọc `assistant_id` cho danh sách hội thoại; vá OpenAPI đúng phần thay đổi.
- Phạm vi frontend: lớp API `assistants`, `answer-reviews`, `conversations`; bộ component `components/assistants/`; tách route danh sách/chi tiết với tab điều khiển bằng URL.
- Giữ nguyên: toàn bộ diff chưa commit của người dùng ngoài phạm vi (knowledge/lifecycle), chuỗi migration (dev DB vẫn `0026`, 0027+0028 chờ duyệt), dữ liệu dev ngoài hai lượt hỏi kiểm thử.
- Ràng buộc: không commit/push/deploy; không re-index; không chạy pytest (người dùng yêu cầu dừng test); không in token/secret; không in nội dung tài khoản dev.

## 2. Hợp đồng sau thay đổi

1. **Xóa thật trợ lý:** `DELETE /platform/v1alpha1/workspaces/{workspace_id}/assistants/{assistant_id}` trả **204**. Chỉ role `admin` (qua `resolve_workspace_access`), khóa row `FOR UPDATE`, hủy tác vụ liên quan, xóa theo thứ tự phụ thuộc trong **một transaction**: lượt hỏi → câu trả lời kiểm thử (`answer_reviews`) → hội thoại → trạng thái vòng đời (`ResourceState` của conversation/assistant) → row trợ lý; ghi workspace event `assistant.deleted`. Không còn bản ghi mồ côi chặn purge kho.
2. **Lọc hội thoại theo trợ lý:** `GET /workspaces/{workspace_id}/conversations?assistant_id=...` (≤64 ký tự, tùy chọn). Bộ lọc áp **sau** các guard hiện có: workspace access, `owner_ref` của người gọi, `visible(...)` cho conversation/assistant/collection. Không đổi hành vi khi bỏ tham số.
3. **Trang danh sách trợ lý:** dữ liệu thật từ API, thẻ trợ lý có trạng thái sẵn sàng và menu vòng đời; form tạo/sửa gồm **Cơ bản** và **Nâng cao** (RAG policy), lưu theo revision để tránh ghi đè.
4. **Trang chi tiết trợ lý:** route `assistants/$assistantId` với ba tab `ask` (Hỏi thử), `reviews` (Kiểm thử), `logs` (Nhật ký); tab lưu trong URL (`validateSearch` + zod `.catch`) nên deep link và back/forward hoạt động.
5. **Nhật ký:** liệt kê 20 hội thoại gần nhất **của chính người dùng** cho trợ lý đang mở; mở rộng từng hội thoại mới tải lượt hỏi (lazy); lượt đang chạy tự poll mỗi 4 giây; câu trả lời dùng chung `AnswerBody` với tab Kiểm thử.
6. **Nhãn lỗi lượt hỏi:** các mã phổ biến được diễn giải tiếng Việt, mã gốc hiển thị kèm dạng mono để đối chiếu log; mã lạ vẫn hiện "Lượt hỏi thất bại." + mã.

## 3. Thay đổi

### 3.1 Backend

- `backendV1/qnu/domains/assistants/router.py`: thêm route `DELETE /{assistant_id}` → 204, gọi `service.delete_assistant`.
- `backendV1/qnu/domains/assistants/service.py`: thêm `delete_assistant` (admin + for_update, `cancel_related_jobs`, xóa `ConversationTurn` → `AnswerReview` → `Conversation` → `ResourceState` → assistant, event `assistant.deleted`, trả số lượng đã xóa).
- `backendV1/qnu/domains/conversations/router.py`: thêm query `assistant_id: str | None = Query(None, max_length=64)`.
- `backendV1/qnu/domains/conversations/service.py`: `listing(...)` dựng query có điều kiện, giữ nguyên guard quyền và thứ tự `updated_at desc, id`.
- `backendV1/docs/openapi-v1.json`: vá đúng khối tham số của path conversations, **+17 dòng**, không regenerate toàn bộ (artifact đã lệch app từ trước).

### 3.2 Frontend — lớp API

- `frontendV2/src/api/assistants/`: `endpoints.ts`, `types.ts`, `requests.ts`, `queries.ts` (list/detail/create/update/delete/readiness, invalidation theo `conversationKeys`/`answerReviewKeys`), `index.ts` re-export.
- `frontendV2/src/api/answer-reviews/`: `endpoints.ts`, `types.ts`, `requests.ts`, `queries.ts` (danh sách + tạo/cập nhật kiểm thử), `index.ts`.
- `frontendV2/src/api/conversations/`: `types.ts`, `requests.ts` (tạo hội thoại, gửi lượt với header `Idempotency-Key`), `queries.ts` (`useAssistantConversationsQuery` limit 20, `useConversationTurnsQuery` poll 4 giây chỉ khi có lượt `running`), `index.ts` re-export.

### 3.3 Frontend — component và route

- `components/assistants/`: `assistant-card.tsx`, `assistant-form-dialog.tsx` (Cơ bản + Nâng cao), `assistant-advanced-fields.tsx` (RAG policy), `model-label.ts`, `readiness.ts`, `ask-test-panel.tsx`, `answer-body.tsx` (trích từ item kiểm thử để dùng chung), `answer-review-card.tsx`, `answer-review-history.tsx`, `answer-review-item.tsx` (ủy thác render cho `AnswerBody`), `assistant-logs.tsx`.
- `routes/assistants.tsx`: thu về layout/outlet; `routes/assistants.index.tsx`: danh sách thật; `routes/assistants.$assistantId.tsx`: tab `ask`/`reviews`/`logs`, deep link `?tab=`.
- `routeTree.gen.ts`: sinh lại theo route mới.
- `assistant-logs.tsx` bổ sung nhãn cho 5 mã lỗi thực gặp/đã biết: `index_not_ready`, `conversation_turn_expired`, `conversation_clarification_required`, `chat_provider_changed`, `conversation_route_invalid` (trước đó chỉ 4 mã).

## 4. Kiểm chứng đã chạy

### 4.1 Tĩnh

- `uv run ruff check qnu/domains/assistants qnu/domains/conversations` (backendV1): **All checks passed**.
- Biome check trên 9 tệp `api/assistants`, `api/answer-reviews`, `api/conversations`, `components/assistants`, `routes/assistants.*`: **PASS**.
- `npx tsc --noEmit` trong `frontendV2`: **exit 0**.

### 4.2 Live API (dev 8002, workspace `ws_f617405c3a51`, trợ lý `ast_3f577d75f723`)

- `GET /conversations?assistant_id=ast_3f577d75f723` → đúng **1** hội thoại, `last_turn_no=2`.
- `GET /conversations?assistant_id=ast_khong_ton_tai` → `[]`.
- `GET /conversations` không lọc → 200, danh sách hợp lệ.
- `POST /conversations/cnv_408c176b53a9/turns` (Idempotency-Key sinh riêng):
  - Lượt #1 câu hỏi tra cứu → **failed**, `error_code=index_not_ready` (kho demo chưa có tài liệu xuất bản nên search trả 409 sau bước định tuyến model).
  - Lượt #2 câu chào → **completed**, `result.status=direct_reply`, `route=greeting`.
- `DELETE /assistants/{id}` trợ lý tạm dùng kiểm tra empty state → **204**; danh sách còn đúng `ast_3f577d75f723`.

### 4.3 Live UI (Vite 3002, trình duyệt ẩn)

- Deep link `?tab=logs` mở đúng tab; chuyển tab bằng sự kiện `mousedown` thật rồi so URL `?tab=ask` ↔ `?tab=logs`: **PASS**.
- Mở rộng hội thoại tải đúng 2 lượt; lượt #1 hiện diễn giải "Kho tri thức chưa có chỉ mục đang hoạt động nên chưa thể trả lời." kèm mã `index_not_ready`; lượt #2 hiện khối trả lời trực tiếp "Chào hỏi".
- Nút Tải lại refetch danh sách: **PASS**. Empty state hiển thị đúng với trợ lý tạm (sau đó đã xóa thật).
- Tab Kiểm thử và Hỏi thử render đúng khung; form Cơ bản/Nâng cao mở đúng dữ liệu trợ lý.

### 4.4 NOT RUN / NOT OBSERVED

- **Pytest: NOT RUN** theo yêu cầu dừng test của người dùng — `NOT RUN ≠ PASS`.
- **NOT OBSERVED:** giao diện báo lỗi khi API sập (không dựng tình huống), nhánh hiển thị câu trả lời RAG trong Nhật ký (kho demo trống nên không có lượt `answered`), trạng thái poll `running` (lượt chạy/fail quá nhanh), viewport mobile + ảnh chụp (trình duyệt ẩn `visibilityState=hidden`), hiệu ứng xóa dây chuyền của `DELETE` khi trợ lý có hội thoại/câu trả lời kiểm thử (chỉ xóa trợ lý tạm không phụ thuộc).
- Không chạy lại migration, không re-index, không đổi dữ liệu ngoài phạm vi.

## 5. Rủi ro và việc còn lại

- `cnv_408c176b53a9` ("Kiểm thử nhật ký P3", 2 lượt) còn trong workspace dev — giữ làm mẫu kiểm tra, **chưa xóa** chờ người dùng quyết định.
- Dev DB vẫn `0026`; migration `0027_drop_ws_model_policy` + `0028` tiếp tục chờ duyệt (#223).
- Trang **Chat V2** (`routes/chat.tsx`) vẫn là mock tĩnh — bước tiếp theo của lộ trình: nối bằng API hội thoại/lượt hỏi thật (đồng bộ, không streaming).
- Sau đó: SSO cho `frontendV2` trước khi thay website trên server.
- Chưa commit/push; working tree còn diff knowledge/lifecycle của phiên trước và nhóm tệp P0–P3 của phiên này.
