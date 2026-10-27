# RAG backendV1: hiện trạng và bổ sung đề xuất — Context670

Ngày 2026-10-27. Phạm vi: phân tích mã hiện tại và tài liệu chính thức; chưa triển
khai, đổi cấu hình, chạy model, reindex hoặc sửa FE đang được phát triển đồng thời.
Các ưu tiên dưới đây là đề xuất kỹ thuật cho QNU, chưa phải cải thiện đã đo được.

## Luồng hiện tại

```text
Actor/workspace/collection/publication hợp lệ
→ câu hỏi độc lập hoặc viết lại follow-up từ các câu hỏi người dùng trước đó
→ dense Qdrant [hoặc dense + PostgreSQL simple FTS → RRF → rerank qua API riêng]
→ các chunk kèm cấu trúc và nguồn ghim revision/hash
→ ModelOps sinh JSON statements + evidence IDs
→ kiểm cấu trúc/ID và kiểm lại quyền, nguồn, generation, cấu hình
→ câu trả lời gắn trích dẫn hoặc insufficient_evidence
```

- `knowledge/index/search.py`: scope collection/document/version/publication trước
  TopK, kiểm SQL/manifest và nguồn hiện hành; có dense/hybrid/hybrid_rerank.
- `knowledge/index/hybrid.py`: PostgreSQL **simple FTS**, RRF và rerank. Đây chưa
  phải BM25 hoặc learned sparse BGE-M3. Chưa có chỉ mục GIN riêng cho FTS.
- `knowledge/index/chunking.py`: đoạn giữ title/heading; bảng giữ header, rowspan,
  nhóm hàng và ghi chú. Đã có table-aware chunking cơ bản, không cần làm lại từ đầu.
- `conversations/rewriting.py`: follow-up viết thành câu độc lập; câu trả lời cũ
  không được dùng làm evidence.
- `rag/answer/service.py` và `drafting.py`: câu trả lời bắt buộc statements/citations,
  kiểm nguồn trước/sau HTTP và tách lỗi hạ tầng khỏi thiếu căn cứ.
- `evaluation/service.py`: so dense/hybrid/hybrid_rerank cùng snapshot/candidates;
  có retrieval metrics. `answer_evaluation` hiện là `NOT RUN`.

Điểm cần nối: `AssistantConfig` mới có top_k/history/model/output budget, chưa có
retrieval_mode/candidate_k/rerank provider. `conversations/execution.py` tạo
AnswerRequest không truyền các trường đó và không truyền reranker. Vì vậy chat
trợ lý hiện dùng dense mặc định, dù API search/answers riêng đã hỗ trợ hybrid.

## Ưu tiên thực hiện

| Thứ tự | Hạng mục/pattern | Chỗ đưa vào | Tác dụng kỳ vọng và giới hạn |
| --- | --- | --- | --- |
| 1 | Metadata-aware retrieval | Khâu biên soạn/duyệt metadata → index → filter query trước TopK | Giữ đúng năm dữ liệu, năm ban hành, hiệu lực, ngành/đợt. Hiện API chưa có scope nghiệp vụ này; yêu cầu trong prompt chưa thay được bộ lọc |
| 2 | Parent-child / sentence-window context | Sau retrieval/rerank, trước đóng gói evidence | Tìm theo đoạn nhỏ rồi cấp thêm phần liên quan của cùng section/bản xuất bản. Giảm nguy cơ đọc thiếu điều kiện/ngoại lệ; cần giới hạn budget và ghim citation |
| 3 | Answer groundedness verification | Sau generation, trước trả kết quả; ban đầu có thể chạy chế độ chỉ ghi nhận | Đối chiếu từng mệnh đề với đoạn được dẫn. Compiler review kiểm bản biên soạn, còn bước này kiểm câu trả lời mới sinh |
| 4 | Query decomposition | Sau resolve intent/scope, trước retrieval | Với câu có nhiều ý hoặc so sánh, tìm chứng cứ riêng cho từng ý rồi tổng hợp; tăng số request nên chỉ dùng khi cần |
| 5 | Structured/table retrieval + tính toán xác định | Router câu hỏi → bảng/facts đã duyệt → truy vấn/công thức giới hạn | Dành cho đếm, liệt kê toàn bộ, so sánh số liệu và phép tính. RAG TopK không bảo đảm đầy đủ tập hợp |

Song song thứ tự1–3, thêm cấu hình retrieval vào assistant và snapshot hội thoại,
để lựa chọn chiến lược đã có mà không đổi ngầm hội thoại đang chạy. Giữ dense làm
baseline, chỉ chọn default khác sau phép so sánh cùng dữ liệu. Đây là hoàn thiện
đường nối hiện có, không cần thay framework.

### Metadata: ràng buộc cần giữ

Metadata phải có nguồn chứng minh và trạng thái xác minh. Có thể nhờ LLM đề xuất
nhưng không tự tin mọi nhãn model sinh. Phân biệt năm từng hàng/cột với năm ký
văn bản và khoảng hiệu lực; trường chưa biết giữ unknown. Câu hỏi có năm rõ phải
lọc cả nhánh dense/FTS trước TopK; ít kết quả không được bỏ năm để tìm rộng hơn.
Router/model chỉ đề xuất scope, backend áp quyền và kiểm giá trị được phép.

### Context: mở rộng có ranh giới

Hiện heading nằm trong text, paragraph chunk có `structure=None`, chưa có liên kết
section/parent để mở rộng xác định. `ordinal` hiện thuộc generation, nên chỉ lấy
chunk kề nhau theo ordinal có thể nhảy sang tài liệu khác.

Đề xuất thêm quan hệ section/paragraph/span vào dữ liệu dẫn xuất có hash, giữ
input/version/publication giống hit, dedup rồi chọn trong token budget. Nội dung
mở rộng phải là phần đã được phép phục vụ của cùng bản xuất bản. OCR nguyên liệu
được dùng đối chiếu provenance; không tự thêm mọi nội dung OCR chưa duyệt vào
câu trả lời qua một nhánh fallback. Nếu đổi cấu trúc index thì tạo generation mới
theo quy trình đã có, không sửa manifest/generation hiện hành tại chỗ.

[SentenceWindowRetriever](https://docs.haystack.deepset.ai/docs/sentencewindowretriever)
của Haystack lấy phần lân cận sau retriever;
[AutoMergingRetriever](https://docs.haystack.deepset.ai/docs/automergingretriever)
minh họa lấy parent khi nhiều phần con liên quan. QNU có thể học cách tổ chức này
trong các module đang có; hiệu quả trên QNU cần thử riêng.

### Câu trả lời: ID đúng chưa đủ chứng minh ý đúng

Probe trực tiếp `parse_answer`, chỉ trong bộ nhớ, dùng nguồn tổng hợp ghi **100**
và câu trả lời ghi **900** với ID `E1` hợp lệ: parser vẫn trả `answered`.
Điều này chứng minh ranh giới kiểm tra hiện tại, không chứng minh model thật đã
sinh sai hoặc một request end-to-end thực tế đã trả câu đó.

Bổ sung kiểm chứng statement ↔ đoạn được dẫn, số liệu/đơn vị/năm và mâu thuẫn;
giữ trạng thái supported/unsupported/uncertain rõ. Judge có thể sai, cần mẫu được
người duyệt trước khi dùng để chặn câu trả lời. Lỗi judge/provider vẫn là lỗi,
không biến thành "không có dữ liệu". Giới hạn lần sửa/tìm bổ sung và ghi usage.

[FaithfulnessEvaluator](https://docs.haystack.deepset.ai/docs/faithfulnessevaluator)
là ví dụ kiểm từng mệnh đề với context. Đây là nguồn tham khảo cách đánh giá,
không phải chứng nhận tính đúng của mọi câu trả lời QNU.

### Tách câu hỏi và truy vấn số liệu

Ví dụ tổng hợp: "Điều kiện xét tuyển và mức học phí của chương trình X?" cần
theo dõi đủ hai nhóm chứng cứ. Có thể giới hạn 2–4 câu con theo policy, giữ câu
gốc và scope, ghim cùng snapshot, hợp nhất/dedup và giữ coverage từng câu con.
Các câu trả lời trung gian do model tạo không tự trở thành evidence.

Haystack mô tả cách này trong
[Query Decomposition](https://haystack.deepset.ai/blog/query-decomposition);
[LangChain Query Transformations](https://www.langchain.com/blog/query-transformations)
mô tả nhiều cách biến đổi query. Chọn decomposition cho câu nhiều ý khác với
tạo nhiều cách diễn đạt cho cùng một ý; không cần bật cả hai trên mọi request.

Với đếm/tính/liệt kê toàn bộ, trước hết cần facts/bảng chuẩn hóa đã duyệt và dẫn
được tới từng ô. Sau đó dùng truy vấn chỉ đọc, tham số hóa/allowlist và công thức
đã chốt; không giao quyền SQL tùy ý cho model.
[Vanna](https://github.com/vanna-ai/vanna) là tham khảo cho hướng hỏi dữ liệu SQL,
nhưng repo hiện được GitHub đánh dấu archived/read-only. Không đề xuất cài nó
vào runtime QNU trong phiên này.

## Cách chọn pattern bằng bằng chứng

Đợt thử cũ [Context658](../context658/REVIEW.md) có ba câu literal lookup với nhãn
draft, chưa được người duyệt/holdout. Annotated Recall@3: dense1,000;
hybrid/hybrid_rerank0,833. Mẫu này chưa cho thấy cải thiện; cũng không đủ để kết
luận dense luôn tốt hơn. Không bật rerank mặc định chỉ vì đã có model.

Nên có một tập câu hỏi thực đã duyệt, tách nhóm lookup, bảng, ngoại lệ, multi-hop,
follow-up, thiếu dữ liệu và sai năm. Giữ snapshot/index/model/scope nhất quán;
so baseline với **mỗi thay đổi riêng**, đo retrieval và answer support/correctness,
đúng năm/đơn vị, abstention, latency/usage. Bộ evaluator hiện tại tái dùng được
cho retrieval; bổ sung answer evaluation và lưu kết quả để so các phiên bản.

## Phần để sau

GraphRAG/RAPTOR phù hợp khi nhu cầu thực đòi hỏi liên kết thực thể hoặc tổng hợp
trên quy mô nhiều tài liệu. HyDE/multi-query chỉ nên thử khi đã thấy vấn đề cách
diễn đạt/recall. Agentic/corrective loops cần thêm giới hạn số bước, nguồn và chi
phí. Hiện chưa có benchmark QNU chứng minh các phần đó đáng ưu tiên hơn scope,
context và answer verification. Semantic cache cũng cần khóa theo quyền,
publication/model/config và kiểm lại nguồn khi hit.

Tối ưu FTS bằng GIN/tối ưu đọc manifest là việc đo tải riêng sau khi có quy mô
corpus/latency cụ thể; không đổi parser/embedding hoặc reindex chỉ để áp pattern.

## Kiểm chứng và phạm vi

- Đọc mã search/hybrid/chunking/answer/assistant/conversation/evaluation hiện tại.
- Chạy một probe Python cục bộ (exit0): xác nhận parser nhận ID đúng dù số mâu
  thuẫn; assistant chưa có trường retrieval; SearchRequest từ chối `data_year`;
  paragraph giữ heading nhưng chưa có cấu trúc parent.
- Đọc tài liệu chính thức Haystack/LangChain/Vanna. Trang notebook GitHub chỉ trả
  vỏ trang; thử raw timeout, không coi notebook đó đã đọc. Dùng bài chính thức
  tương ứng làm nguồn pattern.
- Không chạy Pytest/full suite, DB, API, inference hay benchmark mới vì không đổi
  hành vi ứng dụng. Số đo Context658 là bằng chứng lịch sử có giới hạn nêu trên.
- Chưa sửa BE/FE, cấu hình ModelOps, migration, nguồn/chỉ mục hoặc runtime.
