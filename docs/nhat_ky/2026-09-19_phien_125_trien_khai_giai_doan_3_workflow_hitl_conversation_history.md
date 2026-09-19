# NHẬT KÝ PHIÊN LÀM VIỆC #125
**Ngày**: 2026-09-19 21:30 | **Kỹ sư**: AI Senior Full-Stack Architect  
**Mục tiêu**: Triển khai Giai đoạn 3 (Workflow, Tools & Multi-Turn Conversations) theo Kế hoạch Cải thiện Toàn diện 07 ([`docs/ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md`](../ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md)).

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Sau khi hoàn thành Giai đoạn 2 (Database & Cross-Store Integrity, RAG Hybrid Hardening, ModelOps Dynamic Fallback & Quota Accounting), Giai đoạn 3 tập trung giải quyết 3 khoảng hở lớn trong tầng điều phối tác vụ (Workflow Orchestration), tương tác công cụ an toàn có kiểm soát (Tool Gateway HITL) và ngữ cảnh hội thoại nhiều lượt (Multi-Turn Conversations):

1. **Tool Gateway & HITL Handshake (P0 / P1)**:
   - Khi Workflow gặp một node thực thi công cụ có tác động thực tế (side-effect tools như `export_administrative_document`, `export_exam_matrix`) cần người phê duyệt (`requires_approval=True`), execution engine chuyển trạng thái run sang `paused_for_approval`.
   - Tuy nhiên, trước đây tầng Assistant chat (`assistant_service.chat` và `chat_stream`) không bắt trạng thái này một cách tường minh, dẫn tới việc hệ thống coi như không có kết quả hợp lệ và rơi vào fallback `no_answer_message` ("*Xin lỗi, tôi không tìm thấy thông tin...*").
   - **Mục tiêu**: Bắt rõ `paused_for_approval`, trả về trạng thái phê duyệt kèm `approval_id`, hướng dẫn truy cập Hộp thư Phê duyệt (`/runs`), yield SSE event `event: approval_required` tới UI Chat Studio và hiển thị banner thông báo chờ duyệt trực quan.

2. **Multi-Turn Conversation Context (P1)**:
   - Chatbot AI khi nhận câu hỏi mới chỉ xử lý câu hỏi đơn lẻ mà không liên kết các tin nhắn trước đó trong thread, dẫn tới việc các câu hỏi mang đại từ chỉ định ("*Nó có giá trị trong bao lâu?*", "*Ngành đó có điểm chuẩn bao nhiêu?*") không thể được RAG và LLM giải đáp chính xác.
   - **Mục tiêu**: Tự động truy vấn tối đa 6 tin nhắn gần nhất từ `conversation_messages` theo thứ tự thời gian (chronological order) và truyền vào `conversation_history` của Workflow inputs; chèn context này vào cả `llm_generate_node.py` và `rag_service.ask()` giữa System Prompt và câu hỏi hiện tại.

3. **DAG Compiler Hardening (P1)**:
   - Trình biên dịch DAG (`compiler.py`) cần cảnh báo trước cho nhà phát triển khi thiết kế workflow nếu có node `api_caller` sử dụng công cụ yêu cầu phê duyệt con người, giúp người thiết kế chủ động cấu hình nhánh chờ duyệt.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 2.1. RAG Service & Schemas Support Multi-Turn History
- **[`backend/app/modules/rag/schemas.py`](../../backend/app/modules/rag/schemas.py)**:
  - Bổ sung trường `history: list[dict[str, str]] | None = None` vào schema `AskRequest` để tiếp nhận lịch sử hội thoại nhiều lượt.
- **[`backend/app/modules/rag/service.py`](../../backend/app/modules/rag/service.py)**:
  - Trong `ask()`: Bổ sung logic chèn `history` (tối đa 6 tin nhắn gần nhất) vào `llm_messages` nằm giữa System Prompt và câu hỏi hiện tại của người dùng. Chuẩn hóa format role (`user`, `assistant`) và lọc bỏ các message rỗng.

### 2.2. Workflow Nodes Context Forwarding
- **[`backend/app/modules/workflows/nodes/rag_answer_node.py`](../../backend/app/modules/workflows/nodes/rag_answer_node.py)**:
  - Trích xuất `conversation_history` từ `context.inputs` và truyền vào `AskRequest(query=query, ..., history=history)`.
- **[`backend/app/modules/workflows/nodes/llm_generate_node.py`](../../backend/app/modules/workflows/nodes/llm_generate_node.py)**:
  - Chèn `conversation_history` từ `context.inputs` vào mảng `messages` của `LLMGenerateRequest` để các prompt tổng hợp/sáng tạo nắm bắt trọn vẹn ngữ cảnh trò chuyện trước đó.

### 2.3. Assistant Chat Service & HITL Handshake
- **[`backend/app/modules/assistants/service.py`](../../backend/app/modules/assistants/service.py)**:
  - Bổ sung helper `_get_recent_conversation_history(db, conversation_id, limit=6)`:
    - Truy vấn các tin nhắn trước đó của thread theo thứ tự thời gian tăng dần (`created_at.asc()`), loại bỏ tin nhắn hệ thống hoặc tin nhắn rỗng.
  - Cập nhật hàm `chat()` (Non-streaming):
    - Tự động nạp lịch sử hội thoại trước khi lưu user message mới, truyền vào `WorkflowExecuteRequest.inputs["conversation_history"]`.
    - Xử lý khi `workflow_response.status == "paused_for_approval"`: Không rơi vào `no_answer_message`, mà trích xuất `approval_id` và trả về `status="paused_for_approval"` kèm thông báo hướng dẫn người dùng/cán bộ truy cập Hộp thư Phê duyệt (`/runs`).
  - Cập nhật hàm `chat_stream()` (SSE Streaming):
    - Tự động nạp lịch sử hội thoại và truyền vào context execution.
    - Bắt trạng thái `paused_for_approval`:
      - Yield event SSE chuyên biệt: `event: approval_required` kèm payload JSON `{approval_id, paused_node_id, action_required, tool_name}`.
      - Yield token nội dung thông báo mã phê duyệt và hướng dẫn xử lý.
      - Gửi `status: "paused_for_approval"` trong sự kiện `event: done`.

### 2.4. DAG Compiler Static Analysis
- **[`backend/app/modules/workflows/compiler.py`](../../backend/app/modules/workflows/compiler.py)**:
  - Bổ sung kiểm tra trong `_validate_node_config_schema`:
    - Khi node thuộc type `api_caller` sử dụng công cụ từ danh mục hệ thống có thuộc tính `requires_approval=True`, tự động phát sinh một issue warning: `code="workflow_tool_requires_approval_info"`, thông báo rõ node này sẽ tạm dừng thực thi khi chạy để chờ phê duyệt HITL.

### 2.5. Frontend UI & SSE Hook Integration
- **[`frontend/src/hooks/use-rag-stream.ts`](../../frontend/src/hooks/use-rag-stream.ts)**:
  - Mở rộng interface `ChatMessageItem` với các trường: `approvalId?: string`, `toolName?: string`, và trạng thái `status: "sending" | "streaming" | "done" | "paused_for_approval" | "error"`.
  - Lắng nghe `event.event === "approval_required"`: Tự động cập nhật message hiện tại với `status = "paused_for_approval"`, `approvalId`, và `toolName`.
  - Đồng bộ `status: "paused_for_approval"` từ sự kiện `done`.
- **[`frontend/src/components/ai/chat-message.tsx`](../../frontend/src/components/ai/chat-message.tsx)**:
  - Thiết kế và tích hợp component **HITL Approval Pending Banner**:
    - Hiển thị khối thông báo nổi bật phong cách Academic Teal/Amber với icon đồng hồ cát `Clock`, badge `Chờ Phê Duyệt Tác Vụ`.
    - Hiển thị mã phiếu phê duyệt (`approvalId`) và công cụ thực thi (`toolName`).
    - Nút bấm điều hướng trực tiếp: `[Xem & Phê Duyệt Tại Hộp Thư /runs]` giúp cán bộ mở ngay giao diện phê duyệt tác vụ.

### 2.6. Kiểm Thử Độc Lập Toàn Diện
- **[`backend/tests/test_workflow_hitl_and_history.py`](../../backend/tests/test_workflow_hitl_and_history.py)**:
  - `test_chat_handles_workflow_paused_for_approval`: Kiểm tra hàm `chat()` trả về đúng `status="paused_for_approval"` và message chứa `approval_id`.
  - `test_chat_stream_yields_approval_required_event`: Kiểm tra hàm `chat_stream()` yield đúng `event: approval_required` với payload chứa `approval_id` và token thông báo.
  - `test_get_recent_conversation_history_fetches_and_formats_in_chronological_order`: Kiểm tra hàm helper lấy tối đa 6 tin nhắn cũ và sắp xếp đúng thứ tự thời gian.
  - `test_rag_service_injects_history_into_llm_messages`: Kiểm tra `rag_service.ask` chèn đúng danh sách tin nhắn lịch sử vào mảng `llm_messages` gửi tới model.
  - `test_workflow_compiler_warns_on_approval_tool`: Kiểm tra DAG compiler phát sinh warning `workflow_tool_requires_approval_info` khi node sử dụng tool có `requires_approval=True`.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Backend Verification**:
   - `uv run ruff check .` : **All checks passed (0 errors)**.
   - `uv run --extra dev pytest -v` : **250/250 tests passed (100%)**, 47 warnings (Pydantic deprecation warnings thông thường).
2. **Frontend Verification**:
   - `npm run lint` : **Checked 162 files, 0 errors, 0 warnings**.
   - `npm run typecheck` : **0 errors**.
   - `npm run build` : **Thành công trong 9.75s**, tạo bundle sạch sẽ.
3. **Mã Hóa & Tiếng Việt**:
   - `python scripts/check_mojibake.py` : **318/318 files passed**, 0 ký tự lỗi / UTF-8 sạch 100%.

---

## 4. Đánh Giá & Các Bước Tiếp Theo

Giai đoạn 3 đã hoàn thành toàn bộ mục tiêu đề ra trong Kế hoạch 07 (Đợt 6). Hệ thống hiện tại sở hữu khả năng điều phối workflow mượt mà, hỗ trợ hội thoại nhiều lượt sâu sắc và cơ chế HITL minh bạch giữa Backend và Frontend UI.
Sẵn sàng bước sang **Giai đoạn 4: Quality Gate, Benchmark & Observability** (Đợt 7 và 8).
