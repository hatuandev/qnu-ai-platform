# QUY TRÌNH 03: TRUY VẤN HYBRID RAG & CHỐNG BỊA ĐẶT (HYBRID RAG & ANTI-HALLUCINATION RETRIEVAL FLOW)

Tài liệu này đặc tả cơ chế tìm kiếm hỗn hợp (Dense Vector + Sparse Lexical), thuật toán dung hợp thứ hạng Reciprocal Rank Fusion ($k=60$), tái xếp hạng Cross-Encoder và chốt chặn bảo vệ trích dẫn (Citation Guardrail).

---

## 1. Sơ Đồ Quy Trình Xử Lý Truy Vấn RAG

```mermaid
flowchart TD
    Q([Câu hỏi người dùng]) --> G1[1. Input Safety Guardrail]
    G1 -->|Phát hiện Prompt Injection / Jailbreak| DENY[Từ chối trả lời & ghi log vi phạm an ninh]
    G1 -->|Hợp lệ| G2[2. PII Redaction: Che mờ CCCD, SĐT, Email]
    
    G2 --> FACT_STEP{3. Tra cứu Structured Fact Layer?}
    FACT_STEP -->|Tìm thấy bản ghi trùng khớp mã ngành / học phí| FACT_FOUND[Lấy thông số thực tế từ DB bảng facts]
    FACT_STEP -->|Không có trong fact layer| HYBRID_SEARCH
    
    subgraph HYBRID_RETRIEVAL [4. Tìm Kiếm Lai Đa Tầng (Hybrid Retrieval)]
        HYBRID_SEARCH[Đồng thời kích hoạt 2 động cơ tìm kiếm]
        HYBRID_SEARCH -->|Dense Vector Search: BGE-M3 1024D| QD[(Qdrant Vector DB)]
        HYBRID_SEARCH -->|Sparse Lexical Search: FTS tiếng Việt| PG[(PostgreSQL FTS)]
        
        QD -->|Top Dense Candidates| RRF[5. Reciprocal Rank Fusion - RRF k=60]
        PG -->|Top Sparse Candidates| RRF
        
        RRF -->|Danh sách ứng viên dung hợp| RERANK[6. Cross-Encoder Reranker: BGE-Reranker-v2-m3]
        RERANK -->|Nếu Reranker offline / timeout| FALLBACK_RRF[Graceful Fallback: Giữ nguyên thứ hạng RRF]
        RERANK --> TOP_CHUNKS[Top 3-5 Chunks liên quan nhất]
        FALLBACK_RRF --> TOP_CHUNKS
    end

    TOP_CHUNKS --> CIT_GUARD{7. Kiểm định Citation Guardrail}
    CIT_GUARD -->|Điểm liên quan < ngưỡng hoặc thiếu chứng cứ| NO_ANSWER[8. No-Answer Policy: Từ chối lịch thiệp & cung cấp Hotline Tuyển sinh 0256.3846.156]
    
    CIT_GUARD -->|Hợp lệ| PROMPT_BUILD[9. Answer Format Planner: Lắp ráp Prompt thông minh]
    FACT_FOUND --> PROMPT_BUILD
    
    PROMPT_BUILD -->|Gửi Prompt| LLM_GATEWAY[10. ModelOps LLM Gateway: gpt-4o-mini / gemini-1.5-flash]
    LLM_GATEWAY --> OUT_GUARD[11. Output Safety Guardrail: Quét rò rỉ API key / Prompt nội bộ]
    OUT_GUARD --> FINOPS[12. FinOps Cost Tracker: Tính toán Token & Chi phí USD]
    FINOPS --> RES([13. Trả câu trả lời kèm Trích dẫn Nguồn & Gợi ý câu hỏi])
```

---

## 2. Chi Tiết Kỹ Thuật Từng Bước

### Bước 1 & 2: Bảo vệ An ninh & Dữ liệu Riêng tư (Guardrails)
- **Input Safety Guardrail**: Quét phát hiện tấn công Prompt Injection (`Ignore all previous instructions...`, `Reveal system prompt...`).
- **PII Data Redaction**: Tự động nhận diện và che mờ các thông tin nhạy cảm của thí sinh/sinh viên trước khi gửi sang LLM (CCCD thành `077******988`, SĐT thành `0912***678`, Email thành `sin***@qnu.edu.vn`).

### Bước 2.5: Phân Loại Ý Định Truy Vấn & Định Tuyến Ưu Tiên Số Liệu (Fact-First Query Routing)
- **Phân biệt paraphrase tổ hợp môn vs xét tuyển thẳng (phiên #183)**:
  * Câu hỏi mơ hồ `"ngành CNTT cần những môn học nào để xét tuyển"` được chuẩn hóa thành `"tổ hợp môn"` trước retrieval; `QueryClassifier` ánh xạ `môn + xét tuyển/ngành` sang `fact_attributes=["subject_combinations"]` khi không chứa marker `học sinh giỏi / tuyển thẳng / ưu tiên xét tuyển`.
  * Truy vấn HSG / tuyển thẳng giữ nguyên để không lấn át Phụ lục 1; truy vấn ngày tháng thuần túy không bị ép Fact-First.
- **Tra cứu ngược theo tên môn + token ILIKE đặc thù (phiên #184)**:
  * `QueryClassifier.SUBJECT_PATTERNS` bóc tách tên môn chuẩn (`toán/lý/hóa/sinh/văn/sử/địa/tiếng anh/tin...`) vào `QueryAnalysis.subject_names` khi có ngữ cảnh `tổ hợp` hoặc `môn + xét tuyển`; đại từ `anh` trần và truy vấn HSG bị loại trừ.
  * `select_ilike_tokens()` tách từ bằng regex `\w+` (hết dính dấu phẩy `toán,`), loại âm tiết chung (`các/ngành/xét/tuyển/hợp/môn`) để token đặc thù dẫn dắt ILIKE thay vì 3 token đầu chung chung.
- **Bộ phân loại ý định thông minh (`QueryClassifier`)**:
  * Phân tách câu hỏi thành 3 nhóm ý định chuyên biệt (`QueryIntent`):
    - `EXACT_FACT`: Tra cứu số liệu cụ thể (mã ngành `7\d{6}`, chỉ tiêu, điểm chuẩn, học phí, quy đổi IELTS/VSTEP, mã nhiệm vụ `\d+\.\d+`, đơn vị chủ trì, hạn hoàn thành).
    - `NARRATIVE`: Câu hỏi giải thích chính sách, quy chế đào tạo, thủ tục nhập học, văn bản hướng dẫn.
    - `MIXED`: Câu hỏi tổng hợp đòi hỏi cả số liệu cụ thể kèm văn cảnh diễn giải.
  * **Trích xuất thực thể miền sâu (Domain Entity Extraction)**: Tự động bóc tách các mã định danh chuẩn (`entity_codes` như `7480107`, `6.8`, `certificate_conversion`) và danh mục thuộc tính nghiệp vụ (`fact_attributes` như `expected_quota`, `cutoff_score`, `lead_unit`, `end_date`, `converted_score`).
- **Chiến lược điều phối tìm kiếm thích ứng (Intent-tailored Retrieval Strategy)**:
  * Khi `is_fact_first = True` (thuộc `EXACT_FACT` hoặc `MIXED`):
    - Hệ thống ưu tiên tra cứu trực tiếp từ `KnowledgeFact` qua `lookup_facts` với bộ lọc `entity_codes` và `fact_attributes`.
    - Kết quả số liệu được định dạng thành Markdown Table chuẩn và đưa lên vị trí trang trọng nhất (`BẢNG SỐ LIỆU ĐÃ XÁC THỰC`) trong ngữ cảnh cung cấp cho LLM.
    - Với `EXACT_FACT`, hệ thống thu gọn phạm vi Hybrid Retrieval (`top_k=4`, `rerank_top_k=3`) nhằm tránh hiện tượng văn bản thừa làm loãng hoặc xung đột với số liệu chính xác.
  * Với `NARRATIVE`, hệ thống mở rộng Hybrid Retrieval (`top_k=8`, `rerank_top_k=5`) để bao quát đầy đủ các điều khoản và quy định liên quan.

### Bước 3: Ưu Tiên Tuyệt Đối Bảng Sự Thật (Structured Fact Layer) & Ràng Buộc Vòng Đời Tài Liệu
- Tra cứu bảng `knowledge_facts` trên PostgreSQL kết hợp `outerjoin` với `knowledge_documents`.
- **Ràng buộc Vòng đời Phê duyệt (Document Lifecycle Binding)**: Chỉ trích xuất facts gắn với tài liệu ở trạng thái đã kiểm duyệt và hiệu lực (`status in ["approved", "completed", "processed", "ready"]` và `is_active = True`) hoặc các facts số liệu độc lập không gắn tệp (nhập qua bảng tính Excel/CSV). Tuyệt đối loại trừ 100% facts từ tài liệu đang chờ duyệt hoặc đã lưu trữ.

### Bước 3.5: Cơ Chế Lập Chỉ Mục Qdrant An Toàn Theo Phiên Bản (Revision-Safe Qdrant Indexing)
- **Staging Revision**: Khi tài liệu có bản sửa đổi mới (`document_revision`), các chunks mới được tính toán vector và nạp vào Qdrant với `is_retrievable = False` và `document_status = "indexing"`. Revision cũ vẫn tiếp tục phục vụ tìm kiếm bình thường mà không bị gián đoạn (Zero Downtime).
- **Parity Verification (`verify_revision_parity`)**: Trước khi công bố, hệ thống đối soát tự động số lượng points trong Qdrant có cùng `document_id` và `document_revision` với số chunks trong PostgreSQL. Nếu phát hiện lệch số lượng hoặc thiếu metadata, quá trình kích hoạt bị chặn đứng ngay lập tức (Fail-Fast).
- **Kích hoạt nguyên tử (`activate_document_revision`)**: Chỉ khi parity đạt 100%, hệ thống cập nhật đồng loạt payload sang `is_retrievable = True` và `document_status = "ready"`.
- **Dọn dẹp an toàn revision cũ (`purge_stale_revisions`)**: Sau khi revision mới đã active thành công, hệ thống xóa bỏ các points thuộc các revision cũ hơn (`document_revision < current_revision`), triệt tiêu 100% hiện tượng "vector ma" (ghost chunks).
  * Tương tự, `search_sparse_fts` và `lookup_facts` trên PostgreSQL cũng chỉ truy xuất các bản ghi thuộc tài liệu có `status.in_(["ready", "approved"])`, `is_active=True`, bảo đảm tính đồng thuận và nhất quán 100% giữa 3 nguồn dữ liệu.
- **Công thức Reciprocal Rank Fusion kết hợp Trọng số Pháp lý (Legal Priority Weighted RRF)**:
  $$RRF\_Score(d) = \left( \sum_{m \in \{Dense, Sparse\}} \frac{1}{k + rank_m(d)} \right) \times \left(1.0 + (\text{priority} - 5) \times 0.02\right) \quad (\text{với } k = 60)$$
  * Điểm `priority` (1-10) phản ánh giá trị pháp lý của 37 loại văn bản theo chuẩn ĐH Quy Nhơn (Quy chế, Quyết định có priority=10 được nhân hệ số boost $+10\%$; Thông báo/Tin tức có priority=5 giữ nguyên hệ số $1.0$).
  * Giúp các văn bản quy phạm pháp luật cốt lõi tự động bứt phá lên vị trí đầu bảng kết quả khi điểm tương quan ngữ nghĩa tương đương với các văn bản tin tức/hướng dẫn phụ trợ.
- Cân bằng tối ưu giữa khả năng hiểu ngữ nghĩa sâu sắc của Vector BGE-M3 và độ chính xác tuyệt đối của từ khóa FTS tiếng Việt.

### Bước 6: Tái xếp hạng (Cross-Encoder Reranker) kèm Fallback
- Gọi mô hình Cross-Encoder `BAAI/bge-reranker-v2-m3` để chấm điểm tương quan cặp `(Query, Chunk)`.
- **Cơ chế phòng thủ Graceful Fallback**: Nếu dịch vụ reranker bị timeout (>3 giây) hoặc ngoại tuyến, hệ thống tự động suy thoái an toàn về thứ tự ban đầu của thuật toán RRF mà không làm gián đoạn request của người dùng.

### Bước 7 & 8: Chốt chặn Trích dẫn Nghiêm Ngặt (Strict Evidence-Based Citation Guardrail) & Chính Sách Không Trả Lời
- **Bộ lọc Trích dẫn Nghiêm ngặt (Strict Citation Filtering)**:
  * **Lọc bỏ từ dừng học thuật tiếng Việt (`ACADEMIC_STOPWORDS`)**: Trước khi tính điểm giao thoa giữa câu trả lời và đoạn trích, thuật toán loại trừ toàn bộ các từ dừng phổ biến như *"sinh viên"*, *"quy nhơn"*, *"đại học"*, *"trường"*, *"theo"*, *"trong"*, *"với"*, *"tối"*... nhằm loại bỏ hoàn toàn các trường hợp match giả (false positive overlap).
  * **Xử lý an toàn `quote is None`**: Đảm bảo không bao giờ phát sinh lỗi ngoại lệ khi trích đoạn rỗng.
  * **Tuyệt đối không cấp Citation giả**: Khi không có trích dẫn nào vượt qua ngưỡng kiểm định bằng chứng, hệ thống trả về danh sách rỗng (`[]`) và chuyển trạng thái câu trả lời sang `insufficient_context` (chấm dứt hoàn toàn cơ chế fallback trả ngẫu nhiên 2 citation đầu).
- **Phản hồi từ chối chuẩn mực (No-Answer Policy)**: Khi thiếu căn cứ, phản hồi hướng dẫn lịch sự kèm hotline tư vấn tuyển sinh chính thức: `0256.3846.156` hoặc email `tuyensinh@qnu.edu.vn`.

### Bước 8b: Chốt Số Liệu Trích Dẫn Ở Runtime (phiên #185)
- `CitationGuard.verify_numeric_grounding()` trích số nhiều chữ số trong đáp án (so sánh không phân biệt `,`/`.`), đối soát với quotes + facts; số lạ → `insufficient_context` + No-Answer thay vì trả liều. Số 1 chữ số và đáp án không số được miễn (nhiễu).

### Bước 8c: Đợt B — Rank Facts, RRF Trọng Số, Prompt Tầng, Eval Online (phiên #186)
- **Rank facts theo số môn khớp (B1)**: `count_subject_matches()` đếm môn trong `attribute_value` (không quét tên thực thể, tránh `Kế Toán` khớp `toán`); `lookup_facts(..., subject_names)` over-fetch ×3 rồi xếp hạng và cắt limit.
- **RRF trọng số theo intent (B2)**: `reciprocal_rank_fusion(..., dense_weight, sparse_weight)`; EXACT_FACT (1.0/1.2) tin lexical, NARRATIVE (1.2/0.8) nghiêng ngữ nghĩa, MIXED cân bằng; log policy mỗi lượt.
- **Prompt phân tầng + ép temperature (B3)**: fact-query tách TẦNG 1 facts / TẦNG 2 chunks / TẦNG 3 history kèm quy tắc xung đột, history gắn nhãn tham khảo, `temperature = min(req, 0.2)`.
- **Eval online từ vote (B4)**: bảng `conversation_feedbacks` + `POST /conversations/feedback` + `GET /conversations/feedback/stats` (up-rate); nút 👍/👎 Chat Studio gửi vote best-effort kèm thread/câu hỏi/trả lời.

### Bước 8d: Đợt C — Parent-Child, Multi-Query, Drift Dashboard (phiên #187)
- **Parent-child mở rộng ngữ cảnh (C1)**: `expand_with_neighbors()` lấy chunks kề cùng document theo `chunk_index` (fallback `page_number`), tối đa 2 chunks top đầu; đưa vào prompt dưới nhãn `BỐI CẢNH MỞ RỘNG`, không trích dẫn, không làm evidence; lỗi DB suy thoái êm.
- **Multi-query sparse fusion (C2)**: service dựng `keyword_query` từ mã/môn/từ khóa dài; `retrieve(..., sparse_variants)` chạy thêm tối đa 2 truy vấn sparse song song (không tốn embedding), dung hợp RRF với trọng số chiết khấu 0.5 qua `extra_lists`.
- **Trend + samples + panel eval (C3)**: `GET /conversations/feedback/trend` (buckets ngày, gom bằng Python cho tương thích PG/SQLite), `GET /conversations/feedback/samples` (down mới nhất); tab `Đánh Giá Người Dùng` trên `/evaluation` với KPI up-rate, thanh trend 14 ngày và bảng down cần đối soát.

### Bước 9: Phân Vùng Bộ Nhớ Đệm Ngữ Nghĩa Đa Tầng (Multi-Tenant & Policy Partitioned Semantic Cache)
- Lớp cache ngữ nghĩa trên Redis (`SemanticCache`) sử dụng khóa phân vùng bảo vệ chặt chẽ:
  `rag:cache:{tenant_id}:{workspace_id}:{collection_id}:{preferred_model}:{policy_version}:{hash(query)}`
  với `policy_version = "v1"`.
- Việc phân tách 5 lớp (`tenant_id`, `workspace_id`, `collection_id`, `model`, `policy_version`) bảo đảm:
  1. Tuyệt đối không rò rỉ dữ liệu hoặc câu trả lời giữa các tenant và workspace.
  2. Khi người dùng đổi mô hình (`gpt-4o-mini`, `gemini-1.5-flash`, `qwen2.5-7b`), cache không trả kết quả lệch lạc do định dạng của model trước đó sinh ra.
  3. Khi chính sách retrieval thay đổi (`policy_version`), cache tự động phân tách mà không bị ô nhiễm bởi kết quả từ chính sách cũ.
- Hỗ trợ cơ chế vô hiệu hóa cache chủ động theo mẫu wildcard (`invalidate_collection`) bao quát cả mẫu khóa mới `rag:cache:*:*:{collection_id}:*` và mẫu khóa kế thừa `rag:cache:*:{collection_id}:*` ngay khi có tài liệu mới được duyệt/lập chỉ mục hoặc bị xóa.
- **Cache theo history (phiên #185)**: key thêm hậu tố `history_hash` (SHA-256 16 ký tự của 4 turns gần nhất, `nohist` khi không có history) qua `SemanticCache.hash_history()`; query ngắn <8 từ kèm history (ví dụ `có tôi muốn`) bị bỏ qua cache đọc/ghi để không trả đáp án của ngữ cảnh cũ.
- **Scoping history theo chủ đề (phiên #185)**: `scope_history_by_topic()` giữ turn mới nhất + các turn cũ có trùng mã thực thể/tên môn/từ khóa dài, tối đa 4 tin nhắn; tên môn trần chỉ tính khi tin nhắn cũ bàn về tổ hợp (chống `Kế toán` khớp nhầm `toán`).
- **Unaccent fallback (phiên #185)**: `strip_vietnamese_accents()` + `is_unaccented_query()`; query không dấu kích hoạt lượt ILIKE bổ sung dùng `func.unaccent()` (bỏ qua êm khi CSDL thiếu extension).
- **Rerank quan sát được (phiên #185)**: timeout Cloudflare 10s→3s, log `provider/latency_ms/in/out` cho cả 3 nhánh (cloudflare/custom/rrf_fallback).

### Bước 10: Định dạng thông minh (Answer Format Planner)
Tự động lập kế hoạch trình bày câu trả lời:
- Hỏi so sánh / danh sách ngành $\rightarrow$ Trả về **Bảng Markdown** (`markdown_table`).
- Hỏi thủ tục / hồ sơ $\rightarrow$ Trả về **Danh sách kiểm tra** (`checklist`).
- Hỏi lịch trình / mốc thời gian $\rightarrow$ Trả về **Dòng thời gian** (`timeline`).

### Bước 11: Tái sử dụng dùng chung cho mọi Trợ lý mới (Generic Reusable RAG)
- **Query Router theo module (`query_router.py`)**: Registry `FACT_KEYWORD_PACKS` cho admissions, regulations, library, drafting, question_bank; trợ lý mới dùng tín hiệu generic (số hiệu QĐ/NĐ/TT, số tiền triệu/tỷ, năm, bao nhiêu/danh sách/liệt kê) mà không cần sửa code. API `analyze(query, module_code="general")` tương thích ngược.
- **System Prompt dùng chung (`service.py`)**: `build_generic_system_instruction(module_code, custom_prompt)` ưu tiên prompt của trợ lý, ngược lại dùng instruction Zero-Hallucination toàn trường kèm contact theo module (admissions giữ hotline 0256.3846.156, module mới dùng contact tổng quát).
- **Phát hiện từ chối phi thiên vị**: `is_refusal_answer(answer, has_evidence)` chỉ dựa vào cụm từ từ chối + có/không có citations/facts, thay thế hoàn toàn heuristic cũ chỉ biết triệu/học phí/điểm chuẩn.
- **Mặc định an toàn**: `AskRequest.module_code` mặc định `general` (thay vì admissions) để trợ lý mới không bị nhiễm ngữ cảnh tuyển sinh.

### Bước 12: Ràng Buộc Thực Thể, Chỉ Đạo Định Dạng & Bộ Lọc Hậu Xử Lý (phiên #188)
- **Nhận diện Thực thể Trọng tâm (`target_entities`)**: `QueryClassifier.analyze()` tự động trích xuất các thực thể cụ thể (ví dụ: ngành đào tạo, mã ngành, văn bản) từ câu hỏi người dùng.
- **Ràng buộc Trích xuất theo Thực thể (Entity-Scoped Prompt Injection)**: Khi người dùng hỏi về một thực thể cụ thể (ví dụ: *Công nghệ thông tin*), hệ thống inject chỉ thị bắt buộc vào `user_content`:
  * Chỉ được phép trích xuất thông tin liên quan đến thực thể đó.
  * Tuyệt đối không sao chép hay hiển thị thông tin của các ngành/đối tượng khác có trong bảng/tài liệu.
- **Chỉ đạo Định dạng Động từ `AnswerFormatPlanner`**: `get_format_instructions(format_type, target_entity, is_combo_query)` đưa trực tiếp quy tắc trình bày vào prompt:
  * Tổ hợp môn: Bắt buộc dùng danh sách gạch đầu dòng (-) rõ ràng từng tổ hợp môn `(Môn 1, Môn 2, Môn 3)`, giải thích rõ ràng các ký hiệu số phương thức (ví dụ: 1, 2, 3, 4 là Phương thức xét tuyển 1-4).
  * Bảng số liệu: Bắt buộc dùng cú pháp bảng Markdown chuẩn chỉnh đầy đủ Header, cấm viết ký tự pipe `||` thô dính chùm.
- **Bộ lọc Hậu xử lý Làm sạch Cú pháp Bảng (`sanitize_rag_answer`)**:
  * Tự động làm sạch các cụm ký tự pipe rác `||||||` do OCR tài liệu sinh ra.
  * Chốt chặn trường hợp LLM nhả cả khối bảng nhiều ngành: tự động phân tích và chuyển đổi thành danh sách gạch đầu dòng chuẩn mực cho đúng thực thể được hỏi.
  * Giữ nguyên vẹn tính toàn vẹn của các bảng Markdown chuẩn.

### Bước 13: Chuẩn Hóa Góc Độ Nút Gợi Ý & Chống Entity Hijacking Đa Lượt (phiên #189)
- **Chuyển đổi góc độ Nút Gợi Ý (`convert_or_filter_suggestion_perspective`)**:
  * Rào chắn chống lộn vai trò: Nhận diện và chuyển đổi các câu hỏi tu từ bot hỏi người dùng (*"Bạn có muốn tìm hiểu về tổ hợp môn xét tuyển của ngành cụ thể nào không?"*) sang góc độ người dùng hỏi bot (*"Các ngành của trường xét tuyển những tổ hợp môn nào?"*).
  * Lọc sạch câu hỏi lịch sự mơ hồ (*"Bạn có muốn mình chia sẻ thêm điều gì không?"* $\rightarrow$ loại bỏ hoàn toàn, không hiển thị).
  * Chỉ dẫn System Prompt: Ép 100% câu gợi ý phải đặt câu hỏi từ góc độ người dùng, cấm bắt đầu bằng *"Bạn có muốn..."*, *"Bạn có quan tâm..."*.
- **Chống Entity Hijacking & Intent Drift trong Query Router & Query Rewrite**:
  * Loại trừ danh sách từ placeholder mơ hồ (*"cụ thể"*, *"cụ thể nào"*, *"nào đó"*, *"bất kỳ"*, *"gì"*, *"khác"*,...) khỏi việc trích xuất `target_entities`.
  * Cấm gán ghép thiên kiến ngành vào câu hỏi chung khi xử lý đa lượt, ngăn chặn hiện tượng kéo tên ngành cũ (như CNTT) vào làm biến dạng ý định câu hỏi hiện tại.


