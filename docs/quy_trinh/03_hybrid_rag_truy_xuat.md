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

### Bước 3: Ưu Tiên Tuyệt Đối Bảng Sự Thật (Structured Fact Layer) & Ràng Buộc Vòng Đời Tài Liệu
- Tra cứu bảng `knowledge_facts` trên PostgreSQL kết hợp `outerjoin` với `knowledge_documents`.
- **Ràng buộc Vòng đời Phê duyệt (Document Lifecycle Binding)**: Chỉ trích xuất facts gắn với tài liệu ở trạng thái đã kiểm duyệt và hiệu lực (`status in ["approved", "completed", "processed", "ready"]` và `is_active = True`) hoặc các facts số liệu độc lập không gắn tệp (nhập qua bảng tính Excel/CSV). Tuyệt đối loại trừ 100% facts từ tài liệu đ### Bước 4 & 5: Tìm kiếm lai song song (Concurrent Hybrid Retrieval) & Dung hợp thứ hạng RRF ($k=60$)
- **Thực thi song song phi phong tỏa**: Động cơ `retriever.py` kích hoạt đồng thời Dense Vector Search trên Qdrant và Sparse FTS Lexical Search trên PostgreSQL thông qua `asyncio.gather`, giảm tối đa 50% độ trễ (latency) so với truy vấn tuần tự.
- **Ràng buộc Vòng đời & Phân quyền Đa người thuê theo Positive Allowlist (Giai Đoạn D)**:
  * Qdrant payload lưu trữ đầy đủ 11 trường: `tenant_id`, `workspace_id`, `collection_id`, `document_id`, `document_revision`, `chunk_id`, `document_status`, `is_retrievable`, `content_hash`, `embedding_model`, `payload_schema_version`.
  * `search_dense` áp dụng bộ lọc **Positive Allowlist** tuyệt đối (loại bỏ hoàn toàn cơ chế blacklist `must_not`):
    - `is_active = True`
    - `is_retrievable = True`
    - `document_status in ["ready", "approved"]`
    - `tenant_id` và `workspace_id` khớp chính xác với ngữ cảnh truy vấn.
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

### Bước 9: Phân Vùng Bộ Nhớ Đệm Ngữ Nghĩa Đa Tầng (Multi-Tenant & Policy Partitioned Semantic Cache)
- Lớp cache ngữ nghĩa trên Redis (`SemanticCache`) sử dụng khóa phân vùng bảo vệ chặt chẽ:
  `rag:cache:{tenant_id}:{workspace_id}:{collection_id}:{preferred_model}:{policy_version}:{hash(query)}`
  với `policy_version = "v1"`.
- Việc phân tách 5 lớp (`tenant_id`, `workspace_id`, `collection_id`, `model`, `policy_version`) bảo đảm:
  1. Tuyệt đối không rò rỉ dữ liệu hoặc câu trả lời giữa các tenant và workspace.
  2. Khi người dùng đổi mô hình (`gpt-4o-mini`, `gemini-1.5-flash`, `qwen2.5-7b`), cache không trả kết quả lệch lạc do định dạng của model trước đó sinh ra.
  3. Khi chính sách retrieval thay đổi (`policy_version`), cache tự động phân tách mà không bị ô nhiễm bởi kết quả từ chính sách cũ.
- Hỗ trợ cơ chế vô hiệu hóa cache chủ động theo mẫu wildcard (`invalidate_collection`) bao quát cả mẫu khóa mới `rag:cache:*:*:{collection_id}:*` và mẫu khóa kế thừa `rag:cache:*:{collection_id}:*` ngay khi có tài liệu mới được duyệt/lập chỉ mục hoặc bị xóa.

### Bước 10: Định dạng thông minh (Answer Format Planner)
Tự động lập kế hoạch trình bày câu trả lời:
- Hỏi so sánh / danh sách ngành $\rightarrow$ Trả về **Bảng Markdown** (`markdown_table`).
- Hỏi thủ tục / hồ sơ $\rightarrow$ Trả về **Danh sách kiểm tra** (`checklist`).
- Hỏi lịch trình / mốc thời gian $\rightarrow$ Trả về **Dòng thời gian** (`timeline`).
