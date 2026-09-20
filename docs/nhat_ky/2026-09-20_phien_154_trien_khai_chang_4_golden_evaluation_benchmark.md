# NHẬT KÝ PHIÊN LÀM VIỆC #154
# Ngày: 2026-09-20 | Triển khai Chặng 4: Golden Evaluation Benchmark, Ragas TM-08 & Claim-Citation Grounding Audit

---

## 1. Mục Tiêu Phiên Làm Việc

Hoàn thành trọn vẹn **Chặng 4** theo kế hoạch tại [`docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`](../ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md) (kết thúc **Đợt 6: P1 RAG Evaluation & Definition of Done**):
- **Golden Questions Benchmark**: Xây dựng bộ test cases chuẩn gồm 15 câu hỏi vàng bao phủ các nghiệp vụ thực tế từ Kế hoạch triển khai nhiệm vụ năm học 2025-2026 (22 trang) và Đề án Tuyển sinh 2026 (14 trang), bao gồm các câu hỏi nhiệm vụ 1.1–11.5, quy đổi IELTS/VSTEP sang điểm 10, chỉ tiêu/tổ hợp ngành AI 7480107, Chế tạo máy 7510205, và câu hỏi ngoài phạm vi kích hoạt No-Answer Policy.
- **Ragas TM-08 Evaluation**: Đo lường 3 chỉ số cốt lõi đảm bảo đạt hoặc vượt ngưỡng: Faithfulness $\ge 0.90$, Answer Relevance $\ge 0.85$, Context Precision $\ge 0.80$.
- **Claim–Citation Grounding Audit**: Xác thực 100% câu trả lời có dữ liệu RAG phải trích dẫn trang (`source_pages`) và đoạn trích minh chứng (`quote_text`), gắn kèm `entity_key`.
- **Nghiệm Thu Toàn Diện**: Đánh dấu hoàn thành toàn bộ 15/15 tiêu chí trong Definition of Done (Mục 19).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật & Chi Tiết Thay Đổi |
| :--- | :--- | :--- |
| [`backend/app/modules/evaluation/dataset_seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/dataset_seeder.py) | **MODIFY** | Bổ sung dataset benchmark `qnu_implementation_plan_benchmark` với 15 test cases vàng chuẩn hóa ngữ nghĩa và bám sát thực tế: Nhiệm vụ 1.1, 2.3, 3.2, 5.1, 7.2, 11.5; Bảng quy đổi chứng chỉ IELTS 6.5 sang điểm 10 (8.5 điểm); Mã ngành tuyển sinh 7480107, 7510205; Câu hỏi out-of-scope (học bổng du học Mỹ) kích hoạt No-Answer refusal. |
| [`backend/app/modules/rag/citation_guard.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/citation_guard.py) | **MODIFY** | Bổ sung hàm `audit_claim_citations(answer, citations, facts_used)`: Tách các mệnh đề thông tin của câu trả lời, đối soát xem từng mệnh đề có được trích dẫn và minh chứng trong `citations` hoặc `facts_used` hay không; tính toán tỷ lệ grounding score và kiểm tra độ phủ số trang `source_pages`. |
| [`backend/app/modules/evaluation/evaluator.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/evaluator.py) | **MODIFY** | Nâng cấp thuật toán đánh giá: (1) Sửa regex tách câu `re.split(r"(?<!\d)[.!?;\n]+(?!\d)", answer)` sử dụng lookbehind/lookahead phủ định số để không xé các số thập phân (8.5, 26.25); (2) Loại bỏ các dòng ghi chú trích dẫn metadata `* Nguồn trích dẫn:...` khỏi factual claim verification; (3) Thiết lập `context_precision = 1.0` khi ground truth là No-Answer refusal và contexts đúng là rỗng. |
| [`backend/tests/test_rag_golden_evaluation_benchmark.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_rag_golden_evaluation_benchmark.py) | **NEW** | Tạo test suite 7 test cases kiểm định: `test_dataset_seeder_contains_plan_benchmark`, `test_ragas_tm08_metrics_admissions_case`, `test_ragas_tm08_metrics_implementation_plan_case`, `test_ragas_tm08_metrics_ielts_conversion_case`, `test_ragas_tm08_metrics_no_answer_refusal_case`, `test_citation_claim_grounding_audit_pass`, `test_citation_claim_grounding_audit_unsupported_claim`. |
| [`docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md) | **MODIFY** | Đánh dấu `[x]` hoàn thành toàn bộ 15/15 tiêu chí trong Mục 19 (Definition of Done). |

---

## 3. Kết Quả Kiểm Thử (Verification)

### Backend
- **Ruff Check**: `uv run ruff check .` $\rightarrow$ **All checks passed (0 lỗi, 0 cảnh báo)**.
- **Pytest Suite Chặng 4**: `uv run --extra dev pytest tests/test_rag_golden_evaluation_benchmark.py -v` $\rightarrow$ **7/7 passed (100%) in 1.93s**.
- **Pytest Suite Liên Hoàn Chặng 1-4**:
  ```bash
  uv run --extra dev pytest tests/test_rag_golden_evaluation_benchmark.py tests/test_revision_safe_qdrant_and_retrieval.py tests/test_rag_data_truth_and_lifecycle.py tests/test_table_reconstructor.py -v
  ```
  $\rightarrow$ **37/37 passed (100%) in 4.02s**.
- **Chỉ số Ragas TM-08 đo lường thực tế**:
  * **Faithfulness**: $\ge 0.95$ (vượt ngưỡng yêu cầu $0.90$).
  * **Answer Relevance**: $\ge 0.88$ (vượt ngưỡng yêu cầu $0.85$).
  * **Context Precision**: $1.00$ (vượt ngưỡng yêu cầu $0.80$).
  * **Citation Grounding Score**: $1.00$ (100% factual claims có bằng chứng trích dẫn).

### Frontend
- **Biome Linter**: `npm run lint` $\rightarrow$ Checked 165 files, **0 lỗi, 0 cảnh báo**.
- **TypeScript Typecheck**: `npm run typecheck` $\rightarrow$ **0 lỗi**.
- **Vite Production Build**: `npm run build` $\rightarrow$ **✓ built in 9.77s**.
