# Phiên 645 — Runtime chat và Compiler backendV1

Ngày 26/10/2026, múi giờ Asia/Bangkok.

Người dùng chọn bước 1–2 BE: runtime LLM ModelOps và Compiler v1, dùng 9router
localhost với `gh/gpt-6-luna`, ưu tiên hoạt động được và để đánh giá chất lượng sau.
Endpoint/credential chỉ dùng trong phạm vi thử được cấp; không lưu key trong docs,
source hoặc `.env`. Chưa cấu hình hay migrate DB phục vụ.

## Triển khai

- Chat port/request/result và adapter OpenAI-compatible có auth/egress/timeout,
  JSON/finish/usage/raw, không tự retry/fallback/redirect. Runtime giải quyết từ
  ModelOps DB có mã hóa, kiểm grant/capability/model/capacity/quota.
- Domain `knowledge/compilation`: model/schema/router/service, input evidence,
  prompt/version/citation guard, artifacts và worker lease/execution.
- API tạo/list/status/draft/markdown/raw. Job ARQ trên queue v1 hiện hữu,
  Idempotency-Key, snapshot ghim nguồn/model, worker kiểm lại quyền, reconcile,
  timeout/in-flight uncertain và raw recovery không gọi lại LLM.
- Migration 0007 tạo ba bảng Compiler, thêm unique scope OCR, FK tổ hợp và chặn
  downgrade mất bằng chứng. Đăng ký ownership/ORM/route/container/worker phù hợp.
- Bản nháp chưa duyệt; bảng nguồn đính kèm nguyên bản, không dùng LLM ghi đè OCR.
  Chưa publication/index/RAG/FE và chưa Compiler nhiều vòng cho nguồn quá dài.

## Bằng chứng

- Baseline một ca FAIL đúng API 404 trước sửa; focused cuối **32 PASS**, 46,92s.
- 31 ca mới đều PASS. Full đầu **316 PASS/1 FAIL**, do thông báo downgrade chưa
  khớp hợp đồng; đã sửa migration mới, không sửa assertion. Regression downgrade
  và ORM sau sửa **2 PASS**, 6,62s.
- Full cuối vẫn **FAIL: 316 PASS / 1 FAIL / 0 SKIP**, 174,15s, pytest exit 1.
  Ca `test_same_key_writers_do_not_fail_storage_under_contention` gặp WinError 5
  ở `LocalBlobStore:48/52`, cùng ID/cause đã ghi Context642. Driver/test đó giữ
  nguyên hash; không sửa ngoài phạm vi hoặc lặp full để chọn kết quả xanh.
- Ruff `qnu scripts tests alembic` PASS; OpenAPI 45 path/61 operation, path cũ giữ.
- Chat `gh/gpt-6-luna` thật qua ModelOps PASS: 7,110s, 2.084 token, finish stop.
- Compiler thật qua Redis/ARQ + model PASS: completed, 13,328s, 5.216 token,
  1 section/2 paragraph/9 citation references/1 bảng nguồn; read APIs và replay
  idempotency PASS. PDF tự tạo, OCR mock loopback; không phải live Nemotron/QNU corpus.
- Lượt chuẩn bị live đầu timeout GET danh mục 10s, chưa gọi Compiler/LLM; tăng
  thời gian đọc metadata ở script thử rồi chạy được. Không resend request uncertain.
- 475/475 file legacy app giữ SHA; 31 ca mới, không bỏ ca cũ; 10 DB test đã dọn,
  Redis test keys đúng namespace đã xóa. Bí mật nhập không echo, mã hóa ở DB test.

## Lệnh và bàn giao

Cwd `backendV1`, wrapper ignored gọi harness cô lập:

```text
.venv/Scripts/python.exe -B storage/context645/run_checks.py focused-final tests/integration/test_compiler_api_645.py tests/integration/test_compiler_queue_645.py tests/unit/test_chat_adapter_645.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -B storage/context645/run_checks.py full-final tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context645/run_checks.py migration-regression tests/integration/test_knowledge_regressions_639.py::test_downgrade_cannot_mark_success_and_block_next_upgrade tests/migrations -q --tb=short
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Wrapper in log cp1252 lỗi khi có tiếng Việt; XML/receipt đã ghi và cleanup xong,
đã sửa stdout wrapper ignored. Không coi lỗi xuất log là kết quả Pytest.

[Báo cáo và file thay đổi](../bao_cao/context645/REVIEW.md) ·
[Hợp đồng Compiler v1](../../backendV1/docs/compiler-v1.md) ·
[Snapshot](../memory/snapshots/2026-10-26_session_645.md).

Không restart/deploy/commit/push, không chạy Compiler legacy, không reindex hoặc
publication. Đánh giá chất lượng diễn giải/OCR so ảnh nguồn NOT RUN theo phạm vi.
Bước vận hành sau là cấu hình môi trường/ModelOps v1 và áp migration vào DB được
phép trước khi chạy API/worker thường trực; lỗi LocalBlobStore Windows còn mở.
