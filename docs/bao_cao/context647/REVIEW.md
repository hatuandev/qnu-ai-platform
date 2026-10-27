# Context647 — Dense index và search backendV1

Ngày 2026-10-26. Thực hiện bước tiếp theo sau publication646 theo yêu cầu người
dùng, dùng server AI được chỉ định. Phạm vi là dense retrieval có nguồn qua
ModelOps/BGE-M3/Qdrant; không cài Haystack hoặc tự thêm framework/worker.

## Kết quả

| Kiểm tra | Kết quả thực chạy |
|---|---|
| Baseline chức năng chưa có | 1 FAIL: ModelOps chưa nhận `embedding_dimension` (422) |
| Smoke lần đầu | ERROR collection: syntax trong search mới; đã sửa trước lượt kiểm sau |
| Smoke sửa / focused đầu | 2 PASS / 7 PASS |
| Focused mở rộng | 38 PASS/0 FAIL/0 SKIP,82,11s |
| Provider tắt trong khi embedding | 1 PASS ngay trước hardening; không cần sửa runtime để làm ca này xanh |
| Hardening baseline | 2 FAIL/2 PASS: thiếu seal cấu trúc bảng và nhận upsert chưa `completed` |
| Focused cuối | **43 PASS/0 FAIL/0 SKIP**,101,29s,exit0 |
| Full backendV1 | **376 PASS/0 FAIL/0 SKIP**,341,56s,exit0;42ca mới/0ca mất |
| Ruff / format có phạm vi | PASS; toàn `qnu scripts tests alembic` sạch,22 file mới/sửa kiểm format |
| Migration/ORM | PASS trong focused; head `0009_dense_index` |
| OpenAPI | **58 path/77 operation**;54path cũ giữ,4path mới,5operation mới |
| Hash phạm vi | 475 file legacy app giữ;724file Python baseline,16file đổi/19file mới trong v1 |
| Live embedding | PASS: BGE-M3 trả4vector/1024chiều,usage51token,0,875s; tokenizer báo8192 |
| Live index/search | **PASS**: Redis/ARQ thật1job hoàn tất/0lỗi, Qdrant thật,2chunk; index1,906s/search0,625s |
| Dọn tài nguyên thử | 12 DB theo receipt đã dọn/0còn;0collection vector v1 còn quan sát; live queue key đã dọn |

Các thời gian chỉ là quan sát một lượt với dữ liệu mẫu nhỏ, không phải SLA hoặc
benchmark tải/chất lượng. Live dùng PDF tổng hợp và OCR/chat giả lập; embedding,
ModelOps credential/quota, Redis/ARQ, PostgreSQL, BlobStore và Qdrant là thật.
Search đưa bảng có giá trị mẫu150 lên đầu (score0,62025285), citation đúng revision;
withdraw trả `no_eligible_content`, không phát sinh embedding usage mới.

Khóa đầu trả401 cả qua adapter lẫn request trực tiếp. Người dùng xác nhận server,
sau đó gửi khóa sửa; lượt gọi thật mới thành công. Không lưu khóa hoặc dấu vân tay
khóa vào source/docs/log; getpass đưa bí mật vào process, API ModelOps mã hóa trong
DB thử, sau đó DB bị dọn. Không ghi LLM key vào `.env` hoặc cấu hình provider đang phục vụ.

## Thay đổi và lý do

- Embedding adapter OpenAI-compatible strict count/index/dimension/finite/nonzero,
  model identity, auth và timeout. Endpoint/model/capacity/dimension động từ
  ModelOps được cấp; không fallback hay retry inference chưa rõ kết quả.
- Ba bảng run/input/chunk ghim publication receipt và scope qua FK tổ hợp.
  Migration0009 thêm unique scope receipt vào bảng v1 đã có, không sửa migration cũ;
  partial unique chặn hai job hoặc hai active generation cùng collection.
- Chunk văn bản giữ heading/citation; bảng lấy snapshot OCR, giữ ô/header/span,
  nhóm rowspan, footnote/caption và các giá trị0/rỗng/gạch. Nhóm quá budget chặn
  indexing, không biến dữ liệu dẫn xuất thành nguồn hay gán năm từ tên file.
- Job bền vững và idempotent trên ARQ hiện có: transaction trước dispatch,
  lease/heartbeat/fencing/reconcile. Raw embedding, vector staging và batch receipt
  giữ cho phục hồi; marker HTTP chưa rõ kết quả chuyển `uncertain`, không gửi lại.
- Qdrant staging riêng mỗi generation; chỉ namespace v1, không viết collection
  legacy. Point ID ổn định, upsert `wait=true` phải xác nhận `completed`.
- Manifest lưu hash input/config/text/vector/citation/structure. Generation chỉ
  active sau khi kiểm lại quyền/model/publication; lỗi generation mới giữ active cũ.
- Search scope trước TopK, kiểm lại sau HTTP, đối chiếu vector hit với SQL/manifest.
  Thu hồi/nguồn đổi loại nội dung; publication/receipt mới cần index mới. Lỗi provider,
  quota, vector hoặc hash là lỗi rõ, không giả thành không có dữ liệu.
- API create/list/status/manifest/search nằm trong knowledge/index, router mỏng.
  Phản hồi search/manifest `private, no-store`. Các route cũ giữ; ModelOps schema
  chỉ thêm trường dimension/status. Test invariant cùng ID chuyển sang adapter
  reranker còn là stub; không bỏ assertion fail-loud hoặc che embedding bằng stub.

## Bằng chứng kiểm tra và lệnh

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`, Python3.12 theo venv/lock v1.
Wrapper ignored đọc credential hạ tầng có sẵn vào process, không in chúng.
Harness tạo/migrate/dọn DB loopback `qnu_v1_test_*`; sentinel legacy giữ.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context647/run_checks.py hardening-baseline tests/integration/test_index_api_647.py::test_table_structure_tampering_is_rejected tests/unit/test_qdrant_adapter_647.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context647/run_checks.py focused-final tests/integration/test_index_api_647.py tests/unit/test_embedding_adapter_647.py tests/unit/test_index_chunking_647.py tests/unit/test_qdrant_adapter_647.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context647/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context647/probe_embedding.py
.venv/Scripts/python.exe -X utf8 -B storage/context647/probe_index.py
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Artifacts cục bộ ignored `backendV1/storage/context647/`: baseline seal, log/XML/
receipt, live embedding/index/search JSON, scope/OpenAPI/test/cleanup verification.
Không đưa dữ liệu nguồn, credential, Base64 OCR hoặc prompt riêng vào Git.

Regression ở API/worker/adapter gồm quyền và role, idempotency, dimension/model
đổi, source revision đổi, withdrawal trước worker/trong query, disabled provider,
quota,401/5xx/malformed, foreign vector scope, structure tamper, pending batch
uncertain, failed replacement và filter trước TopK. Unit kiểm protocol/bảng;
integration dùng mock HTTP embedding4chiều với Qdrant thật, không chứng minh
chất lượng model. Live thử riêng kiểm kết nối và relevance rất hẹp trên mẫu.

## Giới hạn và bàn giao

- Chưa migrate0009 vào DB phục vụ hoặc khởi động/restart/deploy API/worker;
  chưa đăng ký provider/key trong DB phục vụ. Không publish/index corpus thật.
- Chưa hybrid/BM25/sparse, rerank, RAG answer/chat, FE hoặc benchmark corpus.
  `bge-reranker-v2-m3`, `qwen3.5-9b` và live OCR Nemotron không thử ở batch này.
- Chưa GC generation/raw/vector staging cũ. Quota input là upper bound text bảo
  thủ; usage thực lấy provider. Production private endpoint tuân egress server
  hiện có; không nới quyền private-network từ request.
- Phục hồi `uncertain` cần xem evidence và quyết định run mới; không tự rerun
  inference. Capacity/dimension cấu hình là trạng thái configured, không gắn nhãn
  verified cho mọi model. Không đánh đồng functional PASS với chất lượng QNU.
- Bước sau phù hợp: nối evidence/citation từ search vào runtime trả lời, vẫn lấy
  model chat qua ModelOps và báo thiếu căn cứ/lỗi provider trung thực.

[API/vận hành](../../../backendV1/docs/dense-indexing.md) ·
[Quy trình24](../../quy_trinh/24_index_va_tim_kiem_dense_backendv1.md).
