# Phiên #441 — Chat RAG trực tiếp và đối soát chứng cứ

## Phạm vi được người dùng yêu cầu

Đưa DAG ra khỏi quy trình chatbot hỏi–đáp; tham khảo `rohitg00/ai-engineering-from-scratch`; xử lý các câu lỗi đã ghi nhận ở #438/#439. Giữ module workflow cho tác vụ riêng, không xóa lịch sử DAG, không reset DB, reindex, xuất bản lại hoặc đổi cấu hình ModelOps. Các câu kiểm thử tạo hội thoại và usage log thật.

Áp dụng skills backend, clean-code, chatbot-builder, rag-pipeline; frontend-architect và admin-frontend-design cho phần điều hướng trợ lý. Không sao chép mã mẫu của repo bên ngoài vào runtime.

## Quyết định kiến trúc

- Assistant có chế độ `rag` hoặc `workflow`. Chat/SSE ở chế độ RAG gọi RAGService trực tiếp, không tạo WorkflowExecuteRequest; execution_id=null. Cấu hình workflow cũ được giữ. Chế độ tường minh ưu tiên; trợ lý legacy bật evidence policy dùng RAG, legacy khác giữ workflow.
- Trợ lý mới mặc định RAG khi không gửi config. Trợ lý tác vụ trong seed giữ workflow. Tạo, nhân bản và xuất bản RAG không cần fork/pin DAG.
- Giữ scope tenant/workspace, lịch sử, PII/input guard, cấu hình model/provider/fallback/reranker, policy nguồn/năm, citations, no-answer và ghi nhận gap. Lịch sử phải đúng tenant/trợ lý; không nhập tệp người dùng làm chứng cứ chính thức. RAG chat báo 422 rõ ràng khi gửi attachments, yêu cầu đưa tài liệu vào kho đã xuất bản.
- SSE chỉ phát nội dung đã đối soát; provider/internal failure phát error, không phát done thành công giả. Hiện phát một delta sau verification, chưa phải stream nháp LLM từng token.
- UI ẩn tab/menu DAG và công cụ hành động cho RAG; URL workflow cũ hiển thị giải thích. Không tạo primitive mới, dùng Card/Button/navigation sẵn có.

## Các phần tham khảo hữu ích

| Tài liệu trực tiếp trong repo | Ứng dụng vào QNU | Giới hạn |
| --- | --- | --- |
| [Structured Outputs](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/phases/11-llm-engineering/03-structured-outputs/docs/en.md) | Schema động giới hạn mã đoạn chứng minh; kiểm tra hợp đồng và sửa tối đa một lần | JSON đúng schema không chứng minh câu trả lời đúng |
| [Context Engineering](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/phases/11-llm-engineering/05-context-engineering/docs/en.md) | Ưu tiên nội dung trả lời, giữ header/parent cần thiết và nhóm liệt kê | Context dài hơn không thay thế relevance/coverage |
| [Advanced RAG](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/phases/11-llm-engineering/07-advanced-rag/docs/en.md) | BM25 + semantic anchors, RRF, reranker cấu hình từ AI server; metadata năm/phạm vi và parent context | Không dùng HyDE sinh đáp án giả làm chứng cứ; không đổi quyền ưu tiên nguồn của quản trị |
| [Evaluation](https://github.com/rohitg00/ai-engineering-from-scratch/blob/main/phases/11-llm-engineering/10-evaluation/docs/en.md) | Tách HTTP success, source-span correctness, completeness và answer correctness; so sánh trên cùng snapshot | Không gọi tỷ lệ answered là accuracy/Ragas |

Đã đọc tài liệu các bài trên; không tuyên bố kiểm toán toàn repo hoặc chạy hết projects minh họa. QNU đã có hybrid retrieval, không thay engine bằng một demo từ repo.

## Chứng cứ và thuật toán

Model chọn passage IDs do máy chủ cấp. Máy chủ gắn lại quote/offset/hash/revision nguyên gốc, tránh lỗi model chép dấu ba chấm, sai mã block hoặc ký hiệu công thức. Audit dùng IDs giới hạn bằng enum động, không sao chép lại claim/quote hoặc đánh số reference. Kiểm tra thiếu/duplicate verdict và ID giả fail closed. Các kiểm tra số, cùng nguồn, entity row, year applicability và source preference vẫn giữ.

Lượt chat20 đầu phát hiện supported vẫn thiếu điều kiện (13/19/22), câu16 bỏ năng khiếu khỏi PT5, câu6 chỉ giữ53; mã trường bị verifier so khớp nhãn quá máy móc, câu9 xếp hạng ưu tiên tiêu đề/section hơn đoạn có đáp án. Không coi những câu này là đúng dù HTTP200/supported.

BM25 field-weighted dùng body1/context0.15, giữ revision-keyed cache. Enumeration mở rộng tối đa3 body children từ heading phù hợp mà không vượt section; giữ danh sách cú pháp nguyên nhóm. Đã có regression body-vs-label và bounded section expansion. Câu trả lời bảo toàn nguyên câu nguồn được chọn để không làm mất ngoại lệ/quan hệ. Text model chỉ là nhãn: số/hình thức diễn đạt do model nghĩ ra không được xuất bản. Không hardcode bảng đáp án, từ điển domain hoặc model.

## Tệp chính

- Backend assistants: runtime.py, schemas.py, seeder.py, services/assistant_chat_service.py, assistant_rag_chat.py, assistant_lifecycle_service.py.
- Backend RAG: evidence_passages.py, evidence_indexed_audit.py, evidence_claims.py, evidence_verification.py, evidence_scope.py, evidence_bm25.py, evidence_pipeline.py, evidence_blocks.py.
- Conversations: schemas.py, service.py; lịch sử theo tenant/trợ lý.
- Frontend: types/assistants.ts; assistant-header.tsx, assistant-workspace-nav.tsx, sections/assistant-tools-section.tsx; assistant-detail-page.tsx; use-rag-stream.ts báo lỗi dễ đọc và chặn EOF hoàn tất giả.
- Tests: test_rag_chat_441.py; các suite evidence, workflow ownership, assistants và HITL/history.
- Harness: scripts/evaluate_evidence_417.py hỗ trợ route chat và runtime fingerprint.

## Kiểm thử và nghiệm thu

Focus110 passed; Ruff toàn BE đạt (warnings về ACL thư mục temp cũ), Biome6files đạt, Vite+TS build5115modules exit0. Full cuối1253cases:1227 passed/11 failed/15 skipped;11 lỗi baseline ngoài thay đổi (consulting export/universal tools/publishingGC-canary/reconciliation/authcookie). XML: backend/storage/pytest441_acceptance.xml. Lượt full đầu có2 lỗi fixture HITL chưa khai báo thread nonexistent sau thêm scope check; đã sửa fixture và kiểm chứng routing/HITL, không làm yếu validation để hợp mock.

Lượt chat20 trước extractive:19HTTP200/1scope502,15supported/3missing/1partial, nhưng supported có lỗi thiếu ý/quan hệ; không phải accuracy. Lượt final20 gặp16ALL_PROVIDERS_UNAVAILABLE,3supported/1missing. GET9router có timeout trong khi healthBE200; người dùng xác nhận router chạy và mạng quốc tế thấp. Lượt verified20 dừng sau6case để hoàn tất section expansion.

Lượt acceptance20:20/20HTTP200,17supported/2partial(câu5/13)/1missing(câu38),không execution_idDAG; runtime/config/publication unchanged=true. Mean29,65s,min16,64s,max66,02s. Đốisoát31/31canonical citations khớp raw span/hash DB. Primary105lượt/fallback7lượt thànhcông. SSElive mãtrườngHTTP200,status→citation→token→done,answered/execution_id=null. Các câu6/9/16/19/22/25/80/81/82 đã giữ đúng phạm vi, điều kiện và năm khi đọc kết quả; không xem17supported làaccuracy85%.

Còn falsepartial5 do numeric qualifier lấy cảsốnền củaquote dài;13 chọnchưađủpolicy nhóm giáo viên;38 cầnđốisoátretrieval/scope, chưakhẳngđịnhtoàncorpus thiếu. Còn lặpparagraph/sentence con ở48 và phrasingextractive chưađẹp. Chưa sửa xong tấtcả lỗi; ưu tiên3ca này trướcfull82. [Báocáo20câu](../kiem_thu/2026-10-14_20_cau_chat_rag_truc_tiep.md).

Artifacts raw ở backend/storage/admissions_eval441_*.json. Lượt probe7 có thay đổi runtime trong lúc chạy, chỉ dùng chẩn đoán, không dùng làm bảng so sánh nghiệm thu. Lượt chat20 giữ fingerprint riêng và không bao gồm đáp án chuẩn trong request gửi model.

Không chạy đủ82 hoặc xác nhận đạt TM-08 trước khi các ca có nguồn được đối soát đầy đủ. Cần giữ rõ các ca thiếu dữ liệu thực sự và lỗi runtime/provider, không nhập chung vào một tỷ lệ thất bại.
