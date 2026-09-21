# Nhật Ký Làm Việc — Phiên #179 (2026-09-21)
# Khắc Phục Lỗi RAG Không Bắt Được Tổ Hợp Môn Ngành CNTT (Entity Augmentation) & Chống Rò Rỉ Few-Shot Prompt Trong Query Rewrite

## 1. Bối Cảnh & Vấn Đề Người Dùng Báo Cáo
Người dùng kiểm thử 3 câu hỏi liên tiếp với Trợ lý Tuyển sinh ĐH Quy Nhơn:
1. `"bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?"`
2. `"ý tôi muốn hỏi là tổ hợp môn xét tuyển của ngành công nghệ thông tin"`
3. `"xin chào cho tôi biết phương thức tuyển sinh năm 2026"`

Phát hiện các hiện tượng bất thường:
- **Hiện tượng 1 (Thừa thông tin học phí)**: Ở câu 3, trợ lý tự ý đưa thêm học phí (đã xử lý ở phiên #178 qua Scope Guardrail). Người dùng yêu cầu xóa số tiền học phí cố định trong prompt để hệ thống tự tra cứu động qua RAG.
- **Hiện tượng 2 (Câu 2 không trả lời được tổ hợp môn)**: Khi hỏi câu 2 `"ý tôi muốn hỏi là tổ hợp môn xét tuyển của ngành công nghệ thông tin"`, RAG trả lời *"Rất tiếc là trong các đoạn tài liệu hiện tại mình đang nắm giữ chưa có thông tin chi tiết về các tổ hợp môn xét tuyển cụ thể của ngành Công nghệ thông tin"*, trong khi văn bản Đề án tuyển sinh 2026 tại Trang 6 có đầy đủ bảng tổ hợp môn của ngành CNTT mã `7480201`.
- **Hiện tượng 3 (Rò rỉ ví dụ Few-Shot trong Query Rewrite khi trò chuyện liên tục)**: Khi chạy trong luồng hội thoại nhiều lượt (Multi-turn), câu 3 bất ngờ trả lời về *"Điểm chuẩn Quản trị kinh doanh năm 2024 là 17 điểm"*.

## 2. Phân Tích Nguyên Nhân Cốt Lõi (Root Cause Analysis)

### 2.1. Tại sao RAG bỏ sót Trang 6 khi hỏi câu 2?
- Trong tài liệu Đề án tuyển sinh 2026 (PDF), ngành Công nghệ thông tin được liệt kê trong bảng dưới dạng: `Mã xét tuyển: 7480201`, `Tên ngành: Công nghệ thông tin`, `Tổ hợp: (Toán, Anh, Lý) (Toán, Anh, Văn) (Toán, Anh, Hóa)...`.
- Khi người dùng hỏi `"ý tôi muốn hỏi là tổ hợp môn xét tuyển của ngành công nghệ thông tin"`, từ khóa `"công nghệ thông tin"` bị phân tán giữa nhiều ngành kỹ thuật và các trang phụ lục.
- `QueryClassifier.analyze()` đã trích xuất được `entity_codes: ['7480201']`, nhưng trong `rag_service.py`, chuỗi query gửi sang Hybrid Retriever (`dense` + `sparse FTS`) chỉ dùng raw query của người dùng mà **không đính kèm entity_code** vào câu truy vấn. Do đó, điểm BM25/FTS và vector dense không ưu tiên đúng trang chứa mã ngành `7480201` (Trang 6), dẫn đến Trang 6 bị rớt khỏi top_k.

### 2.2. Tại sao Query Rewrite bị rò rỉ "Điểm chuẩn QTKD 2024"?
- Trong `backend/app/modules/workflows/nodes/query_rewrite_node.py`, hàm `build_rewrite_prompt` có ví dụ few-shot:
  ```
  Input: diem chuan qtkd nam 2024
  Điểm chuẩn ngành Quản trị kinh doanh năm 2024 là bao nhiêu?
  ```
- Khi gọi LLM rewrite cho câu `"xin chào cho tôi biết phương thức tuyển sinh năm 2026"`, nếu mô hình trích xuất ứng viên bị trôi hoặc lặp dòng ví dụ trước đó, candidate nhận được câu hỏi QTKD.
- Bộ lọc phòng vệ `query_words & cand_words` trước đây chỉ loại bỏ 5 từ (`"bạn", "biết", "không", "cho", "nào"`). Cả câu hỏi gốc (năm 2026) và candidate (năm 2024) đều chứa từ `"năm"`. Vì `{"năm"} & {"năm"}` khác rỗng nên guard clause bị vượt qua, chấp nhận câu hỏi QTKD và chuyển sang RAG.
- Ngoài ra, `get_node_instruction` gặp lỗi `AttributeError: 'AssistantPersonaScope' object has no attribute 'role_description'` (do thuộc tính đúng là `persona`).

## 3. Các Giải Pháp Đã Triển Khai

### 3.1. Entity Code Augmentation trong RAG Service (`backend/app/modules/rag/service.py`)
- Khi `QueryClassifier` phân tích câu hỏi và nhận diện được mã thực thể (ví dụ: mã ngành `7480201` cho CNTT, `7340101` cho QTKD):
  ```python
  # Augment retrieval query with detected entity codes (e.g. program codes 7480201)
  retrieval_query = req.question
  if analysis.entity_codes:
      extra_tokens = [c for c in analysis.entity_codes if c not in retrieval_query]
      if extra_tokens:
          retrieval_query = f"{retrieval_query} {' '.join(extra_tokens)}"
  ```
- Nhờ bổ sung mã ngành `7480201`, cả PostgreSQL Full-Text Search và Qdrant Vector Search đều nhắm trúng Trang 6 của Đề án tuyển sinh với điểm số cao nhất.

### 3.2. Chuẩn Hóa Stopwords & Loại Bỏ Ví Dụ Gây Nhiễu (`query_rewrite_node.py`)
1. **Sửa thuộc tính `persona_scope`**: Sử dụng `getattr(persona_scope, "persona", None)` thay vì truy cập cứng `role_description`.
2. **Loại bỏ ví dụ QTKD năm cũ**: Thay thế ví dụ trong few-shot prompt thành ví dụ chuẩn hóa câu hỏi tổ hợp môn, triệt tiêu nguy cơ rò rỉ năm 2024 và ngành QTKD.
3. **Mở rộng Stopwords phòng vệ đa từ**:
   ```python
   _stopwords = {
       "bạn", "biết", "không", "cho", "nào", "tôi", "xin", "chào", "năm",
       "được", "các", "những", "với", "của", "thế", "như", "bao", "nhiêu",
       "gì", "là", "và", "trong", "trường", "đại", "học", "muốn", "hỏi"
   }
   ```
   Bảo đảm candidate rewrite chỉ được chấp nhận nếu có sự trùng khớp từ khóa ngữ nghĩa thực chất (ví dụ: `phương thức`, `tuyển sinh`, `tổ hợp`, `công nghệ`, `thông tin`).

### 3.3. Tinh Chỉnh Stopwords Trong `query_router.py`
- Loại bỏ các phần tử trùng lặp trong set `VI_CONVERSATIONAL_STOPWORDS` (`"thế"`, `"nào"`) đảm bảo Ruff linter đạt 100% không cảnh báo `B033`.

## 4. Kết Quả Kiểm Thử Toàn Diện

### 4.1. Kiểm Thử Đơn Lẻ 3 Câu Hỏi (Clean Session)
- **Câu 1**: `"bạn biết ngành công nghệ thông tin cần những môn học nào để xét tuyển không ?"`
  * Kết quả: Trả lời chính xác 5 tổ hợp môn `(Toán, Tiếng Anh, Vật lý)`, `(Toán, Tiếng Anh, Ngữ văn)`, `(Toán, Tiếng Anh, Hóa học)`, `(Toán, Tiếng Anh, Tin học)`, `(Toán, Tiếng Anh, Giáo dục Kinh tế và Pháp luật)`.
  * Trích dẫn: 6 trích dẫn PDF (Trang 6, Trang 3, Trang 13, Trang 12, Trang 2, Trang 8).
- **Câu 2**: `"ý tôi muốn hỏi là tổ hợp môn xét tuyển của ngành công nghệ thông tin"`
  * Kết quả: Trả lời chính xác 5 tổ hợp môn kèm tên chuyên ngành An toàn, an ninh mạng.
  * Trích dẫn: 6 trích dẫn PDF (Trang 6, Trang 12, Trang 13, Trang 3, Trang 2, Trang 11).
- **Câu 3**: `"xin chào cho tôi biết phương thức tuyển sinh năm 2026"`
  * Kết quả: Trả lời đầy đủ 5 phương thức tuyển sinh (100, 200, 402A, 402B, 405) + Xét tuyển thẳng. **100% không có học phí bị đưa thừa vào**.
  * Trích dẫn: 8 trích dẫn PDF (Trang 3, 1, 9, 11, 2, 7, 12).

### 4.2. Kiểm Thử Hội Thoại Đa Lượt (Multi-Turn Conversation Trong 1 Thread Duy Nhất)
- Chạy liên tiếp cả 3 câu hỏi trong cùng một `thread_id`:
  * Turn 1: Trả lời đúng tổ hợp môn ngành CNTT (Trang 6) ✅
  * Turn 2: Tiếp nối mạch hội thoại, trả lời đúng tổ hợp môn (Trang 6) ✅
  * Turn 3: Trả lời đúng 5 phương thức tuyển sinh 2026, không rò rỉ QTKD, không thừa học phí ✅

### 4.3. Kiểm Tra Chất Lượng Mã Nguồn (CI / Verification)
- **Backend Ruff**: `uv run ruff check .` -> **0 lỗi (All checks passed!)**.
- **Backend Pytest**: `uv run --extra dev pytest tests/test_rag.py tests/test_workflows.py -v` -> **40/40 passed (100%) in 4.22s**.
- **Frontend Biome**: `npm run lint` -> **Checked 168 files in 178ms. 0 errors**.
- **Frontend TypeScript**: `npm run typecheck` -> **0 errors**.
