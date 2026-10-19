# Kiểm chứng JSON output contract — phiên549

## Kết quả hiện tại

Code contract:47test mới trong nhóm238PASS,exit0,108,55s. Gồm regression Context548,
semantic lifecycle/scope/unknown, old chat contract, ModelOps/context-overflow và
RAG inference safety. HTTP mock đặt ở ranh giới provider; một ca đi trọn HTTP→
service→adapter→strict parser→binder thật→stage proposed sau1format retry.
Ruff22file sửa PASS; boundary check sau chốt metadata/parser63PASS,exit0,42,32s.
Full **18FAIL/2336PASS/17SKIP/0ERROR/23subtests**,exit1,407,20s. Đối chiếu exact
IDs/first causes baseline cùng cấu hình:0ID mất/0status đổi/0lỗi mới,47ID mới đều
PASS,18nguyên nhân lỗi nền giống hệt. Backend full vẫn FAIL; không sửa lỗi nền
ngoài phạm vi. [REGRESSION_IDS](REGRESSION_IDS.md) liệt kê đủ ID/cause.

Live G3/G4 **BLOCKED** sau JSON/schema hợp lệ; chưa proposal hợp lệ, chưa có
human review/apply/persist/rebuild thật. Không tuyên bố toàn RAG sẵn sàng.

## Môi trường an toàn và baseline

HEAD đầu `ebd68292`; working tree sạch. DB PostgreSQL127.0.0.1:5432 được xác minh
READ ONLY, MinIO127.0.0.1:9000 và Qdrant127.0.0.1:6333 là cấu hình local. Suite
không chạy trên DB ứng dụng. Reuse harness548 với state/evidence549 riêng tạo
`qnu_test_context548_6d949a792a14`, nonce/ownership mới và49bảng chỉ trong DB test.
Storage local runtime riêng; S3/Qdrant/Redis dead-port1, autoseed/migrate=false.
Defaults/providers và2credential rows mã hóa copy bằng SELECT READ ONLY; không
thay model/config nguồn. Không migration production hoặc live source writes.

Baseline app copy có SHA256 từng file pin trước sửa caller. Lượt đầu DB chưa có
ModelOps defaults:19FAIL/2288PASS/17SKIP,exit1,377,30s. Gồm18nền và1lỗi setup
MODEL_DEFAULT_NOT_CONFIGURED; không gán lỗi này cho patch. Sau khi copy cấu hình
đã có sang DB test, chạy lại cùng baseline code đã ghim: **18FAIL/2289PASS/17SKIP**,
0ERROR/23subtests,exit1,379,82s. Dossier baseline.xml dùng baseline-configured.xml;
giữ baseline-unconfigured.xml làm lịch sử. Không dùng số18lịch sử548 thay đo mới.

Red probe trước khi nối parser mới vào generation: **2FAIL/1PASS**,exit1,5,03s.
Missing field và duplicate key trước đó không raise/stage được; extra data bị chặn.
Full baseline không chứa testfile mới; red JUnit là bằng chứng tái hiện riêng.

## Expected và actual

| Nhóm | Actual |
|---|---|
| Chat cũ không contract | Payload không thêm response_format; old adapter/capability/stream tests PASS |
| Contract đầy đủ | Request→InferenceService→OpenAIAdapter→HTTP response_format/schema thật PASS |
| Legacy thinking signature | Không cần TypeError retry, output_contract vẫn tới adapter PASS |
| Wire schema | Đối chiếu đệ quy toàn field/$defs/$ref/enum/bounds, required và [] explicit PASS |
| Capability/fallback | Strict unsupported dừng; mỗi fallback resolve lại đúng endpoint/model; weaker chỉ policy cho phép PASS |
| HTTP400 | Schema/request lỗi không làm key invalid, không rotate; context/auth giữ taxonomy cũ PASS |
| JSON parser | Extra text,2objects,duplicate,NaN/Infinity,root/list/null/missing/extra/enum/type đều reject PASS |
| Envelope | Một cặp fence toàn JSON chỉ prompt-only; Unicode/escape/brackets giữ nguyên PASS |
| Response status | Refusal/length/empty không stage; missing finish giữ unknown; ambiguous choices reject PASS |
| Evidence | Binder thật chặn source/context/scope sai, không format retry PASS |
| Retry |1syntax retry; packet/evidence/schema giữ nguyên, không merge invalid output;2lần sai dừng PASS |
| Expansion | needs_context dùng đường cũ, không reset format counter PASS |
| Atomic/deadline | Packet1bind thật/packet2lỗi sau retry:3calls/1bind/0stage; cancel/deadline giữ caller PASS |
| Transport | Retry cùng payload,1shared transient budget; charge HTTP bytes trước gửi; không bỏ format khi negotiate PASS |
| Snapshot/review | Context548/service/DB/Storage lifecycle tests PASS; không tạo human review thật |

Focused đầu118PASS/1FAIL do thiếu config test nói trên. Gate rộng đầu236PASS/2FAIL:
hai fallback test cũ trả selector chỉ có context_id, trái contract mới. Chỉ cập
nhật TEST responses trả đầy đủ arrays; assertion preferred/fallback không đổi.
Các fixture cũ khác cũng trả fields rõ ràng, không hạ validator/default-fill trong
runtime. Gate cuối238PASS. Không xóa/skip/xfail để che lỗi.

## Live G2/G3/G4

G2 registry primary/fallback chưa khai báo json_schema_supported/json_object_supported.
Requested json_schema, effective **prompt_only**, reason explicit_policy_allows_weaker_mode.
Không ghi inferred capability vào DB chung; native strict enforcement NOT_VERIFIED.
Payload json_schema xuất trong dossier là minh họa từ request builder thật với
capability TEST được khai báo, không giả là payload mode của live call.

Fixture mô phỏng SHA256:
58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274.
Không phải quy định QNU chính thức. Primary custom/gpt-6-luna, không fallback;
defaults cx/gpt-6-luna/qwen3.5-9b không đổi.

| Giai đoạn | G3 Bảng1 | G4 API toàn tài liệu |
|---|---|---|
| Scope | selected_tables/qnu:t001,1packet | document,22packet build,1packet đã gửi |
| Logical/provider/HTTP attempts |1/1/1 |1/1/1 |
| Provider/finish | PASS,stop,1choice/content | PASS,stop,1choice/content |
| JSON/selector schema | PASS/PASS | PASS/PASS |
| Format retry |0 |0 |
| Evidence | FAIL EVIDENCE_SCOPE_ROW_AMBIGUOUS_SELECT_NARROWER_SPAN | NOT_RUN |
| Expansion | NOT_RUN | FAIL CONTEXT_EXPANSION_BUDGET |
| Proposal | Không stage | Không stage |
| Human review/apply/reload | NOT_RUN | NOT_RUN |
| Exit |1 |1 |

G3:15.577prompt/939completion tokens, logical47.540bytes, HTTP48.597bytes,
build285,33ms/model10.011,16ms, cost0,0028999USD. G4:15.547prompt/496completion,
logical47.625bytes/HTTP48.682bytes, build529,49ms/model6.008,05ms/API8.712,39ms.
Legacy binding_ms ở G4 bao thời gian thử expansion, không phải đã chạy binder;
dossier ghi validation_attempt và binding NOT_RUN, không gọi đó là binding PASS.
Không lặp inference để tìm output PASS, không retry semantic failure như JSON.

G4 dùng HTTP POST semantic-proposals đúng route UI trong isolated ASGI app,
real DB/localStorage/ModelOps/provider, TEST generation actor override. Không
đánh đồng với human review thật. Lượt setup đầu thiếu origin_document_id của test
fixture và dừng trước provider; đã sửa đúng fixture rồi mới chạy API. Không đưa
SQL traceback chứa corpus của lần setup đó vào ZIP.

Original G4 report ghi provider/schema NOT_RUN dù context_expansion đã có model
response; live-summary hiệu đính trạng thái từ attempt trace/exception sau parser,
ghi rõ correction, giữ original report. Runner đã sửa bookkeeping; không gọi
đây là một lần inference mới hoặc đổi kết quả BLOCKED thành PASS.

## Hồ sơ và giới hạn

commands.json có cwd/argv/exit, hashes source/fixture/baseline; JUnit và exact-ID
comparison giữ cả lỗi nền. Export ZIP allowlist có bytes schema/payload mẫu/trace
đã lọc/JUnit/reports, manifest từng member và checksum ZIP. Không raw response,
credential/configdump/DB/Storage/corpus. HTTP raw body mới không được đóng gói;
trace có body hash và decoder metadata, raw final content nội bộ để chẩn đoán.
Raw lịch sử548 NOT_AVAILABLE; xem [DIAGNOSIS_REPORT](DIAGNOSIS_REPORT.md).

Probe đỏ riêng có2FAIL→PASS (missing/duplicate),extra_dataPASS→PASS. Ba ID này
nằm trong47test mới, không có trong full baseline; không mô tả chúng như2lỗi
full suite đã đổi màu. Boundary check cập nhật privacy/finish diagnostics được
chạy riêng, không lặp full suite không cần thiết cho thay đổi thông báo lỗi.

Đã export ZIP allowlist trước cleanup và kiểm CRC/member list. Sau đó harness
xác minh exact database/ownership comment, DROP đúng DB test và SELECT xác nhận
không còn. PowerShell kiểm nonce/name/absolute runtime/no reparse-point rồi xóa
đúng thư mục tạm, xác nhận không tồn tại. cleanup.json=cleaned, database_removed_verified
true/runtime_exists_after false. Không đụng DB/Storage ứng dụng; encrypted keys
copy và raw response trong test runtime đã được dọn. Dossier cuối evidence.zip
giữ metadata đã lọc, manifest từng member/checksum ZIP và kết quả cleanup thực.

Browser UI/human decision/native
strict live/fallback live thành công và approved persist/rebuild thật: NOT_RUN.
FE không sửa, không chạy build frontend lặp thừa. Không commit/push/restart/
deploy/reparse/index/publish/duyệt nguồn thật.
