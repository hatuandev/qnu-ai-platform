# Nhật Ký Làm Việc — Phiên #178
**Ngày thực hiện**: 2026-09-21
**Mục tiêu chính**: Khắc phục hiện tượng Trợ lý Tuyển sinh tự ý trả lời thêm học phí khi người dùng chỉ hỏi phương thức xét tuyển, thiết lập chốt chặn phạm vi (Focus / Scope Guardrail) và đồng bộ CSDL.

---

## 1. Bối Cảnh & Vấn Đề

Người dùng phản ánh:
> *"ok tôi biết rồi, bạn xem giúp tôi sao tôi hỏi câu 'xin chào cho tôi biết phương thức tuyển sinh năm 2026' thì nó trả lời luôn học phí ?"*

Kèm ảnh chụp màn hình Trợ lý Tuyển sinh trả lời:
- Mục 1: Các phương thức tuyển sinh năm 2026
- Mục 2: Thông tin về học phí (83-97 triệu, 112,3 triệu)

### Phân Tích Nguyên Nhân Kỹ Thuật (Root Cause Analysis):
1. **Tầng RAG Hybrid Retrieval**:
   - Khi tìm kiếm câu hỏi `"xin chào cho tôi biết phương thức tuyển sinh năm 2026"`, bộ Hybrid Retriever (kết hợp vector Qdrant và lexical FTS) tìm thấy 5 chunks có điểm tương đồng cao nhất trong tài liệu Đề án tuyển sinh 2026 (`doc_f0c17c002219`).
   - Do tại Mục 8 (Trang 10) có chứa cụm từ *"Lệ phí xét tuyển, thi tuyển, học phí... phương thức xét tuyển"*, đoạn văn bản này được bóc tách vào context gửi cho LLM.
2. **Tầng System Prompt & LLM Generation**:
   - Trong `ast_admissions.system_prompt` trên CSDL PostgreSQL có chỉ dẫn:
     * *"Khi trả lời về học phí: Nêu rõ các khung học phí liên quan trong đề án (cử nhân đại trà 83-97 triệu đồng...)"*.
   - Prompt cũ thiếu một **chốt chặn phạm vi (Scope Constraint)** nghiêm ngặt. Khi LLM nhìn thấy trong ngữ cảnh có đoạn Mục 8 ("Lệ phí xét tuyển, thi tuyển, học phí") kèm theo hướng dẫn cụ thể về học phí trong system prompt, mô hình sinh ngữ (đặc biệt là các dòng Flash/Lite) bị **"thiên kiến quá nhiệt tình"** (over-helpfulness bias), tự động suy diễn rằng người dùng hỏi phương thức tuyển sinh thì cũng muốn nắm luôn học phí và đưa cả Mục 2 vào câu trả lời.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Technical Changes)

### 2.1. Cập Nhật Mẫu System Prompt Toàn Cục (`backend/app/modules/rag/composer.py`)
- Bổ sung quy tắc **BÁM SÁT TRỌNG TÂM CÂU HỎI** vào `SYSTEM_PROMPT_TEMPLATE`:
  ```text
  - BÁM SÁT TRỌNG TÂM CÂU HỎI: Chỉ trả lời đúng và đủ khía cạnh người dùng hỏi. Tuyệt đối không tự ý mở rộng sang các chủ đề khác (như học phí, điểm chuẩn, lệ phí, ký túc xá) nếu câu hỏi không yêu cầu.
  ```

### 2.2. Cập Nhật Cấu Hình Workflow Tuyển Sinh (`configs/workflows/admissions-assistant.v1alpha1.json`)
- Cập nhật `system_prompt` của node `knowledge_answer`, siết chặt chốt chặn phạm vi.

### 2.3. Cập Nhật Seeder & CSDL PostgreSQL (`backend/app/modules/assistants/seeder.py`)
- Xóa bỏ hoàn toàn các con số tiền học phí cụ thể (83-97 triệu, 112,3 triệu, 1,5 lần) ghim cứng trong system prompt để tránh lỗi thời qua các năm học.
- Cập nhật `ast_admissions.system_prompt` theo nguyên tắc động, thường trực (evergreen):
  * *"BÁM SÁT TRỌNG TÂM: Chỉ trả lời đúng và đủ khía cạnh người dùng hỏi. Tuyệt đối KHÔNG tự ý đưa thêm học phí, điểm chuẩn, lệ phí nếu câu hỏi không yêu cầu. Mọi thông tin số liệu (học phí, chỉ tiêu, điểm chuẩn) phải trích xuất chính xác theo đúng tài liệu đề án của năm học đang xét, không suy diễn hoặc tự bịa đặt số liệu."*
- Đã đồng bộ trực tiếp vào CSDL PostgreSQL cho bản ghi Trợ lý `admissions`.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Thử nghiệm 1 (Hỏi phương thức xét tuyển)**:
   - Gửi câu hỏi: `"xin chào cho tôi biết phương thức tuyển sinh năm 2026"`.
   - Kết quả: Trả lời đúng 5 phương thức tuyển sinh chính quy và xét tuyển thẳng, **0% thông tin học phí**. Đầy đủ 5 trích dẫn PDF.
2. **Thử nghiệm 2 (Hỏi học phí)**:
   - Gửi câu hỏi: `"cho tôi biết mức học phí năm 2026 của trường là bao nhiêu?"`.
   - Kết quả: Quy trình RAG DAG tự động bóc tách từ tài liệu đề án tuyển sinh 2026 nạp vào hệ thống để trả lời chính xác: cử nhân đại trà 83-97 triệu, kỹ sư 112,3 triệu, chương trình tiếng Anh 1,5x. Đầy đủ 4 trích dẫn PDF.
3. **Backend**:
   - `uv run ruff check .`: **0 lỗi**.
   - `uv run --extra dev pytest tests/test_assistants.py tests/test_workflows.py tests/test_rag.py -v`: **52/52 passed (100%)**.
4. **Frontend**:
   - `npm run lint`: **Biome check 168 files: 0 lỗi**.
