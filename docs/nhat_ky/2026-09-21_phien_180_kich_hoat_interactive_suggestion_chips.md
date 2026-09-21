# Nhật Ký Làm Việc — Phiên #180 (2026-09-21)
# Kích Hoạt Hệ Thống Nút Bấm Gợi Ý Tương Tác 1-Click (Interactive Suggestion Chips) & Triệt Tiêu Câu Hỏi Tu Từ Rập Khuôn

## 1. Bối Cảnh & Vấn Đề
- Người dùng phản ánh hiện tượng: Khi chat với Trợ lý Tuyển sinh, cuối mỗi câu trả lời bot luôn lặp đi lặp lại một câu hỏi tu từ thụ động: *"Bạn có muốn mình chia sẻ thêm về chỉ tiêu tuyển sinh hoặc các phương thức xét tuyển áp dụng cho các ngành này không?"*.
- Người dùng yêu cầu triển khai theo **Phương án 2 (Toàn diện)**: Vừa chuẩn hóa Prompt định hướng gợi ý theo ngữ cảnh, vừa kích hoạt tính năng **Nút bấm gợi ý 1-Click (Interactive Suggestion Chips)** ngay trên giao diện web để nâng tầm trải nghiệm người dùng tương tự ChatGPT/Perplexity.

## 2. Phân Tích & Giải Pháp Kỹ Thuật

### 2.1. Backend: Bóc Tách Cấu Trúc Gợi Ý & Dọn Sạch Thân Tin Nhắn
1. **[`backend/app/modules/rag/composer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/composer.py)**:
   - Cập nhật `SYSTEM_PROMPT_TEMPLATE`: Cấm tuyệt đối câu hỏi tu từ đóng ở cuối bài (*"Bạn có muốn...", "Bạn có quan tâm đến..."*). Yêu cầu mô hình đề xuất 2 câu hỏi cụ thể đặt trong khối `[GỢI Ý]:`.
   - Viết hàm `extract_suggested_questions(raw_answer: str) -> tuple[str, list[str]]`:
     * Quét khối `[GỢI Ý]:` ở cuối câu trả lời và tách ra danh sách các câu hỏi hành động.
     * Quét và xóa sạch các câu hỏi boilerplate thụ động khỏi thân tin nhắn Markdown.
     * Tự động chuyển đổi các câu hỏi đóng sót lại thành 2 câu hỏi hành động cụ thể theo ngữ cảnh (phương thức, điểm chuẩn, chỉ tiêu, học phí).
2. **[`backend/app/modules/rag/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/schemas.py) & [`service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py)**:
   - Bổ sung trường `suggested_questions: list[str] = Field(default_factory=list)` vào `AskResponse`.
   - Gọi `extract_suggested_questions` trong `rag_service.ask()` trước khi lưu vào Semantic Cache và tạo `AskResponse`.
3. **[`backend/app/modules/workflows/nodes/rag_answer_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/rag_answer_node.py) & [`output_chat_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/output_chat_node.py)**:
   - Truyền `suggested_questions` từ kết quả RAG qua `context.node_data` và `context.outputs` đến payload đầu ra của Workflow.
4. **[`backend/app/modules/assistants/services/assistant_chat_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/services/assistant_chat_service.py)**:
   - Trả về `final_suggested_questions` động trong cả HTTP JSON Response (`AssistantChatResponse.suggested_questions`) và SSE Stream chunk cuối cùng (`event: done`).
5. **Đồng bộ CSDL & Cấu hình**:
   - Cập nhật [`configs/workflows/admissions-assistant.v1alpha1.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/configs/workflows/admissions-assistant.v1alpha1.json), [`backend/app/modules/assistants/seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py).
   - Đồng bộ CSDL PostgreSQL cho Trợ lý `ast_admissions` và quy trình `admissions-assistant`.

### 2.2. Frontend: Nâng Cấp Giao Diện Suggestion Chips
1. **[`frontend/src/components/ai/chat-message.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/chat-message.tsx)**:
   - Nâng cấp mảng `suggestedQuestions` thành các nút bấm Chip tương tác cao cấp:
     * Nền thẻ `bg-card`, viền `border-border/80`, đổ bóng `shadow-2xs`.
     * Hiệu ứng hover nổi bật với Academic Teal: `hover:border-primary/40 hover:bg-primary/5 hover:text-primary`.
     * Icon Lucide `ArrowRight` có vi hiệu ứng dịch chuyển `group-hover/chip:translate-x-0.5`.
     * Gắn tooltip `title="Nhấp để hỏi ngay câu này"`.
   - Kết nối sự kiện `onSuggestedClick(q)`: người dùng nhấp vào chip sẽ tự động gửi câu hỏi ngay lập tức.

## 3. Kết Quả Kiểm Thử Toàn Diện

- **Thử nghiệm trực tiếp với câu hỏi của người dùng**: `"các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học"`:
  * Thân tin nhắn sạch sẽ 100%, liệt kê danh sách 8 ngành kèm mã ngành, **không còn câu hỏi tu từ rập khuôn**.
  * Chân tin nhắn hiển thị 2 Suggestion Chips động:
    1. `[ → Phương thức tuyển sinh áp dụng cho các ngành này là gì? ]`
    2. `[ → Điểm chuẩn trúng tuyển năm gần nhất của các ngành này là bao nhiêu? ]`
- **Bộ kiểm thử chất lượng (CI/CD)**:
  * `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed)**
  * `uv run --extra dev pytest tests/test_rag.py tests/test_workflows.py -v` $\rightarrow$ **41/41 passed (100%)**
  * `npm run lint` $\rightarrow$ **168 files checked, 0 errors**
  * `npm run typecheck` $\rightarrow$ **0 errors**
  * `npm run build` $\rightarrow$ **Build thành công (9.27s)**
