# 09 — Cấu hình Top K và chẩn đoán RAG

## Phạm vi

Phiên 489 bổ sung ngân sách truy xuất dùng chung cho các trợ lý, không thêm
SQLite, framework hay model mới. Không thay OCR, nguồn, vector, trạng thái xuất
bản, quyền đọc, phân biệt năm, engine quy đổi hoặc quy trình duyệt.

Cấu hình được lưu qua API cập nhật trợ lý hiện có, trong
`assistants.config.knowledge_policy.retrieval_policy`; không cần migration.
Đây không phải cấu hình context window/token của model.

## Sử dụng

Trong **Trợ lý → Cấu hình → Tìm kiếm & ngữ cảnh**:

1. **Hiện tại (đối chứng)** giữ hành vi trước phiên 489. Đây là mặc định khi DB
   chưa có trường mới. Nhánh fact/hybrid dùng 8/12 ứng viên mỗi nhánh theo intent,
   kết quả rerank theo `reranker_policy.top_k`; evidence giữ chính sách riêng.
2. **Tùy chỉnh Top K** bật ngân sách riêng cho các bước dưới đây.
3. **Dùng mốc 30/30/30/5** chỉ điền form, chưa tự lưu hoặc chứng nhận tối ưu.
4. Bấm **Lưu thay đổi** để lưu qua API có quyền hiện hữu. Chọn lại **Hiện tại**
   và lưu để quay về đối chứng. Không cần nạp lại vector khi chỉ đổi K.

| Trường | Phạm vi | Ý nghĩa trong chế độ tùy chỉnh |
|---|---|---|
| dense_top_k | 1–100 hoặc null | Ứng viên ngữ nghĩa; null dùng retrieval_limit |
| lexical_top_k | 1–100 hoặc null | Ứng viên lexical; null dùng retrieval_limit |
| fusion_top_k | 1–200 | Giới hạn ứng viên hợp nhất trước rerank |
| context_top_k | 1–20, không quá fusion_top_k | Kết quả chính sau rerank hoặc RRF nếu tắt rerank |
| max_context_chars | 1000–64000 | Ngân sách ký tự bằng chứng, không phải toàn prompt/model context window |

`retrieval_limit` cũ là fallback cho hai trường null trong chế độ tùy chỉnh,
không âm thầm thay hành vi legacy. `reranker_policy` tiếp tục điều khiển provider,
model, enabled và threshold; Top K cũ chỉ điều khiển legacy. UI khóa ô Top K cũ
khi dùng chế độ tùy chỉnh để tránh hai nguồn cấu hình cạnh tranh.

## Các nhánh khác nhau

- Fact/hybrid: ngân sách riêng truyền vào dense và PostgreSQL FTS; weighted RRF
  giới hạn fusion candidates; reranker giữ context_top_k. Hàng nguồn, header,
  footnote và neighbor có thể bổ sung. Nhóm hàng/ngữ cảnh liên kết được giữ nguyên
  hoặc bỏ nguyên nhóm khi quá ngân sách, không cắt ngang ô/chứng cứ. Facts cũng
  được tính vào ngân sách ký tự; quá ngân sách trả trạng thái thiếu ngữ cảnh rõ ràng.
- Evidence: anchor prefetch giữ đến fusion_top_k thay vì cắt sớm còn final K;
  BM25/canonical fusion và pack_context dùng ngân sách tùy chỉnh. Header/dependency
  vẫn theo cơ chế atomic hiện hữu; nhóm không vừa sẽ bị loại có lý do. Corrective
  và historical retrieval giữ cùng ngân sách.
- Liệt kê đầy đủ và tính điểm/facts có nhánh riêng; không dùng Top K để giả định
  đã liệt kê toàn bộ hoặc để cắt kết quả tính xác định. Dấu vết ghi nhánh thực chạy.
- Thay đổi cấu hình nằm trong policy fingerprint nên không tái dùng cache đáp án
  của cấu hình khác. Telemetry nội bộ không tham gia fingerprint và client không
  cung cấp được private trace.

## Kiểm tra tìm kiếm

### Bổ sung491: đối soát đoạn văn sau structured miss

Fact/table chưa có claim/cell được xác minh có thể kiểm tra thêm canonical prose
trong cùng snapshot, với BM25/reranker và source-span/semantic audit hiện hữu.
Đây là bước phục hồi có giới hạn (tối đa3body,6000ký tự,1600output cho subcall),
không bật evidence policy toàn trợ lý hoặc đổi max_tokens trong DB. Header/dependency
vẫn nguyên nhóm; không dùng năm tệp thay năm dữ kiện, không ghi đè conflict/partial.
Trace nằm ở `prose_fallback`; thành công có reason `VERIFIED_PROSE_FALLBACK`.
Numeric failure chưa phục hồi có reason `NUMERIC_GROUNDING_FAILED`, không nói
kho không có dữ liệu. Gate số đầy đủ không thay kiểm chứng loại chỉ số/năm.

Các phép đo10câu của491 vẫn **FAIL quality acceptance**; không coi bước này là
giải quyết toàn bộ từ chối sai hoặc proof rằng TopK đã tối ưu.

### Công cụ search-only

Trong **Thử nghiệm**, mở **Kiểm tra tìm kiếm**. API `/rag/search` nhận
`assistant_code` và kiểm tra trợ lý đang hoạt động, đúng collection trước khi đọc
chính sách đã lưu. Đây là kiểm tra hybrid chunk retrieval, không chạy generation,
không giả vờ đại diện toàn bộ các nhánh facts/liệt kê/semantic verification.

API search còn giữ `top_k`/`rerank_top_k` cũ cho caller độc lập và có thể nhận
`retrieval_policy` có kiểm tra phạm vi. Nếu truyền assistant_code, cấu hình DB được
ưu tiên hơn policy request. Search legacy không có bộ định tuyến intent của chat.
Chat trợ lý dùng runtime profile DB. `/rag/ask` độc lập vẫn tuân theo cơ chế resolve
runtime/evidence hiện hữu; không được coi một request độc lập là một assistant
profile đã xác nhận chỉ vì client truyền JSON.

`retrieval_diagnostics` đi qua JSON và SSE done, hiển thị trong playground:
profile, nhánh, K thực dùng, dense/lexical/fused/rerank/returned counts, số nguồn,
thời gian, dấu hiệu degrade và context packing. Score trả từ search là RRF,
không gọi là xác suất đúng; rerank có điểm quan sát hay không được ghi riêng.
Không có kết quả sau rerank không chứng minh kho không có tài liệu.

## Nghiên cứu và rollout

30/30/30/5 là mốc thử của source tham khảo, không phải kết luận tối ưu QNU từ
arXiv:2407.01219v1. Bài báo thử normalized-score fusion alpha*sparse+dense;
đợt này giữ weighted RRF, chưa triển khai công thức đó, HyDE hay repacking mới.

Runner opt-in `backend/scripts/probe_retrieval_489.py` đọc bộ câu hỏi Markdown,
pin snapshot, so K tại retriever và chặn HTTP ngoài server AI nội bộ/loopback.
Không gọi LLM tạo đáp án, không ghi nguồn/config/vector; transaction dữ liệu đọc
chỉ đọc. ModelOps có thể cập nhật thống kê/lease vận hành như request bình thường.
Kết quả lưu trong storage, không đưa corpus/log runtime vào Git.

Đo hiện tại không có gold IDs đã duyệt; không suy Recall/accuracy từ số hits.
Chạy tuần tự có ảnh hưởng cache/warmup, chưa là kết luận hiệu năng. Đợt tiếp theo:
review 20 câu/căn cứ đúng năm, thử fusion/repacking riêng từng biến, sau đó chạy
82 câu. Chỉ bật cấu hình thắng khi có bằng chứng chất lượng và không hồi quy.

## Kiểm chứng câu trả lời và recovery (phiên492)

Fact truy hồi chỉ là candidate, không tự có độ ưu tiên cao hơn văn xuôi. Nhánh
fact/hybrid kiểm số rồi audit nội dung hiển thị với từng span/quote cùng snapshot;
các con số có mặt trong kho không đủ chứng minh đúng metric, đơn vị, năm hay điều kiện.
Không cache câu bị bác; lỗi provider/DB/schema không được đổi thành “không có dữ liệu”.

Recovery prose đọc cùng publication, lập topic/facet từ câu hỏi gốc; với list/comparison
phải đối soát danh sách/từng năm, không chỉ một mục. Closure tham chiếu là mở rộng
candidate, không quyết định thay thế văn bản. Budget riêng của recovery không phải
ConfigurableTopK hoặc max_tokens đã lưu của trợ lý. Không cần upload lại để dùng logic này.

Bảng thiếu scope vẫn bị chặn. Nếu hai reader đồng thuận về các ô được audit nhưng
selector đọc thừa, có thể trả phần đã chứng minh với nhãn partial và cột chưa chốt;
không tự công nhận đã trả đủ. Liệt kê phân biệt số bản ghi, cách ghi mã+tên và ngành
duy nhất; mục chưa có mã/tên chưa rõ cần đối chiếu, không tự sửa OCR hoặc bỏ khác biệt năm.
