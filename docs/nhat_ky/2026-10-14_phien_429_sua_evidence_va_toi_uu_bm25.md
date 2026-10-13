# Phiên 429 — Sửa evidence RAG/DAG và tối ưu BM25

## Phạm vi

Người dùng đồng ý sửa các lỗi trong batch20 và tối ưu BM25 có sẵn, sau khi đã được giải thích đề xuất. Áp dụng skill Backend, RAG, ModelOps, clean-code và chatbot-builder. Không hardcode FAQ/đáp án/tên model; không reset DB, sửa nguồn, OCR lại, reembed, xuất bản lại hoặc bật backup. Quota vẫn unlimited theo phiên428; giữ guardrails, scopes, verifier và exact source binding.

## Chẩn đoán trước sửa

- Tái dựng context từ lượt428 cho các câu1/9/13/14/15/19/20 tại `backend/storage/evidence429_before.json` (14 kết quả, hai route). Chỉ đọc nguồn và gọi retrieval/reranker đã cấu hình, không gọi model để cung cấp expected answers.
- Câu9 mở rộng list gộp numbered parent (đối tượng/tiêu đề phương thức) và bullet children, rồi cắt6, làm mất PT5. Không phải thiếu PT5 trong nguồn.
- Câu1 preferred prose có mã cơ sở đào tạo DQN, nhưng repeated table labels làm thay đổi IDF và reranker/packing giữ đoạn tên trường/phương thức thay trường định danh. Verifier còn tạo quote của DQN gắn sai vào block heading, gây precedence error. Không cho phép quote không khớp đi qua.
- DAG query rewrite ghi `user_message` thành truy vấn mới, mất ý nghĩa gốc ở bước RAG. Phải giữ input đã được guardrail xử lý, không lấy biến này làm original.
- Regression trước sửa:4/4 fail đúng structural list, atomic packing, reviewed-row quote và partial footer.

## Thuật toán và thay đổi

### BM25

Tách `evidence_bm25.py`: inverted postings tính corpus IDF/length/TF một lần; LRU tối đa4 corpus, khóa gồm binding/index/source/block ID/hash và nội dung. Không cache source authorization, DB validity hay đối tượng EvidenceBlock. Kết quả luôn lấy từ các object đã validate của request hiện tại; scope-year filtering áp dụng mỗi lượt, không nằm trong cache có thể cũ. Không bỏ dấu nội dung để trả lời: token normalization chỉ phục vụ matching.

Giữ công thức BM25 tương đương bản cũ; term order ổn định. Harness đo trên frozen diagnostic58blocks/14queries,30iterations: median mỗi rank7,950ms→2,638ms warm cache, rankings identical14/14,433hits/1miss. Chỉ benchmark phần BM25, không chứng minh end-to-end nhanh3lần. Độ nhớ tối đa4corpus; cache không thay validation tenant/workspace/hash/review ở `load_published_blocks`.

Shared evidence pipeline dùng question gốc + plan variants cho BM25/RRF variant rankings, giữ vector/FTS/RRF anchors của retriever hiện có, reranker AIserver và nhánh reviewed facts riêng. Chưa chuyển toàn bộ legacy PostgreSQL FTS sang BM25 indexed DB/search engine. Không thêm Elasticsearch/dependency.

Preferred source prose xếp hạng riêng, không cộng vào thống kê với repeated table-row field labels; bảng vẫn có lane riêng. Preferred lexical window12/query,cap24; semantic rerank2 và bảo vệ3 lexical hits ngắn; giữ tối đa5 preferred winners trong context. Đây là cửa sổ thuật toán có giới hạn, không danh sách từ khóa/đáp án nghiệp vụ. Không tự khẳng định thông tin của preferred source thay unique information khác.

### Cấu trúc liệt kê

Tách `evidence_lists.py`: nhóm theo source identity + thứ tự span + marker family (bullet/number/letter), không trộn numbered parent vào bullet children; xuyên page markers đã bóc nhưng không xuyên prose boundaries. Enumeration neighbors không cắt nửa nhóm. Context packing atomic cho enumeration: đủ ngân sách thì giữ cả nhóm+same-source season header, không đủ thì bỏ cả nhóm. Giữ một trailing prose paragraph ngắn, không lấy numbered/Markdown/all-uppercase section tiếp theo.

Proposal hướng dẫn mỗi item là claim riêng; deterministic coverage kiểm tra block IDs của nhóm đã chạm tới. Thiếu list member thì có một repair giới hạn, sau semantic verification vẫn thiếu thì fail-closed, không giữ câu tổng “4 phương thức” như verified partial. Không dùng số thứ tự cuối làm chứng cứ đếm. Coverage chỉ là invariant của nhóm đã truy xuất, không chứng minh toàn bộ nguồn/kho đã đầy đủ.

### Quote, precedence và ý định

- `evidence_claims.py`: nếu quote đã khớp trong đúng reviewed row, kiểm tra số trên quote gốc trước, rồi mở rộng thành nguyên dòng đã duyệt để giữ entity. Claim vẫn phải giữ authoritative entity_name, không cho suy rộng từ một row thành cả nhóm, không sửa OCR thành tên đoán. Semantic verifier tiếp tục kiểm tra thuộc tính/ngữ cảnh; không lấy số ở cột khác làm dữ kiện đúng.
- One bounded proposal repair áp dụng cả khi một số claims bị loại hoặc enum còn thiếu. Không retry vô hạn, không đưa expected answer vào validation errors.
- `evidence_precedence.py`: same-claim repeated quote không phải replacement; giữ độc lập verdict booleans, không tự promote scope. Invalid replacement proof loại claim liên quan, ghi `INVALID_PRECEDENCE_PROOF`, không biến thành HTTP502 toàn workflow. Upstream model/DB errors vẫn lỗi thực, không thành fake success.
- `AskRequest.original_question` từ sanitized workflow input, không từ `query_rewrite.user_message`; pipeline lập kế hoạch/kiểm chứng theo câu gốc. RAG input guard kiểm tra cả original và rewritten để không mở bypass.
- QueryPlan có target_institution/exam_organizer/intent riêng để không nhầm trường tuyển sinh với đơn vị tổ chức thi, lựa chọn phương thức với kết hợp điểm. Các field là semantic labels, không vocabulary hardcode.
- Partial giữ claims/citations đã xác minh, dùng thông báo phần còn lại cần đối soát thay no-answer phủ định chính nó. Raw missing labels vẫn lưu trong decision nhưng không chèn vào public answer tiếng Việt.
- Log selection IDs/corpus/candidate/packed và response `stage_timings_ms` cho planning/retrieval/proposal/verification. Không log credentials/model raw response. Hiện chưa trả toàn bộ candidate funnel trong public API.

### Harness

`evaluate_evidence_417.py` thêm DAG RAG node vào fingerprint, dừng khi QUOTA_EXCEEDED/TENANT_BLOCKED. Không đưa expected answers vào prompt. `benchmark_evidence_bm25_429.py` so sánh reference formula offline để không đổi baseline rankings.

## Tệp thay đổi

Runtime: `backend/app/modules/rag/evidence_bm25.py` (mới), `evidence_lists.py` (mới), `evidence_blocks.py`, `evidence_claims.py`, `evidence_precedence.py`, `evidence_pipeline.py`, `evidence_model.py`, `evidence_schemas.py`, `schemas.py`, `service.py`; `backend/app/modules/workflows/nodes/rag_answer_node.py`.

Tests: `backend/tests/test_evidence_retrieval_regressions.py` (17 ca mới), `test_evidence_claims.py` cập nhật contract quoted row fragment→whole identified row; group generalization vẫn reject. Scripts: evaluator và microbenchmark trên. Docs: journal này, index, memory/work log; báo cáo cuối20 chưa chốt khi người dùng bổ sung ngữ cảnh.

## Kiểm thử mã chốt

- 78 focused đạt15,15s, gồm13regressions mới + evidence/contracts/DAGboundary/provider-safety.
- PostgreSQL evidence opt-in đã chạy trong focused (1ca), outer rollback không sửa corpus thật.
- Full Backend1171pass/11baselinefail/13skip187,60s (`storage/pytest429_full.log`). 11 lỗi nền tương tự428 ở consulting export,publishing/GC/canary,reconciliation,auth cookie,universaltools. Không báo fullsuite xanh.
- Ruff toàn Backend đạt, có cảnh báo quyền storagepytest cũ. Không đổi FE, không Vite/Biome.
- Critical iterations không ghép accuracy: lúc đầu5ca DAG4answered/1missing; sourcecode probes cònmissing trước khi tách prose/facts; code-prose cuối2/2answeredDQN. Iterations là diagnosis, không thay fresh20.

## Fresh20 trên mã chốt

Artifact `backend/storage/admissions_eval429_final20.json` đã hoàn tất trên iteration trước bổ sung same-source season-header binding và enumeration_subject: 40/40 HTTP200, DAG10answered/10insufficient; RAG12answered/8insufficient. Integrity26/26,125GPT-OSS calls/no fallback; config/publication/code tracked unchanged. Câu9 giữ đủ PT1–5 và tuyển thẳng, câu1 DQN đúng; các câu thiếu căn cứ vẫn chưa trả lời. Không dùng số answered để kết luận accuracy.

Sau lượt này bổ sung quote năm chỉ từ heading thật cùng binding/index/source, không dùng filename/nguồn khác; thiếu giá trị số vẫn reject. Coverage của danh sách dùng enumeration_subject để không yêu cầu liệt kê toàn bộ phương thức khi câu hỏi thực sự liệt kê ngành. Nhóm không có nhãn cấu trúc đủ rõ vẫn kiểm tra bảo thủ.

Final focused82pass/14,67s (17 regressions + evidence/PG/contracts/provider-safety/workflow boundary). Full final1175pass/11baselinefail/13skip170,09s tại `storage/pytest429_full_verified_unique.log`; dùng basetemp riêng vì lượt dùng thư mục Temp chung có38 lỗi quyền Windows. Ruff đạt. Chưa có failure mới ở bộ RAG/DAG, nhưng fullsuite chưa xanh.

`storage/admissions_eval429_verified20.json` là lượt bị dịch vụ gián đoạn: câu1 hai route thành công, từ câu2 ALL_PROVIDERS_UNAVAILABLE; đọc trực tiếp catalogue9router cũng timeout. Không coi là kết quả chất lượng. Sau catalogue200/khóa active/noquota, chạy mới `storage/admissions_eval429_recovered20.json`. Khi người dùng bổ sung thông tin, file này có22/40 lượt (14answered/8insufficient, HTTP200); tiến trình nền còn chạy, chưa kiểm chứng cuối/fingerprint. Không ghép các iterations thành một batch hoặc kết luận accuracy. Chưa chạy Ragas/full82.

## Ngữ cảnh người dùng bổ sung và bước tiếp theo

Ngày2026-10-14 người dùng xác nhận corpus trộn tài liệu2025/2026 và chưa có đủ nội dung để trả lời82câu; đang tổng hợp một văn bản đầy đủ hơn. Vì vậy không đặt mục tiêu82/82answered hoặc dùng FAQ để ép retrieval. Cần tách: lỗi truy xuất/kiểm chứng, thiếu nội dung trong corpus, khác năm áp dụng và mâu thuẫn cùng ngữ cảnh. Câu không ghi năm dùng năm hiện tại theo chính sách đã thống nhất; hỏi rõ2025 phải giữ2025, không tự lấy2026. Năm ban hành/filename không thay năm hiệu lực. Văn bản tổng hợp cần đọc và đối chiếu nguồn, không tự động coi là có thẩm quyền cao hơn TB1906 hoặc xuất bản thay nguồn hiện hành. Chờ người dùng gửi file trước khi chỉnh thêm theo nội dung; không reset/reembed/publish/đổi model.

## Lưu ý

Dev BE nhận source qua reload; agent không stop/restart các dịch vụ. Worker lâu sống cần restart khi dùng runtime mới. Hai chatmodels cùng9router, chưa chứng minh fallbackGemma trong batch. Giữ reranker `prov_rtx5090_vllm/bge-reranker-v2-m3` và modelGPT-OSS người dùng chọn. Guardrails không bị giảm để tăng tỷ lệ answered. Batch20 được chấm nội dung riêng; supported/integrity không phải accuracy.
