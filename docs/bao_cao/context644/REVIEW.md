# Context644 — Theo dõi và nghiệm thu luồng OCR backendV1

Ngày 26/10/2026. Người dùng cho triển khai cách kiểm chứng/theo dõi theo bước học từ
Haystack cho luồng upload PDF/DOCX → revision → job → render → OCR qua ModelOps →
artifact → API. **Nghiệm thu kỹ thuật PASS; Nemotron thật và chất lượng OCR so với
ảnh nguồn NOT RUN.** Không thêm Haystack dependency.

## Phạm vi thay đổi

- Thêm `qnu/domains/ocr/telemetry.py`: sự kiện bắt đầu/kết thúc bước, dùng allowlist
  ID/hash/model/config, thời gian đơn điệu, bộ đếm và mã lỗi. Không serialize config,
  requester, endpoint, credential, prompt, exception detail hoặc nội dung OCR.
- Nối quan sát vào dispatch, kiểm quyền/model/revision, render, preflight/quota,
  provider, parse, storage, assemble và đọc artifact. Trạng thái từng bước độc lập:
  raw có thể lưu thành công trong khi parse thất bại. Timeout/cancellation không
  thành success. Trace dùng logger hiện hữu, chưa có timeline lưu DB/API lịch sử.
- Thêm `GET .../processing-runs/{run_id}/pages/{page_number}/raw`, đọc nguyên bytes
  qua full scope/quyền và checksum, cả khi run failed. Trả octet-stream, SHA256 ETag,
  private/no-store, nosniff. Không nhận đường dẫn storage tùy ý từ client.
- Thêm `scripts/ocr_acceptance_report.py`: đọc JUnit + receipt, ghim hash đầu vào,
  kiểm đủ ID bắt buộc theo 6 nhóm. Missing/SKIP là NOT RUN; duplicate, failure ngoài
  nhóm hoặc cleanup chưa được receipt xác nhận thì FAIL. Kết quả tổng không tự
  suy chất lượng OCR, approval hoặc Compiler từ provider giả lập.
- 21 ca mới: 12 unit (trace/report), 8 API/worker, 1 transport Redis/ARQ thật. Không sửa
  các test cũ để làm xanh.

## Bằng chứng đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Baseline hai ca hợp lệ trước sửa | **2 FAIL**, đúng thiếu stage observations và raw API 404 |
| Focused cuối | **21 PASS / 0 FAIL / 0 SKIP**, 16,89 giây, exit 0 |
| Full backendV1 cuối | **286 PASS / 0 FAIL / 0 SKIP**, 121,96 giây, exit 0; harness 127,16 giây |
| So test IDs với full 643 | Không mất ca cũ; thêm 21 ca |
| Ruff `qnu scripts tests` | **PASS**, exit 0 |
| Format 6 file mới | **PASS**, exit 0 |
| OpenAPI | **40 path / 55 operation**; chỉ thêm raw route, không đổi path cũ |
| Reporter trên full XML/receipt | **PASS**, 6/6 nhóm, đủ 22 ca bắt buộc |
| Bảo toàn nguồn legacy | **475/475 file** giữ SHA256 so đầu task |
| Dọn dữ liệu kiểm thử | Đối chiếu 6 DB test với receipt: **0 DB còn lại**, toàn bộ receipt xác nhận cleanup |
| Tài liệu mới và mục index mới | UTF-8 không BOM, LF và liên kết trong phạm vi mới: **PASS** |

Các kiểm thử kỹ thuật dùng PostgreSQL thật riêng từng lượt. Một ca còn dispatch
qua API vào Redis thật, chạy WorkerSettings/handler/lifecycle thật trên queue test
riêng, kiểm duplicate delivery, đọc kết quả completed và bảo đảm không gọi lại
provider cho run đã hoàn tất. OCR dùng HTTP loopback **giả lập**, không phải Nemotron
thật. Queue/health/job/result/retry/in-progress keys chỉ dọn đúng namespace/ID của ca.

Các kiểm tra raw read/error/identity đáng chú ý: bytes đọc qua API khớp nguyên
response cả malformed/truncated/layout lỗi; chưa auth 401, ngoài workspace 404,
revision/trang không tồn tại 404. Trace không chứa nội dung văn bản hoặc test key.

## Lệnh và artifact

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`. Các lệnh thực tế được gọi qua wrapper
local `storage/context644/run_checks.py`, đọc cấu hình PostgreSQL hạ tầng có sẵn vào
process con và gọi `scripts/run_isolated_tests.py`; không in credential hay thay
config phục vụ. Egress guard chỉ cho loopback, mỗi lượt tự tạo/migrate/dọn DB test.

```text
.venv/Scripts/python.exe -B storage/context644/run_checks.py baseline-valid "tests/integration/test_ocr_observability_644.py::test_stages_correlate_worker_and_api_without_document_content[pdf]" "tests/integration/test_ocr_observability_644.py::test_raw_api_returns_original_bytes_even_when_processing_fails[ok]" -q
.venv/Scripts/python.exe -B storage/context644/run_checks.py focused-final tests/unit/test_ocr_observability_644.py tests/unit/test_ocr_acceptance_report_644.py tests/integration/test_ocr_observability_644.py tests/integration/test_ocr_queue_transport_644.py -q
.venv/Scripts/python.exe -B storage/context644/run_checks.py full tests -q
.venv/Scripts/ruff.exe check qnu scripts tests
.venv/Scripts/python.exe -B scripts/ocr_acceptance_report.py --junit storage/context644/full.xml --receipt storage/context644/full-receipt.json --output storage/context644/acceptance.json
```

Các test ID và kết quả từng ca nằm trong XML. Các file:
`baseline-valid.{log,xml}`, `focused-final.{log,xml}`, `full.{log,xml}` và receipt
tương ứng; `acceptance.{json,md}`, `scope-verification.json`, `openapi-check.json`,
`live-readiness.json`, `cleanup-verification.json`, `document-check-final.json`.
Chúng ở storage bị Git ignore, không đưa corpus/response vào docs.

Lượt quét liên kết toàn bộ các index lịch sử phát hiện 240 lần tham chiếu thiếu có
sẵn. Giữ nguyên ngoài phạm vi; kết quả kiểm tra tài liệu ở trên chỉ áp dụng cho
tài liệu và mục index mới của Context644.

Lượt fixture đầu dùng workspace code có chữ hoa trả422; đã sửa fixture theo schema,
chạy lại baseline hợp lệ, không tính fixture error là lỗi app. Focused đầu phát hiện
raw page không tồn tại bị helper cũ đổi thành409; raw API nay giữ404 nguyên bản.
Regression đầu còn4expectation sai403 cho non-member; đã đối chiếu resolver hiện hữu
và sửa test thành404 theo chính sách che sự tồn tại tài nguyên, không nới quyền.

## Giới hạn và bước sau

- Cấu hình chạy thật v1 hiện chưa có `.env`, DATABASE_URL password, signing key và
  provider encryption key. Chỉ kiểm boolean readiness; không giải mã/copy credential
  ModelOps hoặc tự seed provider. **Live Nemotron và đối soát ảnh nguồn NOT RUN.**
- DOCX header/footer chưa được converter giữ đầy đủ vẫn bị chặn tường minh như643;
  kết quả này không tuyên bố mọi file DOCX đều được render đầy đủ.
- Không migration trên DB phục vụ, không đổi schema/dependency/default model, không
  restart/reindex/publish/deploy/commit/push. Compiler và evaluation RAG không sửa,
  không chạy lại. API evidence giữ hợp đồng revision/generation/hash sẵn có.

Khi runtime v1 được cấu hình qua quy trình riêng, chạy mẫu PDF/DOCX đã đối soát với
Nemotron thật và ghi kết quả chất lượng riêng; không chuyển báo cáo kỹ thuật thành
approval nội dung.

[Hướng dẫn nghiệm thu](../../../backendV1/docs/ocr-acceptance.md) ·
[Báo cáo máy cục bộ](../../../backendV1/storage/context644/acceptance.md).
