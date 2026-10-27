# Hybrid, rerank và so sánh retrieval — Backend v1

Luồng mở rộng từ [dense search](dense-indexing.md), giữ cùng publication,
snapshot, source revision, workspace authorization và ModelOps hiện có.

## Tìm kiếm và hỏi đáp

`POST /workspaces/{workspace_id}/collections/{collection_id}/search` nhận:

```json
{"query":"...","mode":"hybrid_rerank","top_k":5,"candidate_k":30,"rrf_k":60}
```

`mode` có `dense` (mặc định), `hybrid`, `hybrid_rerank`. Hybrid lấy hai danh sách:
dense từ Qdrant và **PostgreSQL simple FTS**, gộp bằng reciprocal rank fusion
(RRF), khử trùng chunk rồi tùy chọn rerank. FTS sử dụng các từ Unicode của query,
không có từ điển nội dung viết tay. Đây chưa phải BM25 hoặc learned sparse.
Chưa có chỉ mục GIN riêng hoặc số đo tải lớn.

Scope workspace/collection/generation/publication/document áp trước TopK ở cả
hai nhánh. SQL/manifest kiểm lại text, structure và citation. Sau quota commit,
quyền/nguồn/model được kiểm trước khi gửi các ứng viên đi rerank và kiểm lại
trước trả kết quả. Thu hồi nguồn trong lúc HTTP không được trả nội dung cũ.

Provider rerank phải có capability/grant/default hoặc preferred provider hợp lệ,
credential mã hóa và capacity cấu hình trong ModelOps. Adapter gửi một request
`/v1/rerank`, không retry/redirect/fallback ngầm; kiểm đủ index duy nhất trong
phạm vi và score hữu hạn. Provider lỗi trả lỗi thật, không rơi về kết quả dense
mà không thông báo. Usage chưa biết giữ null. Điểm FTS, dense, RRF và reranker
không cùng thang đo, không dùng chung một ngưỡng relevance.

`POST /answers` nhận `retrieval_mode`, `candidate_k`, `rerank_provider_id` cùng
các trường cũ. Citation/evidence vẫn do backend ghim, không do model cấp quyền.
Assistant/conversation hiện giữ mặc định dense; batch này chưa thêm tùy chọn
retrieval vào cấu hình assistant.

## So sánh cùng snapshot

`POST /workspaces/{workspace_id}/collections/{collection_id}/retrieval-evaluations`
cho editor/admin, có `private, no-store`. Ví dụ cấu trúc:

```json
{
  "index_run_id":"ID thực",
  "manifest_sha256":"SHA256 thực của manifest",
  "label_version":"benchmark/v1",
  "label_status":"draft_needs_human_check",
  "label_author":"người hoặc quy trình tạo nhãn",
  "top_k":5,
  "candidate_k":30,
  "include_rerank":true,
  "queries":[{"id":"q1","query":"...","gold_chunk_ids":["ID có căn cứ"],"group":"..."}]
}
```

Tối đa 20 query/lượt, 50 ứng viên, `candidate_k >= top_k`. Gold IDs phải thuộc
snapshot và phạm vi document đã chọn. Nhãn `human_reviewed` là khai báo metadata
của caller; API không tự chứng nhận nhãn hay phê duyệt publication.

Mỗi query chỉ retrieval một lần: lưu thứ hạng dense, danh sách RRF và rerank
**chính danh sách RRF đó**. B/C có cùng candidate IDs/hash; corpus, embedding,
scope và manifest cố định. Trace tách thời gian retrieval chung với chi phí
rerank tăng thêm; không suy latency dense độc lập từ phép đo chung này.

Kết quả JSON có Hit@K, annotated Recall@K, MRR@K và annotated Precision@K.
Gold trống giữ metric null. Mỗi query/strategy có trạng thái riêng; lỗi được giữ
trong mẫu số expected/completed/errors, không biến thành no-data hoặc bỏ khỏi
báo cáo. Trung bình được ghi rõ `completed_only_metrics`; acceptance luôn
`not_determined`. Answer correctness/groundedness chưa được chấm.

Caller lưu JSON trả về thành artifact thí nghiệm; chưa có lịch đánh giá, bảng
lịch sử hoặc quality gate tự động. Cần nhãn độc lập đã duyệt, câu paraphrase,
câu thiếu dữ liệu/sai năm và tập holdout trước khi kết luận retrieval tốt hơn.

## Nguồn học hỏi

[Haystack DocumentJoiner](https://docs.haystack.deepset.ai/docs/documentjoiner)
mô tả gộp kết quả retriever bằng RRF. QNU áp dụng thuật toán trong pipeline sẵn
có; không thêm dependency Haystack. Giao thức rerank tham chiếu
[vLLM scoring](https://docs.vllm.ai/en/stable/models/pooling_models/scoring/).
Việc áp dụng các kỹ thuật này chưa chứng minh tăng chất lượng trên corpus QNU.
