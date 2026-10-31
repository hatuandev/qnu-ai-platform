# Phiên 757 — Áp giới hạn ranh giới model, prompt replay hash và phục hồi review sai hợp đồng

## 1. Mục tiêu và phạm vi

- Xử lý triệt để 3 phát hiện từ phiên 756 liên quan đến Compiler Review:
  1. **P1 (Áp giới hạn tại ranh giới gọi model)**: Trước đây `check_limits()` chỉ chạy khi tạo node con lúc bị `chat_output_truncated`. Khi probe đặt trần 1 request/token thì review vẫn gọi model nhiều lần. Cần áp giới hạn tổng request, token (input + output dự trù) và thời gian thực thi trước mỗi request mới (kể cả root, con, resume, retry).
  2. **P2 (Prompt replay hash nhất quán)**: `rebuild_part` dựng hash theo `scope.request_total` nhưng trước đó `messages_for` lại chèn `total` mới của đợt chạy làm thay đổi hash instruction system prompt khi số lá thay đổi. Cần tách prompt v3 độc lập với số lá anh em và đảm bảo messages/schema chuyển cho adapter khớp 100% với hash đã kiểm.
  3. **P2 (Phục hồi phản hồi sai hợp đồng `compilation_review_invalid`)**: Khi model trả đủ độ dài nhưng vi phạm hợp đồng (ví dụ trả thừa assessment cho readonly context, thiếu unit, sai ref), hệ thống trước đó rơi vào trạng thái `uncertain` hoặc kẹt ở `received` và khi resume lại đọc cùng raw sai. Cần chẩn đoán vi phạm, chuyển về `failed` có lưu raw/usage/chẩn đoán, cho phép refinement chia nhỏ scope bị lỗi theo giới hạn hữu hạn (`max_contract_recoveries`), giữ nguyên phần `completed`.
  4. **Lint Frontend**: Sửa lỗi Biome ở `frontendV1/e2e/stages/workflow.spec.ts` (assignment in expression và format).
- Giữ nguyên checkpoint phiên `f2b0e64738c1`, model `ollama/gpt-oss:120b` qua 9router, không đổi cấu hình DB hay dọn dẹp dữ liệu.
- Chạy kiểm chứng unit regression, integration và live E2E chặng `compilation` đạt PASS.

## 2. Các thay đổi kỹ thuật

### Backend
- **[refinement.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backendV1/qnu/domains/knowledge/compilation/review/refinement.py)**:
  - Bổ sung `ReviewRefinementLimits.max_contract_recoveries = 4`, hằng số `CONTRACT_INVALID`, `TRUNCATED`.
  - Bổ sung ledger `attempts_of(segment)`, `reserve_attempt`, `settle_attempt` ghi nhận từng attempt gọi model với trạng thái `reserved`, `settled`, `usage_unknown`, `unknown`, `released`.
  - Bổ sung `check_request_budget(review, segments, limits, estimate_tokens)` kiểm tra trần request, token (exposure = observed tokens + reserved tokens), và thời gian thực thi claim `execution_elapsed_seconds`.
  - Phân loại lỗi có thể refine: `refine_reason(segment)` nhận cả `chat_output_truncated` và `compilation_review_invalid`.
  - Unknown usage giữ nguyên `None` (không đổi thành 0) và tính exposure theo reserved bound.
- **[parts.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backendV1/qnu/domains/knowledge/compilation/review/parts.py)**:
  - Thêm `SEGMENT_PROMPT_VERSION = "qnu.compiler.review.part.prompt/v3"` (độc lập với số lá anh em, chỉ nêu rõ số lượng unit sở hữu và nghiêm cấm nhận xét readonly context).
  - Giữ `LEGACY_SEGMENT_PROMPT_VERSION = "qnu.compiler.review.part.prompt/v2"` cho replay các plan cũ.
  - Sửa `rebuild_part` trả về đúng bộ `messages` đã được kiểm tra khớp hash `plan.prompt_sha256` và `plan.input_sha256`.
- **[report.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backendV1/qnu/domains/knowledge/compilation/review/report.py)**:
  - Cập nhật `messages_for` hỗ trợ prompt v3 không chèn `index/total` khi `total is None`.
  - Thêm `diagnose_contract(content, payload)` phân tích số lượng expected, returned, missing, extra_context, extra_unknown, duplicates để lưu vết kiểm toán mà không cần lưu raw prompt text.
- **[execution.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backendV1/qnu/domains/knowledge/compilation/review/execution.py)**:
  - `_run_segment`: gọi `refinement.reserve_attempt` trước khi gọi provider; settle attempt sang `settled`/`usage_unknown`/`unknown`; bao bọc decode/validation trong khối bắt `compilation_review_invalid`, ghi nhận `last_failure` và chẩn đoán trước khi đánh dấu `failed`.
  - `_execute_segments`: kiểm tra `refine_reason` cho cả hai loại lỗi và gọi `_refine_segment` với trần `max_contract_recoveries`.
  - Cập nhật phân loại lỗi tổng thể: chỉ coi là `uncertain` khi thực sự có part chưa rõ kết quả thực thi upstream, lỗi sai hợp đồng hay quá budget là lỗi `failed` dứt khoát.
  - `_resume_segment` và `_mark_uncertain`: giải phóng (`released`) các attempt chưa gửi thực tế, settle `unknown` cho attempt bị gián đoạn.
- **[service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backendV1/qnu/domains/knowledge/compilation/review/service.py)**:
  - Cập nhật `_can_resume_segmented` dùng `refine_reason(leaf)` để cho phép tiếp tục phục hồi các node sai hợp đồng.
  - Ghi nhận `execution_started_at` trong `row.trace` mỗi lần claim quyền thực thi.

### Frontend
- **[workflow.spec.ts](file:///d:/DuAnPhanMem/qnu-ai-platform/frontendV1/e2e/stages/workflow.spec.ts)**:
  - Tách phép gán `(state.compilationHistory ||= []).push(...)` thành khối if tường minh tránh vi phạm lint Biome `noAssignInExpressions`.
  - Định dạng format chuẩn Biome cho `api.wait`.
  - Cập nhật kiểm tra review cũ bị `uncertain` do `compilation_review_invalid` ở contract cũ để tạo review phục hồi có suffix hợp lệ.

### Test Regressions
- Thêm **[test_compiler_review_budget_757.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backendV1/tests/unit/test_compiler_review_budget_757.py)** với 17 test cases bao phủ:
  - Trần request dừng trước khi gửi request vượt mức.
  - Trần token tính cả dự trù input + output.
  - Trần thời gian tính theo phiên execution.
  - Refinement/resume không vượt trần tổng.
  - Completed node và raw replay không gọi model / không tính phí.
  - Unknown usage không bị coi là 0.
  - Provider uncertain không tự resend.
  - Messages gửi khớp hash đã lưu khi số lá thay đổi.
  - Replay prompt v2 tương thích ngược.
  - Phục hồi phản hồi sai hợp đồng (dư context, thiếu unit, sai ref) bằng cách chia nhỏ node lỗi, giữ nguyên node hoàn thành.
  - Báo lỗi dứt khoát khi cạn số lần phục hồi hợp đồng.
  - Decode thất bại lưu raw/usage và status `failed`.

## 3. Kết quả kiểm chứng

| Hạng mục | Lệnh | Kết quả |
|---|---|---|
| Ruff backend | `uv run ruff check qnu/domains/knowledge/compilation/review tests/unit/...` | **PASS** (0 warnings/errors) |
| Biome frontend | `npx biome check e2e/stages/admissions-recovery.ts e2e/stages/workflow.spec.ts tests/admissions-recovery.test.ts` | **PASS** (3 files checked) |
| Frontend Typecheck | `npm run test:e2e:typecheck` | **PASS** (exit 0) |
| Vitest frontend | `npx vitest run tests/admissions-recovery.test.ts tests/e2e-provider-selection.test.ts tests/progress-budget.test.ts tests/e2e-capacity-735.test.ts` | **PASS** (32/32 tests passed) |
| Unit Tests trọng tâm | `uv run --extra dev pytest tests/unit/test_compiler_review_budget_757.py tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_review_keyed_655.py tests/unit/test_review_literal_751.py tests/unit/test_review_empty_blocks_736.py tests/unit/test_migration_baseline_661.py -q` | **PASS** (71/71 tests passed) |
| Full Backend Unit | `uv run --extra dev pytest tests/unit -q` | **516 PASS / 1 FAIL nền** (lỗi nền duy nhất `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` lỗi `invalid_identity` từ các phiên trước ngoài scope) |
| Live E2E Compilation | `powershell -NoProfile -File ./test-v1-e2e.ps1 run compilation --headed` | **PASS** (1/1 passed, 18.0s; Review nguồn 1 14.8s, Review nguồn 2 9.0s hoàn tất report hợp lệ) |

## 4. Trạng thái bàn giao

- Phiên E2E `f2b0e64738c1` và checkpoint được bảo toàn nguyên vẹn (`checkpoint.json` cập nhật `compilation: PASS`).
- Tiến trình serve nền (`task-562`, PID 9760/25244) đã được dừng an toàn; các cổng 56266 và 56267 đã được giải phóng (`TimeWait`).
- Các container dữ liệu Docker (`postgres`, `redis`, `minio`, `qdrant`, `gotenberg`) vẫn đang hoạt động bình thường phục vụ phiên.
- Lệnh chạy tiếp theo khi người dùng muốn kiểm tra các chặng tiếp theo:
  - Cửa sổ 1: `powershell -NoProfile -File ./test-v1-e2e.ps1 serve`
  - Cửa sổ 2: `powershell -NoProfile -File ./test-v1-e2e.ps1 run publication --headed` (hoặc chặng mong muốn)
