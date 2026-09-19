# NHẬT KÝ PHIÊN LÀM VIỆC #126
**Ngày**: 2026-09-19 22:15 | **Kỹ sư**: AI Senior Full-Stack Architect  
**Mục tiêu**: Triển khai Giai đoạn 4 (Evaluation Trung Thực & Quality Gate AI) theo Kế hoạch Cải thiện Toàn diện 07 ([`docs/ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md`](../ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md) — Đợt 7).

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Sau khi hoàn thành Giai đoạn 3 (Workflow, Tools & Multi-Turn Conversations), Giai đoạn 4 tập trung giải quyết 3 bất cập lớn trong hệ thống đánh giá chất lượng Trợ lý AI và cổng kiểm soát xuất bản (Quality Gate / Readiness Engine):

1. **Lưu Vết Kết Quả Từng Câu Hỏi Benchmark (`EvaluationResultItem`)**:
   - Trước đây, khi chạy benchmark Ragas TM-08 (`POST /evaluation/run`), hệ thống chỉ tính điểm trung bình tổng thể và lưu một bản ghi duy nhất trong bảng `evaluation_runs`. Bảng `evaluation_result_items` hoàn toàn trống rỗng (zero records).
   - Người quản trị và cán bộ phụ trách không thể drill-down kiểm tra: câu hỏi nào bị ảo giác (hallucination)? Câu hỏi nào bị từ chối (refusal)? Trợ lý đã trả lời chi tiết ra sao và trích dẫn những context nào?
   - **Mục tiêu**: Bổ sung các trường nghiệp vụ quan trọng (`execution_path`, `is_refusal`, `reasoning`) vào `evaluation_result_items`; lưu đầy đủ bản ghi từng câu hỏi vào PostgreSQL; cung cấp API chi tiết `GET /evaluation/runs/{run_id}` và `GET /evaluation/runs/{run_id}/items`.

2. **Evaluator Engine Đa Chế Độ & Chống Đánh Giá Lệch Pha (Truthful Evaluation)**:
   - Cơ chế đánh giá cũ (`evaluator.py`) sử dụng heuristic từ khóa đơn giản. Khi gặp câu trả lời No-Answer Policy ("*Xin lỗi, tôi không tìm thấy thông tin...*"), hệ thống vẫn có thể chấm điểm answer relevance cao nếu câu hỏi có chứa các từ khóa tương đồng, dẫn tới hiện tượng Trợ lý AI không biết trả lời nhưng vẫn "ăn điểm" relevance cao một cách vô lý.
   - **Mục tiêu**:
     - Thiết kế kiến trúc `BaseTM08Evaluator` với 2 chế độ: `HeuristicTM08Evaluator` (precheck tốc độ cao) và `LLMJudgeTM08Evaluator` (chấm qua LLM theo Rubric TM-08 của ĐH Quy Nhơn kèm reasoning).
     - Xử lý refusal trung thực: Nếu Trợ lý kích hoạt No-Answer Policy trong khi bộ benchmark có đáp án thực tế (ground truth), điểm liên quan bị phạt về mức sàn (0.10). Ngược lại, nếu cả câu hỏi và ground truth đều là trường hợp ngoài phạm vi (mutual refusal), Trợ lý được tính điểm tối đa (1.00) vì tuân thủ đúng No-Answer Policy.

3. **Đồng Bộ Quality Gate Xuất Bản (Publish Gate Alignment)**:
   - Trong `AssistantReadinessEngine._check_evaluation`: Engine cũ chỉ kiểm tra `meets_tm08_standard` chung mà không đối soát đợt đánh giá mới nhất (latest run) tương ứng của Trợ lý, cũng như không hiển thị phương pháp đánh giá (`heuristic` hay `llm_judge`).
   - **Mục tiêu**: Cập nhật logic `_check_evaluation` truy vấn chính xác đợt benchmark gần nhất của Trợ lý, kiểm tra tỷ lệ đạt chuẩn, hiển thị phương pháp thẩm định và trừ điểm readiness minh bạch nếu chưa đạt chuẩn TM-08.

4. **Giao Diện Drill-Down Trực Quan Cho Cán Bộ Quản Trị**:
   - Xây dựng `RunBenchmarkDialog`: Cho phép người dùng chọn Trợ lý AI, Bộ dữ liệu Benchmark, Số lượng mẫu câu hỏi (5, 10, 20 hoặc Toàn bộ), và Phương pháp đánh giá (`heuristic` hoặc `llm_judge`).
   - Xây dựng `EvaluationRunDetailSheet`: Cho phép xem chi tiết từng đợt chạy: điểm số 3 tiêu chí TM-08, bộ lọc trạng thái (Tất cả / Đạt chuẩn / Chưa đạt), xem câu hỏi, Ground Truth, Phản hồi của Trợ lý, Ngữ cảnh bóc tách từ RAG, và Lời giải thích/nhận xét điểm số (Reasoning).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 2.1. Backend Database Models & Alembic Migration
- **[`backend/app/modules/evaluation/models.py`](../../backend/app/modules/evaluation/models.py)**:
  - Trên `EvaluationRun`: Bổ sung cột `evaluation_method: Mapped[str] = mapped_column(String(30), default="heuristic")`.
  - Trên `EvaluationResultItem`: Bổ sung các cột:
    - `execution_path: Mapped[str] = mapped_column(String(50), default="assistant_workflow")`
    - `is_refusal: Mapped[bool] = mapped_column(Boolean, default=False)`
    - `reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)`
- **[`backend/alembic/versions/20260919_evaluation_items_and_method_sync.py`](../../backend/alembic/versions/20260919_evaluation_items_and_method_sync.py)**:
  - Migration script an toàn sử dụng `inspect` schema PostgreSQL để bổ sung các cột mới trên `evaluation_runs` và `evaluation_result_items`.

### 2.2. Backend Schemas & Evaluator Engine Đa Chế Độ
- **[`backend/app/modules/evaluation/schemas.py`](../../backend/app/modules/evaluation/schemas.py)**:
  - Cập nhật `EvaluationRunRequest`: Thêm `evaluation_method: str = "heuristic"`.
  - Cập nhật `EvaluationRunResponse`: Thêm `evaluation_method`.
  - Cập nhật `EvaluationResultItemResponse`: Bổ sung `is_refusal`, `execution_path`, `reasoning`.
  - Khởi tạo `EvaluationRunDetailResponse`: Kế thừa `EvaluationRunResponse` và chứa `items: list[EvaluationResultItemResponse]`.
- **[`backend/app/modules/evaluation/evaluator.py`](../../backend/app/modules/evaluation/evaluator.py)**:
  - `BaseTM08Evaluator` (Abstract Base Class): Định nghĩa phương thức chuẩn `evaluate_item(query, answer, contexts, ground_truth)`.
  - `HeuristicTM08Evaluator`:
    - Tính toán Faithfulness dựa trên tỷ lệ câu trả lời được neo trong ngữ cảnh RAG (Grounding).
    - Tính toán Answer Relevance thông minh: Phát hiện No-Answer Policy refusal. Nếu là refusal mà ground truth có dữ liệu thực tế -> phạt điểm relevance (0.10). Nếu cả hai cùng từ chối -> công nhận đạt chuẩn (1.00).
    - Tính Context Precision dựa trên sự xuất hiện của từ khóa truy vấn trong các đoạn trích dẫn bóc tách.
  - `LLMJudgeTM08Evaluator`:
    - Sử dụng ModelOps LLM Adapter để chấm điểm dựa trên Prompt Rubric TM-08 của ĐH Quy Nhơn.
    - Trích xuất điểm số dạng JSON và sinh trường `reasoning` giải thích chi tiết cho từng tiêu chí.
  - Factory function `get_evaluator(method: str) -> BaseTM08Evaluator`: Khởi tạo evaluator phù hợp (`heuristic` hoặc `llm_judge`).

### 2.3. Evaluation Service & Router Drill-Down
- **[`backend/app/modules/evaluation/service.py`](../../backend/app/modules/evaluation/service.py)**:
  - Trong `run_evaluation()`: Khởi tạo evaluator qua factory theo tham số `request.evaluation_method`; lưu vết từng câu hỏi vào bảng `evaluation_result_items` kèm `execution_path`, `is_refusal`, `reasoning`.
  - Bổ sung `get_run_detail(db, run_id)`: Trả về thông tin tổng quan của đợt chạy kèm toàn bộ danh sách `EvaluationResultItemResponse`.
  - Bổ sung `get_run_items(db, run_id)`: Trả về danh sách chi tiết các item phục vụ phân trang hoặc lọc.
- **[`backend/app/modules/evaluation/router.py`](../../backend/app/modules/evaluation/router.py)**:
  - Thêm endpoint `GET /evaluation/runs/{run_id}` -> `EvaluationRunDetailResponse`.
  - Thêm endpoint `GET /evaluation/runs/{run_id}/items` -> `list[EvaluationResultItemResponse]`.

### 2.4. Assistant Readiness Engine Alignment
- **[`backend/app/modules/assistants/readiness.py`](../../backend/app/modules/assistants/readiness.py)**:
  - Cập nhật hàm `_check_evaluation()`:
    - Truy vấn latest run của chính trợ lý đang thẩm định (`EvaluationRun.assistant_code == assistant.code`).
    - Kiểm tra `latest_run.meets_tm08_standard` và tỷ lệ ca kiểm thử đạt chuẩn (`passed_cases / total_cases`).
    - Cung cấp message chi tiết chỉ rõ phương pháp kiểm định (`heuristic` hoặc `llm_judge`), điểm số trung bình của 3 tiêu chí, và áp dụng điểm phạt readiness nếu chưa đạt chuẩn TM-08.

### 2.5. Frontend Drill-Down UI & Benchmark Modal
- **[`frontend/src/types/evaluation.ts`](../../frontend/src/types/evaluation.ts)**:
  - Mở rộng các types: `EvaluationRunItem`, `EvaluationResultItem`, `EvaluationRunDetail`, `EvaluationRunRequest`.
- **[`frontend/src/services/evaluation-api.ts`](../../frontend/src/services/evaluation-api.ts)**:
  - Bổ sung `getDatasets()`, `getRunDetail()`, `getRunItems()`.
- **[`frontend/src/components/evaluation/run-benchmark-dialog.tsx`](../../frontend/src/components/evaluation/run-benchmark-dialog.tsx)**:
  - Modal khởi chạy kiểm định: Chọn Trợ lý AI, Bộ dữ liệu Benchmark, Số lượng mẫu câu hỏi (5 câu nhanh, 10 câu, 20 câu, Toàn bộ), và Phương pháp thẩm định (Heuristic Nhanh hoặc LLM-as-a-Judge).
- **[`frontend/src/components/evaluation/evaluation-run-detail-sheet.tsx`](../../frontend/src/components/evaluation/evaluation-run-detail-sheet.tsx)**:
  - Sheet trượt chi tiết:
    - Thẻ tổng quan đợt chạy với Badge trạng thái TM-08, phương pháp đánh giá, tỷ lệ đạt.
    - Bộ lọc trạng thái: Tất cả / Đạt chuẩn / Chưa đạt.
    - Danh sách câu hỏi có thể mở rộng (Collapsible), hiển thị: Câu hỏi, Ground Truth, Phản hồi của Trợ lý, Ngữ cảnh RAG, Điểm 3 tiêu chí TM-08 và Nhận xét thẩm định chi tiết.
- **[`frontend/src/pages/evaluation-page.tsx`](../../frontend/src/pages/evaluation-page.tsx)**:
  - Bổ sung nút "Chạy Benchmark TM-08" mở `RunBenchmarkDialog`.
  - Bổ sung cột "Phương Pháp" và cột "Thao Tác" (Nút xem chi tiết) trong bảng danh sách đợt đánh giá; hỗ trợ nhấp trực tiếp vào dòng bảng để mở Sheet chi tiết.
  - Khôi phục xử lý `resolveGapMutation` cho Gap Inbox.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

### 3.1. Backend Test Suite
- **Pytest**:
  ```bash
  uv run --extra dev pytest tests/test_evaluation_truthful.py
  ```
  - `7/7 passed (100%)` bao gồm:
    1. `test_run_evaluation_persists_result_items_to_database`: Lưu vết thành công từng câu hỏi vào DB.
    2. `test_get_run_detail_and_items`: Truy vấn run detail và danh sách items qua service.
    3. `test_evaluator_penalizes_relevance_on_refusal_when_ground_truth_exists`: Phạt điểm liên quan khi từ chối vô lý.
    4. `test_evaluator_passes_when_refusal_is_expected`: Chấm 1.00 khi câu hỏi ngoài phạm vi và cả 2 bên cùng từ chối.
    5. `test_llm_judge_evaluator_scores_with_reasoning`: LLM Judge thẩm định qua prompt rubric và trả về reasoning.
    6. `test_publish_gate_evaluates_latest_run_properly`: Readiness engine khớp đợt chạy mới nhất và hiển thị chi tiết.
    7. `test_factory_returns_correct_evaluator`: Evaluator factory phân nhánh chính xác.
  - **Full Backend Suite**: **257/257 passed (100%)**
- **Ruff**:
  ```bash
  uv run ruff check .
  ```
  - Kết quả: `All checks passed!` (0 lỗi)

### 3.2. Frontend Quality Suite
- **Biome Linter**:
  ```bash
  npm run lint  # biome check src
  ```
  - Kết quả: `Checked 164 files in 139ms. No fixes applied.` (0 lỗi, 0 cảnh báo)
- **TypeScript Typecheck**:
  ```bash
  npm run typecheck  # tsc --noEmit
  ```
  - Kết quả: 0 lỗi compilation.
- **Production Bundle Build**:
  ```bash
  npm run build  # tsc -b && vite build
  ```
  - Kết quả: Build thành công rực rỡ trong `7.55s`, tạo bundle tối ưu trong `dist/`.

### 3.3. Text Cleanliness & Zero Mojibake
- **Bộ kiểm toán UTF-8**:
  ```bash
  python scripts/check_mojibake.py
  ```
  - Kết quả: `Tổng số tệp đã quét: 320. Không phát hiện bất kỳ lỗi Mojibake hay vỡ font tiếng Việt nào!`

---

## 4. Kết Luận & Sẵn Sàng Bàn Giao
Giai đoạn 4 đã hoàn thành xuất sắc 100% các yêu cầu của Đợt 7 theo Kế hoạch Cải thiện Toàn diện 07:
- Tầng Evaluation giờ đây hoàn toàn minh bạch và lưu vết chi tiết từng câu hỏi (zero unrecorded runs).
- Cơ chế thẩm định Truthful Ragas TM-08 phân tách rõ giữa precheck nhanh và LLM Judge chuyên sâu, chấm dứt hiện tượng No-Answer Policy "ăn điểm" relevance giả mạo.
- Cổng kiểm soát xuất bản (Quality Gate) của Trợ lý AI liên kết chặt chẽ với kết quả benchmark thực tế.
- Giao diện người dùng cung cấp trải nghiệm phân tích drill-down chuyên nghiệp, trực quan theo chuẩn Academic Teal của Trường Đại học Quy Nhơn.
