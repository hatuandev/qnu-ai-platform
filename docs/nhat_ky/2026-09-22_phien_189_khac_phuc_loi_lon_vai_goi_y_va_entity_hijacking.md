# NHẬT KÝ LÀM VIỆC — PHIÊN #189
**Thời gian**: 2026-09-22 00:00  
**Mục tiêu**: Khắc phục triệt để lỗi lộn vai nút gợi ý (Suggestion Chip Perspective Inversion) và chống hiện tượng Entity Hijacking / Intent Drift trong xử lý hội thoại đa lượt.

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật
Khi người dùng trao đổi với Trợ lý Tuyển sinh:
- **Lỗi 1 (Lộn vai Nút Gợi Ý)**: Mô hình kết bài bằng câu hỏi tu từ bot hỏi người dùng: *"Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"*. Parser lấy nguyên văn câu này đưa lên giao diện làm nút bấm gợi ý (Suggestion Chip). Khi người dùng click vào nút, tin nhắn gửi đi trở thành người dùng hỏi bot bằng đúng câu *"Bạn có muốn..."*, tạo cảm giác ngô nghê và ngược vai trò.
- **Lỗi 2 (Entity Hijacking & Hallucination đa lượt)**: Khi nhận được câu *"Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"*, hệ thống RAG bóc tách từ *"cụ thể nào"* thành `target_entities = ["Cụ Thể Nào"]`, hoặc tầng Query Rewrite lôi tên ngành (CNTT) từ các lượt trao đổi cũ vào để ép câu hỏi thành hỏi về CNTT, làm biến dạng hoàn toàn ý định của người dùng.

---

## 2. Các Thay Đổi Kỹ Thuật (Key Changes)
1. **Chuẩn Hóa Góc Độ Nút Gợi Ý (`backend/app/modules/rag/composer.py`)**:
   - Cập nhật `SYSTEM_PROMPT_TEMPLATE`: Bổ sung chỉ thị bắt buộc 100% câu gợi ý phải viết từ góc độ Người dùng hỏi Trợ lý (*"Tổ hợp môn xét tuyển ngành Công nghệ thông tin gồm những môn nào?"*, *"Chỉ tiêu tuyển sinh năm 2026 là bao nhiêu?"*). Tuyệt đối cấm câu hỏi bắt đầu bằng *"Bạn có muốn..."*, *"Bạn có quan tâm..."*.
   - Triển khai `convert_or_filter_suggestion_perspective(candidate: str) -> str | None`:
     * Nhận diện tiền tố đảo vai (`Bạn có muốn...`, `Bạn có quan tâm...`, `Bạn có cần...`, `Mình có thể...`).
     * Chuyển đổi thông minh các câu hỏi lộn vai sang câu hỏi người dùng (*"Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"* $\rightarrow$ *"Các ngành của trường xét tuyển những tổ hợp môn nào?"*).
     * Loại bỏ hoàn toàn các câu hỏi lịch sự không thể chuyển đổi an toàn (*"Bạn có muốn mình chia sẻ gì thêm không?"* $\rightarrow$ `None`).
   - Cập nhật `_extract_candidates_from_block` và `extract_suggested_questions` để lọc toàn bộ candidate qua hàm chuyển đổi này.

2. **Chống Entity Hijacking trong Query Router (`backend/app/modules/rag/query_router.py`)**:
   - Tại bộ lọc Regex nhận diện tên ngành, bổ sung danh sách loại trừ các từ định danh không xác định/placeholder (*"cụ thể"*, *"cụ thể nào"*, *"nào đó"*, *"nào"*, *"gì"*, *"bất kỳ"*, *"khác"*, *"này"*, *"đó"*, *"mới"*).
   - Ngăn chặn hoàn toàn việc gán `target_entities = ["Cụ Thể Nào"]`.

3. **Chống Thiên Kiến Ngành trong Query Rewrite (`backend/app/modules/workflows/nodes/query_rewrite_node.py`)**:
   - `extract_entity_from_text`: Bổ sung điều kiện loại trừ các từ placeholder mơ hồ.
   - `build_rewrite_prompt`: Bổ sung quy tắc phòng vệ: TUYỆT ĐỐI KHÔNG tự ý suy diễn hoặc gán ghép tên ngành vào câu hỏi nếu câu hỏi gốc không chứa tên ngành và lượt chat trước đó là câu hỏi chung. Thay thế ví dụ few-shot trùng lặp bằng ngành khác (Sư phạm Toán học).

4. **Đồng Bộ CSDL & Seeder (`backend/app/modules/assistants/seeder.py`, `scripts/sync_assistant_prompts.py`)**:
   - Cập nhật prompt trợ lý tuyển sinh trong seeder.
   - Chạy script đồng bộ prompt mới vào CSDL PostgreSQL cho các assistant chuẩn.

5. **Bộ Kiểm Thử Tự Động (`backend/tests/test_suggestion_perspective_and_multiturn.py`)**:
   - 9 ca kiểm thử toàn diện bao quát: chuyển đổi góc độ câu hỏi chung/ngành cụ thể, học phí, học bổng, lọc rác lịch sự, giữ nguyên câu hỏi chuẩn của người dùng, làm sạch khối gợi ý, và bảo vệ thực thể đa lượt.

---

## 3. Kết Quả Kiểm Thử (Verification)
- `uv run --extra dev pytest tests/test_suggestion_perspective_and_multiturn.py`: 9 passed in 2.41s.
- `uv run --extra dev pytest tests/test_rag.py tests/test_multiturn_and_provider_safety.py`: 32 passed in 4.55s.
- `uv run ruff check .`: All checks passed!
- `npm run lint`: 169 files checked, 0 errors.
- `npm run typecheck`: 0 errors.
- Test Live Chat E2E: Nút gợi ý sinh ra hoàn toàn từ góc độ người dùng, click vào trả lời mượt mà, chính xác.
