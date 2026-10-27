# Context673 — RAG mục 1–4 trên backendV1

Ngày 2026-10-27. User cho phép triển khai mục1–4; Meilisearch chỉ tham khảo.
Frontend đang chạy prompt riêng (Context672), không có file FE được sửa trong batch này.

## Hành vi đã triển khai

1. **Retrieval vào chatbot.** Assistant lưu rag_policy có dense/hybrid/hybrid_rerank,
   candidate_k, rrf_k và rerank provider qua ModelOps. Conversation snapshot ghim policy;
   execution truyền vào AnswerRequest và adapter rerank. Provider phải được workspace
   cấp quyền. Client cũ không làm mất policy khi PUT không có trường mới. Snapshot cũ
   dùng mặc định tương thích; thay policy tăng revision, hội thoại cũ được yêu cầu mở mới.
2. **Metadata có căn cứ.** Editor khai báo năm dữ liệu/năm ban hành/hiệu lực/ngành/đợt
   theo đoạn hoặc hàng/ô, có citation và quote đúng nguồn ghim. Document annotation không
   nhận năm dữ liệu/ngành/đợt và chỉ dùng khi có một nguồn OCR. Metadata nằm trong hash
   bundle đăng ký; cổng duyệt yêu cầu người dùng xác nhận đúng metadata hash. Không sửa
   raw OCR hoặc âm thầm biến nhãn do client/model đưa vào thành dữ kiện được duyệt.
3. **Context cùng mục.** Chunker v2 giữ parent/vị trí và mapping metadata trong structure
   có hash. Sau retrieval/rerank, thêm chunk cùng input/section/publication/scope, dedup
   và giới hạn JSON evidence bytes; không nối bằng ordinal toàn generation. Bảng giữ
   header/span/notes hiện có. Generation cũ thiếu parent không bị suy đoán quan hệ.
4. **Kiểm chứng câu trả lời.** Một judge call qua ModelOps đối chiếu từng statement với
   chính evidence đã dẫn, kiểm quote nguyên văn và số liệu, có report/usage/provider trace.
   Observe giữ câu trả lời kèm cảnh báo; enforce không phát hành câu unsupported/uncertain.
   Hạ tầng/model/quyền/quota/cancellation thất bại vẫn là lỗi, không chuyển thành thiếu dữ liệu.

Trace chung bổ sung thứ hạng/score riêng cho dense, PostgreSQL simple FTS, RRF và
rerank, loại score, metadata scope, số ứng viên và thời gian từng nhánh/context/judge.
Không cộng raw score khác thang, không sao chép semanticRatio của Meilisearch sang RRF.

## Ranh giới và tương thích

- Filter scope trước TopK ở cả Qdrant và FTS. Metadata unknown không khớp yêu cầu năm
  đã biết; các trường AND phải cùng annotation. Không bỏ filter do thiếu kết quả.
- Scope turn là dữ liệu bền vững, kế thừa lượt completed gần nhất, không dùng câu trả
  lời cũ làm scope/evidence. Policy trợ lý cố định không bị turn override.
- Chưa tự chuyển mọi câu hỏi tự nhiên thành metadata filter; caller cần gửi scope
  tường minh hoặc đặt ở trợ lý. Một fragment bảng có thể giữ các cột năm khác để bảo
  toàn cấu trúc; metadata của một ô không gán cho mọi ô.
- Đối chiếu giá trị/quote không chứng minh vai trò ngữ nghĩa. Reviewer phải phân biệt
  năm dữ liệu, năm ký và hiệu lực. Judge cũng có thể sai; kiểm chứng nguồn không thay
  đánh giá câu trả lời có giải quyết đúng câu hỏi hay không.
- Mặc định dense/context0/judge off giữ tương thích. Tính năng mới phải bật tường minh.
  Metadata/context mới cần phiên bản được duyệt và generation mới theo luồng hiện có.
- Migration0003 chỉ thêm ba cột JSONB. Baseline0001/0002 giữ bytes; API/worker/recovery
  cùng schema head, heartbeat phải khớp cả code và DB. Không áp DDL DB phục vụ.

## Kiểm chứng

Kết quả máy đọc, exact test IDs và hash mã ở [verification.json](verification.json).
Full cuối **652PASS/0FAIL/0SKIP**, giữ604ID cũ, thêm48, mất0. Bốn nhóm độc lập
272/118/125/137ca đều exit0, DB thử được dọn và sentinel/version legacy giữ nguyên.
Ruff/checkformat39file sửa, migration đối chiếu ORM, OpenAPI101path/128operation
và kiểm tra UTF-8/LF/liên kết có phạm vi đều PASS.
Baseline trọng tâm49PASS trước batch. Provider trong test là HTTP loopback tổng hợp;
PostgreSQL/Qdrant/Redis và handlers là thật trong môi trường thử riêng.

Các ca mới bao phủ policy/schema, quyền provider, PUT cũ giữ policy, idempotency scope,
scope follow-up, unknown/mixed-year, filter trước TopK mọi mode, metadata tamper/human
ack, context cùng mục/budget, quote/statement thiếu hoặc bịa, supported/unsupported/
uncertain, observe/enforce, judge HTTP error và thu hồi nguồn trong khi judge đang chạy.

So sánh kiểm soát dùng cùng snapshot, nhãn fixture độc lập theo vị trí đoạn và cùng
ứng viên hybrid/rerank; cả ba mode đạt annotated Recall@2=1 trên hai chunk được gán
năm2024. Đây là **functional comparison** với embedding SHA256/4 chiều và reranker
đảo thứ tự tổng hợp, không phải benchmark model thật hoặc bằng chứng tăng chất lượng.
Artifact: `backendV1/storage/context672/controlled-retrieval.json` (ignored).

Lượt đầu bộ mới có lỗi fixture đọc ô "Năm2024" như "2024", sau đó có ca kiểm quyền
dựng sai vai trò (member vốn được đọc); đã sửa fixture/assertion theo hợp đồng quyền,
không nới quyền ứng dụng. Một ca thực tế phát hiện budget context tính cả locator DTO
không gửi model; đã đổi sang JSON evidence thật và giữ negative case budget quá nhỏ.
Các lượt FAIL này giữ nguyên log. Một lượt final bị ngắt theo turn, không được coi PASS;
bốn DB thử sở hữu riêng và vector của chúng đã được dọn có sentinel trước khi chạy lại.

## Vận hành và phần chưa làm

Không cài Meilisearch/Haystack, thêm framework, đổi ModelOps/provider config, gọi model
server AI thật, gửi tài liệu nội bộ, migrate/restart/deploy/reindex serving hoặc commit/push.
Không làm query decomposition, engine tính toán, fuzzy tiếng Việt hay ưu tiên trường
tìm kiếm chưa có thí nghiệm. Chưa có phép đo semantic quality, latency p50/p95 hoặc
nghiệm thu production. Không suy chất lượng từ test giả hoặc số repository stars.

[Hợp đồng API và cách bật](../../../backendV1/docs/rag-policies.md).
[Quy trình33](../../quy_trinh/33_rag_policy_metadata_context_va_kiem_chung_backendv1.md).
