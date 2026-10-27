# Context645 — Runtime chat và Compiler backendV1

Ngày 26/10/2026. Người dùng chọn bước 1–2 BE: nối runtime LLM qua ModelOps và
Compiler v1, chỉ định 9router localhost cùng model `gh/gpt-6-luna`. Đã thử model
thật và job Compiler thật với tài liệu mẫu; đánh giá chất lượng chuyên sâu để sau.

## Kết quả chức năng

- Adapter chat OpenAI-compatible/local: normalize endpoint, Bearer credential từ
  ModelOps mã hóa, không redirect/retry/fallback; JSON output, finish reason và
  usage phân biệt thiếu/không hợp lệ. Provider/model/grant/capability/quota động.
- Compiler API: tạo job có Idempotency-Key, list/status/draft/markdown/raw. Scope
  workspace/collection qua resolver, worker kiểm lại membership/role sau dispatch.
- Job trên ARQ v1 hiện hữu: claim, heartbeat/fence, reconcile queued/expired,
  marker trước HTTP; không gửi lại request uncertain. Raw đã lưu được tái xử lý
  nội bộ mà không gọi LLM nữa.
- Ghim snapshot nguồn/revision/OCR generation/canonical hash/manifest hash và model
  config/prompt hash. Không đổi model trong một job hoặc lấy revision mới nhất.
- Lưu JSON/Markdown riêng với trạng thái draft; paragraph có citation trỏ về
  block/cell nguồn, bảng nguyên bản do server đính kèm. Schema/citation hợp lệ
  không được coi là nội dung đã duyệt.
- Migration mới `0007_compilation`: ba bảng `kb_compilation_*`, FK tổ hợp tới
  collection/OCR và unique scope OCR. Không sửa migration 0001–0006. Downgrade từ
  chối để giữ bằng chứng, không xóa dữ liệu âm thầm.

Chi tiết contract, API và vận hành: [Compiler v1](../../../backendV1/docs/compiler-v1.md).

## Lượt gọi model thật

Credential người dùng cấp được nhập qua kênh không echo, đưa qua API ModelOps vào
DB test riêng có mã hóa. Không ghi key trong source, `.env`, report hoặc log.
DB test và queue riêng đã được dọn; không lưu provider/credential vào DB phục vụ.

| Lượt | Kết quả quan sát |
|---|---|
| Chat tối thiểu qua ModelOps | **PASS**, HTTP 200, finish `stop`, 7,110 giây; prompt 2.037 + completion 47 = 2.084 token |
| Lần chuẩn bị Compiler đầu | **FAIL ở GET danh mục**, ReadTimeout 10 giây; chưa gửi yêu cầu biên soạn, DB test dọn |
| Compiler qua API → Redis/ARQ → model thật | **PASS**, run `completed`, 13,328 giây từ tạo job đến đọc lại; một delivery hoàn tất, không job failed |
| Nội dung bản nháp mẫu | 1 section, 2 paragraph, 9 citation references hợp lệ, 1 bảng nguồn, trạng thái `draft` |
| Read APIs | Draft/Markdown/raw HTTP 200; replay cùng Idempotency-Key trả 200 cùng run |
| Usage Compiler | prompt 4.592 + completion 624 = **5.216 token**, finish `stop`; cost không có tariff nên giữ unknown |
| Cleanup live | DB test dropped, các Redis key của queue/job riêng đã xóa |

Giới hạn context 1.050.000 và max completion 128.000 là metadata 9router công bố,
được cấu hình vào provider test. Lượt chat dùng output budget 512, Compiler 4.096;
không thử tải đến trần hoặc khẳng định khả năng tối đa thực tế.

PDF hợp lệ được tạo riêng, OCR nguồn qua endpoint loopback giả lập có bảng/footnote.
**Chat và Redis/ARQ là thật; đây chưa phải thử OCR Nemotron thật hoặc corpus QNU.**
App chạy trong TestClient với seam actor của harness; không triển khai server v1.

## Kiểm tra mã và regression

- Baseline trước triển khai: ca `test_compiler_request_is_durable_and_idempotent`
  **FAIL đúng API 404**, DB test dọn.
- Focused đầu API + migration: **2 PASS**, gồm schema/migration đối chiếu ORM.
- Focused trung gian: **22 PASS / 1 FAIL**; fixture thu hồi membership nhầm actor
  ID thành member ID. Đã đọc contract và sửa fixture lấy member ID qua API, không
  thay quyền ứng dụng.
- Focused cuối: **32 PASS / 0 FAIL / 0 SKIP**, 46,92 giây, exit 0.
- Full đầu: **316 PASS / 1 FAIL / 0 SKIP**, 177,37 giây. Exact ID:
  `tests.integration.test_knowledge_regressions_639::test_downgrade_cannot_mark_success_and_block_next_upgrade`.
  Migration mới từ chối đúng hành vi nhưng thông báo chưa giữ chuỗi hợp đồng
  `evidence must be preserved`; đã sửa thông báo migration 0007, giữ assertion cũ.
- Full cuối: **316 PASS / 1 FAIL / 0 SKIP**, 174,15 giây, pytest exit 1,
  harness 179,78 giây.
  Exact ID còn lỗi:
  `tests.integration.test_knowledge_regressions_639::test_same_key_writers_do_not_fail_storage_under_contention`.
  `LocalBlobStore:48/52` có WinError 5 khi replace và PermissionError khi đọc đích,
  cùng ID/cause đã ghi ở [review642](../context642/REVIEW.md). Driver local và test
  đó giữ nguyên hash trong đợt này. **Full suite vẫn FAIL**, không nới assertion
  hoặc chạy lặp để chọn một lượt xanh. Cả **31 ca mới PASS** trong full cuối.
  Wrapper local in log còn gặp encoding cp1252 khi báo lỗi tiếng Việt; XML/receipt
  đã ghi xong, DB đã dọn. Đã sửa encoding stdout của wrapper ignored, không sửa app.
- Regression riêng sau sửa thông báo downgrade + migration/ORM: **2 PASS**, 6,62
  giây, exit 0. Không sửa test upload bị lỗi Windows.
- Ruff `qnu scripts tests alembic`: **PASS**, exit 0.
- OpenAPI: **45 path / 61 operation**; thêm 5 path/6 operation Compiler, path cũ
  không thay đổi. File OpenAPI đã tái sinh từ app.
- So test IDs: **31 ca mới**, không mất ca cũ (13 unit adapter, 17 integration API,
  1 queue/reconcile thật). Hai test hạ tầng cũ được cập nhật: cleanup thêm bảng mới,
  migration schema mong head 0007 và import ORM mới; không sửa test legacy.
- **475/475 file Python `backend/app`** giữ SHA256 so đầu task. Không đổi lockfile,
  dependency, model default phục vụ hoặc schema legacy.
- Đối chiếu **10 DB test, 0 còn lại**; receipt xác nhận cleanup và sentinel/version
  legacy giữ ở mọi lượt harness. Redis test chỉ xóa key trong queue/job riêng.
- Format 19 file PASS; kiểm UTF-8/LF, literal giống credential và liên kết trong
  phạm vi mới/sửa **43 file PASS**, diff-check các index đã sửa PASS. Không quét
  rồi sửa các liên kết lịch sử ngoài phạm vi.

Ca trọng tâm gồm duplicate/concurrent idempotency, auth/role/revocation, wrong
collection, model disabled/changed, quota, incomplete OCR, input checksum, bad
schema/citation/truncated output, raw retention, timeout uncertain, stale worker
fence và raw recovery không gọi lại LLM. Không xây benchmark/evaluation chuyên sâu.

## Lệnh và bằng chứng

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`. Wrapper local ignored đọc hạ tầng
PostgreSQL/Redis có sẵn vào process, không in credential; gọi harness tạo/migrate/
dọn riêng DB `qnu_v1_test_*`, sentinel/version legacy giữ nguyên.

```text
.venv/Scripts/python.exe -B storage/context645/run_checks.py baseline tests/integration/test_compiler_api_645.py -q
.venv/Scripts/python.exe -B storage/context645/run_checks.py focused-final tests/integration/test_compiler_api_645.py tests/integration/test_compiler_queue_645.py tests/unit/test_chat_adapter_645.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -B storage/context645/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -B storage/context645/run_checks.py full-final tests -q --tb=short
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
.venv/Scripts/python.exe -B storage/context645/probe_model.py
.venv/Scripts/python.exe -B storage/context645/probe_compiler.py
```

Artifacts ignored: XML/log/receipt của các lượt; `live-chat-probe.json`,
`live-compiler-metadata-timeout.json`, `live-compiler-probe.json`, `live-draft.json`,
`live-draft.md`, `openapi-check.json`, `scope-verification.json`,
`final-test-summary.json`, `cleanup-verification.json`, `document-source-check.json`.
Bản nháp mẫu dùng
dữ liệu tự tạo, không đưa source corpus hoặc raw provider response vào Git.

## Giới hạn vận hành

- Chưa migrate hoặc cấu hình DB phục vụ, chưa khởi động/restart/deploy server hay
  worker chạy thường trực. Các API/worker đã được thực thi trong môi trường test.
- Compiler hiện gửi toàn bộ 1–20 nguồn đã chọn trong một request. Cận byte UTF-8
  bảo thủ để preflight; vượt context/budget trả lỗi, chưa tự chia biên soạn nhiều vòng.
- Chưa có duyệt/xuất bản/chunk/embedding/index/RAG/FE v1. Compiler legacy không
  sửa hoặc chạy lại. Không commit/push/reindex/chuyển publication.
- Chất lượng diễn giải và độ chính xác OCR so ảnh nguồn: **NOT RUN** theo phạm vi
  người dùng ưu tiên chức năng. Citation membership chỉ chứng minh liên kết tồn tại.

[Quy trình 22](../../quy_trinh/22_compiler_backendv1.md) ·
[Bản nháp thử model thật cục bộ](../../../backendV1/storage/context645/live-draft.md).
