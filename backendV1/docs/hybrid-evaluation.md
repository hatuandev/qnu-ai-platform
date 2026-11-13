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

Biểu thức `to_tsvector('simple'::regconfig, text)` có GIN expression index
`ix_kb_index_chunks_fts` (migration `0025_index_fts_gin`). Câu SQL phải giữ
regconfig dạng literal `'simple'::regconfig`: tham số hóa regconfig làm planner
không khớp expression index và quay lại sequential scan. Qdrant bảo đảm keyword
payload index cho `run_id`, `workspace_id`, `collection_id`, `version_id`,
`chunk_id` khi tạo collection mới hoặc mở collection hiện có; thao tác idempotent,
phản hồi không xác nhận `completed` là lỗi `vector_unavailable`, không bỏ qua.
Index chỉ tăng tốc lọc/tìm; không thay đổi scope, provenance hay thứ hạng.

Scope workspace/collection/generation/publication/document áp trước TopK ở cả
hai nhánh. SQL/manifest kiểm lại text, structure và citation. Sau quota commit,
quyền/nguồn/model được kiểm trước khi gửi các ứng viên đi rerank và kiểm lại
trước trả kết quả. Thu hồi nguồn trong lúc HTTP không được trả nội dung cũ.

Provider rerank phải có capability/default hoặc preferred provider hợp lệ,
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

## Số đo nháp 2026-11-11

Snapshot `idx_af04993c0a56` (manifest `985565ecf85b4e21b109f7e85a7c40890e9266cc173809901d47698e5b6cac68`),
một tài liệu scan thật đã duyệt, 448 chunk; 16 câu hỏi nháp (14 đơn trị, 2 nhiều
gold) lấy từ chính văn bản đã xuất bản; `label_status=draft_needs_human_check`,
`label_author=assistant-draft-from-published-text` — chưa được người duyệt.

| strategy (candidate_k=30) | Hit@10 | Recall@10 | MRR@10 | Precision@10 |
| :--- | ---: | ---: | ---: | ---: |
| dense | 1,0000 | 1,0000 | 0,8490 | 0,1125 |
| hybrid | 1,0000 | 1,0000 | 0,5906 | 0,1125 |
| hybrid_rerank | 1,0000 | 1,0000 | 0,9688 | 0,1125 |

Cả 16/16 câu hoàn tất, 0 lỗi; eval `eval_24efb39b8ec947cfb93b2afa357553c9`,
thời gian tường 59,125 s. Chạy lại với `candidate_k=20`
(`eval_085bf7df5441436195c668f9293c3e64`) giữ nguyên dense/rerank, chỉ đổi MRR
hybrid 0,5906 → 0,5854; chưa đủ căn cứ đổi mặc định 30.

Thời gian trung bình mỗi câu ở `candidate_k=30`: embedding 233,5 ms, dense 62,6 ms,
FTS 93,7 ms; retrieval dùng chung (một lần embed + dense + FTS + fusion) 1.334,1 ms;
rerank cộng thêm 771,4 ms (trung vị 766,0; cao nhất 875,0) và chỉ chạy ở
`hybrid_rerank`. Không suy latency dense độc lập từ phép đo chung này.

Đọc kết quả: Hit/Recall bão hòa ở top 10 trên corpus nhỏ một tài liệu nên không
phân biệt được mode. MRR hybrid thấp hơn dense vì RRF trọng số đều đẩy chunk khớp
từ khóa lên trước; rerank phục hồi và vượt dense nhưng thêm khoảng 0,77 s/câu.
Đây là quan sát trên văn bản OCR còn lỗi chính tả, không phải kết luận chung.
Giới hạn: một tài liệu/448 chunk, 16 câu, nhãn do trợ lý soạn từ văn bản đã xuất
bản (không độc lập), chưa chấm answer correctness/groundedness; acceptance vẫn
`not_determined`. Không đổi mặc định retrieval/assistant từ số đo này.

## Nguồn học hỏi

[Haystack DocumentJoiner](https://docs.haystack.deepset.ai/docs/documentjoiner)
mô tả gộp kết quả retriever bằng RRF. QNU áp dụng thuật toán trong pipeline sẵn
có; không thêm dependency Haystack. Giao thức rerank tham chiếu
[vLLM scoring](https://docs.vllm.ai/en/stable/models/pooling_models/scoring/).
Việc áp dụng các kỹ thuật này chưa chứng minh tăng chất lượng trên corpus QNU.
