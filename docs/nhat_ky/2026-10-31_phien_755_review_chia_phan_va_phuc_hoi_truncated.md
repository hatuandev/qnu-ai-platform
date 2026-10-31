# Phiên 755 — Tối ưu planner review theo output budget và refinement phục hồi truncated

## 1. Bối cảnh và nguyên nhân lỗi E2E

- Phiên E2E hiện hành `f2b0e64738c1` (`tmp/v1-e2e/f2b0e64738c1`) dùng model `ollama/gpt-oss:120b` qua 9router (`https://qnu-9router.duckdns.org/v1`), `provider_id="prv_e274780a00aa"`, `connection_id="conn_bc1ddea938924b79"`, khai báo `context_window_tokens=131072` và `max_output_tokens=4096`, response alias `gpt-oss:120b` đã được khai báo trong profile E2E.
- Các chặng `provider-setup`, `model-discovery`, `model-chat`, `model-embedding`, `model-rerank`, `model-ocr`, `navigation`, `upload`, `extraction` đều đã PASS.
- Chặng `compilation` tạo run biên soạn `cmp_af9ff45d717e` (`completed`), nhưng bước review `rvw_32ebeb77c954` thất bại với `HTTP 422`, `error_code="chat_output_truncated"` (do adapter chuyển phản hồi upstream có `finish_reason="length"` thành lỗi `chat_output_truncated`).
- Nguyên nhân gốc: Planner review cũ (`review/parts.py` v1–v3) chỉ chia phần khi input vượt `input_char_budget` (tính từ context window `131072`). Với tài liệu ~69 đơn vị source+draft, toàn bộ input vừa khít trong 1 request nhưng JSON kết quả đánh giá + phần reasoning dùng chung ngân sách `max_output_tokens=4096` vượt quá 4096 token. Ngoài ra, khi 1 phần review bị `chat_output_truncated`, `review/execution.py` dừng toàn bộ lượt review thay vì chia tiếp (adaptive refinement) phần bị cụt và bảo toàn các phần đã `completed`.

## 2. Triển khai theo 3 đợt

### Đợt 1 — Planner review xét cả input và output (`review_parts_v4`)

- Cập nhật [`parts.py`](../../backendV1/qnu/domains/knowledge/compilation/review/parts.py) và [`service.py`](../../backendV1/qnu/domains/knowledge/compilation/review/service.py):
  - Bổ sung `ReviewOutputBudget`, `output_budget()`, `estimate_unit_output_tokens()`, `estimate_part_output_tokens()` và `requires_output_segmentation()`.
  - Tách ngân sách `max_output_tokens` thực tế: trừ `REASONING_RESERVE_RATIO = 0.40` khi reasoning dùng chung ngân sách sinh (`0.12` khi `reasoning="off"`), trừ `OUTPUT_FRAMING_RATIO = 0.15` cho JSON schema framing và tính chi phí mỗi owned unit (36–62+ token tùy loại đơn vị, độ dài và số citation).
  - Các đơn vị chỉ nạp làm ngữ cảnh tham chiếu (`context_source_ids`, `context_draft_ids`) không tính vào ownership và không tính vào chi phí output.
  - Bảng dài được chia theo nhóm hàng (`_source_row_groups`, `_draft_row_groups`) có giữ header/caption/footnote/provenance và kiểm tra cả giới hạn input lẫn output; đơn vị đơn lẻ vượt ngân sách và không còn ranh giới ngữ nghĩa để chia tiếp sẽ trả lỗi `compilation_review_unit_too_large` (HTTP 422).
  - Lưu đầy đủ `request_total`, `source_ids`, `draft_ids`, `context_source_ids`, `context_draft_ids`, `output_tokens_estimate`, `output_bytes_estimate`, `budget` và `replay` (`planner_version="review_parts_v4"`, `prompt_version`, `schema_version`, `prompt_sha256`, `input_sha256`, `schema_sha256`) trong `scope_dict()`.

### Đợt 2 — Refinement cha–con và phục hồi review truncated

- Thêm migration [`0010_review_refinement.py`](../../backendV1/alembic/versions/0010_review_refinement.py) và nâng `SCHEMA_HEAD = "0010_review_refinement"` trong [`schema.py`](../../backendV1/qnu/platform/schema.py):
  - Bổ sung cột `parent_segment_id` (kèm index và FK tự tham chiếu) cho bảng `kb_compilation_review_segments`.
  - Mở rộng check constraint `ck_compilation_review_segment_artifact_kind` của `kb_compilation_review_segment_artifacts` để nhận thêm `'markdown'`.
- Tạo [`review/refinement.py`](../../backendV1/qnu/domains/knowledge/compilation/review/refinement.py) và cập nhật [`review/execution.py`](../../backendV1/qnu/domains/knowledge/compilation/review/execution.py):
  - Khi một segment lá gặp `chat_output_truncated` (`is_refinable_truncation`), giữ nguyên segment cha ở trạng thái `failed` kèm `raw_response` và `usage` đã quan sát (hoặc `None` nếu upstream không trả usage), chia owned units của segment đó thành các segment con có `parent_segment_id`, và chạy tiếp trong các wave kế tiếp.
  - Các segment đã `completed` không bao giờ bị gọi lại khi refine hoặc resume (`_can_resume_segmented`).
  - Áp đặt giới hạn cứng: `max_depth=4`, `max_nodes=min(max(roots*31, 31), 256)`, `max_requests=max_nodes`, `max_wall_seconds=1500.0`, kiểm tra giảm số owned units ở mỗi bước chia (`assert_progress`), dừng ngay khi lỗi terminal/cancellation/config mismatch, và ghi nhận usage/raw_response trước khi kiểm tra claim/provider/expiry fence để không mất dấu vết chi phí.

### Đợt 3 — Hợp nhất kết quả lá, kiểm tra coverage và phục hồi E2E

- Cập nhật [`review/execution.py`](../../backendV1/qnu/domains/knowledge/compilation/review/execution.py), [`review/report.py`](../../backendV1/qnu/domains/knowledge/compilation/review/report.py), [`review/artifacts.py`](../../backendV1/qnu/domains/knowledge/compilation/review/artifacts.py), [`review/service.py`](../../backendV1/qnu/domains/knowledge/compilation/review/service.py) và [`review/router.py`](../../backendV1/qnu/domains/knowledge/compilation/review/router.py):
  - Mỗi segment lá lưu riêng artifact `assessment_json` và `markdown` (`segment_markdown_for`); khi các con hoàn tất, tổng hợp ngược lên artifact `assessment_json` và `markdown` của segment cha (`_rollup_parent_artifacts`).
  - Đối chiếu nghiêm ngặt `verify_parent_child_coverage` (mọi parent đã chia phải được thay thế chính xác bởi tập lá hoàn tất, không thiếu và không trùng owned unit) trước khi `_merged_assessments` ghép kết quả theo đúng thứ tự đơn vị chuẩn để sinh `CompilationReviewReport`.
  - Mở endpoint `GET /{review_id}/segments/{segment_index}/assessment` và `GET /{review_id}/segments/{segment_index}/markdown` dưới quyền workspace hiện có.
- Cập nhật [`admissions-recovery.ts`](../../frontendV1/e2e/stages/admissions-recovery.ts) và [`workflow.spec.ts`](../../frontendV1/e2e/stages/workflow.spec.ts):
  - Cho phép E2E nhận diện review cũ bị `chat_output_truncated` tạo bởi planner trước `review_parts_v4` (kể cả khi `max_output_tokens` đã ở trần `4096`) để tạo review key `:recover:v2` chạy qua planner chia phần mới, giữ nguyên lịch sử review lỗi trong DB.

## 3. Rà soát ModelOps (4096 output / 131072 context)

- Cấu hình `context_window_tokens=131072` và `max_output_tokens=4096` của `ollama/gpt-oss:120b` là thông số khai báo trong ModelOps DB của phiên E2E, không mặc định coi là giới hạn vật lý đã xác minh của upstream.
- Với trần `4096`, phần sinh thực tế phải chia sẻ giữa token suy luận (`reasoning`) và JSON kết quả cuối. Do đó planner review và refinement đều giữ nguyên `max_output_tokens=4096`, không tự tăng trần output hay đổi model/reasoning policy để né lỗi.

## 4. Kết quả kiểm chứng

- **Ruff (Backend changed scope)**:
  - `uv run ruff check qnu/domains/knowledge/compilation/review/ alembic/versions/0010_review_refinement.py qnu/platform/schema.py tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_migration_baseline_661.py tests/integration/test_compiler_review_segments_750.py` -> **PASS**.
- **Pytest Unit trọng tâm (Đợt 1 + Đợt 2 + Đợt 3 + Migration baseline)**:
  - `uv run --extra dev pytest tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_migration_baseline_661.py -v` -> **25/25 PASS** (12 test Đợt 1, 11 test Đợt 2 & 3, 2 test migration baseline).
- **Pytest Unit toàn bộ `backendV1/tests/unit`**:
  - `uv run --extra dev pytest tests/unit --basetemp=../tmp/pytest-unit -q` -> **499 PASS / 1 FAIL nền** (`tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` lỗi `invalid_identity` có sẵn từ trước, ngoài phạm vi).
- **Frontend / E2E helper & build**:
  - `npx vitest run tests/admissions-recovery.test.ts` -> **16/16 PASS**.
  - `npx biome check e2e/stages/admissions-recovery.ts tests/admissions-recovery.test.ts` -> **PASS**.
  - `npm run test:e2e:typecheck` -> **PASS**.
  - `npm run build` -> **PASS** (`built in 5.75s`).
- **Integration DB & Live E2E (`Section 9`)**:
  - **NOT RUN**: Dịch vụ Docker trên máy (`com.docker.service`) đang ở trạng thái `Stopped` và các tiến trình/container của phiên E2E `f2b0e64738c1` (cổng `56261`–`56267`, `running: false` trong `manifest.json`) đang dừng. Giữ nguyên toàn bộ checkpoint và dữ liệu phiên `f2b0e64738c1`. Khi người dùng bật Docker, chạy `./test-v1-e2e.ps1 serve` (tự động áp migration `0010_review_refinement`) rồi chạy `./test-v1-e2e.ps1 run compilation --headed`.
