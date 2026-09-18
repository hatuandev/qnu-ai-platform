# Góp Ý Định Hướng Chức Năng Trọng Tâm QNU AI Platform

> **Ngày đánh giá:** 18/09/2026  
> **Phạm vi:** Kho tri thức, Trợ lý AI, RAG, Workflow DAG, ModelOps và Evaluation  
> **Mục tiêu:** Xác định chức năng cần tập trung để QNU AI Platform trở thành nền tảng tạo và vận hành trợ lý AI thực sự, thay vì một ứng dụng chứa năm chatbot cố định.

---

## 1. Kết Luận Điều Hành

QNU AI Platform không nên lấy tiêu chí **“có năm chatbot”** làm thước đo hoàn thành. Thước đo phù hợp hơn là:

> Người quản trị có thể tạo một trợ lý mới, gắn dữ liệu thật, cấu hình model và quyền công cụ, kiểm thử, xuất bản, sau đó nhận câu trả lời có căn cứ và truy vết được.

Năm trợ lý hiện có — Tuyển sinh, Soạn thảo, Thư viện, Ngân hàng câu hỏi và Quy chế — nên được định vị là **Official Starter Templates** của QNU. Chúng là các mẫu tham chiếu để chứng minh năng lực nền tảng, không phải giới hạn cứng của sản phẩm.

Trong giai đoạn hiện tại, nguồn lực nên tập trung vào một **luồng vận hành chuẩn chạy thật từ đầu đến cuối**, thay vì tiếp tục mở rộng số lượng màn hình, chatbot hoặc tính năng trình diễn.

---

## 2. Năng Lực Cốt Lõi Cần Chứng Minh

```text
Tài liệu chính thức
    ↓
Kiểm duyệt và quản lý phiên bản
    ↓
Đánh chỉ mục PostgreSQL + Qdrant
    ↓
Truy xuất Hybrid RAG
    ↓
Sinh câu trả lời qua ModelOps
    ↓
Kiểm tra căn cứ và trích dẫn
    ↓
Trả lời hoặc kích hoạt No-Answer Policy
```

Nếu đường chạy này chưa đáng tin cậy thì việc có thêm chatbot, workflow hoặc dashboard chưa tạo ra giá trị vận hành bền vững.

---

## 3. Thứ Tự Chức Năng Nên Tập Trung

### 3.1. P0 — RAG Data Integrity và Grounded Answer

Đây là ưu tiên cao nhất vì chất lượng của mọi trợ lý phụ thuộc trực tiếp vào chất lượng dữ liệu truy xuất.

- Chỉ truy xuất tài liệu đã được duyệt và sẵn sàng phục vụ.
- Đồng bộ đúng tài liệu, revision, chunk và vector giữa PostgreSQL với Qdrant.
- Không để orphan fact, ghost vector hoặc citation trỏ tới tài liệu không còn hợp lệ.
- Áp dụng tenant/workspace filter cho cả dense search và sparse search.
- Có relevance threshold trước khi đưa ngữ cảnh vào mô hình.
- Mọi kết luận quan trọng phải có citation đối soát được với văn bản gốc.
- Khi thiếu bằng chứng, kích hoạt No-Answer Policy thay vì suy đoán.
- Live Mode không được sử dụng embedding, dữ liệu hoặc câu trả lời giả lập.

**Kết quả mong đợi:** câu trả lời có thể kiểm chứng, truy vết và giải thích được nguồn căn cứ.

### 3.2. P0 — Assistant Runtime Integrity

Trang cấu hình Trợ lý chỉ có ý nghĩa khi toàn bộ cấu hình được runtime thực thi thật:

- `collection_id` và phạm vi dữ liệu được phép truy cập.
- Primary model, fallback model và generation parameters.
- Tool allowlist và quyền gọi từng công cụ.
- Guardrails đầu vào, đầu ra và No-Answer Policy.
- Workflow/version đã được xuất bản.
- Quota, cost cap và chính sách đánh giá.
- Trusted identity của tenant, người dùng và người phê duyệt.

Không nên tiếp tục sử dụng các nhánh xử lý kiểu `if assistant_code == ...` cho nghiệp vụ cốt lõi. Năng lực nên được mô hình hóa bằng capability và policy, ví dụ:

- `knowledge.rag`
- `structured_facts.query`
- `artifact.document.export`
- `artifact.question_bank.export`
- `human_approval.required`
- `citation.required`

**Kết quả mong đợi:** hai trợ lý có cấu hình khác nhau sẽ có hành vi runtime khác nhau đúng theo cấu hình, không cần sửa mã nguồn.

### 3.3. P0 — Một Golden Assistant Hoàn Chỉnh

Không nên hoàn thiện đồng thời cả năm trợ lý. Nên chọn **Trợ lý Quy chế** làm Golden Assistant đầu tiên vì:

- Phạm vi nghiệp vụ rõ ràng.
- Tài liệu có cấu trúc Điều/Khoản thuận lợi cho Clause-Based Chunking.
- Dễ xây dựng bộ câu hỏi đúng/sai và đo chất lượng.
- Phù hợp để chứng minh RAG, citation và No-Answer Policy.
- Ít phụ thuộc dữ liệu giao dịch thời gian thực hơn Trợ lý Tuyển sinh.

Golden Assistant chỉ được coi là hoàn thành khi:

1. Sử dụng tài liệu chính thức đã kiểm duyệt.
2. Quản lý được revision và trạng thái hiệu lực.
3. Truy xuất đúng Điều/Khoản liên quan.
4. Trả lời có citation mở được văn bản gốc.
5. Từ chối trả lời khi không đủ căn cứ.
6. Không dùng mock nghiệp vụ trong Live Mode.
7. Có tối thiểu 50 câu hỏi vàng được chuyên viên xác nhận.
8. Đạt Faithfulness ≥ 0,90; Answer Relevance ≥ 0,85; Context Precision ≥ 0,80.

Sau khi Golden Assistant vượt acceptance gate, kiến trúc có thể được nhân bản lần lượt cho Tuyển sinh, Thư viện, Soạn thảo và Ngân hàng câu hỏi.

### 3.4. P1 — Assistant Builder Thực Sự

Đây là năng lực phân biệt một nền tảng với một ứng dụng chatbot cố định. Người quản trị cần có ba cách tạo trợ lý:

1. Tạo từ Official Starter Template.
2. Nhân bản một trợ lý đang có.
3. Tạo trắng từ đầu.

Quy trình tạo trợ lý phải bao phủ đầy đủ bảy lớp:

1. Persona và phạm vi.
2. Kho tri thức và chính sách RAG.
3. ModelOps và fallback.
4. Guardrails và chống bịa đặt.
5. Tools và Human-in-the-loop.
6. Định dạng đầu ra và citation.
7. Evaluation và observability.

Mô hình sản phẩm được khuyến nghị:

```text
AssistantTemplate
    ↓ tạo mới/nhân bản
AssistantInstance
    ↓ kiểm thử và xuất bản
PublishedAssistantVersion
```

Phiên bản đã xuất bản phải bất biến. Mọi lần chỉnh sửa tiếp theo tạo draft/version mới để có thể audit và rollback.

### 3.5. P1 — Authentication, RBAC và Tenant Isolation

Đây là điều kiện bắt buộc trước khi triển khai cho nhiều phòng ban:

- Ai được tạo hoặc sửa trợ lý.
- Ai được duyệt tài liệu.
- Ai được xuất bản workflow.
- Trợ lý nào được truy cập collection nào.
- Vai trò nào được phép gọi công cụ có side effect.
- Ai đã thực hiện hoặc phê duyệt một hành động.
- Dữ liệu giữa các đơn vị không bị truy xuất chéo.

Tenant/user truyền từ request body không được coi là nguồn danh tính đáng tin cậy. Danh tính và quyền phải đến từ auth context đã xác thực.

### 3.6. P1 — Evaluation và Observability Thật

Evaluation phải chạy qua đúng runtime đang phục vụ người dùng, không được chấm trên câu trả lời mô phỏng hoặc fallback từ ground truth.

Cần theo dõi tối thiểu:

- Assistant version, workflow version và knowledge revision.
- Provider/model đã thực thi và chuỗi fallback.
- Retrieval candidates, rerank score và citation.
- Latency theo từng stage.
- Token, chi phí và quota.
- Faithfulness, relevance, context precision và tỷ lệ No-Answer.
- Correlation ID xuyên suốt từ request đến log và evaluation run.

### 3.7. P2 — Workflow DAG và Tool Gateway

Workflow nên được dùng cho tình huống nhiều bước hoặc có hành động nghiệp vụ; không cần ép mọi câu hỏi RAG đi qua một DAG phức tạp.

Use case phù hợp:

- Soạn thảo → kiểm tra thể thức → cán bộ duyệt → xuất DOCX/PDF.
- Tạo câu hỏi → kiểm tra Bloom/CLO → duyệt → xuất Excel.
- Tuyển sinh → hỏi bổ sung thông tin → tra cứu → tổng hợp kết quả.

Yêu cầu production:

- Không tự động phê duyệt hành động có side effect.
- Execute/resume theo đúng immutable workflow version.
- Có wait/resume, timeout, retry/backoff và cancellation.
- Kiểm tra schema, port, permission và tool allowlist trước khi chạy.
- Lưu đầy đủ audit trail của người thực hiện và người phê duyệt.
- Lỗi export hoặc tool quan trọng phải fail rõ ràng, không trả artifact giả.

### 3.8. P2/P3 — Mở Rộng Trợ Lý và Tối Ưu UI

Chỉ nên mở rộng bốn trợ lý còn lại sau khi Golden Assistant vượt production gate. Thứ tự gợi ý:

1. Quy chế — chứng minh grounded Q&A.
2. Tuyển sinh — bổ sung structured facts và dữ liệu theo năm.
3. Thư viện — tích hợp tra cứu tài nguyên và hướng dẫn thủ tục.
4. Soạn thảo — hoàn thiện approval và artifact export.
5. Ngân hàng câu hỏi — hoàn thiện Bloom/CLO validation và export.

Các hoạt động làm đẹp dashboard, bổ sung animation hoặc mở rộng số lượng màn hình nên đặt sau khi runtime, dữ liệu và quality gate ổn định.

---

## 4. Phân Bổ Nguồn Lực Đề Xuất

| Nhóm công việc | Tỷ trọng đề xuất | Lý do |
| :--- | :---: | :--- |
| RAG, dữ liệu và citation | 30% | Nền móng về độ chính xác và niềm tin |
| Assistant runtime và configuration binding | 25% | Biến màn hình cấu hình thành năng lực thực |
| Golden Assistant Quy chế | 15% | Tạo sản phẩm chuẩn để kiểm chứng toàn hệ thống |
| Auth, RBAC, tenant và audit | 15% | Điều kiện triển khai thực tế trong trường |
| Evaluation và observability | 10% | Đo được chất lượng và phát hiện suy giảm |
| UI polish và tính năng bổ trợ | 5% | Chỉ tối ưu sau khi lõi ổn định |

---

## 5. Roadmap Khuyến Nghị

### Giai đoạn 1 — Làm Sạch Đường Chạy Thật

- Hoàn thiện state machine tài liệu và điều kiện `ready` cho retrieval.
- Reconcile PostgreSQL–Qdrant và xử lý orphan facts/legacy collections.
- Enforce tenant, revision, relevance threshold và citation contract.
- Bind đầy đủ Assistant model/tool/policy vào runtime.
- Tách biệt rõ Demo Mode và Live Mode.

### Giai đoạn 2 — Golden Assistant Quy Chế

- Nạp và duyệt bộ văn bản quy chế chính thức.
- Xây dựng 50 câu hỏi vàng và tiêu chí No-Answer.
- Hoàn thiện citation mở tới Điều/Khoản/trang.
- Chạy benchmark thật và xử lý knowledge gaps.
- Pilot với một nhóm cán bộ nghiệp vụ.

### Giai đoạn 3 — Productize Assistant Builder

- Chuẩn hóa Template → Instance → Published Version.
- Tạo, clone, draft, test, publish và rollback.
- Enforce RBAC, collection access và tool permissions.
- Hiển thị readiness checklist trước khi publish.

### Giai đoạn 4 — Workflow và Mở Rộng Nghiệp Vụ

- Hoàn thiện Human-in-the-loop, immutable version và resilience.
- Đưa Soạn thảo và Ngân hàng câu hỏi qua production gate.
- Nhân bản mẫu đã kiểm chứng cho Tuyển sinh và Thư viện.

---

## 6. Production Acceptance Gate

Một trợ lý chỉ được công bố phục vụ thật khi đạt toàn bộ điều kiện sau:

- [ ] Không có business mock trong Live Mode.
- [ ] Có tài liệu chính thức đã duyệt và revision rõ ràng.
- [ ] PostgreSQL–Qdrant parity đạt yêu cầu, không orphan/ghost data.
- [ ] Model, fallback, tool allowlist và guardrails được runtime enforce.
- [ ] Citation mở được nguồn và khớp nội dung phát biểu.
- [ ] No-Answer hoạt động khi không đủ bằng chứng.
- [ ] Golden dataset chạy qua runtime thật, không dùng ground-truth fallback.
- [ ] Đạt ba ngưỡng TM-08 đã công bố.
- [ ] Có auth, RBAC, tenant isolation và audit identity đáng tin cậy.
- [ ] Workflow có side effect bắt buộc qua Human-in-the-loop.
- [ ] Có quan sát latency, token, cost, lỗi provider và fallback.
- [ ] Có rollback cho Assistant/Workflow/Knowledge version.

---

## 7. Những Việc Chưa Nên Ưu Tiên

- Tạo thêm chatbot chuyên môn khi năm template hiện tại chưa có một mẫu đạt production gate.
- Làm thêm dashboard KPI nếu dữ liệu đo chưa đến từ runtime thật.
- Mở rộng node catalog khi các node hiện tại chưa enforce schema và permission.
- Thêm nhiều provider/model trước khi fallback, quota và cost tracking ổn định.
- Dùng dữ liệu seed/demo để che trạng thái trống hoặc lỗi của Live Mode.
- Tạo workflow phức tạp cho các luồng hỏi–đáp RAG tuyến tính.

---

## 8. Chỉ Số Thành Công Của Sản Phẩm

- Thời gian trung bình để tạo và xuất bản một trợ lý mới.
- Tỷ lệ trợ lý vượt readiness checklist ngay lần đầu.
- Tỷ lệ câu trả lời có citation hợp lệ.
- Tỷ lệ No-Answer đúng khi thiếu dữ liệu.
- Tỷ lệ câu trả lời được cán bộ nghiệp vụ chấp nhận.
- Số knowledge gaps được phát hiện và xử lý mỗi chu kỳ.
- Chi phí trung bình trên một hội thoại thành công.
- Tỷ lệ workflow hoàn tất, chờ duyệt, thất bại và được retry.

---

## 9. Khuyến Nghị Cuối Cùng

Hướng đi phù hợp nhất là:

> **QNU AI Platform — nền tảng quản trị, tạo lập, kiểm định và vận hành các Trợ lý AI chuyên trách cho Đại học Quy Nhơn.**

Trong đó:

- Năm trợ lý hiện tại là bộ mẫu chính thức.
- RAG và dữ liệu có căn cứ là lõi tạo niềm tin.
- Assistant Builder là lõi tạo tính nền tảng.
- Workflow và Tool Gateway là lớp mở rộng hành động.
- Evaluation, Auth và Observability là điều kiện vận hành thật.

Nếu phải chọn duy nhất một mục tiêu tiếp theo, nên chọn: **đưa Trợ lý Quy chế qua đầy đủ production acceptance gate trên dữ liệu thật**, sau đó dùng chính kiến trúc đó để mở rộng toàn hệ sinh thái.
