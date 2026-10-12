# Phiên #361 — Đánh giá BM25 cho RAG và DAG

## Phạm vi

Review runtime và nguồn chính thức, không triển khai BM25, không sửa production code, không reset dữ liệu, không khởi động dịch vụ hoặc sửa qnu-sso. Skills qnu-rag-pipeline và qnu-clean-code-architect hướng dẫn giữ retrieval dùng chung, kiểm chứng theo phạm vi và tránh mở rộng hạ tầng khi chưa có bằng chứng.

## Hiện trạng có bằng chứng

- `backend/app/modules/rag/retriever.py:283`: lexical chính là weighted ILIKE trên content và title/file_name của KnowledgeDocument. `:369` chỉ bổ sung PostgreSQL FTS khi chưa đủ top_k; `:381` dùng ts_rank_cd, không phải BM25. Chấm điểm trọng số token không có corpus IDF và TF saturation của BM25.
- `retriever.py:664` chạy dense/sparse/variants song song; `fusion.py:68` hợp nhất RRF và legal priority; reranker sau fusion. `rag/service.py:186` candidate depth hiện 8 hoặc 12, tùy intent.
- `workflows/nodes/rag_answer_node.py:154` gọi rag_service.ask, tức DAG đã dùng chung pipeline RAG, không cần một bộ BM25 thứ hai trong engine.
- `knowledge/services/vector_generation_service.py:305`: nguồn ADR-012 tạo KnowledgeChunk.document_id=None, title nằm trong chunk_metadata/document_title. Lexical anchor hiện chỉ nhìn KnowledgeDocument nên không tìm được title-only của nguồn mới qua nhánh đó, dù content vẫn tìm được.
- `rag/vector_indexer.py:55` hiện provision dense vector, chưa có sparse BM25. Không tìm thấy BM25/FastEmbed/ParadeDB trong phạm vi app/tests/dependencies đã quét.
- GET http://localhost:6333/ trả version **1.19.0**. Compose infra dùng qdrant:latest; kiểm tra này xác nhận bản đang chạy, không có thao tác upgrade.
- WorkflowContext chưa có workspace_id, AskRequest trong RAG node không truyền workspace; rag/service.py:424 và :446 không truyền tenant vào LLMGenerateRequest. Service vẫn có grounded synthesis sau khi cả provider lỗi. BM25 không sửa các vấn đề scope/error contract này.

## Đề xuất, chưa phải quyết định triển khai

Nên thử BM25 thay nhánh lexical heuristic, không thay dense embedding, facts hay DAG scheduler. Giữ một HybridRetriever dùng chung cho API RAG và DAG: dense + BM25 → RRF → reranker → facts/context → generation/guardrails.

Ưu tiên thử sparse BM25 trong Qdrant đang có, tránh thêm Elasticsearch/OpenSearch hoặc Python in-memory corpus cho mỗi worker. PostgreSQL giữ provenance, canonical chunks/facts, active pointers và policy. Thêm sparse vector là additive; backfill từ Markdown/chunk sets hiện có, không OCR hay embedding dense lại nếu nội dung/cấu hình dense không đổi. Phải kiểm tra SDK API tương thích trước code, không dựa chỉ vào lower-bound qdrant-client>=1.11.0.

Các điều kiện bắt buộc:

1. Tokenization Unicode NFC nhất quán giữa indexing/query, thử tiếng Việt có/không dấu; không dùng mặc định English stemming/stopwords. Không hardcode từ vựng lĩnh vực. BM25 không phải exact phrase filter: mã ngành/số hiệu/năm cần metadata field và exact filter/boost khi thích hợp.
2. Chỉ truy vấn chunks thuộc snapshot active với cùng tenant/workspace/binding/index_revision/vector_generation và lifecycle allowlist như dense. Sparse phải nằm trong build/parity/publish/rollback/purge; staging chưa publish không được trả cho chatbot.
3. Corpus statistics cần scope rõ: IDF Qdrant mặc định trên shard không tự trở thành thống kê chỉ của dữ liệu qua payload filter. Tránh lịch sử/staging/multi-model duplicate làm lệch IDF; cân nhắc namespace generation hoặc cấu hình scope IDF phù hợp, kiểm chứng bằng benchmark.
4. Preserve title, file name, số hiệu, năm và section của nguồn snapshot mới trong lexical indexing. Tách field boost khỏi score raw, giữ RRF thay vì cộng cosine và BM25 trực tiếp.
5. Thử candidate depth 20–40 mỗi nhánh rồi rerank 5–8 là cấu hình thí nghiệm, không phải tối ưu đã đo. Không giữ ba nhánh ILIKE/FTS/BM25 thường trực chỉ để đếm thêm votes; fallback/degraded phải có policy và telemetry rõ.
6. Cache fingerprint phải bao gồm retrieval/tokenizer policy version khi đổi chiến lược. Đổi embedding model không cần OCR lại; BM25 representation có thể tái sử dụng cùng chunk set nhưng snapshot/lifecycle vẫn đúng mỗi generation.

## Kiểm chứng và giới hạn

- 25 tests liên quan đạt: test_dynamic_specificity_retriever.py, test_retrieval_engine_v2.py, test_dag_routing_regression.py; 4.75s. Chạy Python venv với -p no:cacheprovider. Tests gồm unit/mocked boundaries, không chứng minh BM25 hoặc chatbot end-to-end chạy thật.
- Kiểm tra version Qdrant read-only thành công.
- Chưa chạy A/B corpus thật, BM25 query, browser E2E, full Pytest, Ruff hay FE build vì không sửa runtime. Không kết luận BM25 chắc chắn cải thiện bao nhiêu phần trăm.
- Bộ test_rag_golden_evaluation_benchmark hiện có ca schema/heuristic với answer/context cấp sẵn; không thay thế benchmark retrieval thật.

Acceptance đề xuất: tập câu hỏi official có expected chunk IDs/page/revision cho số hiệu, mã ngành, năm, câu paraphrase, không dấu, thiếu căn cứ; so sánh hiện tại/dense-only/BM25-only/hybrid bằng Recall@k, MRR/nDCG và p95 dưới concurrency. Chạy cả /rag và chatbot qua DAG, gồm đổi model, publish/rollback/delete, cross-workspace và provider/Qdrant down. Tắt cache hoặc version cache khi A/B. Nâng cấp chỉ sau khi đúng scope/lifecycle và có lợi so baseline.

## Nguồn chính thức

- [PostgreSQL text-search ranking](https://www.postgresql.org/docs/current/textsearch-controls.html): ts_rank/ts_rank_cd không dùng thống kê toàn corpus.
- [Qdrant full-text/BM25](https://qdrant.tech/documentation/search/text-search/full-text-search/): sparse IDF, language configuration, language-neutral options v1.19 và corpus IDF scope.
- [Qdrant hybrid search](https://qdrant.tech/documentation/search-tuning/hybrid-search/): dense/BM25/RRF, candidate depth và additive sparse vector từ v1.18.

## Tệp tài liệu cập nhật

Nhật ký này, docs/nhat_ky/README.md, docs/WORK_LOG.md, docs/memory/PROJECT_CONTEXT.md và snapshot #361. Không sửa tài liệu quy trình runtime vì kiến trúc đang chạy chưa thay đổi.
