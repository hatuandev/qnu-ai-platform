# NHẬT KÝ LÀM VIỆC — Phiên #175
**Ngày**: 2026-09-21 14:55 (UTC+7)  
**Nhiệm vụ**: Khắc Phục Lỗi Điều Hướng Chào Hỏi Cắt Ngang Tra Cứu, Triệt Tiêu Mẫu Văn Bản Hardcode Cũ Và Khắc Phục Cổng Phân Nhánh DAG

---

## 1. Mục Tiêu & Vấn Đề Người Dùng Báo Cáo
Người dùng trải nghiệm giao diện Trợ lý Tuyển sinh ĐH Quy Nhơn và phát hiện lỗi:
- Gõ câu hỏi: `"xin chào bạn cho tôi hỏi phương thức tuyển sinh năm 2026"`.
- Trợ lý không trả lời phương thức tuyển sinh 2026 mà xuất ra một đoạn văn bản chào hỏi tĩnh bị hardcode từ trước với các mốc thời gian 2024, 2025:
  `1. Điểm chuẩn các ngành tuyển sinh năm 2024`
  `3. Các ngành đào tạo và chỉ tiêu tuyển sinh năm 2025` kèm emoji.

---

## 2. Phân Tích Kỹ Thuật & Nguyên Nhân Gốc (Root Cause Analysis)

1. **Lỗi Phân Loại Ý Định (Condition Route Regex Hijack)**:
   - Trong workflow `admissions-assistant`, node `condition_route` có quy tắc bắt chuỗi regex `"xin chào|hello|hi|chào|..."` trỏ sang node `greeting_output`.
   - Trước đây `ConditionRouteNodeHandler` sử dụng phép tìm kiếm regex thô trực tiếp trên toàn bộ câu. Do người dùng bắt đầu câu bằng *"xin chào bạn..."*, regex đã nhận định sai đây là lời chào thuần túy và điều hướng sang `greeting_output`, bỏ qua hoàn toàn chuỗi câu hỏi nghiệp vụ phía sau (`cho tôi hỏi phương thức tuyển sinh năm 2026`).
2. **Mẫu Văn Bản Tĩnh Lỗi Thời (Outdated Hardcoded Templates)**:
   - Tệp mẫu `configs/workflows/admissions-assistant.v1alpha1.json` và tệp `citation_guard.py` còn lưu trữ đoạn văn bản tĩnh từ giai đoạn tạo khung mẫu ban đầu chứa năm 2024, 2025 và emoji không phù hợp tiêu chuẩn sản xuất của AGENTS.md.
3. **Thất Thoát Thuộc Tính Cổng Phân Nhánh Khi Đọc Từ CSDL (Port Parsing Bug)**:
   - Khi lưu trữ vào PostgreSQL, các cạnh (`edges`) được serialize thành cấu trúc phẳng (`source`, `target`, `source_port`, `target_port`).
   - Khi `WorkflowService._parse_spec_from_json` giải mã lại từ CSDL, hàm chỉ đọc `src.get("port")` (dạng dict lồng nhau từ file JSON), bỏ quên thuộc tính cấp cao nhất `e.get("source_port")`. Kết quả là toàn bộ `source_port` bị biến thành `None`, dẫn đến việc `citation_guard` chọn cổng `grounded` nhưng runtime báo lỗi *"không tìm thấy cạnh tương ứng"*.
4. **Xử Lý Lỗi Fallback Mock Trong Query Rewrite**:
   - Khi tầng LLM của node `query_rewrite` nhận phản hồi mô phỏng từ máy chủ nội bộ (`[Local ...]`), đoạn thông báo fallback bị nhầm là câu hỏi chuẩn hóa, làm ô nhiễm câu hỏi truyền vào RAG.

---

## 3. Các Thay Đổi Kỹ Thuật Chi Tiết

1. **Nâng Cấp Thuật Toán Phân Biệt Chào Hỏi Thuần Túy (`condition_route_node.py`)**:
   - Xây dựng danh sách danh xưng đối tượng: `_TITLE_PATTERNS` (`trợ lý tuyển sinh`, `qnu`, `bạn`, `thầy cô`,...).
   - Bóc tách toàn bộ từ chào hỏi và danh xưng, kiểm tra độ dài nội dung còn lại (`clean_remainder`):
     * Nếu có dấu hỏi `?` hoặc chứa từ khóa tra cứu (`phương thức`, `điểm chuẩn`, `học phí`, `chỉ tiêu`, `năm 202...`) -> **Khẳng định là câu hỏi nghiệp vụ, bỏ qua rule chào hỏi, chuyển thẳng sang `query_rewrite` -> `knowledge_answer`**.
     * Chỉ khi phần nội dung còn lại sau khi trừ từ chào và danh xưng có độ dài $\le 2$ ký tự (ví dụ: *"Xin chào Trợ lý Tuyển sinh!"*, *"Chào bạn"*, *"Hi QNU"*) -> **Khẳng định là chào hỏi thuần túy, điều hướng sang `greeting_output`**.
2. **Chuẩn Hóa Mẫu Chào Hỏi & Từ Chối Thường Trực (Evergreen Templates)**:
   - Cập nhật `configs/workflows/admissions-assistant.v1alpha1.json`: Viết lại `greeting_output` và `no_answer_output` thành nội dung thường trực, chuyên nghiệp, không ghim cứng năm cũ, tuân thủ nghiêm ngặt Zero-Emoji theo AGENTS.md.
   - Cập nhật `backend/app/modules/rag/citation_guard.py`: Xóa bỏ năm 2024 và emoji trong `NO_ANSWER_MESSAGES["admissions"]`.
3. **Sửa Lỗi Bóc Tách Cổng Phân Nhánh Trong `service.py`**:
   - Nâng cấp `WorkflowService._parse_spec_from_json`:
     ```python
     source_port = (src.get("port") if isinstance(src, dict) else None) or e.get("source_port")
     target_port = (tgt.get("port") if isinstance(tgt, dict) else None) or e.get("target_port")
     ```
   - Khôi phục trường `config=n.get("config", {})` cho `WorkflowNodeSpec`.
4. **Phòng Vệ Mock Cục Bộ Trong `query_rewrite_node.py`**:
   - Phát hiện chuỗi `[Local `, `máy chủ AI nội bộ`, `Đã ghi nhận yêu cầu` trong kết quả LLM để lập tức bỏ qua và bảo toàn câu truy vấn đã chuẩn hóa bằng Fast Rules.
5. **Đồng Bộ CSDL & Cập Nhật Test Suite**:
   - Chạy `uv run python -m app.cli db seed --workflows` đồng bộ cấu hình mới vào PostgreSQL.
   - Cập nhật `tests/test_node_catalog.py` từ 13 lên 14 node manifest.

---

## 4. Kết Quả Kiểm Thử & Xác Minh

- **Kiểm thử Luồng Thực Tế (Execution Engine)**:
  * Câu hỏi: `"xin chào bạn cho tôi hỏi phương thức tuyển sinh năm 2026"`:
    - Đi qua đầy đủ các node: `['chat_input', 'condition_route', 'query_rewrite', 'knowledge_answer', 'citation_guard', 'chat_output']`.
    - Kết quả: Trích xuất 5 dẫn chứng từ tài liệu Đề án tuyển sinh 2026 của ĐH Quy Nhơn (`doc_f0c17c002219`) về các phương thức xét tuyển PT1 (THPT), PT2 (học bạ), PT3 (ĐGNL ĐHQG-HCM), PT4 (ĐGNL ĐHSP Hà Nội), PT5 (năng khiếu).
  * Câu chào: `"Xin chào QNU!"`:
    - Đi qua: `['chat_input', 'condition_route', 'greeting_output']`.
    - Kết quả: Lời chào hỗ trợ chuyên nghiệp, trang trọng.
- **Backend Quality Gates**:
  * `uv run ruff check .` -> **0 lỗi**.
  * `uv run --extra dev pytest tests/test_workflows.py tests/test_query_rewrite_node.py tests/test_node_catalog.py -v` -> **34/34 passed (100%)**.
  * Toàn bộ test suite backend: **341/341 passed (100%)**.
- **Frontend Quality Gates**:
  * `npm run lint` -> **Biome check 168 files: 0 lỗi**.
  * `npm run typecheck` -> **0 lỗi**.
  * `npm run build` -> **Vite bundle đóng gói thành công**.
