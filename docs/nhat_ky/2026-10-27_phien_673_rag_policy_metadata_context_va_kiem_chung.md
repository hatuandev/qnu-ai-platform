# Context673 — RAG mục 1–4 trên backendV1

User yêu cầu triển khai retrieval vào chat, metadata-aware retrieval, context
cùng mục và kiểm chứng câu trả lời; Meilisearch chỉ học hỏi nếu phù hợp. Giữ FE
ngoài phạm vi do user đang chạy prompt riêng (Context672).

## Thay đổi

- Assistant rag_policy và conversation snapshot truyền dense/hybrid/rerank, scope,
  window và judge tới pipeline hiện có. Provider qua grant/capability ModelOps.
  PUT client cũ giữ policy, cấu hình mới tăng revision, turn scope kế thừa có kiểm tra.
- Metadata có citation/quote và target đoạn/hàng/ô, hash cùng version; human review
  phải xác nhận đúng metadata hash. Không gán năm dữ liệu toàn tài liệu, không lấy
  metadata một nguồn cho bản tổng hợp nhiều nguồn. Unknown không biến thành năm hỏi.
- Metadata allow-list áp trước Qdrant/FTS TopK; không nới filter khi thiếu kết quả.
  Chunker v2 có parent/position, expansion cùng input/parent/publication và scope,
  dedup và budget JSON evidence, giữ bảng/header/span/notes.
- Judge một lần qua ModelOps, supported/unsupported/uncertain, kiểm đủ statement,
  quote thật và số liệu nguyên dạng. Observe trả kèm báo cáo; enforce chặn nội dung
  chưa được hỗ trợ. Lỗi model/quota/source/cancellation vẫn báo lỗi thật.
- Trace riêng rank/score/timing từng nhánh/context/judge. Không thêm Meilisearch,
  fuzzy tiếng Việt, field boosting, query decomposition hoặc engine tính toán.
- Migration0003 thêm3cột JSONB; baseline0001/0002 giữ bytes. API/worker/recovery
  dùng cùng schema head; heartbeat cần khớp cả code và DB. Không áp DB phục vụ.

Chi tiết file và hợp đồng: [báo cáo](../bao_cao/context673/REVIEW.md),
[verification](../bao_cao/context673/verification.json),
[API](../../backendV1/docs/rag-policies.md),
[quy trình33](../quy_trinh/33_rag_policy_metadata_context_va_kiem_chung_backendv1.md).

## Lệnh và bằng chứng thực chạy

Từ repo dùng Python của backendV1/.venv; không cài thêm dependency. Harness
scripts/run_isolated_tests.py tạo DB test riêng, migrate, giữ sentinel legacy,
chặn network ngoài loopback và dọn DB. Full gate chia75tệp thành4nhóm không trùng;
nhóm TCP/Redis dùng cờ Selector test-only đã có, recovery giữ Proactor.

| Kiểm tra | Kết quả |
|---|---|
| Baseline trọng tâm conversations/answers/hybrid/chunking | PASS49, exit0 |
| Full Pytest cuối qua4nhóm DB riêng | PASS652/0FAIL/0SKIP, cả4exit0; giữ604ID cũ, thêm48, mất0 |
| Ruff check39Python file sửa | PASS, exit0 |
| Ruff format --check39file | PASS, exit0 |
| Migration đối chiếu ORM/legacy/upgrade/downgrade guard | PASS trong full suite;0001/0002 giữ hash |
| OpenAPI đọc từ app | PASS101path/128operation; có policy/metadata/window/judge/hash ack |
| UTF-8 không BOM/LF, local links và diff có phạm vi | PASS |
| So sánh retrieval cùng snapshot | PASS chức năng: dense/hybrid/hybrid_rerank cùng2gold chunk2024, Recall@2=1 |
| Model AI thật/quality corpus QNU/p50-p95/deploy/FE mới | NOT RUN |

So sánh retrieval dùng Qdrant/PostgreSQL thật nhưng embedding SHA256/4chiều và
rerank đảo thứ tự tổng hợp. Không coi Recall@2 fixture là chất lượng model/corpus
thật. Judge cũng dùng HTTP loopback tổng hợp; không có tài liệu nội bộ gửi ra ngoài.

Lịch sử FAIL giữ nguyên: fixture đọc header năm sai; permission assertion dùng
member vốn được phép đọc; budget context tính nhầm locator không gửi model (đã
sửa app và giữ negative case); các lượt sau đạt. Full đầu650PASS trước2unit case
cuối. Một lượt final bị ngắt theo turn, không được tínhPASS; bốnDB thử và vector
của chúng đã dọn có sentinel, sau đó full cuối652PASS. Artifact nằm ở
storage/artifacts/context672-rag (tên lúc khởi tạo trước khi Context672 được FE dùng),
và backendV1/storage/context672; đều ignored, báo cáo công khai dùng số673 chưa trùng.

## Giới hạn và bước sử dụng

Mã BE đã hoàn tất; mặc định vẫn dense/context0/judge off. Để dùng metadata/context
mới cần nâng schema qua migration chủ động, đăng ký/duyệt metadata, tạo generation
mới và cấu hình policy cho trợ lý/hội thoại mới. Không migrate/restart/reindex/
đổi cấu hình đang phục vụ trong batch này. Không commit/push hoặc sửa FE.

Caller còn cần metadata_filter tường minh; chưa tự phân tích mọi câu tự nhiên
thành filter. Giá trị/quote có thật chưa chứng minh nhãn đúng vai trò; human review
vẫn bắt buộc. Judge có thể sai, nên đánh giá observe trên mẫu người duyệt trước
khi dùng enforce để chặn câu thật. Byte budget không phải token usage đã đo.
