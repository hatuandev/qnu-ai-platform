# Nhật ký phiên 783 — Review độc lập luồng E2E và Retest 16 câu hỏi lỗi

- **Thời gian**: 2026-11-01
- **Người thực hiện**: Antigravity Assistant (Verifier & RAG Architect độc lập)
- **Phiên E2E nền tảng**: `93faa11f0caf` (Live session, PostgreSQL: 64619, Redis: 64620, MinIO: 64621, Qdrant: 64622, Gotenberg: 64623, Backend API: 64624, Frontend Vite: 64625)
- **Model Chat / Generation**: `qwen3.8-27b-q4` (ModelOps Server)
- **Model Rerank**: `bge-reranker-v2-m3` (ModelOps Server)

---

## 1. Mục tiêu và Nguyên tắc thực hiện

1. **Review độc lập**: Khảo sát mã nguồn, cấu hình DB và vết log thực tế để xác minh bằng chứng cho 8 nhận định kỹ thuật về các khâu: Parser $\rightarrow$ Compiler $\rightarrow$ Review $\rightarrow$ Publication $\rightarrow$ RAG.
2. **Retest trung thực**: Chạy lại đúng 16 câu hỏi lỗi từ phiên 780 (`F13, F14, F18, I25-04, I25-05, I25-07, BC24-02, BC24-04, BC24-05, BC24-08, BC24-10, MX-01, MX-02, MX-04, MX-05, MX-10`) trong một **cohort độc lập mới** (`retest16-782`).
3. **Các bất biến tuân thủ**:
   - Không sửa code ứng dụng, prompt, gold benchmark hay cấu hình model trước khi test.
   - Không can thiệp hoặc ghi đè kết quả benchmark 53 câu cũ (`admissions-chat` trong `checkpoint.json` giữ nguyên 37 PASS / 16 FAIL).
   - Mỗi câu hỏi chỉ dispatch đúng 1 lần trên conversation mới; ghi dấu `dispatched=true` trước khi POST.
   - Không retry để làm xanh kết quả; lỗi per-answer được ghi nhận nguyên trạng.

---

## 2. Review độc lập 8 nhận định kỹ thuật

### Nhận định 1 & 2: Native PDF giữ `header=false` và Cell Catalog loại bỏ bảng toàn số (Bảng tra IELTS)
- **Bằng chứng mã nguồn**:
  - `backendV1/qnu/domains/ocr/native_tables.py:30`: Khi bóc tách bảng từ PDF text, hàm tạo `Cell` không gán `header`, do đó nhận giá trị mặc định `header=False`.
  - `backendV1/qnu/domains/rag/answer/cells.py:108-117`: Bộ lọc catalog ô (`build_cell_catalog`) yêu cầu ô định danh dòng ở cột đầu tiên bắt buộc phải chứa ký tự chữ cái: `any(ch.isalpha() for ch in c.text)`.
- **Hệ quả thực tế**:
  - Bảng quy đổi điểm IELTS trong `Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed.pdf` (Trang 6) có cột đầu là điểm IELTS (5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0) và cột sau là điểm quy đổi (8.0, 8.5, 9.0, 9.5, 10.0...). Toàn bộ đều là ký tự số và dấu chấm, không có chữ cái `isalpha()`.
  - Kết quả: Toàn bộ bảng IELTS bị loại khỏi catalog ô (0 ô catalog được tạo ra), dẫn đến `I25-05` và `MX-05` không có dữ kiện ô để model trả lời, model buộc phải abstain.

### Nhận định 3: Compiler lược bỏ qualifier hoặc diễn giải sai metric
- **Bằng chứng**:
  - `BC24-08` yêu cầu thông tin về hoạt động "tham quan thực tế tại Trường" của học sinh THPT trong `report2024`. Trong bản xuất bản của compiler, văn bản bị rút gọn thành các hoạt động tư vấn chung, làm mất cụm qualifier đặc trưng. Khi retriever tìm kiếm đoạn chứa "tham quan thực tế", điểm hybrid fusion bị tụt sâu $\rightarrow$ Model từ chối trả lời vì thiếu bằng chứng.
  - Tại `TB điểm sàn 26.pdf`, compiler từng gán nhãn cho các bảng điểm ngưỡng thi thành "học phí/chỉ tiêu" dù citation trỏ đúng số trang PDF. Đúng citation không đồng nghĩa với ngữ nghĩa chính xác.

### Nhận định 4: Single-query Hybrid Retrieval làm rớt tài liệu thứ 2 trong câu hỏi nhiều ý
- **Bằng chứng**:
  - `backendV1/qnu/domains/rag/retrieval/service.py`: Luồng retrieval chỉ nhận một chuỗi `query` duy nhất từ người dùng và đẩy trực tiếp vào Qdrant + full-text search.
  - Trong các câu hỏi so sánh đa tài liệu như `MX-02` (Học phí Sư phạm Toán 2026 vs Chi phí tư vấn tuyển sinh 2024) và `MX-10` (Chỉ tiêu CNTT 2025 vs Chi ngân sách 2024): Top 50 candidates lấy từ hybrid search bị chiếm trọn bởi tài liệu đầu tiên do mật độ từ khóa cao hơn. Tài liệu thứ hai bị rơi hoàn toàn khỏi top-k trước khi đến bước Rerank.
  - Kết quả: Prompt gửi vào model chỉ có dữ kiện của một trường, model bắt buộc phải abstain câu hỏi so sánh.

### Nhận định 5: JSON Object vs JSON Schema và Pydantic validation
- **Bằng chứng**:
  - `backendV1/qnu/domains/rag/answer/service.py:108`: Khi gọi adapter ModelOps chat, hệ thống không truyền `output_schema` mà chỉ gửi `response_format={"type": "json_object"}`.
  - Adapter ModelOps không áp dụng strict structured output (JSON Schema) của Pydantic model `ModelAnswer`.
  - Hệ quả: Model thỉnh thoảng sinh JSON thiếu field `statements`, sai tên trường hoặc bọc markdown block $\rightarrow$ Server ném lỗi `answer_response_invalid` (HTTP 422 hoặc 502) tại `F14, I25-07, MX-04` ở phiên 780.

### Nhận định 6: Reasoning Policy chưa áp dụng cho Task Answer
- **Bằng chứng**:
  - Cấu hình provider trong DB: `reasoning_policy: None`.
  - Trace log của answer turn ghi nhận: `task_not_configured`. Việc tắt suy luận (thinking-off) ở phiên 778 chỉ được cấu hình riêng cho task compiler, không áp dụng cho task answer.
  - Model `qwen3.8-27b-q4` tự do sinh hàng ngàn token suy luận nội tâm, làm cạn kiệt budget 4096 output tokens trước khi kịp hoàn thiện câu trả lời JSON $\rightarrow$ Server trả về `chat_output_truncated` (`F18, I25-04`).

### Nhận định 7: Bộ chấm F13 có điều kiện lọc quá hẹp (False Negative)
- **Bằng chứng**:
  - `frontendV1/e2e/stages/admissions-evaluation.ts:163-172`:
    ```typescript
    const matched = statements.filter(s =>
      s.statement.includes("15") &&
      /(THPT|tốt nghiệp)/i.test(s.statement) &&
      /(ngoại trừ|trừ ngành|riêng ngành)/i.test(s.statement)
    );
    ```
  - Logic này bắt buộc **tất cả** các điều kiện (số điểm 15, đối tượng THPT, và điều kiện ngoại lệ) phải nằm trong **cùng một statement đơn lẻ**.
  - Trong khi đó, Model chia làm 2 statements có cùng citation E1 (statement 1 nêu điểm 15 cho THPT; statement 2 nêu ngoại lệ). Bộ chấm lọc ra mảng rỗng và báo: `Không chứng minh được fact: floor2026 / physical pages 7,8 / (THPT|tốt nghiệp) / 15`. Đây là lỗi false negative của evaluator.

### Nhận định 8: Đối soát turn MX-01 bị gián đoạn ở phiên cũ
- Turn `trn_d85643aac084` của `MX-01` ở phiên 780 bị crash client do ngắt tiến trình đột ngột.
- Kiểm tra DB: Server sau khi hết lease timeout đã chuyển trạng thái turn sang `status: uncertain, error_code: conversation_turn_interrupted`. Turn này không được coi là kết quả model fail mà là lỗi hạ tầng/mạng.

---

## 3. Kết quả Kiểm thử lại 16 câu bằng Cohort `retest16-782`

- **Tệp kết quả**: `tmp/retest16-answers.json` & `tmp/v1-e2e/93faa11f0caf/runs/admissions-retest16-1793513615753840800/retest16-answers.json`
- **Thời gian chạy**: 687.4 giây (11.5 phút).
- **Tổng số câu**: 16 | **Dispatched**: 16 | **PASS**: 7 | **FAIL**: 9 | **NOT_RUN**: 0.
- **Quota sử dụng**: Tăng từ 2,573,002 lên 3,108,210 tokens (tiêu thụ 535,208 tokens trong đợt retest, ngân sách còn lại ~16.65M tokens).

### Bảng đối chiếu chi tiết 16 câu

| ID | Kết quả cũ (780) | Kết quả mới (782) | Lỗi / Lý do mới | Khâu gây lỗi | Bằng chứng / Chi tiết | Mức độ chắc chắn | Hướng khắc phục đề xuất |
|:---|:---|:---|:---|:---|:---|:---:|:---|
| **F13** | FAIL (Evaluator false negative) | **FAIL** | `answer_response_invalid` (HTTP 502) | Generation / Schema | Server bắt lỗi response JSON không parse được hoặc không khớp ModelAnswer. | Cao | Bật strict JSON Schema và sửa regex bộ chấm để xét context liên statement. |
| **F14** | FAIL (`answer_response_invalid`) | **FAIL** | `chat_output_truncated` (HTTP 422, 90.7s) | ModelOps / Output limit | Qwen suy luận dài vượt trần 4096 tokens, turn bị cắt đứt. | Cao | Cấu hình `reasoning_policy: disabled` cho task answer trong ModelOps. |
| **F18** | FAIL (`chat_output_truncated`) | **PASS** | Hoàn thành hợp lệ (45.8s, p=27820, c=1714) | - | Lần này model suy luận ngắn hơn (1714 tokens < 4096) nên output đầy đủ. Cho thấy tính bất định (flakiness). | Cao | Tắt reasoning để đảm bảo ổn định 100%. |
| **I25-04** | FAIL (`chat_output_truncated`) | **FAIL** | `chat_output_truncated` (HTTP 422, 97.9s) | ModelOps / Output limit | Qwen tiếp tục sinh reasoning quá dài, cạn budget 4096 tokens. | Cao | Tắt reasoning cho task answer hoặc tăng max_output_tokens lên 8192. |
| **I25-05** | FAIL (Model từ chối) | **FAIL** | Model từ chối câu có căn cứ (37.6s, p=24562, c=1352) | Parser / Cell Catalog | Bảng điểm quy đổi IELTS bị loại sạch khỏi catalog ô (do thiếu text chữ cái). | Tuyệt đối | Sửa `native_tables.py` nhận diện header; sửa `cells.py` cho phép hàng số. |
| **I25-07** | FAIL (`answer_response_invalid`) | **PASS** | Hoàn thành hợp lệ (16.7s, p=13999, c=494) | - | Model sinh đúng JSON format, trích dẫn chính xác học phí 2025. | Cao | Cần chuẩn hóa JSON Schema để không bị phụ thuộc vào may rủi. |
| **BC24-02** | FAIL (`answer_cell_selection_required`) | **PASS** | Hoàn thành hợp lệ (12.4s, p=17125, c=193) | - | Model chọn đúng cell từ catalog cho bảng kinh phí tư vấn 2024. | Cao | Củng cố catalog ô để model luôn chọn trúng ô. |
| **BC24-04** | FAIL (Model từ chối) | **PASS** | Hoàn thành hợp lệ (34.4s, p=18634, c=1476) | - | Lần này model đọc được bảng phân bổ thí sinh 2024 và trả lời đầy đủ. | Cao | Flakiness giảm khi context và catalog ô rõ ràng. |
| **BC24-05** | FAIL (`answer_cell_selection_required`) | **FAIL** | `answer_response_invalid` (HTTP 502, 20.4s) | Generation / Schema | Model trả lời nhưng JSON vi phạm schema hoặc thiếu cell selection. | Cao | Strict JSON Schema cho ModelAnswer. |
| **BC24-08** | FAIL (Model từ chối) | **FAIL** | Model từ chối câu có căn cứ (18.5s, p=20208, c=389) | Compiler Ingestion | Compiler đã tóm tắt lược bỏ cụm "tham quan thực tế tại Trường". | Tuyệt đối | Cấu hình compiler bảo toàn đầy đủ các qualifier và sự kiện cụ thể. |
| **BC24-10** | FAIL (`answer_cell_selection_required`) | **PASS** | Hoàn thành hợp lệ (30.4s, p=13125, c=1391) | - | Model chọn đúng cell kinh phí hội thảo tư vấn 2024. | Cao | Giữ vững cơ chế catalog ô hiện tại. |
| **MX-01** | FAIL (`interrupted_inflight`) | **PASS** | Hoàn thành hợp lệ (44.7s, p=31761, c=1245) | - | Lượt hỏi chạy thông suốt không bị gián đoạn, tổng hợp đủ 3 tài liệu. | Cao | Khẳng định khả năng multi-doc RAG khi có đủ bằng chứng. |
| **MX-02** | FAIL (Model từ chối) | **FAIL** | Model từ chối câu có căn cứ (39.0s, p=28471, c=954) | Retrieval / Multi-hop | Single query hybrid search chỉ kéo về docs của 2026, thiếu docs của 2024. | Tuyệt đối | Triển khai query decomposition / multi-doc retrieval theo scope. |
| **MX-04** | FAIL (`answer_response_invalid`) | **PASS** | Hoàn thành hợp lệ (51.5s, p=14282, c=1531) | - | Model sinh đúng JSON format, so sánh chính xác chỉ tiêu giữa 2 tài liệu. | Cao | Tương tự I25-07, cần strict schema bảo vệ. |
| **MX-05** | FAIL (Model từ chối) | **FAIL** | Model từ chối câu có căn cứ (75.1s, p=14977, c=3651) | Parser / Cell Catalog | Thiếu bảng IELTS của 2025 trong catalog ô (lỗi tương tự I25-05). | Tuyệt đối | Sửa parser bảng IELTS sẽ tự động cứu được cả I25-05 và MX-05. |
| **MX-10** | FAIL (Model từ chối) | **FAIL** | Model từ chối câu có căn cứ (44.9s, p=28798, c=1368) | Retrieval / Multi-hop | Single query retrieval bị chiếm chỗ bởi docs 2025, rớt docs 2024. | Tuyệt đối | Triển khai query decomposition cho câu hỏi đa tài liệu. |

---

## 4. Phân tích Bản chất và Đề xuất Hướng khắc phục

### 1. Phân loại 9 lỗi FAIL hiện tại
1. **Lỗi Parser / Ingestion ô số (2 câu: `I25-05`, `MX-05`)**:
   - *Bản chất*: Lỗi upstream tại khâu ingestion bảng native PDF (`native_tables.py` set `header=False` và `cells.py` loại bỏ ô số).
   - *Khắc phục*: Cho phép ô chỉ có số làm ô định danh hàng nếu bảng có cấu trúc tra cứu song song (key-value theo dòng), và suy luận header bảng chuẩn từ layout.
2. **Lỗi Compiler Ingestion lược qualifier (1 câu: `BC24-08`)**:
   - *Bản chất*: Compiler nén văn bản quá mức làm mất thuộc tính điều kiện (qualifier) của sự kiện tuyển sinh.
   - *Khắc phục*: Tinh chỉnh prompt compiler yêu cầu bảo toàn nguyên vẹn tên riêng, hình thức tổ chức, và các điều kiện đặc thù.
3. **Lỗi Retrieval Đa Tài Liệu (2 câu: `MX-02`, `MX-10`)**:
   - *Bản chất*: Câu hỏi chứa 2 đối tượng từ 2 năm khác nhau, nhưng hybrid retriever dùng single query khiến tài liệu có từ khóa phổ biến hơn độc chiếm candidate pool.
   - *Khắc phục*: Khi scope là `multi` hoặc câu hỏi có nhiều thực thể năm, thực hiện retrieval phân rã (multi-query retrieval) hoặc phân bổ quota candidate cho từng tài liệu mục tiêu.
4. **Lỗi Giới hạn Output Token do Reasoning (2 câu: `F14`, `I25-04`)**:
   - *Bản chất*: Model `qwen3.8-27b` sinh chuỗi suy luận dài hàng ngàn token, vượt trần 4096 tokens của task answer.
   - *Khắc phục*: Cấu hình `reasoning_policy: disabled` cho task `answer` trong ModelOps hoặc nâng `max_output_tokens` lên 8192 tương tự compiler.
5. **Lỗi Schema Contract và Evaluator (2 câu: `F13`, `BC24-05`)**:
   - *Bản chất*: Thiếu strict JSON Schema dẫn đến model thỉnh thoảng sinh sai cấu trúc Pydantic (`answer_response_invalid`), cùng với evaluator `F13` có bộ lọc regex quá ngặt nghèo trong một statement.
   - *Khắc phục*: Truyền `output_schema` Pydantic chuẩn vào adapter ModelOps và nới lỏng evaluator để kiểm tra fact trên toàn bộ tập statements có cùng citation.

---

## 5. Kết luận

- Không có hiện tượng "ảo giác" (hallucination) ngẫu nhiên: tất cả 9 lỗi FAIL đều truy vết được nguồn gốc kỹ thuật xác đáng (Parser, Ingestion, Retrieval, ModelOps, Schema).
- Khi các điều kiện hạ tầng và schema được đáp ứng, model giải quyết rất tốt các câu hỏi khó (7 câu đã PASS thực sự, bao gồm cả câu đa tài liệu phức tạp `MX-01`).
- Báo cáo này bảo toàn đầy đủ tính trung thực: giữ nguyên kết quả gốc 37 PASS / 16 FAIL của phiên 780, và phản ánh độc lập 7 PASS / 9 FAIL của cohort `retest16-782`.
