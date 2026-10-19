# Validation — bản vá context547, phiên548

## Kết quả kiểm chứng

Regression trọng tâm: **183 PASS**, exit0,71,64s; sau sửa fixture DB,25ca patch
PASS thêm một lượt,exit0,20,07s. Frontend14behavior tests, Biome5file và build
Vite/TypeScript PASS. Full cuối **18 FAIL/2289 PASS/17 SKIP**,exit1,376,20s;
18ID và nguyên nhân lỗi nền giữ nguyên, không lỗi mới. Live **BLOCKED tại schema**: primary phản hồi nhưng JSON có
phần dư sau object, không có binding/proposal/review/apply thật.

## Môi trường và baseline

- Cấu hình local được audit bằng transaction READ ONLY: PostgreSQL127.0.0.1:5432,
  MinIO127.0.0.1:9000, Qdrant127.0.0.1:6333; không dùng DB ứng dụng để chạy suite.
- DB test mới `qnu_test_context548_ac0b8df43d40`, ownership comment với nonce;
 49bảng tạo chỉ ở DB này. Không chạy production migration. Ba index ORM khai
  trùng giống hệt được deduplicate trong metadata setup tạm như phiên547.
- Child ENVIRONMENT=test; DEV_AUTO_MIGRATE/SEED=false, LocalStorage trong runtime
  riêng; S3/Qdrant/Redis trỏ127.0.0.1:1. ModelOps defaults và keys mã hóa copy từ
  shared DB bằng SELECT READ ONLY; accounting test nằm ở DB test, không log secret.
- Lượt baseline đầu bị ngắt khi chat bị dừng, chỉ là kết quả dở dang. Baseline
  hoàn chỉnh dùng bản copy `app/` cố định trước sửa, có hash từng file và bootstrap
  pin package path, để sửa mã hiện hành không đổi mã đo baseline. Test IDs được
  thu thập tại đầu lượt; script/test mới được ghi rõ, không mặc định baseline547.
- Baseline hoàn chỉnh: **24 FAIL/2266 PASS/17 SKIP/0 ERROR**,23subtests,
  exit1,371,01s. Gồm18lỗi nền từng có trong môi trường này và6regression mới tái
  hiện đỏ. Hai lần full cuối/baseline không được thay bằng tổng lỗi lịch sử.

Một focused nhỏ đầu có4FAIL/1PASS: ca unit cap khi đó còn fail tại setup packet
(IndexError), chưa phải probe đúng nguyên nhân. Đã sửa fixture thành packet2rows
dưới cap, và baseline hoàn chỉnh tái hiện đúng “expand không raise”. Không dùng
IndexError ban đầu để tuyên bố đã chứng minh unit-cap bug.

## Expected / actual theo nhóm

| Nhóm | Expected | Actual |
|---|---|---|
| Issue-only/mixed | Không empty sạch; generic comment không bypass | PASS qua stage/application guard |
| Reject/change | Ghi quyết định dù thiếu context; active giữ nguyên | PASS cả khi đã có active snapshot; reload còn context blocker |
| Legacy empty | Preview/state/publication vẫn thấy lỗi | PASS legacy source guard và UI5status; summary Studio là read-only, không backfill DB |
| Quyết định cụ thể | Sai issue/target/actor/span bị từ chối | PASS5negative variants, actor từ server; request schema extra forbid |
| Missing source | Không đóng bằng known unknown/checkbox | PASS; reprocess cần evidence unit bổ sung rồi tạo scope issue mới vẫn chờ human |
| Issue identity/history | Đổi reason/tập thứ tự không đổiID; khác target không nhập | PASS; omitted issue giữ lại và replacement giữ prior issue/proposal hash |
| Multi-year | Quote nhiều năm còn nguyên, chỉ apply sau quyết định riêng | PASS; full-source evidence, exact columns và server actor |
| Exclusion/simple conflict | Generic review không chấp nhận sai scope; single2027→2026 vẫn reject | PASS; không coi year overlap là chứng minh ngữ nghĩa |
| Unit budget | Expand2→40rows/cap6 phải dừng; packet gốc giữ nguyên | PASS accounting union public IDs; directory chỉ tính bytes |
| Packet2 failure | Packet1 binder thật đạt, packet2 lỗi, zero stage | PASS2calls/1bind; timeout và cancellation là ca riêng |
| Deadline | Run/call/provider/cancel phân biệt; thread stage không ghi muộn | PASS; delayed stage thread chỉ sửa private copy, caller giữ nguyên sau hạn |
| Snapshot/replay | Decision/scope/hash/policy giữ qua session khác, không model | PASS PostgreSQL test + LocalStorage; version2 semantic hash đổi khi tamper target |
| Snapshotv1 | Recipe checksum cũ không đổi, unresolved vẫn cần review | PASS; không sửa snapshot bất biến hoặc backfill production |
| API whole document | Đi qua đủ10bảng với deadline như UI, pending không đổi raw/facts/graph | PASS handler/service thật, model adapter TEST; actual DOCX/pair/Storage/DB, không giả live provider |
| Publication | Bypass semantic endpoint vẫn bị chặn khi issue còn mở | PASS tại guard source; limited-publication vẫn tắt |
| Frontend | Issue ở proposed/empty/rejected/change/verified, intent không chứa actor | PASS14tests; Biome/build đạt; browser layout chưa kiểm |

Testfile mới `backend/tests/test_context548_patch.py` có25cases trong lượt cuối;
focused group còn gồm semantic_context_binding/proposals/lifecycle/source_limits/
qnu_serving và clean_content_510. Các assertion của C-2027 cập nhật theo contract
human scope review; test single-year conflict độc lập vẫn giữ ranh giới reject.
Không xóa/skip/xfail test để đổi màu suite.

Lượt full đầu sau sửa: **19 FAIL/2288 PASS/17 SKIP**, exit1,372,47s.
Ngoài18lỗi nền, API whole-document test lỗi `NoneType.send` do fixture ModelOps
dùng kết nối asyncpg thuộc event loop pytest đã đóng. Sửa riêng fixture dùng
engine NullPool trên đúng DB test, không sửa adapter ứng dụng. Củng cố packet1
bằng annotation thật và assert stage thread đã chạy. Sau sửa: **25 PASS**,exit0,
20,07s; full chạy lại với label `after-final`. Giữ JUnit lượt19FAIL trong dossier
thành `after-first.xml`, không thay hoặc che kết quả đó.

## Live ModelOps — một attempt

Fixture DOCX mô phỏng SHA256:
`58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`.
Source pair và Office resource archive được xác minh trước inference. Không phải
quy định QNU chính thức. Scope chỉ Bảng1, đủ13dòng trong1packet; max_calls2,
run/call deadline dùng cùng SemanticContextPolicy với API. Không đổi defaults
`cx/gpt-6-luna`/`qwen3.5-9b` hay provider timeouts trong DB chung.

| Tầng | Kết quả |
|---|---|
| Provider | PASS custom/gpt-6-luna, is_fallback=false,1call |
| Selector/schema | FAIL `SEMANTIC_OUTPUT_INVALID`; JSONDecodeError `Extra data`,line1,column2669 |
| Evidence binding | NOT_RUN vì chưa có selector object hợp lệ |
| Proposal | Không stage; exit1/BLOCKED |
| Human review/apply/persist/reload thật | NOT_RUN; không tự duyệt, không source writes |

Input47.714UTF8bytes,16.920prompt/1.345completion tokens; ModelOps cost trả về
0,003345USD. Build192,29ms, provider14.598,24ms; validation attempt0,59ms là parse
schema, không phải binding thành công. Không có provider error class ở attempt
này; không gọi nó là timeout. Original report lúc gọi gộp stage là `binding`;
summary dossier đã phân rõ schema failure và binding NOT_RUN từ raw response có
SHA256 `7f9bc1b414e96006d4258b6dc819f9469c7882e051ebb5569fad99473df827de`.
Sau đó chỉ sửa phân loại metadata, không sửa response rồi báo thành công.

Không lặp gọi provider để tìm một output PASS. Code/contract checks không thay
thế điều kiện live E2E: thiếu selector hợp lệ, review thật và persist/reload thật
nên **E2E BLOCKED**. Không có proposal thật để xin người dùng duyệt trong lượt này.

## Phép đo context có đối chứng

Cùng saved structured fixture/pair, cùng host,48.000bytes/packet, không provider,
3samples/build; baseline app copy và app sau sửa được pin riêng.

| Chỉ số | Trước | Sau |
|---|---:|---:|
| System/schema bytes | 5.800 | 6.640 |
| Packet count | 19 | 19 |
| Focal units bị bỏ | 0 | 0 |
| Tổng request bytes gồm system lặp | 655.956 | 672.460 |
| Median build ms | 522,92 | 487,97 |

Schema/review contract thêm16.504bytes tổng; không tuyên bố giảm token hay tăng
chất lượng. Latency đo trong lúc full regression chạy nên có nhiễu; không coi
median3lượt là benchmark khẳng định nhanh hơn. Tokens/call/model latency so cặp
offline đều NOT_MEASURED; chỉ live attempt có token thực như trên.

## Commands và hồ sơ

Từ root, dùng Python3.12 trong `backend/.venv`; harness tracked
`backend/scripts/context_patch_validation.py` gán environment test cho child và
lưu cwd/argv/exit trong run.json. Đừng chạy suite trực tiếp bằng DB development.

- `audit_context_patch.py`, `context_patch_validation.py setup/seed-modelops`: exit0.
- `context_patch_validation.py run --label baseline`: exit1,24FAIL/2266PASS/17skip.
- `... run <7 focused files> --label focused-gate`: exit0,183PASS.
- `... script --label live --args-json <test args>`: exit1,schema invalid.
- `... run --label after`: exit1,19FAIL/2288PASS/17skip; lỗi fixture được ghi ở trên.
- `... run tests/test_context548_patch.py --label patch-isolated`: exit0,25PASS.
- `... run --label after-final`: exit1,18FAIL/2289PASS/17skip/0ERROR/23subtests.
- Ruff theo file sửa, Biome5file, frontend14test/build: exit0.
- `measure_context_patch.py` pin baseline/current app: exit0,mỗi phía3samples.

`commands.json` ghi exact argv/cwd/exit và source/fixture hashes.
`regression-comparison.json` liệt kê added/removed/changed/failing IDs và causes.
Đối chiếu24FAIL baseline với18FAIL cuối: **6FAIL→PASS,17ID thêm đềuPASS,0ID mất,
0lỗi mới,18nguyên nhân đầu giữ nguyên**. [REGRESSION_IDS](REGRESSION_IDS.md)
liệt kê đủ ID và nguyên nhân, không chỉ so tổng số. Backend full vẫn **FAIL**;
không sửa lỗi nền ngoài phạm vi để làm toàn bộ suite xanh.
ZIP evidence dùng allowlist riêng; gồm baseline/after/focused/red JUnit, commands,
live summary, metrics, cleanup và3report, có manifest.sha256. Không đóng toàn
Storage/DB, credential, raw model text hay corpus nội bộ vào ZIP. Export chặn
pattern có khả năng là secret thay vì tự đưa vào hồ sơ.

Đã export và kiểm tra ZIP allowlist trước cleanup. Sau đó xác minh ownership,
DROP đúng `qnu_test_context548_ac0b8df43d40` và SELECT xác nhận không còn DB;
PowerShell kiểm absolute runtime/name/nonce và không có reparse point rồi xóa
đúng runtime tạm, xác nhận không còn thư mục. `cleanup.json` ghi **cleaned**,
database_removed_verified=true/runtime_exists_after=false. Không xóa Storage
hay dữ liệu ứng dụng. Dossier cuối `evidence.zip` chứa kết quả cleanup thực tế,
có external SHA256 và manifest từng member; bản export trước cleanup giữ ở
evidence ignored làm lịch sử. Giữ báo cáo context547 nguyên,
không ghi đè lịch sử. Source ZIP được nêu trong prompt không có ở Downloads nên
checksum ZIP đó NOT_VERIFIED; audit dựa trên checkout thực HEAD9b86ba45 và diff.

## Giới hạn chưa chạy

Live multi-packet/whole-document thành công, live fallback thành công, review thật,
browser visual/accessibility và production: NOT_RUN. Test adapter chỉ chứng minh
contract nội bộ. Không bật limited publication, không commit/push/deploy/restart/
reparse/reindex hoặc phê duyệt nguồn thật. Nguồn537/PDF cũ không tự được duyệt.
