# Nhật ký phiên 786 — Retest 9 câu hỏi FAIL sau khi tắt suy luận và tăng output tối đa

- **Thời gian**: 2026-11-01
- **Người thực hiện**: Antigravity Assistant (Verifier & RAG Evaluator độc lập)
- **Phiên E2E**: `93faa11f0caf` (Live session)
- **Cohort ID**: `retest9-786-1793515952895`
- **Model Chat / Generation**: `qwen3.8-27b-q4` (ModelOps Server)
- **Model Rerank**: `bge-reranker-v2-m3` (ModelOps Server)
- **Cấu hình runtime xác nhận**:
  - Task `answer`: `reasoning_policy.tasks.off` chứa `["compiler", "answer"]`, `mode: "chat_template_kwarg"`, `parameter: "enable_thinking"`, `off_value: false`, `verified: true`.
  - Assistant: ID `ast_1acc28ced4d4`, `revision: 2`, `max_output_tokens: 16384`, `context_max_bytes: 98304`.
  - Combined Index: `idx_eb8078869135` (3 tài liệu: `floor2026`, `info2025`, `report2024`).
  - Config Fingerprint: `abaec10f1426aa906561ce661232f21e355c6d4a8d296019efd473e6748683f6`.

---

## 1. Mục tiêu và Kỷ luật Thực thi

1. **Phạm vi kiểm thử**: Chạy lại đúng 9 câu hỏi còn FAIL (`F13, F14, I25-04, I25-05, BC24-05, BC24-08, MX-02, MX-05, MX-10`) với nguyên vẹn câu hỏi, scope và tiêu chí chấm từ benchmark 53 câu.
2. **Khắc phục triệt để các phát hiện của phiên 784**:
   - **Loại bỏ False-Green (P1)**: Runner kiểm tra toàn vẹn và ném exception nếu có bất kỳ câu nào chưa đạt hoặc bị halted, buộc Playwright test và tiến trình thoát với mã lỗi nonzero (`exit 1`).
   - **Scope fail-closed (P2)**: Triển khai hàm `resolveDocumentBinding` trong `frontendV1/e2e/stages/retest9-core.ts`. Scope `single` thiếu binding bắt buộc ném lỗi `BLOCKED` trước dispatch, tuyệt đối không fail-open thành scope all.
   - **Khóa cấu hình & Drift Detection (P2)**: Tự động tính toán config fingerprint thực tế và kiểm tra drift trước mỗi câu hỏi. Nếu phát hiện thay đổi runtime giữa chừng, dừng ngay cohort.
   - **Không can thiệp checkpoint cũ**: Không dùng helper `save(state)` ghi đè vào `checkpoint.json`. Báo cáo được lưu nguyên tử và độc lập ra `tmp/v1-e2e/93faa11f0caf/runs/admissions-retest9-1793515946696606800/retest9-answers.json` và `tmp/retest9-answers.json`.
3. **Kiểm tra offline trọng tâm trước khi gọi model**:
   - Viết `frontendV1/tests/retest9-integrity.test.ts` kiểm tra 4 kịch bản: Scope thiếu binding bị chặn, không dispatch trùng, cấu hình đổi bị chặn, và report có failure khiến runner assert thất bại.
   - Chạy Vitest offline: **12/12 tests PASS** (exit 0, thời gian 314ms, không gọi API/model).

---

## 2. Kết quả Thực tế của Cohort Retest 9

- **Tổng số câu**: 9 | **Dispatched**: 9 | **PASS**: 0 | **FAIL**: 9 | **NOT_RUN**: 0 | **UNCERTAIN**: 0 | **Halted**: None.
- **Thời gian thực thi toàn bộ 9 câu**: **2.7 phút** (trung bình 9.8s – 23.0s/câu, giảm 70% so với mức 45s – 97s khi còn bật suy luận).
- **Quota tiêu thụ**: 314,421 tokens. Quota còn lại của workspace: **16,337,727 tokens** (`is_blocked = False`).
- **Exit code**: `1` (Playwright ném lỗi `RUNNER_INCOMPLETE` do có 9/9 câu chưa đạt tiêu chuẩn PASS, hoàn toàn trung thực, không false-green).

### Bảng đối chiếu chi tiết 9 câu hỏi

| ID | Scope | Target Doc | Baseline 780 | Retest 782 | Retest 786 (Off thinking) | Thời gian | Tokens (P/C) | Phân loại lỗi mới | Khâu gây lỗi | Bằng chứng thực tế xác minh |
|:---|:---:|:---:|:---|:---|:---:|:---:|:---:|:---|:---|:---|
| **F13** | single | floor2026 | FAIL (Checker regex) | FAIL (`answer_response_invalid`) | **FAIL** | 23.0s | 33.5k / 188 | Evaluator False Negative | Evaluator Checker | Model trả lời đủ 2 ý chính xác kèm trích dẫn E1, nhưng bộ chấm lọc cả 15 và ngoại lệ trong cùng 1 statement đơn lẻ |
| **F14** | single | floor2026 | FAIL (`answer_response_invalid`) | FAIL (`chat_output_truncated`) | **FAIL** | 19.9s | 0 / 0 | `answer_response_invalid` | Schema Contract | Hết lỗi truncated (19.9s vs 90.7s), nhưng model sinh JSON vi phạm Pydantic validation do thiếu JSON Schema |
| **I25-04** | single | info2025 | FAIL (`chat_output_truncated`) | FAIL (`chat_output_truncated`) | **FAIL** | 20.1s | 0 / 0 | `answer_response_invalid` | Schema Contract | Hết lỗi truncated (20.1s vs 97.9s), nhưng model sinh JSON vi phạm Pydantic validation |
| **I25-05** | single | info2025 | FAIL (Model abstain) | FAIL (Model abstain) | **FAIL** | 16.5s | 24.5k / 12 | Model Abstained | Parser / Cell Catalog | Model từ chối ngay lập tức (12 tokens) vì bảng IELTS không có trong catalog ô (bug header=False và thiếu chữ cái) |
| **BC24-05** | single | report2024 | FAIL (`cell_selection_required`) | FAIL (`answer_response_invalid`) | **FAIL** | 9.8s | 17.3k / 12 | Model Abstained | Grounding / Cell Catalog | Model từ chối ngay lập tức (12 tokens) vì không chọn được cell tỷ lệ nữ sinh viên trong catalog ô |
| **BC24-08** | single | report2024 | FAIL (Model abstain) | FAIL (Model abstain) | **FAIL** | 13.0s | 0 / 0 | `answer_response_invalid` | Ingestion & Schema | Compiler lược qualifier "tham quan thực tế", đồng thời model sinh JSON vi phạm schema |
| **MX-02** | all | all | FAIL (Model abstain) | FAIL (Model abstain) | **FAIL** | 18.7s | 28.4k / 12 | Model Abstained | Retrieval Multi-hop | Single-query hybrid retrieval bị chiếm chỗ bởi docs 2026, thiếu fact Sư phạm Tin 2025 |
| **MX-05** | all | all | FAIL (Model abstain) | FAIL (Model abstain) | **FAIL** | 14.7s | 0 / 0 | `answer_response_invalid` | Parser & Schema | Bảng IELTS thiếu catalog ô, đồng thời output vi phạm schema validation |
| **MX-10** | all | all | FAIL (Model abstain) | FAIL (Model abstain) | **FAIL** | 19.4s | 28.7k / 12 | Model Abstained | Retrieval Multi-hop | Single-query retrieval thiếu fact số lượng Bình Định 2024 trong context |

---

## 3. Phân tích Bản chất Kỹ thuật

### 1. Hiệu quả của việc Tắt Suy luận (`enable_thinking=false`) & Tăng Output (`16384`)
- **Triệt tiêu hoàn toàn lỗi `chat_output_truncated`**: Cả `F14` và `I25-04` từng bị treo 90 – 97 giây rồi bị cắt đứt ở mốc 4096 tokens, nay hoàn tất trong 19.9s – 20.1s mà không hề bị ngắt cụt.
- **Tốc độ phản hồi vượt bậc**: Thời gian phản hồi giảm từ trung bình 45s – 97s xuống còn 9.8s – 23.0s/câu.
- **Tiết kiệm token tối đa khi từ chối**: Khi model nhận thấy thiếu dữ kiện để trả lời (`I25-05, BC24-05, MX-02, MX-10`), model sinh đúng **12 tokens** (`{"answer":null,"lookups":[],"statements":[],"abstain":true}`) thay vì tốn hàng ngàn tokens suy luận lan man.

### 2. Nguyên nhân 9 câu FAIL
1. **Lỗi Evaluator False Negative (1 câu: `F13`)**:
   - Model trả về:
     - Statement 1: *"Theo thông báo năm 2026, thí sinh xét tuyển phải có tổng điểm 03 môn thi kỳ thi tốt nghiệp THPT năm 2026 (hoặc sử dụng điểm thi môn Toán, Ngữ văn và một môn thi khác) đạt tối thiểu 15,00 điểm theo thang điểm 30."* [E1]
     - Statement 2: *"Ngoại lệ áp dụng cho các ngành đào tạo giáo viên và ngành Luật, các ngành này thực hiện theo ngưỡng do Bộ Giáo dục và Đào tạo quy định."* [E1]
   - Cả hai statement đều đúng sự thật và trích dẫn chuẩn `E1`. Nhưng `admissions-evaluation.ts:163-172` lọc từng statement đơn lẻ đòi hỏi phải có đồng thời cả điểm 15, THPT và từ "ngoại lệ", nên đã đánh rớt câu trả lời đúng.
2. **Lỗi Schema Contract / JSON Validation (4 câu: `F14, I25-04, BC24-08, MX-05`)**:
   - `backendV1/qnu/domains/rag/answer/service.py:108` gọi adapter model chat không truyền `output_schema` JSON Schema của `ModelAnswer`, chỉ dùng `response_format={"type": "json_object"}`.
   - Khi tắt thinking, model sinh trực tiếp JSON nhưng không có strict schema ràng buộc ở mức engine inference, dẫn tới output bị sai lệch cấu trúc nhẹ hoặc bọc markdown, khiến `ModelAnswer.model_validate_json(content)` ném `ValidationError` $\rightarrow$ Server trả về `answer_response_invalid` (HTTP 502).
3. **Lỗi Thiếu Bằng chứng Upstream (4 câu: `I25-05, BC24-05, MX-02, MX-10`)**:
   - `I25-05` & `MX-05`: Bảng IELTS thiếu catalog ô do `native_tables.py` gán `header=False` và `cells.py` loại bỏ ô số.
   - `BC24-05`: Không ánh xạ được ô tỷ lệ nữ sinh viên vào catalog ô.
   - `MX-02` & `MX-10`: Single-query retrieval làm rơi rớt tài liệu thứ hai trong các câu hỏi so sánh đa tài liệu.

---

## 4. Kết luận và Khuyến nghị

1. **Khẳng định kết luận trước đây**: Việc tắt reasoning và tăng trần output đã giải quyết triệt để lỗi thắt cổ chai về latency và `chat_output_truncated`, nhưng **không thể tự động sửa các lỗi thiếu evidence, lỗi parser bảng hay lỗi schema contract**.
2. **Bước tiếp theo đề xuất**:
   - **P1 (Schema Contract)**: Đưa Pydantic JSON Schema của `ModelAnswer` vào tham số `output_schema` khi gọi adapter inference, ép model sinh đúng cấu trúc 100%.
   - **P1 (Evaluator F13)**: Sửa bộ chấm `F13` để kiểm tra ngữ cảnh trên toàn bộ tập statements có cùng citation E1 thay vì ép trong một câu đơn lẻ.
   - **P2 (Parser Ingestion)**: Sửa `native_tables.py` và `cells.py` để giữ header bảng native PDF và chấp nhận hàng toàn số cho bảng tra cứu IELTS.
   - **P2 (Multi-hop Retrieval)**: Triển khai query decomposition cho câu hỏi so sánh đa tài liệu.
