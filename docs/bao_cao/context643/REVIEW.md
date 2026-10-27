# Context643 — Sửa sáu lỗi OCR backendV1 và replay phản hồi người dùng

Ngày 2026-10-26. Người dùng cung cấp một phản hồi Nemotron và yêu cầu sửa6lỗi của
[review642](../context642/REVIEW.md). **Sáu lỗi đã được xử lý, full v1 cuối PASS.**

## Bản sửa

| Phát hiện642 | Thay đổi643 | Bằng chứng |
|---|---|---|
| F1 — Worker startup thiếu settings | Nạp Settings trực tiếp; không trông chờ ARQ tự truyền ctx.settings | Regression tạo Worker từ WorkerSettings thực và gọi startup với context ARQ chuẩn PASS |
| F2 — OCR bỏ qua capacity/quota request | Mỗi trang resolve lại ModelOps, kiểm profile/context/input/output và accounting ảnh/prompt; reserve tổng input bound + output | Model có output thấp hoặc thiếu accounting bị chặn trước HTTP; quota10000 không cho request cần16384 dù output chỉ8192 |
| F3 — Retry trộn model/endpoint | Ghim/check hash target/type/timeout/capacity và prompt. Kiểm trước từng trang; completed reuse cũng kiểm target hiện tại | Sau lỗi trang2, đổi endpoint/model cùng provider_id bị chặn; đổi capacity tạo generation mới, không reuse bản cũ |
| F4 — Job mất worker không phục hồi | Startup đúng; claim token riêng mỗi execution; heartbeat; row-lock fencing trước commit/request; cron lấy expired running và delivery queued cũ | Heartbeat giữ lease qua thời điểm hết hạn cũ; worker cũ không commit sau takeover; kết quả HTTP về sau mất claim không được publish; cron phục hồi job |
| F5 — DOCX mất header | Từ chối docx_layout_unsupported khi có header/footer theo section mà Story chưa thể giữ đầy đủ | Gói OpenXML có header không còn bị render body-only âm thầm; regression chấp nhận lỗi tường minh |
| F6 — Parse lỗi mất raw | Adapter giữ bytes của response đã nhận qua OcrResponseError; worker lưu raw trước parse và validation | Invalid layout, malformed JSON structure, truncated và HTTP error vẫn có raw artifact; sample replay đọc raw byte-for-byte bằng đầu vào |

F5 là **chặn an toàn**, chưa bổ sung bộ dàn trang Word đầy đủ. File gốc vẫn được giữ;
có thể dùng PDF đã giữ bố cục. Không ghép header phỏng đoán vào trang hoặc báo đầy đủ
khi converter chưa bao phủ nội dung.

## Capacity và accounting ảnh

ModelOps token_limits thêm ocr_page_input: max_image_width, max_image_height,
input_tokens_upper_bound, prompt_sha256. Đây là khai báo bảo thủ của quản trị viên
theo căn cứ của endpoint/model, vẫn operator_configured; không phải verified hoặc
tokenizer/discovery tự động. Mẫu usage của một trang không chứng minh token của mọi
ảnh khác. Ảnh/prompt ngoài phạm vi hoặc thiếu accounting bị chặn trước HTTP.

Ngân sách output workflow vẫn tường minh, không tự clamp để che lỗi. Không có trần
8K/32K áp chung cho model. OCR_PAGE_TOKEN_BUDGET được giữ để tương thích cấu hình cũ,
runtime không dùng số đó thay tổng request. Profile dùng JSONB sẵn có; không DDL mới.

## Phản hồi người dùng

Replay ngoại tuyến parse thành10block,1bảng6cột/6hàng kể cả header,6ô header. Ô số,
chữ OCR và line break trong ô được giữ; không thêm thư viện sửa chính tả hay sửa
nhận định/năm từ nội dung. Phản hồi có finish_reason=stop; tổng usage hợp lệ4077.

Replay qua provider giả loopback → worker → BlobStore → API **PASS**: canonical giữ
cấu trúc, raw đọc lại khớp bytes của bản JSON cung cấp, usage4077 được ghi nhận.
Đây không phải một lượt OCR Nemotron mới và không đối chiếu độ chính xác với ảnh
nguồn. Không suy chất lượng nhận dạng từ HTTP200 hoặc từ việc parser đọc được.

JSON người dùng và test replay riêng được lưu dưới storage/context643, Git ignore;
không đưa corpus, prompt riêng hoặc Base64 vào report/source test đã port.

## Kiểm chứng thực chạy

| Lượt | Kết quả |
|---|---|
|6regression chính trước sửa | **6FAIL**,10,92s,exit1, đúng F1–F6 |
| Focused đầu sau sửa | **66PASS**,28,78s,exit0 |
| Focused cuối + ownership/heartbeat/quota/raw/reuse | **76PASS/0FAIL/0SKIP**,45,61s,exit0 |
| Full v1 cuối | **265PASS/0FAIL/0SKIP**,98,51s,exit0 |
| Replay phản hồi người dùng xuyên worker/storage/API | **1PASS**,4,26s,exit0 |
| Ruff toàn backendV1 / format13file |PASS,exit0 |
| OpenAPI export |PASS,exit0 |

Thêm16ca chính thức:6regression642 và10ca safety. Cùng venv Python3.12/lockfile v1,
PostgreSQL thật riêng, provider loopback giả. Hai warning deprecation Starlette vẫn
còn. Full chỉ chạy một lần sau batch ổn định; không chọn lại lượt xanh.

Lệnh, cwd backendV1 (DATABASE_URL hạ tầng truyền trong bộ nhớ bởi wrapper):

```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests/integration/test_ocr_regressions_643.py -q --tb=short
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests/integration/test_ocr_regressions_643.py tests/integration/test_ocr_safety_643.py tests/integration/test_ocr_processing_api.py tests/unit/test_ocr_provider_adapter.py tests/unit/test_model_capacity_641.py -q --tb=short
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py tests -q --tb=short
.venv\Scripts\python.exe -X utf8 scripts/run_isolated_tests.py storage/context643/test_user_response_replay.py -q --tb=short
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -X utf8 scripts/export_openapi.py
```

Full265PASS gồm regression local writer trước đây chập chờn. Driver local không đổi
ở643; lượt PASS này không chứng minh nguyên nhân PermissionError642 đã được sửa.
Không sửa/nới test writer để đạt xanh.

## Phạm vi bảo toàn và bàn giao

- 8file ứng dụng v1 hiện có thay đổi và2file mới budget.py/lease.py;475file legacy
  backend/app giữ hash. Không sửa migration, không backfill hoặc sửa bytes nguồn.
- Test helper OCR khai báo capacity/accounting **tổng hợp** phù hợp provider giả;
  không seed hoặc cấu hình model thật từ các giá trị test.
- 5DBtest thuộc phiên đã dọn, sentinel/version legacy giữ, catalog0còn lại; DB phục
  vụ chưa có version table v1. Không xóa DBtest khác, restart/deploy/default/key/Git.
- Cần cấu hình token_limits và accounting có căn cứ qua ModelOps trước OCR thật.
  Chưa live inference, chưa hỗ trợ dàn trang DOCX header/footer đầy đủ; chưa Compiler,
  chunk/index/publication/RAG. Snapshot cũ thiếu identity hash không tự được resume.
- Log/XML/receipt dưới storage/context636:0dc42038b6ae42ff (baseline),e26f29778ec945dd
  (focused đầu),6ebae95e96fc4f6f (focused cuối),ebf081b61753430f (full),92fc66095f164247
  (sample), prefix qnu_v1_test_. Source seal và replay artifacts ở storage/context643.

[Hợp đồng OCR](../../../backendV1/docs/ocr-processing.md) ·
[Capacity/accounting](../../../backendV1/docs/model-capacity.md) ·
[Quy trình21](../../quy_trinh/21_xu_ly_ocr_backendv1.md).
