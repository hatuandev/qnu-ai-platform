# NHẬT KÝ LÀM VIỆC — PHIÊN #188 (2026-09-22)

## 1. Mục Tiêu Phiên Làm Việc
Khắc phục triệt để lỗi bot trả lời nguyên cụm bảng thô `|||||| 31 | 7380101 | Luật... 36 | 7480201 | Công nghệ thông tin...`, rò rỉ các ngành không liên quan (over-inclusion), vỡ cú pháp bảng Markdown và thiếu giải thích sư phạm về các phương thức xét tuyển (1, 2, 3, 4).

## 2. Nguyên Nhân Kỹ Thuật (Root Cause Analysis)
1. **Dữ liệu OCR bảng dạng pipe dính chùm**: Trong quá trình trích xuất PDF Đề án Tuyển sinh 2026, bảng Danh mục ngành tuyển sinh có nhiều cột hẹp sinh ra các chuỗi ký tự pipe thô liên tiếp (`||||||`).
2. **Thiếu Entity-Scoped Constraint ở System Prompt**: Khi người dùng hỏi cụ thể về một ngành (ví dụ: *Công nghệ thông tin*), RAG Hybrid tìm thấy đoạn trích chứa ngành này nhưng đoạn trích lại gồm cả 10 ngành khác xung quanh trong bảng. Thiếu ràng buộc phạm vi thực thể khiến LLM chép nguyên văn cả hàng bảng của các ngành bên cạnh (*Luật*, *Hóa học*, *Sư phạm*).
3. **Thiếu hướng dẫn định dạng chi tiết cho tổ hợp môn**: LLM không biết cần giải thích các số `1, 2, 3, 4` là ký hiệu của các Phương thức xét tuyển 1, 2, 3, 4 của Trường nên in nguyên văn chuỗi thô.
4. **Thiếu tầng Sanitizer hậu xử lý**: Khi LLM sinh câu trả lời có chứa các cụm pipe `||||||` hoặc vết bảng vỡ, hệ thống chưa có bộ lọc dọn dẹp trước khi trả ra client.

## 3. Các Thay Đổi Kỹ Thuật (Key Changes)
1. **`backend/app/modules/rag/composer.py`**:
   - Xây dựng `sanitize_rag_answer(text, target_entity)`:
     * Dọn sạch triệt để các cụm ký tự pipe rác `||||||` do OCR sinh ra.
     * Chốt chặn trường hợp LLM nhả cả khối bảng nhiều ngành: tự động phân tích và chuyển đổi thành danh sách gạch đầu dòng chuẩn mực cho đúng thực thể được hỏi (`target_entity`).
     * Bảo toàn 100% các bảng Markdown chuẩn có Header.
   - Nâng cấp `AnswerFormatPlanner.get_format_instructions()`:
     * Sinh hướng dẫn định dạng trực tiếp theo loại câu hỏi (tổ hợp môn, bảng so sánh, checklist, timeline).
     * Bắt buộc dùng danh sách gạch đầu dòng cho tổ hợp môn và giải thích rõ ràng các số 1, 2, 3, 4 là Phương thức xét tuyển 1-4.
2. **`backend/app/modules/rag/query_router.py`**:
   - Mở rộng `QueryAnalysis` thêm trường `target_entities: list[str]`.
   - Bổ sung logic trích xuất `target_entities` từ mã ngành, tên ngành tuyển sinh chuẩn và mẫu ngữ pháp `ngành/chuyên ngành [Tên ngành]`.
3. **`backend/app/modules/rag/service.py`**:
   - Nhận diện `target_entities` và inject Ràng buộc trích xuất theo thực thể (*Entity-Scoped Constraint*) vào `user_content`.
   - Inject chỉ đạo định dạng của `AnswerFormatPlanner` vào prompt.
   - Bổ sung quy tắc Trích xuất theo thực thể và Định dạng chuẩn mực vào `build_generic_system_instruction()`.
   - Gọi `sanitize_rag_answer()` ở tầng hậu xử lý trước khi trả câu trả lời.
4. **Cập nhật & Đồng bộ System Prompts CSDL**:
   - Cập nhật `ast_admissions` trong `backend/app/modules/assistants/seeder.py`.
   - Cập nhật node `knowledge_answer` trong `configs/workflows/admissions-assistant.v1alpha1.json`.
   - Chạy script `backend/scripts/sync_assistant_prompts.py` đồng bộ thành công cả 5 Trợ lý chuẩn vào PostgreSQL.
5. **Đồng bộ Quy trình Hệ thống**:
   - Bổ sung Bước 12 (*Ràng Buộc Thực Thể, Chỉ Đạo Định Dạng & Bộ Lọc Hậu Xử Lý*) vào `docs/quy_trinh/03_hybrid_rag_truy_xuat.md`.
6. **Kiểm thử Toàn diện**:
   - Tạo bộ test tự động `backend/tests/test_rag_entity_scoped_formatting.py` (6/6 tests passed).

## 4. Kết Quả Kiểm Thử (Verification)
- **Backend Tests**:
  * `uv run --extra dev pytest tests/test_rag_entity_scoped_formatting.py -v`: 6 passed (100%).
  * `uv run --extra dev pytest tests/test_rag.py -v`: 26 passed (100%).
  * `uv run ruff check .`: 0 lỗi.
- **Frontend Tests**:
  * `npm run lint`: 169 files checked, 0 lỗi.
  * `npm run typecheck`: 0 lỗi.
  * `npm run build`: Vite build thành công (8.38s).
- **Thử nghiệm Thực tế (Live Database & ModelOps)**:
  * Câu hỏi 1: *"bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?"*
    $\rightarrow$ Kết quả: Trả lời chuẩn xác duy nhất ngành CNTT (mã 7480201), danh sách 5 tổ hợp môn sạch sẽ, giải thích rõ các phương thức 1, 2, 3, 4; 0 ký tự `||||||` rác, 0 ngành Luật/Hóa học thừa thãi.
  * Câu hỏi 2: *"xin chào cho tôi biết các phương thức tuyển sinh năm 2026 của trường"*
    $\rightarrow$ Kết quả: Bảng Markdown 5 phương thức tuyển sinh chính thức kèm mã 100, 200, 402A, 402B, 405; không bị thừa học phí.
