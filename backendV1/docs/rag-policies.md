# RAG: cấu hình trợ lý, metadata, context và kiểm chứng

Luồng hiện tại: quyền workspace/collection → scope và publication hiện hành →
dense hoặc PostgreSQL simple FTS + dense/RRF → rerank tùy chọn → context cùng mục →
ModelOps sinh câu trả lời → kiểm citation → kiểm chứng tùy chọn → kiểm lại nguồn,
quyền và cấu hình trước khi trả kết quả. Không cài Haystack/Meilisearch hoặc thêm
framework/worker. Query decomposition và truy vấn bảng/tính toán chưa nằm trong batch này.

## Cấu hình và tương thích

Migration tăng dần `0003_rag_policy_metadata` thêm ba cột JSONB vào assistant,
compiled version và turn. Baseline/0002 giữ nguyên. DB phục vụ chỉ nâng schema
qua thao tác migration chủ động; không stamp head, không sửa generation đang phục vụ.
API/worker/recovery dùng `qnu.platform.schema.SCHEMA_HEAD`; worker phải khớp cả
schema DB và phiên bản code trong heartbeat.

`POST/PUT .../workspaces/{workspace_id}/assistants` nhận thêm `rag_policy`:

```json
{
  "name": "Trợ lý tra cứu",
  "collection_id": "collection-id",
  "chat_provider_id": "chat-provider-id",
  "rag_policy": {
    "retrieval_mode": "hybrid_rerank",
    "candidate_k": 30,
    "rrf_k": 60,
    "rerank_provider_id": "rerank-provider-id",
    "metadata_filter": {},
    "context_window": 1,
    "context_max_bytes": 16000,
    "verification_mode": "observe",
    "verification_max_output_tokens": 2048
  }
}
```

ID là ví dụ, cần chọn provider được workspace cho phép, đúng capability/capacity
và có credential bảo vệ trong ModelOps. Có thể chọn `verification_provider_id`
riêng với capability chat; khi không chọn dùng chat provider của yêu cầu/default
ModelOps. Không sao chép key vào cấu hình trợ lý hoặc biến môi trường LLM.

Mặc định tương thích: dense, context_window=0, verification_mode=off. Cần bật
tường minh chức năng mới. candidate_k >= top_k ở hybrid/rerank; không chọn
rerank provider trong mode khác. Các số ví dụ/default là ngân sách, chưa phải tối ưu.
Policy được lưu trong snapshot hội thoại. Thay cấu hình làm tăng revision và cần
hội thoại mới theo hợp đồng hiện có. Client cũ PUT không có rag_policy giữ policy
đang lưu; hội thoại/snapshot cũ thiếu policy dùng mặc định tương thích.

`POST .../collections/{collection_id}/answers` nhận các trường policy ở cấp ngoài
cùng (không bọc rag_policy), bên cạnh question/top_k/provider_id. API search giữ
`mode`, candidate_k/rrf_k/rerank_provider_id và nhận thêm metadata_filter.

## Metadata có nguồn và người duyệt

Khi đăng ký tài liệu hoặc phiên bản, gửi `retrieval_metadata` cùng compilation_run_id:

```json
{
  "compilation_run_id": "compilation-run-id",
  "retrieval_metadata": [
    {
      "target": "paragraph:0:0",
      "values": {"data_year": 2024},
      "evidence": [{"citation": "ocr-run-id:evidence-id", "quote": "Năm 2024"}]
    }
  ]
}
```

Target dùng chỉ số bắt đầu từ 0: `paragraph:section:paragraph`,
`table:ocr-run-id:evidence-id:row:r` hoặc thêm `:column:c`. Target phải tồn tại;
quote phải có nguyên văn trong block/ô của nguồn đã ghim, citation cùng nguồn OCR
của target. Giá trị phải xuất hiện trong trích đoạn; ngày chấp nhận ISO hoặc dạng
ngày/tháng/năm được hỗ trợ. Kiểm tra này xác minh vị trí/giá trị, không tự chứng minh
đúng vai trò ngữ nghĩa: người duyệt vẫn phải đối chiếu năm dữ liệu với năm ban hành.

Các trường: data_year, issued_year, effective_from, effective_until, program và
intake. Target `document` chỉ dùng issued_year/hiệu lực; năm dữ liệu/ngành/đợt phải
gắn đoạn hoặc hàng/ô. Không suy metadata từ tên file hoặc đồng loạt gán năm ký
cho mọi hàng. Không khai báo thì giữ unknown. Trong bản này lọc effective_on cần
cả hai đầu hiệu lực đã biết; thiếu một đầu không tự biến thành khoảng vô hạn.
Target document chỉ dùng khi bản biên soạn có một nguồn OCR; bản tổng hợp nhiều
nguồn phải gắn metadata ở từng đơn vị, không lấy năm ký của nguồn này gán nguồn khác.

Metadata được bọc vào hash bundle đăng ký, bất biến cùng phiên bản. GET version
trả retrieval_metadata và retrieval_metadata_sha256. Nếu có metadata, khi approve
phải bổ sung đúng hash này vào review_ack.retrieval_metadata_sha256, bên cạnh
xác nhận báo cáo Compiler và giải trình findings theo cơ chế cũ. Thiếu/sai hash
trả publication_metadata_review_required. Hash preview/approval/publication/index
ghim metadata; sửa DB đơn phương bị phát hiện khi đọc/duyệt/phục vụ.

Sau xuất bản cần tạo index generation mới theo luồng đã có để nhận metadata và
quan hệ context mới. Không backfill hoặc chuyển active tự động. Sửa metadata đã
đăng ký cần phiên bản mới từ Compiler run mới và duyệt lại; không sửa raw OCR.

## Scope trước TopK và câu hỏi nối tiếp

metadata_filter gồm data_year, issued_year, effective_on (ngày ISO), program và
intake. Các trường trong một filter kết hợp AND trên cùng đơn vị được annotation;
không ghép năm của hàng này với ngành của hàng khác. SQL đọc metadata có hash
manifest trong đúng generation/binding, tạo allow-list chunk cho Qdrant và điều
kiện WHERE cho FTS trước LIMIT/TopK. Không bỏ filter khi ít/không có kết quả.
Chunk unknown không khớp filter yêu cầu giá trị đã biết. Không có chunk phù hợp
thì không gọi embedding/rerank/chat chỉ để tìm rộng hơn.
Một chunk bảng có thể còn các cột/năm khác để giữ cấu trúc. Filter chỉ xác nhận
đơn vị đã annotation có trong chunk, không đổi metadata của tất cả các ô còn lại.

Turn API nhận metadata_filter tùy chọn. Không gửi thì kế thừa scope của lượt
completed gần nhất và policy trợ lý; gửi trường mới để đổi scope ở những trường
không bị policy trợ lý cố định. Mâu thuẫn scope cố định trả conversation_scope_conflict.
Không dùng câu trả lời cũ làm metadata/evidence. Muốn bỏ scope đã ghim thì mở
hội thoại mới. Bản này chưa tự phân tích mọi câu hỏi tự nhiên thành filter; caller
cần truyền scope tường minh hoặc cấu hình ở trợ lý. Không coi prompt là bộ lọc DB.

## Context cùng bản xuất bản

Chunker v2 lưu parent mục, vị trí đoạn/phần và annotation trong structure có hash.
Sau retrieval/rerank, context_window lấy các chunk kề trong cùng input và parent,
giữ version/publication, áp cùng metadata_filter và loại trùng. Không dựa vào
ordinal toàn generation để nối sang tài liệu khác, không đưa OCR chưa duyệt vào.
Bảng tiếp tục giữ header, nhóm rowspan, ô và chú thích theo chunker đã có.

context_max_bytes giới hạn JSON evidence thực gửi model (text/kind/structure),
không tính DTO locator/citation chỉ trả cho API. Evidence chính vượt budget thì
báo answer_context_budget_exceeded; context bổ sung hết budget được bỏ qua có
trace, không cắt ô/bảng giữa chừng. Tổng evidence tối đa 20. ModelOps vẫn kiểm
capacity toàn request và output budget; byte budget không phải số token đã đo.
Generation cũ thiếu parent vẫn đọc được, không đoán quan hệ để mở rộng.

## Kiểm chứng câu trả lời

Mỗi lần chỉ một lượt judge qua ModelOps, không tự sửa/tìm lại vô hạn:

- off: không gọi judge.
- observe: trả câu trả lời kèm báo cáo supported/unsupported/uncertain trong trace.
- enforce: chỉ phát hành khi supported; unsupported/uncertain giữ answer=null,
  statements=[], với reason answer_not_supported hoặc answer_verification_uncertain.
  Sources giữ để đối chiếu và vẫn được kiểm lại khi đọc lịch sử.

Judge phải bao phủ đúng một lần từng statement, chỉ trích evidence chính statement
đã dẫn, và quote phải khớp nội dung/ô/chú thích đã cấp. Báo cáo thiếu/trùng/quote
bịa trả answer_verification_invalid. Supported thiếu số nguyên dạng trong quote
bị hạ thành uncertain; khác định dạng số cũng có thể cần người kiểm lại. Judge
vẫn có thể đánh giá sai ngữ nghĩa, vì thế nên thử observe và nhãn được người duyệt
trước khi bật enforce cho dữ liệu thật. Groundedness không thay thế answer relevance.

Lỗi HTTP/auth/quota/capacity/cancellation hoặc nguồn/model thay đổi là lỗi thật,
không biến thành insufficient_evidence. Checkpoint quyền/nguồn/turn/provider chạy
trước và sau judge. Usage judge có reservation và settlement riêng; missing usage
giữ null, không đổi thành 0 đã đo.

## Chẩn đoán và phạm vi bằng chứng

Trace trả thứ hạng/score riêng cho dense, FTS, RRF và rerank, ghi rõ loại score,
metadata scope, số ứng viên, thời gian embedding/dense/FTS/rerank, context thêm và
ngân sách. Score khác thang không cộng trực tiếp và không là xác suất câu trả lời
đúng. trace.total_tokens hiện là generation; usage/total_tokens judge nằm trong
trace.verification, không gọi số generation là tổng toàn pipeline.

Bài học tham khảo Meilisearch là trường lọc và giải thích xếp hạng; không sao chép
semanticRatio sang RRF, không thêm dịch vụ Meilisearch hoặc fuzzy matching số/năm.
Tìm không dấu/lỗi gõ tiếng Việt và ưu tiên trường cần thí nghiệm riêng trước khi
thay lexical ranking đang chạy.

Các test tích hợp dùng PostgreSQL/Qdrant thật, provider HTTP loopback tổng hợp.
So sánh ba mode cùng snapshot/nhãn fixture chỉ chứng minh scope/contract hoạt
động; không chứng minh model thật, độ chính xác tiếng Việt hoặc cải thiện chất
lượng trên corpus QNU. Không tự reindex/publish hoặc gửi tài liệu thật để nghiệm thu.
