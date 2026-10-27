# Context666 — Duyệt, dọn dẫn xuất, phục hồi và readiness backendV1

## Yêu cầu/phạm vi được phép

Người dùng đồng ý triển khai cả bốn mục đề xuất, rồi yêu cầu tiếp tục. Chỉ
backendV1: human review gate, GC dẫn xuất, recovery và nghiệm thu môi trường thử.
Giữ ngoại lệ workspace/membership của v1, backend legacy, sửa đổi FE đồng thời và
hệ thống phục vụ. Phạm vi egress dùng PDF 2 trang và server AI đã được người dùng
cho phép trước đó; khóa chỉ đưa vào ModelOps DB mã hóa, không ghi `.env` hoặc log.

## Thay đổi

- Duyệt cần review completed đúng input/draft/bundle, hash báo cáo và xác nhận
  của actor có quyền. Giải trình đủ finding; preview/hash/receipt ghim ack. Publish
  và replacement kiểm lại approval ack. Không AI tự duyệt hoặc tự khai đã sửa.
- Storage cleanup có preview/accept/key/audit, admin quyền server, khoảng chờ,
  terminal owner, kiểm references và conditional delete Local/S3; giữ nguồn/raw.
- Recovery bundle mã hóa/xác thực toàn bảng sở hữu v1 và tệp được tham chiếu;
  token quản trị, master key ở secret store riêng, MVCC/quiescence. Restore chỉ
  DB chưa tồn tại/kho trống, schema Alembic, rows có kiểu và hash tệp; vector được
  dựng từ DB vào namespace mới, cả inactive remap để cleanup không chạm nguồn.
- Readiness quan sát schema/dependency/worker queue và ModelOps config. Worker
  heartbeat TTL 90s/30s, actual DB head. Không coi GET readiness là live inference.
- Migration tăng dần 0002_operational_readiness: một cột ack và một bảng receipts.
  Baseline 0001/archive cũ giữ bytes. CLI, tài liệu API/ops/ADR và quy trình32 cập nhật.

## Kiểm chứng trung gian và lỗi đã xử lý

Tất cả test integration dùng DB qnu_v1_test_* riêng, network guard chỉ loopback;
restore dùng DB qnu_v1_restore_* riêng. Không reset schema phục vụ.

- Gate trước sửa: 1 FAIL đúng duyệt thiếu review vẫn HTTP200. Sau nối gate, nhóm
  publication/migration18 PASS. Review/gate mới10 PASS trong lượt cùng GC.
- GC đầu6 FAIL vì gọi job_union thiếu đối số. Sửa theo contract hiện hữu, GC6 PASS
  gồm bytes/references/expiry, quyền và pending retry. Không bỏ assertion.
- S3 exists trước sửa nuốt lỗi503 thành missing: regression1 FAIL; sửa chỉ coi404
  là missing. Unit/restore nhóm8 PASS; unit chạy trực tiếp lúc đầu có lỗi quyền
  basetemp Windows, dùng harness sở hữu basetemp riêng rồi kiểm lại đủ.
- Restore đầu3 setup ERROR vì fixture publication cũ chưa gửi ack. Cập nhật
  fixture qua review API thật với reviewer protocol tổng hợp; không bypass gate.
- Probe inactive đầu lỗi dựng test vì DTO không lộ vector_collection, không tính
  là lỗi sản phẩm. Đọc bằng DB test, tái hiện1 FAIL đúng alias namespace nguồn;
  sửa remap mọi generation rồi nhóm recovery3 PASS, cleanup bản phục hồi giữ nguồn.
- CLI import headless thiếu model chat_assistants: fresh-process regression1 FAIL;
  sửa đăng ký model qua app creation (không chạy lifespan/I/O), sau1 PASS. Kiểm
  thêm lệnh CLI backup/preview thật với token được xác thực và đủ43 bảng:2 PASS.

## Nghiệm thu thực

API HTTP loopback thật + token dev của môi trường riêng + ARQ worker/Redis thật;
PDF mức học phí 2024 (2 trang) và Nemotron/Qwen/BGE-M3/rerank trên server đã cho phép.
OCR7,391s, Compiler13,485s, auto-review completed/no_issues_detected, index2,141s,
answer answered/5sources/4413token; functional, chưa semantic accuracy acceptance.
Duyệt thử là thao tác đảo ngược được cho phép trong DB riêng, không publish phục vụ.
Recovery18 tệp, credential giải mã được và query embedding thật sau restore trả5hit.
Readiness ready khi worker sống; production auth NOT RUN (dev token của test).
DB/vector test dọn theo receipt. MinIO thật: conditional change giữ object mới,
conditional delete thành công và bucket thử sở hữu riêng được dọn.

## Full gate và giới hạn Windows

Full đầu ba nhóm exit0; nhóm3 đủ148 test bodies PASS nhưng kẹt Proactor.close của
TestClient, không JUnit/receipt hoàn tất. Lưu evidence, dừng đúng child pytest theo
DB name + process chain; harness dọn DB/sentinel. Full command vẫn FAIL, không gọi
601 PASS cho lượt này. Chạy lại cùng nhóm, cùng app bytes, lại kẹt close.

Bổ sung cờ test-only QNU_TEST_WINDOWS_SELECTOR_LOOP=true để TCP/Redis group dùng
Selector trong TestClient. Default loop và production app không đổi; nhóm recovery
có async subprocess vẫn kiểm trên Proactor mặc định. Không đổi assertion hoặc
mock thêm backend để che lỗi. Kết quả kiểm lại cuối bổ sung sau khi có receipt.
Nguyên nhân sâu của Proactor Windows chưa được sửa; đây là workaround host có phạm vi.

## Lệnh thực chạy

Cwd backendV1, Python .venv/Scripts/python.exe:

- storage/context661/run_tests.py <testfiles> -q, log/receipt từng nhóm có trong
  storage/context666 và DB harness storage/context636.
- -m pytest tests/unit/test_storage_maintenance_666.py::test_s3_outage_is_not_reported_as_missing_object -q (FAIL trước sửa).
- -m pytest tests/unit/test_recovery_archive_666.py::test_recovery_cli_registers_every_owned_table_in_a_fresh_process -q (FAIL→PASS).
- storage/context666/full_gate.py (ba nhóm đạt, một nhóm teardown chưa hoàn tất).
- storage/context666/retry_group3.py (cùng nhóm, tái hiện teardown).
- storage/context666/retry_group3_selector.py (workaround có phạm vi, đang kiểm lại).
- storage/context666/live.py: inference thật, API HTTP/ARQ, restore; nhập key không echo.
- Ruff check/format theo danh sách scoped-python.json, không auto-fix toàn repo.

Chưa migration/config/restart/deploy hệ thống phục vụ; chưa SSO QNU thật, benchmark
ngữ nghĩa/quality, restore legacy/full cluster hoặc quy mô vượt giới hạn bundle.

## Kết quả cuối

604 PASS / 0 FAIL / 0 SKIP, 29 mới/0 mất so575. Hợp ba nhóm453, Selector149 và
hai ca mới qua CLI/readiness boundary, dedupe node IDs; các lượt trước thất bại
giữ nguyên trạng thái. Nhóm Selector đã exit0/dọn DB; không còn tiến trình test.
Ruff/format37file PASS, OpenAPI101path128op và43bảng/head0002.
CLI backup/preview token thật2PASS; readiness quota cuối3PASS. Quota probe đầu
fixture chưa cấp default OCR nên fail trước điều kiện kiểm, không coi là repro
false-ready; sửa fixture cấp đúng providers rồi kiểm thiếu/0/unlimited/blocked.
0 DB sở hữu còn, 0 vector v1 quan sát; MinIO test bucket đã dọn.

[Báo cáo](../bao_cao/context666/REVIEW.md) · [Receipt](../bao_cao/context666/verification.json).
