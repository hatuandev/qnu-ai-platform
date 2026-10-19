# Validation — Structure-aware context và evidence binding, phiên 547

## Kết luận hiện tại

Đã triển khai selectors → backend exact binding và context có cấu trúc trong
pipeline hiện hữu. Focused regression **127 PASS**, Ruff 12 file, frontend 8
behavior tests, Biome 3 file và build/TypeScript đạt. **ModelOps end-to-end BLOCKED**:
lượt trên mã cuối trả `ALL_PROVIDERS_UNAVAILABLE`, primary ghi `ReadTimeout`.
Không có proposal thật hợp lệ, human approval hoặc apply/reload thật.

Full regression cuối: **18 FAIL / 2264 PASS / 17 SKIP / 0 ERROR**,23subtests,
exit1,360,23s. Đúng18failure IDs và nguyên nhân đầu tiên của baseline; không mất
test cũ, không đổi trạng thái test cũ, thêm21case PASS. Suite vẫn **FAIL**.
Database test và Storage tạm đã xóa, xác minh không còn tồn tại.

## Môi trường và baseline trước sửa

- Kiểm cấu hình development: PostgreSQL 127.0.0.1:5432, MinIO :9000,
  Qdrant :6333; xác minh transaction READ ONLY và Docker local.
- Không chạy tests vào DB ứng dụng. Tạo DB riêng
  `qnu_test_context547_5cddd8aa7841`, ownership nonce, 49 bảng trong DB mới;
  không migration hay DDL trên DB ứng dụng/production.
- Test child: ENVIRONMENT=test, auto migrate/seed false, StorageDriver local
  trong runtime riêng; MinIO/Qdrant/Redis trỏ 127.0.0.1:1. Cảnh báo Qdrant
  không lấy được server version là hệ quả chủ động vô hiệu endpoint thật.
- Chỉ cấu hình ModelOps + credential mã hóa được sao chép bằng SELECT READ ONLY
  sang test DB. Accounting/health/quota live kiểm thử cũng ở DB này.
- Baseline trước integration: **18 FAIL / 2243 PASS / 17 SKIP / 0 ERROR**,
  23 subtests, exit 1, 344,33 s. Không thay bằng baseline13 lỗi lịch sử.
- Dossier `backend/storage/context547-evidence/` giữ `baseline.json` với từng ID,
  PASS/FAIL/SKIP, nguyên nhân và hash trước sửa; `full-baseline.xml/.log` và
  `full-baseline-run.json` chứa command/cwd/exit code.

## Kết quả theo yêu cầu T01–T17

| ID | Expected | Actual và bằng chứng |
|---|---|---|
| T01 | Backend lấy exact quote từ selector | PASS: `test_T01_backend_binds_selected_source_without_model_copying_quote`; pending không thay effective data |
| T02 | Không nhận model diễn đạt lại | PASS: extra quote bị strict schema từ chối; legacy whitespace rewrite vẫn bị exact validator chặn |
| T03 | Chặn sai unit/revision/span/hash/sibling | PASS: sáu biến thể `test_T02_T03_rewritten_foreign_or_stale_evidence_never_binds` |
| T04 | Không nhầm byte/UTF-16/Unicode | PASS: NFD, khoảng trắng/newline và emoji giữ nguyên; span code points, không fuzzy repair |
| T05 | TB1 toàn đúng Bảng 1 | PASS DOCX thật: review TEST rồi kiểm từng row/column context |
| T06 | C-2027 chỉ cột2027 | PASS DOCX thật: các cột khác không nhận note; negative year conflict bị từ chối |
| T07 | AM-0007 khác AM-0070 | PASS DOCX thật: đúng một row; wrong identifier bị chặn |
| T08 | NV16–30, không nhóm khác | PASS DOCX thật: row directory bảo toàn group xuyên cửa sổ và kiểm scope từng field |
| T09 | Hai note cùng chữ độc lập | PASS: `test_T09_identical_actual_notes_keep_distinct_source_and_table`; quote bằng nhau nhưng source/table/evidence IDs khác |
| T10 | `/` chưa rõ giữ nguyên | PASS: actual CT-06 raw `/`, state ambiguous; phase2 candidate/ack/replay tests cũng đạt |
| T11 | K-05 đúng CT-05 | PASS: `test_T10_T11_actual_scoped_legend_preserves_unknown_slash`; không kéo note sang CT-06 hoặc đổi raw/state |
| T12 | Far reference duy nhất hoặc unresolved | PASS: exact Clause9/remote condition, explicit expansion, duplicate label trace và no-new rejection |
| T13 | Partition/budget không mất dữ liệu âm thầm | PASS: 120-row fixture đủ row IDs, byte/unit/packet caps; requested row nạp đủ fields; total-budget fail trước model |
| T14 | Không tự duyệt/không stage nửa bộ | PASS: stage pending giữ effective, malformed context và budget failure không mutate; API quyền/hash/idle/draft regressions đạt |
| T15 | DB/Storage reload không model | PASS: `test_T15_bound_evidence_survives_real_db_storage_and_rebuild` dùng PostgreSQL test, LocalStorage, session khác; binding và chunks giữ note. Đây là actor TEST, không review thật |
| T16 | Real provider/binding/review phân biệt | BLOCKED, chi tiết dưới; không dùng mocks để báo end-to-end PASS |
| T17 | So exact IDs trước/sau | Đối chiếu đạt: cùng18FAIL IDs/cause, không lỗi mới/ID bị mất; thêm21PASS. Toàn suite vẫn FAIL18 |

Checksum DOCX thật được assert trước parse:
`58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`.
Office raw resource archive cũng được kiểm checksum. Đây là tài liệu mô phỏng,
không phải dữ liệu/quy định QNU chính thức.

Red trước implementation: exact legacy rewrite rejection PASS, selector test
FAIL vì chưa có ContextBuilder (1 FAIL/1 PASS, exit1). Cuối dùng cùng ranh giới
evidence, không nới assertion hay validator để chuyển xanh.

## ModelOps thật

Giữ đúng defaults primary `cx/gpt-6-luna` và fallback `qwen3.5-9b` đã được user
cho phép từ phiên546. Không sửa provider/model/endpoint/timeout/config DB chung.
Mỗi lượt giới hạn một top-level call, chỉ phân tích Bảng1 của DOCX mô phỏng.

| Giai đoạn | Lượt trước tối ưu gói | Lượt trên mã cuối |
|---|---|---|
| Provider phản hồi | PASS, custom/gpt-6-luna, không fallback | FAIL, `ALL_PROVIDERS_UNAVAILABLE`; primary `ReadTimeout` |
| Context | 2 gói tối thiểu; model yêu cầu thêm7 dòng | 1 gói có đủ13 dòng, packet+system dưới48.000 bytes |
| Evidence binding | NOT COMPLETED: expansion vượt byte budget trước bind | NOT RUN: không có response hợp lệ |
| Proposal hợp lệ | Không tạo, exit1 | Không tạo, exit1 |
| Human review/apply/persist thật | NOT RUN | NOT RUN |
| E2E | BLOCKED | BLOCKED |

Lượt đầu ban đầu phân loại exception là `SEMANTIC_EVIDENCE_INVALID`, reason
`CONTEXT_EXPANSION_BUDGET`. Sau review code đã tách lỗi expansion thành
`SEMANTIC_CONTEXT_INCOMPLETE`, không gọi nó là quote bịa. Giữ report gốc;
không viết lại lịch sử thành kết quả của mã cuối. Mã cuối kiểm cả tổng các gói
tối thiểu trước inference, tránh tiêu một phần ngân sách rồi mới phát hiện thiếu.

Dossier ignored: `live/` giữ context/response/report thật ở lượt đầu;
`live-final/` giữ context/report lỗi trên mã cuối. Raw text chỉ là fixture mô phỏng
đã được phép gửi, không chứa credential. Không phát sinh proposal để người dùng
duyệt; chưa có trạng thái WAITING_FOR_REVIEW thật.

## Số đo và giới hạn

| Phép đo | Kết quả quan sát |
|---|---|
| Catalog cũ toàn fixture | 75.884 UTF-8 bytes, 62.168 ký tự, build một lần 4,91ms |
| Context mới toàn fixture, offline | 19 gói, 0 focal unit bị bỏ, 655.956 bytes tổng request gồm schema/system lặp; build486,03ms |
| Gói mới lớn nhất | 41.882 bytes payload +5.800 bytes system/schema <48.000 |
| Thực gọi lượt đầu | 1 call, 36.710 input bytes, build204,31ms, model11.886,09ms, validation/expansion20,44ms |
| Token/cost lượt đầu | 13.044 prompt /936 completion; ModelOps trả cost0,0025182USD |
| Accepted/rejected lượt đầu | 0 accepted; 1 lượt bị chặn do budget trước khi bind, không phải một semantic proposal được chứng minh sai |
| Mã cuối provider timeout | Không có output/token/quote để chấm; binding latency NOT MEASURED |

Đây là số đo một lần, có phép đo diễn ra cùng regression CPU; không phải benchmark
latency công bằng. Cũ/toàn tài liệu và live/chọn bảng khác phạm vi, không kết luận
giảm token hay chất lượng tốt hơn. Context mới có tổng overhead lớn hơn catalog cũ;
giới hạn tổng/call/timeout vẫn có thể chặn tài liệu lớn. Tham chiếu deferred được
giữ ID/trace/unresolved, không giả đã đọc hoặc tự hiểu pháp lý.

## Lệnh và khả năng chạy lại

Từ root repo, harness task-local `isolate547.py` kiểm safety/ownership trước tạo DB,
gán test environment cho mọi child và lưu run.json. Phải tạo nonce/runtime mới khi
chạy lại sau cleanup; không tái dùng tên DB đã xóa hay chạy trực tiếp bằng cấu hình
development có auto migrate/seed.

- Baseline: `isolate547.py run --label full-baseline` → exit1.
- Focused cuối: `isolate547.py run tests/test_semantic_context_binding.py tests/test_semantic_proposals.py tests/test_semantic_lifecycle.py tests/test_source_limitations.py tests/test_qnu_serving.py --label focused-compact` → exit0,127PASS,50,44s.
- Full cuối: `isolate547.py run --label full-stable` → exit1,18FAIL/2264PASS/17SKIP/0ERROR/23subtests,360,23s.
- Ruff: `backend/.venv/Scripts/ruff.exe check` trên12file backend của lượt này → exit0.
- Từ frontend: `node --test src/features/knowledge/components/semantic-review-preview.test.mjs` → exit0,8PASS;
  `npm exec -- biome check --line-ending=lf` trên3file thay đổi → exit0;
  `npm run build` (Vite + TypeScript) → exit0.
- Live: harness `script` với `live547-final-args.json` → exit1, không ghi source DB.

Một lượt full trung gian (`full-final`) đã chủ động dừng ở khoảng43% để tối ưu
context; exit4294967295, không đủ kết quả, không tính là PASS hoặc baseline.
Full stable đã được so đúng từng ID/nguyên nhân với baseline qua `comparison.json`
và [REGRESSION_IDS](REGRESSION_IDS.md), không chỉ so tổng số lỗi.

Browser layout, live fallback thành công, full19-call real analysis, review/apply
nguồn thật và production: **NOT RUN**. Không commit/push/restart/reparse/index/publish.

## Dọn dữ liệu kiểm thử

Sau khi tất cả child đã kết thúc, harness kiểm đúng tên DB và ownership comment,
terminate chỉ sessions của DB test đó, DROP rồi SELECT xác nhận DB không còn.
Native PowerShell kiểm absolute targets trong workspace, đúng runtime nonce,
không phải reparse-point target, rồi xóa runtime cùng `live/objects`,
`live-final/objects` và bản sao `before.json`/`canonical.md` của hai lượt.
Test-Path xác nhận cả7targets không tồn tại. `cleanup.json` và state
`context547-isolation.json` ghi **cleaned**; cả hai bước cleanup exit0.

Giữ JUnit, run.json, baseline/comparison, context/response của fixture mô phỏng
và report để truy vết; không giữ credential trong dossier. DB ứng dụng,
MinIO/Qdrant thật và các dữ liệu kiểm thử lịch sử ngoài nonce này không bị dọn.
