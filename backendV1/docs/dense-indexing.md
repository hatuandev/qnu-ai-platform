# Chỉ mục và tìm kiếm dense — Backend v1

[RAG policy](rag-policies.md) bổ sung metadata filter trước TopK và chunker v2 có
parent/position phục vụ context. Generation cũ tiếp tục đọc được; cần generation
mới để nhận metadata/quan hệ mới, không backfill hoặc chuyển active tự động.

Mở rộng Context656: [hybrid/evaluation](hybrid-evaluation.md) thêm FTS/RRF/rerank
vào cùng search; [operations](operations.md) thêm theo dõi/phục hồi có preview.
Phần kiểm chứng Context647 bên dưới là ghi nhận lịch sử của riêng batch647.

Context647 nối tiếp [publication](compiled-publication.md): chỉ bản đang xuất bản,
còn đúng nguồn/revision/hash và có receipt hợp lệ mới được đưa vào chỉ mục.
Không cần cài Haystack; sử dụng các ranh giới và adapter sẵn có của QNU.

## Cấu hình và quyền

- Platform admin đăng ký provider OpenAI-compatible với capability `embedding`,
  credential mã hóa qua ModelOps, rồi cấp provider cho workspace. Admin workspace
  chọn default embedding trong danh sách được cấp; quota tháng phải được cấu hình.
- Provider có `embedding_dimension` và `token_limits.max_input_tokens` hoặc
  `context_window_tokens`. Hai cấu hình gắn với endpoint/model; đổi danh tính làm
  cấu hình cũ `stale`. Không lấy số chiều từ biến cấu hình vector cũ.
- Thử trực tiếp ngày 2026-10-26: server `http://100.105.13.53:8000/v1`, model
  `bge-m3`, vector **1024 chiều**; `/tokenize` báo `max_model_len=8192`.
  Đây là quan sát của server này tại thời điểm thử, không phải mặc định mọi provider.
  Khóa được nhập vào DB thử qua ModelOps, không có trong source hay `.env`.
- Adapter dùng Bearer, `POST /v1/embeddings` với `encoding_format=float`, không
  redirect hoặc retry ngầm. Kiểm đủ vector/index, đúng model/dimension, số hữu hạn
  và vector khác 0. Usage chưa biết giữ NULL.
- Workspace v1 là biên giới quyền: reader đọc/tìm; editor/admin tạo index. Actor,
  membership và collection được kiểm ở server; body không nhận URL hoặc vector filter.

## Luồng xử lý

1. `POST indexing-runs` ghim toàn bộ publication hiện hành của collection, gồm
   document/version/decision, nguồn, bundle và cấu hình model. Lưu run/input/chunk
   cùng audit trong transaction trước khi gửi hàng đợi.
2. Đoạn văn giữ heading, citation và ranh giới từ. Bảng lấy từ snapshot OCR gốc,
   giữ ô/header/span/row index, số 0, ô rỗng và dấu gạch; header lặp lại khi chia
   nhóm hàng, footnote/caption cùng trang vẫn có tham chiếu. Không suy năm từ tên file.
   Nhóm rowspan không thể chia trong budget thì trả lỗi rõ, không cắt âm thầm.
3. Worker ARQ claim bằng lease/token; kiểm lại quyền người yêu cầu, publication,
   provider/grant/capacity và quota trước mỗi batch. Ghi dấu đang gọi trước HTTP;
   lưu raw response có hash, vector staging và usage receipt khi hoàn tất.
4. Upsert vào collection Qdrant riêng của generation, tên `qnu_v1_idx_<uuid>`;
   deterministic point ID và `wait=true`, yêu cầu xác nhận `completed`. Namespace
   của backend cũ không được adapter này ghi. Payload vector chỉ có ID/hash/scope.
5. Kiểm lại toàn snapshot và cấu hình, lưu manifest có hash của text/vector/
   citations/structure, rồi chuyển active generation trong transaction. Generation
   mới thất bại giữ index cũ đang hoạt động.
6. Search xác định tài liệu còn hợp lệ trước embedding query; scope Qdrant theo
   run/workspace/collection/version trước TopK. Sau HTTP kiểm lại quyền, publication,
   active index và model. Kết quả được đối chiếu SQL/manifest rồi trả text, cấu trúc
   và citation chứa revision/page/block nguồn. Không sinh câu trả lời bằng LLM.

## API

Prefix `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}`.

| Method và path | Ý nghĩa |
|---|---|
| `POST /indexing-runs` | Body `{}` hoặc `{"provider_id":"..."}`, bắt buộc `Idempotency-Key`; 201 tạo mới, 200 replay |
| `GET /indexing-runs?limit=20&offset=0` | Danh sách generation, có phân trang |
| `GET /indexing-runs/{run_id}` | Trạng thái, lỗi, attempts, số chunk, active, dimension |
| `GET /indexing-runs/{run_id}/manifest` | Manifest có ETag và `private, no-store` |
| `POST /search` | `{"query":"...","top_k":5,"document_ids":["..."]}`; document filter tùy chọn, không mở rộng scope |

Run có `queued/running/completed/failed/uncertain`; `completed` và `is_active`
là hai trường khác nhau. Mỗi collection có tối đa một lượt queued/running và một
generation active. Cùng actor/workspace/key replay đúng yêu cầu; đổi body/path
với key cũ trả `idempotency_conflict`.

Search trả `results`, `no_match` hoặc `no_eligible_content`. Tài liệu đã thu hồi
hoặc nguồn đổi được loại và báo lý do; không còn tài liệu thì không gọi embedding.
Có publication mới hoặc receipt mới chưa index thì trả `409 index_outdated`.
Không có index trả `409 index_not_ready`. Provider/vector/storage lỗi trả RFC7807,
không đổi thành danh sách rỗng. Model/config đổi phải tạo generation tương thích.

## Phục hồi và vận hành

Baseline `0001_initial_schema` gồm ba bảng `kb_index_runs/inputs/chunks`, FK scope,
unique publication receipt và index một generation active. Downgrade từ chối để
giữ evidence. Batch647 chỉ migrate DB thử, chưa migrate DB đang phục vụ.

ARQ dùng worker/queue/reconcile hiện có, cron 5 phút khi được bật. Dispatch lỗi
giữ run bền vững; reconcile phục hồi queued/expired lease. Vector/storage lỗi sau
khi vector đã lưu có thể upsert lại cùng ID, không gọi embedding lại batch đó.
Worker mất lease không được kích hoạt generation. Gặp marker HTTP chưa rõ kết quả
thì chuyển `uncertain`, không tự gửi lại. Operator phải xem trạng thái trước khi
tạo run mới bằng key mới; không sửa trực tiếp run cũ hoặc xóa receipt.

Giới hạn server: chunk tối đa 3000 byte, batch 16, 100 document/20000 chunk,
lease 900 giây và tối đa 3 attempts. Đây là giới hạn vận hành, độc lập capacity
model. Budget text dùng UTF-8 byte + 32 cho mỗi đầu vào như trần bảo thủ; usage
thực tế lấy từ provider. Vector staging và raw batch được giữ cho resume/audit;
chưa có chính sách GC cho generation cũ.

## Phạm vi kiểm chứng

Live mẫu qua ModelOps → Redis/ARQ → BGE-M3 → Qdrant → search API thành công:
2 chunk, bảng đứng đầu với giá trị mẫu 150 và citation đúng revision; withdraw
ngừng trả nội dung mà không gọi embedding. OCR/chat của fixture là giả lập.
Không gửi corpus nội bộ, không benchmark chất lượng tổng quát.

Chưa có hybrid/BM25, sparse vector, reranker, RAG answer/chat, giao diện hoặc
benchmark trên corpus thật. `bge-reranker-v2-m3` và `qwen3.5-9b` trong danh sách
server chưa được tích hợp/thử trong batch này. Xem [báo cáo647](../../docs/bao_cao/context647/REVIEW.md).
