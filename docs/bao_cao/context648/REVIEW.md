# Context648 — API hỏi đáp có citation backendV1

Ngày 2026-10-26. Người dùng yêu cầu thực hiện bước5 sau dense index/search647,
học cách tổ chức pipeline của Haystack, citation của Kotaemon, RAG cơ bản và quyền
xuyên luồng. Triển khai trên kiến trúc QNU sẵn có, không thêm framework/dependency.

## Kết quả thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Lượt đầu | 1ERROR fixture: tên chat provider trùng với fixture Compiler, sửa tên provider thử |
| Focused đầu | 10PASS/0FAIL/0SKIP,63,77s |
| Focused mở rộng | 18PASS/0FAIL/0SKIP,108,61s |
| Repro citation chèn vào text | 1FAIL: `[E999]` trong text vẫn trả200 dù structured ID hợp lệ |
| Sau guard text | 1PASS/0FAIL,8,55s |
| Full v1 lần đầu | FAIL/không nghiệm thu: hết các ca nhưng kẹt Windows Proactor khi đóng TestClient, dừng đúng pytest PID; exit4294967295,695,17s; DB/sentinel dọn/giữ |
| Full v1 chạy lại | **396PASS/0FAIL/0SKIP**,466,33s,exit0;20ca mới/0ca mất, cùng code/assertion/phạm vi |
| Ruff / format | PASS toàn `qnu scripts tests alembic`;9file kiểm format |
| OpenAPI | 59path/78operation; thêm1path/1operation,58path cũ giữ nguyên contract path |
| Phạm vi source | 743file Python baseline;475legacy app giữ,2file v1 đổi/6file mới |
| Live API | **PASS**,BGE-M3 + Qwen3.5-9B + Qdrant qua ModelOps,2,891s/1.979token |
| Replay cuối | Output live được validator cuối chấp nhận; không gọi model thêm để thử guard |
| Dọn tài nguyên | 8DB theo receipt đã dọn/0còn,0collection vector v1 quan sát |

Live có2statement/1source, đọc đúng ô mẫu150 và nêu nguyên ghi chú2023, citation
đúng revision. Chat `/tokenize` báo131072; embedding dùng dimension1024/input8192
đã quan sát ở647. Cả hai credential nhập hidden, thêm qua API ModelOps có mã hóa
trong DB thử, không lưu key/fingerprint trong source/env/docs/log.

PDF tổng hợp/OCR/Compiler giả lập; embedding/chat API, quota/DB/storage/Qdrant và
handler hỏi đáp là thật. Index gọi worker domain hiện có; không chạy ARQ mới trong
lượt này vì answer đồng bộ. Mẫu nhỏ không là benchmark chất lượng/hiệu năng tải.

## Thay đổi và bằng chứng thiết kế

- `rag/answer/router.py`: POST `/answers` scoped workspace/collection, router mỏng,
  response `private, no-store`. Không có tool write hoặc model tự quyết quyền.
- `schemas.py`: question/topK/document/provider/output budget; model chỉ trả
  status/statements với ID, extra field bị chặn. Mỗi ý phải có nguồn, abstain rỗng.
- `drafting.py`: prompt có phiên bản, phân biệt chỉ dẫn hệ thống với dữ liệu không
  tin cậy. Chỉ text/structure/ID được gửi cho chat; mapping revision/page/path/hash
  giữ ở BE. Không cắt chunk/bảng âm thầm; token overflow trả lỗi.
- `service.py`: reuse search647 và ModelOps chat645; reserve quota trước inference,
  settle usage quan sát, không retry/fallback. Trước HTTP bị chặn thì settle0;
  đã gửi nhưng chưa rõ kết quả giữ unknown/reservation, không giả miễn phí.
- `knowledge/index/validation.py`: revalidate evidence đã lấy, không embedding
  hoặc tìm vector lần hai. Kiểm workspace/collection/active generation/provider/
  publication receipt/revision/hash/manifest và nội dung chunk/citation/structure.
  Source/model/quyền đổi trong lúc inference thì không trả đáp án cũ.
- Marker source do BE gắn. Ngoài ID lạ/trùng, schema sai, thiếu citation, output
  truncated, còn chặn model chèn marker citation/Markdown link/HTML vào text.
- Trace response/log có ID/config hash/count/timing/usage; không ghi câu hỏi,
  evidence text, prompt, raw provider hoặc secret. Chưa lưu raw/hội thoại.
- Chỉ wiring router và default budget2048 trong Settings; capacity thật tiếp tục
  lấy ModelOps. Không đổi thuật toán retrieval/ranking, OCR, Compiler hoặc publication.
  Không cần migration mới; head vẫn0009.

Regression qua API/real DB/Qdrant + HTTP model giả lập: valid answer/citation,
foreign/inline/uncited/schema/truncation/5xx, model abstain, no-hit/withdraw trước
chat, outsider/member/auth, document scope/duplicate, capacity, ungranted preferred
provider, withdrawal/membership/provider disabled/model identity/index change trong
chat và thay index sau reserve trước HTTP (0token,0chat request).

## Lệnh và artifacts

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`, đúng Python3.12/venv/lock v1.
Wrapper ignored đọc bí mật hạ tầng vào process; harness chỉ tạo/migrate/dọn DB
loopback riêng và giữ sentinel/version legacy. Không dùng DB phục vụ để thử.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py focused-final tests/integration/test_answers_api_648.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py inline-baseline tests/integration/test_answers_api_648.py::test_invalid_answer_is_an_error_not_no_data[inline_citation-answer_response_invalid] -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py inline-final tests/integration/test_answers_api_648.py::test_invalid_answer_is_an_error_not_no_data[inline_citation-answer_response_invalid] -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py full tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/run_checks.py full-retry tests -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context648/probe_answer.py
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Artifacts ignored `backendV1/storage/context648/`: baseline/OpenAPI seals, test log/
XML/receipt, live response/report/log, scope/test/cleanup và kiểm tài liệu. Không
đưa dữ liệu mẫu, credential hoặc nội dung private vào Git.

## Giới hạn

- Citation validation chứng minh tham chiếu hợp lệ, không chứng minh toàn bộ ngữ
  nghĩa được nguồn hỗ trợ. Prompt chống injection chưa phải bằng chứng chống mọi
  tấn công; không có tool hoặc hành động ghi được cấp cho model ở bước này.
- Chưa quality benchmark corpus thật, semantic verifier, year filter cấu trúc,
  enumeration coverage hoặc engine tính toán. Không tuyên bố trả đúng mọi câu hỏi.
- Một câu hỏi đồng bộ; chưa lưu hội thoại/raw answer/prompt, replay idempotent,
  streaming, cache, hybrid/rerank hoặc FE. Mỗi POST mới có thể tính usage mới.
- Chưa migrate/cấu hình DB phục vụ, start/restart/deploy API/worker, publish/index
  corpus thật hoặc commit/push. Runtime còn cần0009/config/quota/index hợp lệ.
- Nguồn/citation/API647 và475legacy app giữ nguyên; không đánh đổi provenance để
  làm test xanh. Giá/cost chưa biết giữ NULL, không dùng thời gian mẫu làm SLA.
- Lượt full đầu bị kẹt trong Windows Proactor khi đóng TestClient, chưa xác định
  nguyên nhân gốc. Retry sạch không chứng minh đã sửa lỗi shutdown này; không sửa
  lifecycle hoặc đổi test backend để che lỗi.

[API/vận hành](../../../backendV1/docs/rag-answers.md) ·
[Quy trình25](../../quy_trinh/25_hoi_dap_co_trich_dan_backendv1.md).
