# NHẬT KÝ LÀM VIỆC — PHIÊN #238
**Thời gian**: 2026-10-01 17:25 (UTC+7)  
**Vai trò**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Chủ đề**: Chuẩn Hóa Thuật Toán Tổng Quát Bóc Tách Bảng (Sub-header Invariant) & Tập Trung Hóa Từ Điển Đánh Giá Ragas TM-08 Theo Tôn Chỉ 7 AGENTS.md

---

## 1. Bối Cảnh & Yêu Cầu Của Người Dùng

Trong phiên làm việc này, Người dùng đã đưa ra chuỗi câu hỏi và yêu cầu rà soát chất lượng kiến trúc hệ thống:
1. **Kiểm tra tính hiệu lực của `max_tokens`**: Người dùng thắc mắc tham số `max_tokens` khi cấu hình trên giao diện Trợ lý AI (`/assistants`) có thực sự hoạt động hay không, và mức `4000` tokens có ổn định cho nghiệp vụ hay không.
2. **Rà soát vị trí áp dụng thuật toán trong toàn bộ repository**: Người dùng muốn biết các thuật toán trong hệ thống hiện đang nằm ở đâu, có phải chỉ dùng cho RAG hay còn ở các phân hệ khác.
3. **Rà soát và chuẩn hóa thuật toán ngoài RAG**: Sau khi xác định thuật toán RAG đã ổn định, người dùng yêu cầu rà soát các phân hệ còn lại và chuẩn hóa 2 điểm phát hiện có hardcode từ khóa/từ vựng sang thuật toán tổng quát và từ điển cấu hình tập trung theo đúng Tôn chỉ 7 của `AGENTS.md`.

---

## 2. Kết Quả Rà Soát & Kiến Trúc Đã Xác Minh

### 2.1. Phân Tích & Xác Minh Tham Số `max_tokens`
- **Luồng truyền tham số hoàn chỉnh**:
  - Giao diện Frontend (`assistant-models-section.tsx`) $\rightarrow$ API `PUT /assistants/:id` lưu vào cột `config.model_policy.max_tokens` trong CSDL PostgreSQL.
  - Runtime Profile Builder (`build_runtime_profile`) nạp `max_tokens` vào `AssistantRuntimeProfile.model_policy`.
  - DAG Workflow Node Handler (`llm_generate_node.py`) trích xuất `max_tokens` từ `profile.model_policy` và gán vào `LLMGenerateRequest.max_tokens`.
  - `InferenceService` nhận `request.max_tokens` và chuyển trực tiếp sang tham số adapter của từng Provider (`OpenAIAdapter`, `GeminiAdapter`, `MistralAdapter`).
- **Đánh giá mức `4000` tokens**:
  - Hoàn toàn tối ưu: Nằm an toàn trong dải cho phép của ModelOps (50 - 8192 tokens) và vượt trên mức sàn 2048 tokens cần thiết cho cơ chế suy luận Thinking/Reasoning của Google Gemini 2.5 Flash / Nemotron.

### 2.2. Bản Đồ Thuật Toán Toàn Nền Tảng (Algorithms Map)
- Hệ thống áp dụng thuật toán trên 5 phân hệ cốt lõi:
  1. **Hybrid RAG & Retrieval Engine**: Reciprocal Rank Fusion (RRF), Cross-Encoder Reranking, Morphological Entity Matching, Stopwords Dynamic Suppression.
  2. **Knowledge Ingestion & Chunking**: ClauseBasedChunker (cây ngữ pháp điều khoản pháp lý), SemanticChunker (tương đồng cosine trượt).
  3. **OCR & Table Reconstruction**: Morphological Stitcher (hàn gắn từ qua ranh giới trang), Table Reconstructor (khôi phục cấu trúc bảng liên trang, forward-fill phân cấp).
  4. **DAG Workflow Engine**: Topological Sort, Directed Acyclic Graph traversal, HITL state machine.
  5. **Evaluation Engine (TM-08)**: Ragas Average Precision at k (AP@k), Heuristic Faithfulness & Relevance overlap scoring.

---

## 3. Các Thay Đổi Mã Nguồn & Tinh Chuẩn Kỹ Thuật

### 3.1. Chuẩn Hóa Nhận Diện Hàng Tiêu Đề Con Theo Bất Biến Hình Thái Học
- **Tệp thay đổi**: `backend/app/modules/knowledge/normalization/table_reconstructor.py`
- **Nguyên nhân**: Hàm `is_sub_header_row` trước đây sử dụng mảng từ khóa gán cứng `sub_header_kws = ["chỉ tiêu", "trúng tuyển", "điểm", "nhập học", "xét tuyển", "tuyển sinh"]`, vi phạm Tôn chỉ 7 của `AGENTS.md`.
- **Giải pháp**: Loại bỏ hoàn toàn mảng từ khóa cứng, thay thế bằng **Bất biến Hình thái học & Cấu trúc Dữ liệu tổng quát**:
  1. `first_three_empty`: 3 ô đầu tiên của hàng rỗng (đặc trưng thụt lề phân cấp).
  2. `len(non_empty) >= 2`: Hàng chứa ít nhất 2 ô có nội dung.
  3. Độ dài nhãn tiêu đề: Mọi ô văn bản đều ngắn gọn ($\le 60$ ký tự) và không kết thúc bằng dấu chấm câu `.` hoặc `;` (phân biệt với đoạn văn mô tả / ghi chú nhiều dòng).
  4. Tỷ lệ ký tự chữ cái cao: `alpha_ratio >= 0.70` (xác nhận đây là văn bản phân loại chuyên mục).
  5. Tỷ lệ ký tự số thấp: `numeric_ratio <= 0.25` (loại trừ các hàng số liệu đo lường).

### 3.2. Tập Trung Hóa Từ Điển Từ Dừng Đánh Giá Ragas TM-08
- **Tệp thay đổi**:
  - `configs/stopwords_vi.txt` & `backend/app/core/resources/stopwords_vi.txt`
  - `backend/app/modules/evaluation/evaluator.py`
- **Nguyên nhân**: `evaluator.py` tự khai báo biến `set` cứng `VIETNAMESE_QUESTION_STOPWORDS` (60 từ) trong code, dẫn tới sự thiếu đồng bộ với hệ thống từ dừng chung và khó tùy biến cho cán bộ vận hành.
- **Giải pháp**:
  1. Bổ sung 15 từ nghi vấn/hư từ tiếng Việt vào phần `# --- 4. Từ nghi vấn, Yêu cầu & Cụm từ công thức ---` trong tệp cấu hình tập trung `stopwords_vi.txt`: `áp, dụng, chuẩn, cụ, thể, gồm, hay, hãy, hỏi, mấy, nêu, rõ, thường, đh, đối`.
  2. Trong `evaluator.py`: Thay thế hardcode bằng hàm `get_vietnamese_stopwords()` nạp động từ file tài nguyên cấu hình ngoài, giữ `VIETNAMESE_QUESTION_STOPWORDS` làm alias tương thích ngược.

---

## 4. Kết Quả Kiểm Thử & Đảm Bảo Chất Lượng (Verification)

1. **Bộ kiểm thử toàn diện**:
   - `pytest tests/test_stopwords.py`: **6/6 passed**
   - `pytest tests/test_evaluation_truthful.py`: **7/7 passed**
   - `pytest tests/test_evaluation.py`: **8/8 passed**
   - `pytest tests/test_table_reconstructor.py`: **18/18 passed**
   - `pytest tests/test_table_stitching_and_page_partition.py`: **14/14 passed**
   - $\rightarrow$ **Tổng cộng: 53/53 tests PASSED 100% trong 3.19s**.
2. **Kiểm tra Linter & Formatting**:
   - `ruff check app/modules/knowledge app/modules/evaluation app/core/stopwords.py` $\rightarrow$ **All checks passed! (0 cảnh báo, 0 lỗi)**.

---

## 5. Trạng Thái & Công Việc Tiếp Theo
- **Trạng thái**: HOÀN THÀNH 100%.
- **Tuân thủ Git**: Không chạy `git push`, giữ nguyên commit cục bộ để Người dùng tự chủ động kiểm soát.
