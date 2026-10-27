# Context642 — Review độc lập luồng OCR backendV1

Ngày 2026-10-26. Người dùng đã chạy xong prompt640 và yêu cầu xem lại. Kết luận:
**CHANGES REQUESTED**. Đã tái hiện6lỗi mới; chưa đủ điều kiện nối Compiler.
Không sửa mã ứng dụng hoặc test suite chính trong lượt review.

## Phát hiện đã tái hiện

### F1/P1 — ARQ worker không khởi động được bằng cấu hình hiện tại

[workers/tasks/ocr.py:21](../../../backendV1/qnu/workers/tasks/ocr.py#L21)
đọc ctx["settings"], trong khi WorkerSettings không cung cấp ctx này. ARQ đang
cài chỉ thêm redis trước gọi on_startup. Docker Compose chạy đúng WorkerSettings
này. Probe tạo worker từ cấu hình thực, dùng context ARQ chuẩn, tái hiện KeyError
settings; chưa tới claim/job/OCR. Các test640 gọi execute_run trực tiếp nên không
bao phủ startup. Cần nạp Settings từ nguồn cấu hình hoặc truyền ctx hợp lệ và
kiểm thử đường khởi động worker, không chỉ hàm xử lý.

### F2/P1 — Capacity đăng ký trong ModelOps chưa bảo vệ request OCR

[execution.py:475](../../../backendV1/qnu/domains/ocr/execution.py#L475)
lấy output từ ProcessingConfig và reserve quota bằng OCR_PAGE_TOKEN_BUDGET riêng;
không gọi plan_model_request/resolve_model_capacity. Probe đăng ký shared context128,
max_output32 qua API ModelOps, rồi chạy một trang: HTTP vẫn gửi max_tokens8192 và
run báo completed với provider giả. Đây là capacity tổng hợp để kiểm contract,
không phải giới hạn của Nemotron thật. Cần nối guard trước HTTP, có ngân sách ảnh,
framing và output đúng protocol; quota phải dựa vào request đã tính, không số cố định.

### F3/P1 — Retry trộn endpoint/model trong cùng generation

[execution.py:326–337](../../../backendV1/qnu/domains/ocr/execution.py#L326)
chỉ so provider_id. Endpoint/model của cùng provider có thể thay đổi trong DB,
nhưng run tiếp tục dùng target mới. Probe2trang: trang1 hoàn tất với model cũ;
giả lập lỗi hạ tầng trước request trang2 để run về queued; sửa endpoint/model cùng
provider_id qua API rồi chạy lại. Trang2 gửi changed-model sang endpoint mới,
run completed và canonical ghi provider/model mới cho cả tài liệu. Provenance trang1
bị gán sai. Cần ghim/check hash identity endpoint/model/config/capacity, chặn resume
khi khác; generation mới là hành động riêng. Cache reuse cũng phải cùng identity.

### F4/P1 — Job đã dispatch bị bỏ lại sau khi worker chết

[workers/tasks/ocr.py:58–62](../../../backendV1/qnu/workers/tasks/ocr.py#L58)
chỉ reconcile queued có dispatched_at=null. Một run running đã dispatch và hết lease
không bao giờ được cron này enqueue lại; ARQ retry đã tắt. Probe tạo run, mô phỏng
worker kết thúc bằng expired lease, chạy reconciler:0job, run vẫn running. Claim có
nhánh expired lease nhưng không có đường tự động gọi lại nó. Cần phục hồi run hết
lease và retry enqueue thất bại kể cả đã có dispatched_at, với ownership/heartbeat
và fencing để worker cũ còn sống không ghi đè worker mới.

### F5/P1 — DOCX mất header trước OCR nhưng không báo giới hạn

[artifacts/docx_html.py:330](../../../backendV1/qnu/domains/ocr/artifacts/docx_html.py#L330)
bỏ sectPr và chỉ chiếu body. HeaderReference/header1.xml không được đưa vào PDF,
cũng không có warning. Probe gói OpenXML tổng hợp có Content_Types, package/document
relationships, body và header: PDF chỉ còn BODY_TEXT, mất HEADER_123_2026,
warnings=[]; tái kiểm riêng vẫn FAIL. Số văn bản/ngày/đơn vị trong header có thể mất
trước khi Nemotron nhìn thấy ảnh. Cần converter giữ nội dung liên quan, hoặc phát
hiện cấu trúc chưa hỗ trợ và báo thiếu/chặn đánh giá đầy đủ. Giữ file gốc riêng
không làm ảnh render đã thiếu nội dung trở thành bằng chứng đầy đủ.

### F6/P2 — Lỗi parse làm mất phản hồi OCR gốc

[execution.py:488–499](../../../backendV1/qnu/domains/ocr/execution.py#L488)
parse_page trước ghi raw_response; lỗi parse đi continue. Probe provider trả HTTP200
với layout không hợp lệ: run failed, artifact chỉ có page_image/canonical_json/
markdown/manifest, không còn raw_response để kiểm tra hoặc parse lại. Adapter cũng
raise trước trả raw ở các trường hợp truncated/response không hợp lệ. Cần lưu raw
đã nhận trước diễn giải/validation, kèm trạng thái lỗi; không phục vụ nó như kết
quả hoàn tất nhưng phải giữ chứng cứ của lần thực thi.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Full suite hiện tại | **248PASS/1FAIL/0SKIP**,83,42s,exit1 |
|6probe độc lập sau sửa cách báo lỗi của probe | **0PASS/6FAIL/0ERROR**,11,57s,exit1; đúng F1–F6 |
| Tái kiểm riêng header với gói OpenXML có đủ declarations/relations | **1FAIL**,2,88s,exit1; đúng F5 |
| Ruff toàn backendV1 | PASS,exit0, không auto-fix |
| Source/migration seal |640file giữ hash; gồm475file legacy |

Full còn FAIL ở
`tests/integration/test_knowledge_regressions_639.py::test_same_key_writers_do_not_fail_storage_under_contention`:
WinError5 khi replace rồi PermissionError khi đọc đích tại LocalBlobStore:48/52.
Đã tái hiện ngay trong harness, path nằm dưới D:/.../backendV1/storage/context636/
qnu_v1_test_8202231a662b45f0/objects, không phải tmp_path ngoài harness ở %TEMP%.
Vì vậy kết luận640 rằng lỗi này chỉ do chạy ngoài harness chưa được bằng chứng
hiện tại ủng hộ. Không ghép full248PASS thành249PASS, không lặp để chọn lượt xanh.

Probe lần đầu có1FAIL/6ERROR vì pytest.fail được gọi qua AnyIO portal làm portal
dừng; đó là lỗi cách báo kết quả của probe, không phải6lỗi ứng dụng. Đã sửa chỉ
probe để assertion chạy ngoài portal, rồi tái chạy đủ6ca không còn fixture error.

Lệnh, cwd backendV1, dùng venv đã khóa và DATABASE_URL hạ tầng truyền trong bộ nhớ:

```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests -q --tb=short
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py storage/context642/review_probes.py -q --tb=short
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py storage/context642/review_probes.py::test_docx_header_is_preserved_or_reported_as_missing -q --tb=short
.venv\Scripts\ruff.exe check .
```

DB full8202231a662b45f0, diagnostic3d0ab741c3c743b0, probe1749eb22792e4146,
headerb7d4629c0bda4eed (prefix qnu_v1_test_). Cả4đã dọn, sentinel/version legacy giữ,
đối soát catalog0còn lại. Không đụng DB ngoài ownership; DB chính chưa version v1.
Probe/observations/source seal/log/XML/receipt được Git ignore dưới storage/context642
và storage/context636. Tài liệu tổng hợp và provider loopback; không gọi Nemotron thật.

Luồng API scope/checksum/immutable artifact, migration0006 parity, bảng và timeout
có kiểm thử hữu ích; chúng không thay thế các điều kiện còn thiếu trên. Sau khi sửa,
chuyển probe thành regression chính và kiểm chứng worker thật cùng mẫu live nhỏ
được phép trước Compiler. Lượt này không migrate/restart/deploy/Git hoặc sửa source.
