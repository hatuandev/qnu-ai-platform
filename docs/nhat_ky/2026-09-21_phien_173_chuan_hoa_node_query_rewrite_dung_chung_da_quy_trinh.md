# NHẬT KÝ LÀM VIỆC — PHIÊN #173
**Ngày**: 2026-09-21 | **Thời gian**: 14:22 (UTC+7)  
**Tiêu đề**: Chuẩn Hóa Node DAG Query Rewrite Dùng Chung Đa Quy Trình & Visual Prompt Inspector

---

## 1. Bối Cảnh & Yêu Cầu

Trước đây, trong `query_rewrite_node.py` có chứa một từ điển ánh xạ cố định 5 phân hệ hệ thống (`DOMAIN_CONTEXT_MAP`: admissions, regulations, library, drafting, question_bank). Điều này vi phạm tính mở và khả năng tái sử dụng của DAG Engine vì người dùng không thể tự do thêm các quy trình mới (ký túc xá, khảo thí, công tác sinh viên, văn phòng khoa,...) mà node lại tự động áp dụng đúng ngữ cảnh mong muốn.

Yêu cầu kỹ thuật:
1. **Loại bỏ hoàn toàn canh cứng 5 mô đun** trong `query_rewrite_node.py`.
2. **Node dùng chung (Generic Shared Node)**: Bất kỳ quy trình nào khi tạo cũng có thể kéo/thêm node này vào DAG.
3. **Cấu hình Prompt / Instruction riêng theo từng quy trình**: Khi click vào node trên canvas, người dùng có thể viết prompt/instruction đặc thù cho quy trình đó (ví dụ: quy định ngữ cảnh, từ viết tắt đặc thù, quy tắc viết hoa tên ngành/phòng ban).
4. **Visual Property Inspector**: Cập nhật thanh thuộc tính `PropertyInspector` trên frontend để người quản trị dễ dàng nhập `instruction`, bật/tắt tầng Fast Rules và tầng LLM Rewrite trực quan mà không cần chỉnh JSON thủ công.

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật

### 2.1. Backend (`query_rewrite_node.py`)
- Xóa bỏ hoàn toàn biến toàn cục `DOMAIN_CONTEXT_MAP`.
- Cung cấp hàm `get_node_instruction(context: WorkflowContext, config: dict[str, Any]) -> str` theo cơ chế phân giải ưu tiên:
  1. `config.get("instruction")` hoặc `config.get("prompt")` hoặc `config.get("custom_prompt")`: Ưu tiên hàng đầu được thiết lập riêng trên chính node của quy trình.
  2. `config.get("domain")`: Cung cấp ngắn gọn tên lĩnh vực (ví dụ `"ký túc xá"`, `"khảo thí"`).
  3. `context.assistant_profile`: Kế thừa ngữ cảnh vai trò từ Assistant Profile nếu đang chạy trong workflow của Trợ lý.
  4. Fallback chung toàn trường ĐH Quy Nhơn cho bất kỳ quy trình tổng quát nào.
- Hàm `build_rewrite_prompt(query: str, instruction: str) -> str`:
  - Hỗ trợ placeholder `{query}` nếu người dùng cung cấp template tùy biến hoàn chỉnh.
  - Tự động đóng gói kèm các quy tắc chuẩn hóa nghiêm ngặt (không giải thích, không thêm tiền tố, giữ nguyên ý định, ví dụ mẫu few-shot).

### 2.2. Frontend (`property-inspector.tsx`)
- Tách riêng nhánh render cho `query.rewrite` (`nodeType === "query.rewrite" || nodeType.includes("rewrite")`).
- Tích hợp Textarea đa dòng cho `Prompt / Hướng dẫn chuẩn hóa` (`instruction`).
- Tích hợp 2 công tắc Switch:
  - `Quy tắc nhanh (0ms Fast Rules)`: Sửa tức thì trượt phím Telex & viết tắt QNU.
  - `Tầng LLM chuẩn hóa (~150ms)`: Dùng LLM siêu tốc chuẩn hóa câu hỏi phức tạp theo instruction đã viết.

### 2.3. Cập nhật Manifest & Workflow CSDL
- `configs/nodes/query.rewrite.v1alpha1.json`: Khai báo thuộc tính `instruction` và `prompt` trong `config_schema`.
- `configs/workflows/admissions-assistant.v1alpha1.json`: Gán `instruction` chuẩn hóa chuyên biệt cho tuyển sinh vào config node `query_rewrite`.
- Đồng bộ vào CSDL PostgreSQL (`workflow_definitions`, `workflow_drafts`, `workflow_versions`).

---

## 3. Kết Quả Kiểm Thử Toàn Diện

- **Backend Ruff**: 0 cảnh báo, 0 lỗi linter (`uv run ruff check .`).
- **Backend Pytest**:
  - `tests/test_query_rewrite_node.py`: 7/7 passed.
  - `tests/test_workflows.py`: 24/24 passed.
- **Frontend Biome**: Check 168 tệp nguồn, 0 lỗi linter (`npm run lint`).
- **Frontend TypeScript**: `tsc --noEmit`, 0 lỗi kiểu dữ liệu (`npm run typecheck`).
- **Frontend Vite Build**: Đóng gói thành công trong 8.15s (`npm run build`).
- **Kiểm thử End-to-end Chat**:
  - Input: *"học phí ngày công nghệ thông tin là bao nhiêu"*
  - Query Rewrite: *"học phí ngành Công nghệ thông tin là bao nhiêu"*
  - Kết quả RAG: Trả lời chính xác 83-97 triệu (cử nhân 4 năm), 112,3 triệu (kỹ sư 4,5 năm), 1,5x hệ tiếng Anh, kèm 4 trích dẫn PDF chính thức và hotline tuyển sinh 0256.3846.156.
