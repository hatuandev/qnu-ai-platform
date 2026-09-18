# Đánh Giá Sau Các Cải Thiện & Review Mã — QNU AI Platform

> **Thời điểm rà soát:** 18/09/2026  
> **Phạm vi:** Dữ liệu tri thức, RAG, Assistant, Evaluation, Workflow, seed data và phần code đang thay đổi trong worktree.  
> **Lưu ý về phạm vi truy cập:** Dự án đang phát triển nội bộ. Báo cáo này **không yêu cầu RBAC/SSO phức tạp** ở giai đoạn hiện tại; một Dev Access Gate bằng mật khẩu, triển khai phía server, là đủ trước khi chia sẻ môi trường cho người khác.

## Kết Luận

Nền tảng đã cải thiện thật ở ba điểm: đã có dữ liệu trong năm collection, RAG đã đi qua ModelOps và giao diện được phân rã tốt hơn. Chuyển Question Bank sang luồng RAG có citation cũng giúp phần **tra cứu quy định** an toàn hơn.

Tuy nhiên, đợt thay đổi hiện tại chưa thể bàn giao. Có lỗi lint, lỗi test, các method cleanup bị định nghĩa trùng trong `KnowledgeService`, và một số seed đang được gắn nhãn “official” nhưng chưa có tài liệu gốc/provenance để kiểm chứng. Trong lúc review có một session song song tiếp tục sửa code; các điểm dưới đây phân biệt rõ phần đã cải thiện và phần vẫn chưa đạt. Mức độ trưởng thành giữ ở khoảng **6,4/10 — Internal Beta**, không nâng điểm ở đợt này.

| Phân hệ | Đánh giá hiện tại | Nhận xét |
| :--- | :---: | :--- |
| Dữ liệu tri thức & seed | 6/10 | Đã có dữ liệu, nhưng Library/Question Bank chưa chứng minh được nguồn gốc chính thức và file gốc chưa được lưu qua storage driver |
| RAG retrieval & citation | 6,5/10 | Có FTS, RRF, threshold; dense retrieval vẫn chưa lọc lifecycle, tenant, workspace và revision |
| Assistant runtime | 6/10 | Đã bind primary model; fallback, structured-fact và tool policy chưa được enforce tại runtime |
| Evaluation TM-08 | 3,5/10 | Vẫn tự chèn ground truth khi runtime không có kết quả; benchmark đang có nguy cơ tự chấm chính dữ liệu seed |
| Workflow & approval | 5,5/10 | Luồng tra cứu Question Bank tốt hơn; approval/tool policy và immutable version chưa được xử lý triệt để |
| Truy cập giai đoạn dev | Chưa có | Chỉ cần Dev Access Gate server-side, chưa cần RBAC/SSO |
| Chất lượng code worktree | Chưa đạt | `ruff` lỗi 7 chỗ; test trọng tâm 71 pass, 1 fail |

## Các Cải Thiện Đã Xác Nhận

### Dữ liệu live không còn trống

Kiểm tra PostgreSQL/Qdrant trước đợt review này xác nhận cả năm collection đã có dữ liệu; Question Bank đã được đưa về collection Qdrant chuẩn và orphan facts đã giảm từ 788 xuống 0.

| Collection | Documents sẵn sàng | Chunks PostgreSQL | Facts | Points Qdrant |
| :--- | ---: | ---: | ---: | ---: |
| `col_admissions` | 1 | 7 | 8 | 7 |
| `col_regulations` | 1 | 6 | 7 | 6 |
| `col_library` | 1 | 6 | 7 | 6 |
| `col_drafting` | 1 | 6 | 7 | 6 |
| `col_question_bank` | 1 trong tổng 3 | 23 | 7 | 23 |

### Những thay đổi kỹ thuật có giá trị

- RAG gọi ModelOps để tổng hợp trả lời; FTS và dense search được kết hợp qua RRF.
- `primary_model` của Assistant đã được truyền xuống RAG/ModelOps.
- Dense và sparse search hiện chạy song song, giảm thời gian chờ của retrieval.
- Workflow Question Bank đã chuyển từ trả lời không có căn cứ sang `core.knowledge.answer` → citation guard → output/no-answer. Đây là hướng tốt cho **tra cứu quy định**.
- Frontend đã cải thiện rõ về SRP và code splitting từ các đợt trước.

## Review Mã Nguồn — Các Điểm Cần Sửa

### P0.1 — Seed “official” chưa có nguồn gốc có thể kiểm chứng

Library và Question Bank đang được seed như tài liệu chính thức, nhưng seed chỉ ghép các đoạn text trong code, tự tính hash/kích thước/trang và ghi một `storage_path` giả định. Không có số quyết định, ngày hiệu lực, URL/file gốc, trang trích dẫn hay hash của PDF/DOCX nguồn. Seed cũng không gọi storage driver để lưu tệp gốc.

**Bằng chứng:** [Library seed](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py:491), [Question Bank seed](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py:623), [storage path nhưng không lưu tệp](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py:503). Đối chiếu `qnu-ai-core` chỉ thấy template/benchmark tổng quát, không thấy các thông tin QNU cụ thể như hotline Thư viện, hạn mức mượn, Turnitin hoặc các ngưỡng P/D được dùng làm nguồn dữ liệu Platform.

Đây không phải kết luận rằng từng thông tin chắc chắn sai; vấn đề là mã hiện tại **không thể chứng minh thông tin đúng**. Với chatbot của trường, dữ liệu chưa truy xuất nguồn phải được coi là `draft/unverified`, không được gắn là official hay dùng làm căn cứ trả lời.

**Cần làm:** lấy PDF/DOCX/quyết định gốc, lưu qua MinIO/local storage, ghi `source_url`, `issuer`, `document_number`, `effective_date`, `file_hash` và `evidence_page/quote` cho từng fact. Nếu chưa có nguồn, chuyển các collection này sang Sample/Demo và không để RAG public trả lời như văn bản chính thức.

### P0.2 — Evaluation vẫn dựng câu trả lời từ ground truth

Khi chat/RAG không trả lời hoặc thiếu citation, `EvaluationService` vẫn tạo `actual_answer` và `actual_contexts` trực tiếp từ `ground_truth`. Vì thế một runtime fail/no-answer có thể vẫn đạt TM-08. Việc mới thêm keyword/ground-truth coverage vào relevance còn làm score dễ tự khớp với seed hơn.

**Bằng chứng:** [fallback từ ground truth](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/service.py:128), [relevance dùng benchmark keyword/ground truth](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/evaluator.py:112), [No-Answer trả faithfulness 1.0 theo cụm từ](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/evaluator.py:36).

**Cần làm:** bỏ hoàn toàn nhánh dựng answer/context; lưu rõ trạng thái `runtime`, `no_answer`, `failed`, `invalid`; khi runtime lỗi hoặc citation thiếu thì item phải fail/invalid. Đổi nhãn dashboard thành **TM-08 heuristic** cho đến khi có judge/trace độc lập và kiểm duyệt con người.

### P0.3 — `KnowledgeService` có method trùng, làm mất hành vi dọn file gốc

Các method `delete_document`, `delete_collection`, `archive_document` đang bị định nghĩa lại ở cuối class; trong snapshot mới nhất, `delete_document` còn xuất hiện thêm một lần nữa. Python sẽ âm thầm dùng bản sau. Riêng bản cuối không xóa file từ storage driver, trong khi bản cũ có; các bản mới nuốt lỗi Qdrant rồi vẫn xóa PostgreSQL, có thể để ghost vector. Lint bắt đúng nhóm lỗi này.

**Bằng chứng:** [bản delete cũ có xóa storage](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py:1278), [bản delete mới ghi đè](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py:1469), [collection method trùng](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py:437), [bản collection ghi đè](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py:1502), [archive trùng](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py:637), [archive ghi đè](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py:1535).

**Cần làm:** hợp nhất mỗi hành vi thành một method duy nhất; xóa file gốc, chunks, facts và vector theo một saga/outbox có trạng thái retryable. Không được log “graceful” rồi xác nhận xóa thành công nếu Qdrant thất bại; cần trả trạng thái `cleanup_pending` hoặc fail rõ ràng.

### P0.4 — Seeder Assistant vẫn ghi đè cấu hình quản trị viên

Docstring nói seed chỉ thêm template thiếu, nhưng code thực tế thay `system_prompt`, `collection_id` và toàn bộ `config` cho mọi Assistant đã tồn tại. Seeder lại được gọi khi application startup, vì vậy một lần restart có thể làm mất cấu hình do người dùng đặt.

**Bằng chứng:** [docstring](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py:266), [đoạn overwrite](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py:303), [startup gọi seed](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py:100).

**Cần làm:** startup chỉ insert bản ghi thiếu. Cập nhật template phải là tác vụ quản trị riêng, có preview diff/xác nhận và template version tách khỏi instance đã cấu hình.

### P0.5 — Dense retrieval chưa được ràng buộc lifecycle/tenant/revision

Sparse FTS có join với document và lọc status, nhưng dense Qdrant chỉ lọc `is_active`. Payload index chưa có `tenant_id`, `workspace_id`, document status, revision hay `is_retrievable`; vì vậy vector của tài liệu pending/phiên bản cũ có thể được citation.

**Bằng chứng:** [payload index](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py:222), [dense filter chỉ có is_active](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py:309), [sparse filter hiện tại](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/retriever.py:39).

**Cần làm:** state machine `pending → review_pending → indexing → ready/index_failed → archived`; chỉ index/serve revision `ready`; bắt buộc filter tenant/workspace/revision ở Qdrant; thêm test parity “pending không xuất hiện ở dense, sparse hay citation”.

### P0.6 — Approval và Tool Gateway vẫn bypass được

Diff mới đã bỏ hard-code `is_approved: true`, nhưng chỉ thay bằng `request.is_approved`. Client vẫn có thể gửi `true`, nên bypass chưa được loại bỏ. Tool endpoint vẫn chạy tool theo request mà không kiểm tra `enabled_tools`, approval requirement hay actor tin cậy. Điều này chưa được giải quyết bởi đổi Question Bank workflow, vì các workflow/endpoint khác vẫn còn đường bypass.

**Bằng chứng:** [chat](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/service.py:256), [SSE chat](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/service.py:320), [Tool Gateway](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/service.py:68), [resume lấy decided_by từ request](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/service.py:634).

**Cần làm:** bỏ `is_approved` khỏi chat request; Tool Gateway lấy Assistant profile server-side và enforce allowlist; tool có side effect phải chờ approval record; actor approval lấy từ session server-side, không từ DTO.

### P0.7 — Citation Guard vẫn phát citation khi không có bằng chứng

Hàm mới lọc citation theo số từ trùng giữa answer và quote, nhưng nếu không có citation nào đủ bằng chứng thì lại trả `citations[:2]`. Điều này phủ định mục tiêu của guard: một câu trả lời không được quote hỗ trợ vẫn có thể hiện hai citation như thể đã được căn cứ.

**Bằng chứng:** [evidence filter](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/citation_guard.py:57).

**Cần làm:** khi không đủ evidence phải trả mảng rỗng và chuyển response sang `insufficient_context`/no-answer nếu policy yêu cầu citation. Đồng thời xử lý `quote=None` an toàn và thêm test âm “answer không overlap không được giữ citation”.

## Các Điểm P1 Quan Trọng

### Question Bank đang đổi mục tiêu sản phẩm

Config mới bỏ `extract.fields` → `compose_questions` → `human.approval`, thay bằng RAG tra cứu quy định. Đây là đúng cho chatbot hỏi “quy định ra đề thế nào?”, nhưng không còn thực hiện lời hứa “tạo câu hỏi/ma trận/rubric rồi duyệt giảng viên”.

**Khuyến nghị:** tách thành hai workflow rõ tên: `question_bank_consult` (RAG + citation) và `question_bank_generate_draft` (nhận CLO/đề cương, tạo bản nháp, validation Bloom, human approval trước export). Không nên dùng một workflow để cố làm cả hai.

### Seed chưa tự hồi phục khi index thiếu

Library return ngay nếu document đã tồn tại; Question Bank chỉ index khi vừa tạo chunks. Nếu lần index đầu thất bại hoặc Qdrant bị xóa, startup seed sau đó không tự reconcile lại vector/facts/file gốc.

**Bằng chứng:** [Library return sớm](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py:482), [Question Bank chỉ index chunk mới](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py:702).

**Cần làm:** seed idempotent theo từng asset (document/chunk/fact/object/vector), có `reconcile --dry-run` và reindex explicit; không seed đồng bộ nặng trong startup.

### Cấu hình có nhưng chưa phải enforcement

`require_structured_facts` xuất hiện trong cấu hình Assistant nhưng chưa có nhánh runtime nào sử dụng nó. Tương tự, fallback model đã có schema nhưng RAG node chỉ gửi `primary_model`.

**Bằng chứng:** [config structured facts](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py:45), [RAG node chỉ truyền primary model](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/rag_answer_node.py:32).

**Cần làm:** hoặc enforce đúng trong RAG/service, hoặc không hiển thị như tính năng đã hoạt động. Fallback phải chuyển sang đúng model được cấu hình và log nguyên nhân/model được chọn.

### Cache đã thêm model key nhưng vẫn chưa đủ scope

Cache mới đã phân biệt `preferred_model_name` và có invalidate theo collection ở một số luồng. Đây là tiến bộ. Tuy vậy key chưa có tenant/workspace, Assistant system prompt/policy, content revision; edit/archive/delete vẫn chưa được bảo đảm invalidation ở một đường duy nhất.

**Cần làm:** dùng cache key gồm tenant, workspace, collection, document revision, Assistant revision, policy/model; gọi invalidation từ lifecycle service duy nhất sau khi transaction thành công.

### Workflow execution đã tiến gần hơn tới immutable version nhưng còn fail-open

Diff mới đã ưu tiên đọc `WorkflowVersion.dag_spec` ở execute và resume, là hướng sửa đúng. Nhưng nếu `workflow_version_id` tồn tại mà không tìm thấy version row, code lại fallback sang `WorkflowDefinition.dag_spec` mutable; thiếu content hash và test publish mới trong lúc pause rồi resume.

**Bằng chứng:** [execute](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/service.py:452), [resume](/D:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/service.py:654).

### Dev Access Gate là đủ cho giai đoạn này

Không cần JWT, SSO hay RBAC đa vai trò lúc này. Nhưng trước khi cho người khác dùng môi trường dev, cần một lớp nhỏ, đúng chỗ:

1. `POST /auth/login` kiểm tra **password hash từ biến môi trường** ở backend.
2. Lưu session ký số bằng cookie `HttpOnly`, `SameSite=Lax`; có `/auth/me` và `/auth/logout`.
3. Frontend chỉ có một trang `/login`; không kiểm mật khẩu ở trình duyệt.
4. Session cấp principal cố định `tenant_qnu`, `workspace_qnu`, `role=admin`; dependency bảo vệ API thay đổi dữ liệu, Tool Gateway và approval.

Lớp này vừa phù hợp yêu cầu đơn giản, vừa tạo actor tin cậy để sửa approval. RBAC thật chỉ cần làm khi xuất hiện nhiều cán bộ, nhiều tenant hoặc hành động có phân quyền khác nhau.

## Kết Quả Kiểm Tra Tự Động

- `uv run ruff check .`: **fail, 7 lỗi tại snapshot đầu review**.
  - 6 lỗi trong worktree hiện tại: duplicate stopword, ba method redefine và hai type `Any` chưa import.
  - 1 duplicate stopword khác nằm ở `openai_adapter.py`.
- `pytest tests/test_assistants.py tests/test_evaluation.py tests/test_rag.py tests/test_knowledge.py tests/test_workflows.py -v`: **71 passed, 1 failed, 17 warnings tại snapshot đầu review**.
  - Lỗi ở `test_seed_preserves_existing_user_configuration`: code gọi query bổ sung rồi overwrite Assistant hiện hữu.
  - Warnings còn có Qdrant API key qua HTTP và một số coroutine mock chưa await.
- Trong lúc review có một session song song tiếp tục đổi các file backend. Vì vậy hai kết quả trên không đại diện cho trạng thái cuối của session đó; cần chạy lại lint/test sau khi session kết thúc. Frontend không có thay đổi trong worktree tại snapshot đầu review, nên không chạy lại build frontend.

## Thứ Tự Sửa Đề Xuất

1. Dừng gọi seed Library/Question Bank là “official” cho đến khi gắn nguồn gốc và lưu file gốc qua storage driver.
2. Hợp nhất các method trùng; sửa cleanup thành có trạng thái/retry, rồi đưa `ruff` về xanh.
3. Sửa seed Assistant để chỉ insert missing; thêm test không overwrite và test reconciliation asset-by-asset.
4. Bỏ ground-truth fallback trong Evaluation; ghi outcome thật của runtime.
5. Enforce lifecycle/tenant/revision tại Qdrant và thêm parity tests.
6. Gỡ approval/tool bypass; triển khai Dev Access Gate tối giản để có trusted actor.
7. Tách Question Bank thành workflow tra cứu và workflow tạo nháp có approval.
8. Khóa execute/resume vào `WorkflowVersion` immutable; hoàn thiện fallback model, structured facts và provider streaming thật.

Sau sáu hạng mục đầu, chạy lại benchmark bằng source đã được xác minh và runtime không fallback. Khi đó dashboard mới có thể dùng làm acceptance gate cho pilot nội bộ.
