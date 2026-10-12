# Các thuật toán nâng cao chất lượng và tối ưu QNU AI Platform

Ngày: 2026-10-11. Trạng thái: tài liệu đề xuất, chưa phải danh sách chức năng đã triển khai hoặc lệnh triển khai tất cả.

## 1. Kết luận nhanh

Ưu tiên cải thiện khả năng tìm đúng bằng chứng và giữ đủ ngữ cảnh trước khi tăng số mô hình hay số node DAG.

Hướng gần hạn: **dense embedding + BM25 → RRF → reranker → ngữ cảnh theo cấu trúc → facts và kiểm chứng trích dẫn**. Chống trùng/đa dạng ngữ cảnh chỉ thêm khi đo thấy kết quả bị lặp. Learned sparse, ColBERT và HyDE là thử nghiệm tùy nhu cầu, không bật toàn bộ mặc định.

Đây là suy luận áp dụng cho repo từ khảo sát #361 và tài liệu chính thức, không phải cam kết tăng độ chính xác hoặc tốc độ theo một tỷ lệ đã đo. Cần A/B trên dữ liệu thật để quyết định giữ hoặc bỏ từng cải tiến.

## 2. Ranh giới nghiệp vụ không thay đổi

- Kho tài liệu chỉ quản lý nhóm, tệp gốc, phiên bản tệp và metadata nhập bởi người dùng; không OCR, embedding hoặc xuất bản tri thức.
- Kho tri thức nhập snapshot độc lập, bóc tách/chuẩn hóa, duyệt nếu cần, tạo chunk sets/facts, embedding và xuất bản.
- Markdown chuẩn hóa là nội dung đầu vào; Qdrant lưu vector của chunks cùng payload, không phải chỉ lưu nguyên tệp `.md` rồi tự hiểu nội dung.
- Đổi embedding model tái sử dụng bản bóc tách và chunk set nếu cấu hình nội dung không đổi. Đổi tokenizer/chunking có thể cần dựng lại chỉ mục tương ứng, không mặc nhiên OCR lại.
- Xóa vĩnh viễn nguồn trong Kho tri thức phải dọn các chỉ mục/artifacts thuộc nguồn, nhưng giữ tệp trong Kho tài liệu.
- Mọi thuật toán retrieval phải giữ đúng tenant/workspace, collection, source/binding, index revision và generation đã xuất bản. Không lấy staging hay phiên bản chờ duyệt để trả lời.
- DAG là đồ thị điều phối công việc. **DAG không đồng nghĩa GraphRAG**: có canvas DAG không có nghĩa đã có đồ thị thực thể để tìm kiếm tri thức.

## 3. Những gì repo đã có

Khảo sát phiên #361 xác nhận các điểm dưới đây; cần rà lại nếu code thay đổi sau ngày này. “Đã có” chỉ nói thành phần tồn tại, không đồng nghĩa đã nghiệm thu production.

| Thành phần | Bằng chứng trong repo | Định hướng |
| :--- | :--- | :--- |
| Dense retrieval, cosine và Qdrant/HNSW | `backend/app/modules/rag/vector_indexer.py` | Giữ; tuning theo benchmark |
| Lexical weighted ILIKE + FTS ts_rank_cd bổ sung | `backend/app/modules/rag/retriever.py` | Chưa phải BM25; thử thay nhánh heuristic |
| RRF và trọng số ưu tiên văn bản | `backend/app/modules/rag/fusion.py` | Tối ưu, không viết thêm fusion song song |
| Cross-encoder reranker | `backend/app/modules/rag/reranker.py` | Giữ ModelOps động, điều chỉnh candidate depth |
| Biến thể truy vấn từ khóa và mở rộng chunks lân cận | `backend/app/modules/rag/retriever.py`, `service.py` | Có nền tảng, chưa đồng nghĩa parent-child hoàn chỉnh |
| Facts, citation/no-answer guard, cache theo snapshot | `backend/app/modules/rag/facts.py`, `citation_guard.py`, `schemas.py`, `service.py` | Giữ; kiểm chứng policy/invalidation |
| OCR theo trang, Docling DOCX, preview/layout thật | `backend/app/modules/knowledge/services/source_extraction.py` | Đã tối ưu #360; đo và tinh chỉnh tiếp |
| DAG routed inputs và chờ các predecessor được kích hoạt | `backend/app/modules/workflows/engine.py`, `nodes/routed_inputs.py` | Giữ tính đúng đã sửa; không viết scheduler thay thế khi chưa cần |
| DAG gọi chung RAG pipeline | `backend/app/modules/workflows/nodes/rag_answer_node.py` | Một HybridRetriever cho API và chatbot DAG |

Chi tiết hiện trạng: [Review BM25 #361](../nhat_ky/2026-10-11_phien_361_danh_gia_bm25_cho_rag_dag.md). Qdrant live ở phiên đó là 1.19.0; cần kiểm tra lại version server/SDK khi triển khai, không dựa vào image `latest`.

## 4. Ma trận lựa chọn

Ưu tiên dưới đây là đề xuất, không phải kết quả benchmark. Chi phí tương đối so với pipeline hiện tại.

| Kỹ thuật | Bài toán chính | Tình trạng | Chi phí thêm | Ưu tiên |
| :--- | :--- | :--- | :--- | :--- |
| BM25 | Từ khóa, số hiệu, mã ngành, tên mục | Chưa có | Chỉ mục sparse và backfill | Cao |
| RRF + candidate-depth tuning | Hợp nhất dense/lexical, giữ đủ ứng viên | Đã có RRF | Tăng retrieval/rerank nếu tăng depth | Cao |
| Parent-child / structure-aware expansion | Không mất điều kiện, ngoại lệ khi cắt đoạn | Có neighbor expansion | Quan hệ cấu trúc và context tokens | Cao |
| Deduplication / MMR | Giảm ngữ cảnh trùng, tăng bao phủ bằng chứng | Cần đánh giá riêng | So sánh ứng viên | Theo triệu chứng |
| Multi-query / query decomposition | Câu hỏi mơ hồ hoặc nhiều ý | Có biến thể lexical đơn giản | Thêm truy vấn, có thể thêm LLM | Theo triệu chứng |
| pg_trgm fuzzy matching | Tên văn bản/ngành gõ sai | Chưa xác nhận cấu hình/index | Extension/index và giới hạn scope | Bổ trợ |
| BGE-M3 sparse / SPLADE | Sparse representation do mô hình học | Chưa xác nhận API server hỗ trợ | Inference và sparse index | Thử sau BM25 |
| ColBERT / late interaction | So khớp chi tiết cấp token | Chưa có đường runtime xác nhận | Multi-vector storage/inference | Thử nghiệm sau |
| HyDE | Câu hỏi mô tả khó tìm | Chưa có | LLM + embedding + latency | Thấp |
| HNSW / quantization tuning | Tốc độ và bộ nhớ khi corpus lớn | Có HNSW; quantization chưa xác nhận | Reindex, đo recall | Khi có bottleneck |
| Cache / single-flight | Giảm xử lý lặp đồng thời | Có semantic cache; single-flight cần khảo sát | Invalidation, khóa phân tán | Khi có tải thật |
| Bounded concurrency / token-budget batching | Nạp nhiều file không nghẽn OCR/embedding | Có worker; cần đo giới hạn thực tế | Điều phối và telemetry | Cao với đa người dùng |

## 5. Hướng áp dụng cụ thể

### 5.1. BM25: nâng nhánh từ khóa

BM25 tính điểm bằng tần suất từ, độ hiếm của từ trong corpus và độ dài đơn vị được lập chỉ mục. Với repo, đơn vị chính nên là **chunk**, không phải toàn PDF. Nó bổ sung dense retrieval, không thay thế embedding hoặc Facts Layer. [Qdrant BM25](https://qdrant.tech/documentation/search/text-search/full-text-search/).

Đề xuất tận dụng sparse BM25 trong Qdrant đang có thay vì thêm search service mới hoặc tải toàn corpus vào RAM mỗi worker. Backfill từ nội dung chunks đã chuẩn hóa; giữ dense vectors hiện có nếu hợp lệ.

Điều kiện triển khai:

- Unicode NFC, tokenizer nhất quán giữa index/query, benchmark tiếng Việt có/không dấu; tránh mặc định English stemming/stopwords.
- Metadata nguồn mới cần title, file name, số hiệu, năm và section. Hiện nguồn ADR-012 có document_id=None và title trong chunk_metadata, trong khi lexical anchor còn nhìn KnowledgeDocument. Phải xử lý điểm này cùng BM25.
- Số hiệu, mã ngành và năm chính xác cần field/filter/boost phù hợp; BM25 không bảo đảm khớp nguyên cụm hoặc đúng văn bản chỉ nhờ score cao.
- Scope IDF phải rõ. Qdrant mặc định tính IDF trên shard; payload filter không tự biến nó thành thống kê chỉ của active snapshot. Tránh staging/history/bản lặp đa model làm lệch thống kê. [Qdrant IDF và cấu hình BM25](https://qdrant.tech/documentation/search/text-search/full-text-search/).
- Sparse index tham gia build/parity/publish/rollback/purge; khi thiếu sparse, không báo đã index đủ.

Kiểm chứng: câu hỏi theo số hiệu, mã ngành, năm, tên ngành, không dấu và trường hợp cùng nội dung ở nhiều năm. So với lexical hiện tại, dense-only và hybrid; không kết luận chỉ từ một ví dụ đúng.

### 5.2. RRF và reranker: tối ưu thành phần đã có

RRF hợp nhất theo thứ hạng, tránh cộng trực tiếp cosine score với BM25 score khác thang đo. Reranker đánh giá lại ứng viên nhưng không thể cứu đoạn chưa được retrieval lấy vào. [Qdrant hybrid search](https://qdrant.tech/documentation/search-tuning/hybrid-search/).

Repo đang lấy khoảng 8–12 ứng viên mỗi nhánh theo intent. Thử 20–40 mỗi nhánh, rồi rerank 5–8 là **dải thử nghiệm**, không phải cấu hình tối ưu cố định. Chốt theo recall, p95 và chi phí server.

Không cho ILIKE/FTS/BM25 ba phiếu ngang nhau chỉ vì có ba tên thuật toán. Các nhánh tương quan có thể nhân đôi ảnh hưởng lexical. Giữ một lexical chính, fallback/shadow có chủ đích. Ưu tiên pháp lý không được đẩy văn bản không liên quan lên trên bằng chứng trực tiếp.

### 5.3. Parent-child: mở rộng theo Điều/Khoản/mục

Tìm child chunk nhỏ để chính xác, sau đó lấy parent section đủ để chứa điều kiện và ngoại lệ. Đây là chiến lược retrieval, không đòi hỏi thêm LLM. [Parent Document Retriever](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever).

Ví dụ: tìm được một khoản về dự tuyển thạc sĩ nhưng điều kiện loại trừ nằm trong khoản liền trước. Mở rộng theo Điều phù hợp hơn lấy hai đoạn sát nhau một cách máy móc.

Đề xuất nâng neighbor expansion hiện có bằng quan hệ heading hierarchy, điều/khoản, table/record và page provenance. Dùng cấu trúc tổng quát, không gõ tay danh sách từ khóa từng lĩnh vực. Parent chỉ thuộc cùng nguồn/revision; giới hạn context tokens và tránh kéo toàn tài liệu vào prompt. Bảng cần giữ header với record, không tách cột mất nghĩa.

Kiểm chứng: trích dẫn đúng đoạn con và trang, trả đủ ngoại lệ, không lấy parent của bản cũ hoặc nguồn khác. Đổi chunk hierarchy có thể cần rebuild chunk set/index; không cần OCR lại nếu canonical Markdown còn hợp lệ.

### 5.4. Chống trùng và MMR: ngữ cảnh đa dạng nhưng vẫn đúng

Trước tiên dùng content hash để bỏ **trùng nguyên văn** trong candidate/context, vẫn giữ provenance cần thiết. Với gần trùng có thể đánh giá shingles/Jaccard hoặc MMR. Không dùng dedup ngữ cảnh để xóa nguồn thật hay hợp nhất các văn bản khác năm.

MMR chọn lần lượt ứng viên dựa trên liên quan với câu hỏi và độ khác biệt với phần đã chọn. Nếu áp dụng sau fusion/rerank, phải có similarity representation hợp lệ cho mọi ứng viên, không nhầm RRF score với cosine similarity. Qdrant có MMR cho nearest-neighbor search, nhưng điều đó không tự tạo MMR cho toàn bộ danh sách fusion của repo. [Qdrant MMR](https://qdrant.tech/course/beginners/module-6/diversity-mmr/).

Chỉ thử khi nhiều kết quả lặp cùng nội dung. Câu hỏi về một quyết định không nên bị ép lấy tài liệu khác để “đa dạng”. Luôn đặt minimum relevance, giữ bằng chứng bắt buộc và so chất lượng trước/sau.

### 5.5. Multi-query và decomposition: xử lý câu hỏi khó

Multi-query tìm cùng ý bằng vài cách diễn đạt; decomposition tách các ý của một câu hỏi nhiều phần. Không phải cùng một thao tác. Repo đã có sparse_variants, nên mở rộng đúng chỗ thay vì tạo bộ truy vấn thứ hai trong DAG. [MultiQueryRetriever](https://reference.langchain.com/python/langchain-classic/retrievers/multi_query/MultiQueryRetriever).

Chỉ kích hoạt khi có nhiều ý hoặc lần tìm đầu thiếu bằng chứng. Giới hạn số biến thể, bỏ trùng và giữ nguyên số hiệu, mã ngành, năm, phủ định cùng điều kiện. Hợp nhất bằng RRF, rồi đối chiếu từng ý có bằng chứng. Câu hỏi mơ hồ nên hỏi lại nếu rewrite buộc phải đoán.

Không chạy các SQL queries đồng thời trên cùng AsyncSession; khi mở rộng concurrency phải dùng session riêng/tuần tự theo ranh giới transaction. LLM rewrite lấy model/provider từ ModelOps, có budget, timeout và audit.

### 5.6. pg_trgm: chỉ bổ trợ tìm tên gần đúng

PostgreSQL pg_trgm hỗ trợ similarity dựa trên trigram và indexes cho chuỗi gần giống. Phù hợp tìm tên ngành/tên tài liệu gõ sai hơn là thay thế toàn bộ RAG. [PostgreSQL pg_trgm](https://www.postgresql.org/docs/17/pgtrgm.html).

Nếu thêm: chỉ dùng trên metadata đã scoped, có threshold/limit và truy vấn indexed; kết quả gợi ý cần phân biệt exact với fuzzy. Mã ngành, số hiệu, số tiền và năm không được sửa gần đúng rồi coi là sự thật. Khi có nhiều lựa chọn, yêu cầu người dùng chọn hoặc giữ ambiguity.

### 5.7. Learned sparse: BGE-M3 sparse hoặc SPLADE

Khác BM25, learned sparse dùng mô hình để tạo trọng số/biểu diễn thưa, có thể mở rộng lexical matching. Đây là nhánh thay thế/đối chứng, không bắt buộc chạy kèm BM25. [SPLADE v2](https://arxiv.org/abs/2109.10086).

BGE-M3 bản mô hình hỗ trợ dense, sparse và multi-vector, nhưng API vLLM đang phục vụ repo chưa được xác nhận xuất đủ ba dạng. Không suy ra từ việc /embeddings trả dense rằng sparse cũng sẵn sàng. Cần kiểm tra server contract, output token IDs/weights, model/tokenizer version và batch performance. [BGE-M3 chính thức](https://github.com/FlagOpen/FlagEmbedding/blob/master/docs/source/bge/bge_m3.rst).

Chỉ thử sau BM25 baseline. Đo riêng tiếng Việt, mã số và OCR text; không mặc định checkpoint SPLADE tiếng Anh phù hợp QNU. Thêm adapter/capability qua ModelOps nếu cần, không hardcode model, không giả sparse từ dense vectors.

### 5.8. ColBERT / late interaction: hướng nâng cao

Biểu diễn nhiều token vectors cho mỗi đoạn và so khớp bằng late interaction/MaxSim, thay vì một dense vector cho toàn đoạn. Qdrant hỗ trợ multivectors. [Qdrant late interaction](https://qdrant.tech/documentation/advanced-tutorials/using-multivector-representations/).

Hợp lý để thử nếu câu hỏi có nhiều chi tiết mà dense + BM25 + reranker vẫn bỏ sót. Ưu tiên rescore candidate set nhỏ trong thí nghiệm, không quét toàn corpus ngay. Cần model phù hợp tiếng Việt và đo dung lượng lưu trữ, inference, QPS/p95; multi-vector không “miễn phí” dù dùng cùng tên BGE-M3.

### 5.9. HyDE: chưa ưu tiên

HyDE sinh văn bản giả định từ câu hỏi rồi embed để tìm tài liệu thật. Nó là công cụ tìm kiếm, không phải bằng chứng để trả lời. [Nghiên cứu HyDE](https://aclanthology.org/2023.acl-long.99/).

Với số liệu và quy chế QNU, văn bản giả định có thể đưa số/mã sai vào truy vấn. Chỉ thử câu hỏi mô tả khi baseline yếu; giữ truy vấn gốc, không ghi văn bản giả định vào Kho tri thức, không trích dẫn nó, không dùng thay facts. Cộng thêm một lượt LLM nên phải có lợi đo được.

## 6. Tối ưu tốc độ và tài nguyên

### 6.1. HNSW và quantization

HNSW đã có, không cần xây lại thuật toán. Đo approximate recall với exact-search đối chứng trên cùng filters/snapshot trước khi chỉnh hnsw_ef, m và ef_construct. Tăng recall thường đổi bằng tài nguyên/latency; metadata payload indexes cũng cần kiểm tra. [Qdrant ANN recall](https://qdrant.tech/documentation/tutorials-search-engineering/ann-recall/).

Quantization chỉ thử khi bộ nhớ/index size là bottleneck thực tế. Giữ original vectors, đánh giá rescoring/oversampling và chất lượng trên corpus QNU; không coi đây là cách sửa OCR hoặc chunking sai. [Qdrant quantization](https://qdrant.tech/documentation/manage-data/quantization/).

### 6.2. Cache đúng phiên bản và single-flight

Cache đã có; cần kiểm chứng fingerprint đủ snapshot/epoch, tenant/workspace, lịch sử hội thoại, model/provider, prompt/guardrails và retrieval policy version. Không reuse câu trả lời khác năm, scope hoặc chính sách chỉ vì embedding câu hỏi gần nhau.

Single-flight là đề xuất gom các yêu cầu **giống hệt trong cùng phạm vi** đang chạy để tránh tính lặp. Khi đa worker cần khóa phân tán có TTL, owner token và recovery, không chỉ dictionary in-memory. Cache/single-flight không che outage, không dùng dữ liệu giả, không thay authorization.

### 6.3. OCR theo trang và batching có giới hạn

Giữ hướng đã làm #360: native text/layout cho PDF số, Paddle cho trang scan hoặc text layer không đạt chất lượng; DOCX giữ Docling và preview dẫn xuất để Studio có geometry thật. Đo tỷ lệ gọi OCR, thời gian mỗi trang và page coverage. PDF hỗn hợp không được bỏ scan vì vài trang đầu có text.

Worker điều phối concurrency riêng cho OCR/embedding/reranker theo năng lực server. Batch embedding theo token budget bên cạnh số chunks, tránh một batch quá dài gây timeout. Retry có backoff/jitter cho lỗi tạm thời; lỗi nội dung/credential không retry vô hạn. Dùng idempotency, cancellation và trạng thái stage thật; đây là kỹ thuật vận hành, không phải thuật toán thay BM25.

## 7. Áp dụng với DAG

- Không thêm một node riêng cho mỗi thuật toán chỉ để làm canvas dài hơn. API RAG và DAG RAG node dùng cùng policy/HybridRetriever.
- Giữ join/routed-input semantics đã sửa #343. Scheduler không được chạy join trước nhánh dài, chờ nhánh không được chọn hoặc lấy nhầm shared output.
- Trước tuning: truyền scope tenant/workspace và provider policy xuyên luồng, phân biệt thiếu bằng chứng với provider outage. Những khoảng hở thấy ở #361 không thể chữa bằng BM25.
- Nếu cần tăng tốc DAG, đo critical path và chỉ thử chạy song song các node thực sự độc lập, có concurrency cap. Không chia sẻ mutable state hoặc AsyncSession giữa tác vụ đồng thời; output aggregation phải deterministic.
- Không tự thay DAG bằng LangGraph/GraphRAG hoặc thêm graph database. Chỉ đánh giá graph retrieval khi corpus có quan hệ thực thể cần multi-hop mà pipeline cơ bản không giải quyết được.

## 8. Lộ trình đề xuất và điều kiện đi tiếp

Không chia thành nhiều phiên bắt buộc. Có thể code theo batch rồi chạy verification cuối batch; với scope, publish, purge, concurrency phải có regression test tái hiện trước theo AGENTS.

| Đợt | Công việc | Chỉ đi tiếp khi |
| :--- | :--- | :--- |
| 0 — Tính đúng và baseline | Scope/error contract, title metadata nguồn mới, corpus và expected evidence | Không leak/staging/ghost citations; biết baseline thật |
| 1 — Hybrid lexical | BM25 additive + RRF/reranker depth, lifecycle/backfill/cache policy | A/B có lợi hoặc chứng minh tình huống cần; không regression scope/publish |
| 2 — Ngữ cảnh đủ và gọn | Parent-child; dedup trước, MMR nếu cần | Ngoại lệ/bảng giữ đủ; tokens/lặp giảm mà relevance không giảm |
| 3 — Truy vấn khó và tải | Multi-query có budget, worker/batching/cache/HNSW theo bottleneck | Chất lượng và p95/concurrency trong budget đã thống nhất |
| 4 — Thử nghiệm nâng cao | Chọn một trong learned sparse/ColBERT/HyDE | Vượt baseline trên câu hỏi mục tiêu, chi phí chấp nhận được |

## 9. Cách đo chất lượng và nghiệm thu

### 9.1. Dataset thật

Đề xuất bắt đầu 50–100 câu hỏi, mở rộng sau; đây là kích thước khởi điểm, không phải đủ để chứng minh mọi miền nghiệp vụ. Mỗi ca lưu expected source/revision/chunk hoặc evidence span/page và yêu cầu no-answer nếu thiếu căn cứ. Không chỉ lưu keywords hay câu trả lời mẫu.

Các nhóm bắt buộc: mã ngành/số hiệu; cùng thông tin khác năm; Điều/Khoản/ngoại lệ; bảng/chỉ tiêu/học phí; paraphrase; không dấu/lỗi gõ; câu hỏi nhiều ý; ngoài phạm vi; PDF số/scan/hỗn hợp/DOCX; nguồn đã xóa hoặc chưa xuất bản.

### 9.2. Chỉ số

- Recall@k: tỷ lệ bằng chứng liên quan được lấy vào candidate set; dùng nhãn relevance rõ ràng.
- MRR và nDCG@k: chất lượng thứ hạng theo nhãn của dataset.
- Evidence coverage: đủ các ý/điều kiện cần thiết, không chỉ đúng một chunk.
- Faithfulness/citation correctness: các khẳng định có nguồn thật đúng revision/trang; kiểm tra cả số liệu và năm.
- Latency p50/p95, QPS, queue wait, failure/retry rate, tokens, provider requests và memory/storage.

So current baseline, dense-only, BM25-only và hybrid; thêm một kỹ thuật mỗi thí nghiệm để biết cải thiện đến từ đâu. Tắt cache hoặc version cache theo experiment, giữ cùng corpus/snapshot và model policy. Không dùng test heuristic với answer/context cấp sẵn để tuyên bố retrieval thật đã đạt.

### 9.3. Acceptance

- Chốt trước ngân sách latency và ngưỡng regression chấp nhận được; không chọn sau khi đã xem kết quả. Có thể dùng mục tiêu chất lượng dự án hiện có nhưng không bảo đảm đạt chỉ nhờ thêm thuật toán.
- Không chấp nhận bất kỳ leak scope, staging result, nguồn đã xóa còn trả lời hay provenance sai trong suite nghiệm thu.
- Kiểm tra publish/rollback/edit/delete/đổi model, Qdrant/provider down, worker restart/cancel và nạp nhiều file đồng thời.
- E2E phải đi qua FE → BE → worker/provider → DB/Qdrant và chatbot DAG. Test unit chỉ là một lớp bằng chứng.
- Chạy regression trọng tâm và final gates theo AGENTS khi triển khai runtime; ghi rõ lỗi nền ngoài phạm vi. Tài liệu này chưa chạy benchmark mới và không chứng nhận các thuật toán đề xuất đã hoạt động.

## 10. Quy tắc bàn giao cho phiên triển khai

Chỉ triển khai đợt được người dùng chọn. Đọc AGENTS, memory và skill liên quan; khảo sát code hiện tại trước sửa. Không reset DB, xóa corpus, đổi credential, restart service hay đụng qnu-sso ngoài quyền đã được giao. Không hardcode model hoặc từ điển vá tiếng Việt. Cấu hình retrieval phải có version và đường rollback; shadow thử nghiệm không được làm thay đổi câu trả lời production trước nghiệm thu.

Giữ scope thay đổi nhỏ, báo cáo kết quả trước/sau và lý do giữ/bỏ mỗi kỹ thuật. Không gọi tên mọi bước trong pipeline là “thuật toán mới”: RRF/reranker/HNSW đã có, facts/metadata/lifecycle là nền tảng tính đúng cần giữ.

## 11. Tài liệu liên quan

- [Kế hoạch 12 — ranh giới Kho tài liệu/Kho tri thức](./12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md).
- [Review RAG/DAG #342](../nhat_ky/2026-10-11_phien_342_review_rag_dag.md).
- [Sửa join và routed inputs #343](../nhat_ky/2026-10-11_phien_343_fix_dag_join_va_routed_inputs.md).
- [Layout/OCR/DOCX preview #360](../nhat_ky/2026-10-11_phien_360_layout_native_ocr_theo_trang_va_docx_preview.md).
- [Đánh giá BM25 #361](../nhat_ky/2026-10-11_phien_361_danh_gia_bm25_cho_rag_dag.md).

**Khuyến nghị cuối:** làm đúng scope/provenance và có baseline, rồi ưu tiên BM25 + tuning hiện có + parent-child. Dedup/MMR và concurrency là tối ưu theo triệu chứng; các mô hình nâng cao chỉ thêm khi chứng minh được lợi ích.
