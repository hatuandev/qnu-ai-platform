---
name: qnu-rag-pipeline
description: Tune or debug QNU retrieval, scope, fusion, reranking, evidence context and citations in the existing Python pipeline. Use for RAG behavior changes; use qnu-rag-evaluation for comparative benchmarks and qnu-knowledge-ingestion for parsing.
---

# Retrieval có phạm vi và bằng chứng

Đọc mã/config/snapshot trước. Điểm vào thường ở `backend/app/modules/rag/service.py`, `retriever.py`, `vector_indexer.py`, `fusion.py`, `reranker.py`, `evidence_pipeline.py`, `evidence_runtime.py` và `facts.py`; pipeline chọn theo assistant/policy, không mặc định mọi request đi cùng một nhánh.

## Cách làm

1. Vẽ luồng thật ngắn: resolve hội thoại/scope → snapshot/quyền → retrieval → fusion/rerank → evidence/context → answer/citation/cache. Chỉ ra nhánh đang dùng, nhánh chưa chạy và điểm lỗi trước khi sửa.
2. Scope gồm actor/tenant/workspace, collection/binding, publication/index/source revision và yêu cầu năm/đợt/ngành/metric. Lọc đủ mọi nhánh trước khi chấm/chọn candidate khi có scope xác thực; không chỉ lọc ở prompt hoặc sau TopK. Unknown không tự biến thành năm được hỏi. Nếu schema chưa có trường cần thiết, nêu gap và phương án riêng, không giả vờ filter đã có.
3. Phân biệt năm ban hành, năm từng dòng/cột, hiệu lực và trường tổ chức kỳ thi với trường đích. Query expansion/history không được thay đổi scope gốc. Follow-up phải tái dựng cùng scope/nguồn; lỗi resolver không thành unknown rồi trả answered.
4. Xác minh embedding endpoint trả được gì. Dense, PostgreSQL FTS, BM25 và BGE-M3 learned sparse là những nhánh khác nhau. BM25 trong evidence không có nghĩa sparse Qdrant đã được index. Đổi dimension/model/normalization phải có generation/reindex tương thích và rollout được phép.
5. Fusion giữ ID và provenance; không cộng raw cosine/FTS/BM25 khác thang. RRF gộp thứ hạng; weighted RRF khác weighted normalized score. Alpha từ paper không phải tỷ lệ 30/70 hay tham số RRF. Trọng số và legal priority là quyết định cần ablation, không thay kiểm tra hiệu lực.
6. Tách `K_dense`, `K_sparse`, `K_fusion`, `K_rerank_input`, `K_context`; lấy từ config thật, ghi trace. Giá trị 30/30/30/5, k=60, dimension hoặc ngưỡng score chỉ là ví dụ/thiết lập khi đã xác minh, không tối ưu mặc định.
7. Giữ thứ hạng, source/binding/revision/hash qua dedup, expansion và rerank; xử lý ID thiếu/trùng, ties và response sai. Lỗi reranker chỉ degrade nếu policy cho phép, kèm trace; lỗi auth/tenant không được biến thành no-answer hay fallback mở quyền.
8. Context giữ header/đơn vị/footnote cùng ô được trích; không gộp số liệu khác nguồn/năm chưa rõ. Câu hỏi liệt kê toàn bộ cần enumeration có scope, pagination/set coverage; TopK RAG không chứng minh đã liệt kê hết. Phép tính dùng engine/rule đã duyệt và source-bound, không để LLM tự tính số chính thức.
9. Cache key/validation phải gắn tenant/workspace, quyền, assistant/policy, normalized query, scope, snapshot và model/config ảnh hưởng đáp án. Cache hit vẫn kiểm tra quyền và nguồn còn hiệu lực; không dùng threshold cache cố định để bỏ qua kiểm chứng.
10. Trước bàn giao đối chiếu evidence/citations thật; thiếu căn cứ thì abstain/clarify với lý do. Không bịa trang/URL/thông tin liên hệ. Dùng [qnu-rag-evaluation](../qnu-rag-evaluation/SKILL.md) khi đo chất lượng và [gate chung](../../rules/verification.md) khi kiểm chứng.

## Bằng chứng bàn giao

Luồng đang chạy, phạm vi file, diff hành vi, test scope/provenance/ranking, candidate counts, fallback trace và giới hạn chưa chạy. Không tuyên bố dense/hybrid/model thật hoạt động chỉ vì có class hoặc mock test xanh.
