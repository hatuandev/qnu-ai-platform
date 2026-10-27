# Phiên 648 — Hỏi đáp có trích dẫn backendV1

Ngày 26/10/2026, Asia/Bangkok. Người dùng yêu cầu thực hiện bước5: nối search647
vào model chat, học tổ chức pipeline/citation/quyền từ bốn repo đã tham khảo.
Giữ mục tiêu backend hoạt động, quality benchmark corpus thật để sau.

## Thực hiện

- `rag/answer`: API POST `/answers` theo workspace/collection, DTO question/topK/
  document scope/preferred chat provider/output budget và response statements/sources/trace.
- Search647 giữ nguyên ranking/filter. BE cấp ID E1/E2, gửi text/structure và ID
  vào chat, giữ mapping revision/page/path/hash tại server. Không cắt bảng để vừa budget.
- Chat qua ModelOps645: active/grant/capacity/quota/credential mã hóa, không retry/
  fallback. Model phải trả JSON từng ý có ID hợp lệ hoặc abstain rỗng.
- `index/validation`: kiểm lại quyền/index/publication/receipt/revision/hash/
  manifest/chunk/model trước HTTP và sau generation, không gọi embedding lần hai.
  Không trả đáp án nếu source/model/quyền đã đổi. Lock thả trong lúc gọi model.
- Chặn schema sai, ID ngoài danh sách/trùng/thiếu, truncated output, citation giả
  chèn trong text, Markdown link/HTML. BE ghép answer và marker nguồn; chưa semantic verifier.
- Usage lấy token provider; error/unknown phân biệt thiếu căn cứ. Dừng trước HTTP
  settle0token, đã gửi mà chưa rõ thì giữ unknown/reservation. Trace không log nội dung.
- Wiring1router và default budget2048, không migration/dependency mới. Head0009
  giữ; OpenAPI59path/78operation, thêm1path/1operation,58path cũ không đổi.

## Bằng chứng

- Lượt đầu1ERROR fixture provider name trùng; sửa fixture, không phải API pass.
- Focused10PASS,63,77s; mở rộng18PASS,108,61s.
- Repro inline citation1FAIL → sau guard1PASS,8,55s.
- Full v1 đầu: FAIL/không nghiệm thu, kẹt Proactor Windows khi đóng TestClient sau
  các ca; dừng riêng pytest PID đã xác minh, exit4294967295/695,17s. Harness giữ
  sentinel và dọn DB. Retry cùng code/assertion/phạm vi: **396PASS/0FAIL/0SKIP**,
  466,33s,exit0/harness472,53s;20ca mới/0ca mất. Chưa sửa hoặc kết luận nguyên nhân gốc shutdown.
- Ruff toàn `qnu scripts tests alembic` và format9file PASS.
- Baseline743file Python;475legacy app giữ hash,2file v1 đổi/6file mới, UTF-8 không BOM/LF.
- 8DB thử theo receipt đã dọn/0còn,0collection vector v1 quan sát.
- Live BGE-M3 + Qwen3.5-9B + Qdrant qua ModelOps/API PASS:2statement/1source,
  1.979token,2,891s. Đọc đúng ô150 và giữ ghi chú2023, revision đúng. Tokenizer chat
  báo max_model_len131072. Không lưu key hoặc fingerprint; key qua getpass/DB thử mã hóa.
- OCR/Compiler mock với PDF tổng hợp; không corpus nội bộ. Index chạy worker domain
  thật, answer đồng bộ không cần job ARQ mới. Validator cuối replay live output PASS.

## Lệnh

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`; wrapper ignored và harness DB thử
loopback riêng, không in credential hạ tầng, giữ sentinel/version legacy.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py focused-final tests/integration/test_answers_api_648.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py inline-baseline tests/integration/test_answers_api_648.py::test_invalid_answer_is_an_error_not_no_data[inline_citation-answer_response_invalid] -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py inline-final tests/integration/test_answers_api_648.py::test_invalid_answer_is_an_error_not_no_data[inline_citation-answer_response_invalid] -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py full-retry tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/probe_answer.py
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Artifacts ignored `backendV1/storage/context648/`: seals, OpenAPI, log/XML/receipt,
live response/report/log, scope/test/cleanup và kiểm tài liệu. Không commit dữ liệu mẫu.

## Giới hạn

Chưa semantic verifier, benchmark corpus thật/chống injection, year filter cấu
trúc, enumeration coverage, tính toán chính thức, hội thoại/history/raw storage,
streaming/cache/hybrid/rerank/FE hoặc idempotent replay. Mỗi POST là lượt mới.
Citation hợp lệ không bảo đảm mọi ý đúng ngữ nghĩa; functional live nhỏ không là SLA.

Không migrate/cấu hình DB phục vụ, restart/deploy/start API/worker, publish/index
corpus thật hoặc commit/push. Khi vận hành vẫn cần0009/config/quota/index phù hợp.

[Báo cáo648](../bao_cao/context648/REVIEW.md) ·
[API](../../backendV1/docs/rag-answers.md) ·
[Snapshot](../memory/snapshots/2026-10-26_session_648.md).
