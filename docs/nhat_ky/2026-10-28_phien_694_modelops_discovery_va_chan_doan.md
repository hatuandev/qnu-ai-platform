# Phiên694 — ModelOps lấy danh sách, chạy thử và đọc kết quả

Người dùng đồng ý triển khai mục1–2 sau nghiên cứu9router, làm rõ “Tải model”
là lấy danh sách rồi yêu cầu đưa server QNU `http://100.105.13.53:8000/v1/models`
vào luôn. Dùng tên nút **Lấy danh sách model**. Phạm vi backendV1/frontendV1,
giữ sửa đổi trước phiên; áp dụng skill ModelOps, backend/frontend và clean-code.

## Triển khai

Thêm port/provider diagnostic adapter, domain diagnostics schemas/service/router,
đăng ký3route: GET diagnostics, POST discover và POST probe theo capability.
Admin ModelOps mới đọc/chạy được; target/key lấy từ DB theo cùng priority như
runtime, không nhận URL/secret/model tùy ý từ body. Provider tắt/capability sai
bị chặn trước inference. Giữ policy mạng của runtime, không redirect/env proxy,
retry hoặc fallback. Auth optional OCR chỉ lấy từ cấu hình server hiện có.

Tái dùng URL builder, payload và decoder chat/embedding/rerank/Nemotron; thêm
OCR public contract wrapper dùng prompt/layout parser hiện có. Mẫu nhỏ tự tạo,
ảnh PNG chỉ ở RAM, không lấy corpus. Check chat cơ bản/finish/content, vector
hữu hạn và dimension, rerank index/score, OCR bbox layout. Listed không là
verified; chat test chưa chứng minh strict JSON/tools/chất lượng.

Lịch sử20lượt nằm trong Provider.extra_config, không thêm migration. Chỉ giữ
metadata an toàn: ID/thời điểm/latency/code/HTTP/Retry-After/model/dimension/token.
Không lưu raw response, ảnh, prompt/header/secret. ModelOpsEvent ghi actor/action/
provider/code. Cấu hình/key fingerprint thay đổi làm lịch sử stale; thay trong
lúc gọi upstream trả409, không gán success cho target mới. Không giữ transaction
khi chờ mạng; khi lưu lock provider và merge history.

FE chi tiết provider có lấy danh sách, thử từng capability, trạng thái lỗi/trống/
chờ thật, độ trễ và thời điểm. Model selector mở dialog sửa có sẵn và cần người
dùng lưu; không tự đổi model/capacity/dimension/default/grant. Query theo session,
remount tương tác khi đổi session; invalidate khi sửa provider/rotate/revoke key.
Request thử có timeout70giây riêng, giữ timeout mặc định30giây của API khác.
Hiện6lượt gần nhất; unsupported không bị tô thành công.

OpenAPI được xuất bằng script hiện có. Cập nhật README/contract ModelOps,
guide38 và thêm [guide39](../quy_trinh/39_modelops_lay_danh_sach_va_chay_thu.md).

## Server QNU — thao tác live đã được người dùng cho phép

DB V1 hiện tại chưa có provider. Đọc `/v1/models` thực tế trả200 và4IDs:
`bge-m3`, `bge-reranker-v2-m3`, `qwen3.8-27b-q4`, `nemotron-parse`.
Đăng nhập dev theo cấu hình hiện có, tạo4provider + key qua API ModelOps đang
chạy; kiểm trùng theo endpoint/model và chỉ thêm key khi chưa có active key.
Khóa người dùng đã cung cấp được gửi trong bộ nhớ tới API tạo key và lưu mã
hóa, không thêm vào env/source/docs/log hoặc thay credential hệ thống.

Giữ base URL `/v1`, phân vai embedding/rerank/chat/ocr tương ứng; không tự đặt
default, cấp workspace, quota hay khai báo capacity/dimension giả. Run diagnostics
bằng actor thực đã xác thực và key giải mã từ DB; cả4discovery và4probe đạt:

| Model | Phép thử | Kết quả quan sát |
| --- | --- | --- |
| bge-m3 | embedding | vector hợp lệ,1024chiều,77ms |
| bge-reranker-v2-m3 | rerank | index/score hợp lệ,78ms |
| qwen3.8-27b-q4 | chat | content/finish hợp lệ,719ms |
| nemotron-parse | OCR ảnh sinh sẵn | layout có tọa độ hợp lệ,219ms |

Đây là lượt thử nhỏ, không benchmark hoặc SLA. Receipt an toàn
`storage/artifacts/context694-modelops-diagnostics/live-probes.json`.

## Kiểm chứng

Cwd frontendV1 cho npm/Biome, backendV1 cho Ruff/unit; harness từ root dùng
uv project backendV1 và DB riêng:

- Ruff scoped10tệp Python PASS; Biome scoped10tệp FE PASS.
- `npm run build` gồm TypeScript PASS; còn cảnh báo bundle lớn đã có.
- FE trọng tâm15PASS gồm UI, timeout riêng và regression session/secret.
  Test Radix ban đầu dùng pointerDown thiếu API jsdom nên một ca chưa mở Select;
  đổi thao tác fixture sang phím ArrowDown thật, không sửa component/giảm assert.
- Full FE: **393PASS/0FAIL/0SKIP**, exit0, receipt fe-full.json.
- Adapter ban đầu22PASS; thêm2ca tái hiện total deadline và HTTP200 error+data[]:
  cả2FAIL trước sửa, sau sửa24PASS. Deadline tổng asyncio.timeout tối đa60giây;
  error envelope không thành danh sách rỗng. Giữ log trước/sau để truy vết.
- Final adapter+API regression qua harness DB riêng: **33PASS**, exit0;
  negative cases quyền, secret, disabled, cap sai, key/model stale, đổi target
  khi đang gọi, response sai, timeout và không tự retry. DB test đã dọn.
- Full BE khởi chạy trước hai guard cuối, thu686ca: **682PASS/2FAIL/2SKIP**,
  exit1,27phút40giây. Không báo lượt full này PASS. Hai lỗi:
  `test_readiness_666::test_worker_heartbeat_is_queue_scoped_and_removed_on_shutdown`
  thiếu TEST_REDIS_URL; `test_recovery_666::test_full_recovery_into_new_targets_keeps_originals_credentials_and_search`
  chạy dưới Windows Selector không hỗ trợ subprocess. Không sửa code/test để né.
- Chạy lại heartbeat + hai ca queue đã skip với Redis DB15/queue UUID và Selector:
  **3PASS**. Chạy lại recovery với Proactor mặc định: **1PASS**. Cả hai dùng DB
  test mới, cleanup đạt. Giữ nguyên kết quả FAIL của full đầu; final33ca kiểm
  đúng mã sau hai guard, không lặp toàn bộ BE cho hai guard chỉ ở diagnostics.
- Log failure của test cũ có thể in parent environment. Đã làm sạch các artifact
  log/XML lỗi bằng redaction, giữ nguyên số ca và stack nguyên nhân. Wrapper thử
  lại dùng môi trường con tối thiểu, không đổi môi trường đang chạy của người dùng.
- Browser thật trên phiên thử API8014/FE3004: đọc history, click lấy danh sách và
  thử chat thành công, Select đủ4model; mở dialog có model đã chọn rồi Hủy,
  cấu hình gốc giữ nguyên. Desktop và390×844 không tràn ngang; console error rỗng.
  Ảnh modelops-desktop.png/modelops-mobile.png trong thư mục artifact trên.

Harness receipts: full qnu_v1_test_488974e07cae42df (FAIL), final regression
qnu_v1_test_38427a470cb8419f (PASS), Redis recheck qnu_v1_test_8f213929a8734467
(PASS), recovery qnu_v1_test_52f35720e8784a4f (PASS). Đều xác nhận DB đã drop và
legacy sentinel giữ nguyên. Không đưa credential của máy chủ vào test DB.

## Bàn giao

Source thay đổi20tệp trong danh sách artifact changed-source.json; đối chiếu
hash trước/sau để giữ các sửa đổi ngoài phạm vi. Không sửa backend legacy,
migration, env, quyền workspace hay index; không deploy/commit/push.

Phiên thử8014/3004 đã kết thúc; API/FE người dùng trên8002/3001 vẫn chạy. Kiểm
OpenAPI8002 lúc bàn giao chưa có diagnostic routes: cần Ctrl+C đúng phiên
v1-dev cũ rồi `.\make.ps1 v1-dev`, sau đó tải lại trang. Không tự ngắt phiên
của người dùng.4provider và lịch sử thử đã lưu bền vững trong DB hiện tại.

[Snapshot694](../memory/snapshots/2026-10-28_session_694.md).
