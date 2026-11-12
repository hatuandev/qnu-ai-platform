# Phiên 936 — Bền vững soát chính tả tự động và tự chạy lại index sau lỗi tạm thời

- Yêu cầu: ổn định quy trình upload → OCR → soát chính tả → duyệt chính tả → duyệt/xuất bản → tự đánh index → lưu Qdrant. Chỉ sửa lỗi độ bền trong chuỗi này; RAG để sau. Không retry câu hỏi model để làm xanh kết quả, không nới assertion/bỏ guard; `NOT RUN` không phải `PASS`; F13 vẫn là vấn đề chất lượng riêng, chưa sửa. Không chạy test trên DB ứng dụng, không cài thêm dependency, không tự commit/push/deploy.
- Hiện trạng đã đối chiếu: chuỗi thật trên dữ liệu phiên 935 đi hết các bước. Index generation 1 `failed index_publication_changed` là bảo vệ snapshot cũ **có chủ đích** (test `test_withdrawal_while_building_keeps_newer_intent_and_never_activates_stale_content` khẳng định `failed`), không phải lỗi cần sửa. Hai lỗ hổng độ bền còn lại được xử lý trong phiên này.

## Lỗ hổng 1 — Retry lỗi vector/hạ tầng chờ tới 5 phút

- Trước sửa: `execute_run` gặp `vector_unavailable`/`storage_unavailable` đưa run về `queued`, `dispatched_at=None`; chỉ cron `index_reconcile` 5 phút mới giao lại.
- Sau sửa: `backendV1/qnu/workers/tasks/indexing.py` — sau `execute_run`, nếu run `queued` và chưa dispatch thì gọi ngay `dispatch()` sẵn có (`qnu:v1:index:{run_id}:{attempt_count + 1}`). Các trạng thái khác giữ nguyên; trần `INDEX_MAX_ATTEMPTS=3` không đổi; cron reconcile vẫn là lưới an toàn.
- Test mới: `test_transient_vector_failure_is_redispatched_without_waiting_for_reconcile` (`backendV1/tests/integration/test_publication_index_sync_878.py`) — upsert giả lỗi một lần, lần giao lại có `dispatched_at`, job id `...:2`, lần hai `completed`, embedding chỉ gọi một lần.

## Lỗ hổng 2 — Mất lượt soát chính tả tự động khi enqueue một lần bị thất lạc

- Trước sửa: chỉ `ocr_process_run` enqueue `spelling_check_job` khi OCR xong; enqueue lỗi hoặc worker chết trước khi tạo bản ghi cha thì run `completed` không có lượt soát nào và người dùng phải tự phát hiện.
- Sau sửa: `backendV1/qnu/workers/tasks/ocr.py` thêm `spelling_reconcile` (grace 10 phút, cửa sổ 24 giờ, tối đa 20 run/lượt). Truy vấn `NOT EXISTS` lượt cha tự động (`run_id`, `version=0`, khóa `auto:spl:document:`), enqueue `spelling_check_job` với job id theo bucket 5 phút. Đăng ký trong `backendV1/qnu/workers/settings.py` (hàm + cron 5 phút trong khối `OWN_RECONCILE`).
- An toàn trùng lặp: unique `(workspace_id, created_by, idempotency_key)` và khóa dòng OCR run (`authorize(lock=True)`) tuần tự hóa job đồng thời; lần trùng trả trạng thái hiện có, không gọi thêm model. Cửa sổ 24 giờ/giới hạn 20 giới hạn chi phí backfill.
- Test mới: `test_spelling_reconcile_restores_a_completed_run_with_no_check` (`backendV1/tests/integration/test_ocr_safety_643.py`) — run hoàn tất bị làm cũ 1 giờ, reconcile giao đúng job, job chạy tạo đúng một lượt `completed`, lượt reconcile thứ hai trả `0`.

## Lệnh thật và kết quả

- Ruff trên 5 tệp sửa: **PASS** (0 lỗi; đã chạy trước batch test).
- `uv run --project backendV1 python backendV1/scripts/run_isolated_tests.py tests/integration/test_publication_index_sync_878.py tests/integration/test_ocr_safety_643.py -q` → **23 passed / 124,06 giây**, exit 0; DB `qnu_v1_test_6a2e8dfd8be540af` tự dọn, sentinel giữ.
- `uv run --project backendV1 python backendV1/scripts/run_isolated_tests.py tests/integration/test_ocr_text_review_651.py tests/integration/test_ocr_context_review_801.py tests/integration/test_ocr_regressions_643.py tests/integration/test_ocr_queue_transport_644.py tests/integration/test_index_api_647.py tests/unit/test_worker_model_timeout_819.py -q` → **73 passed / 371,26 giây**, exit 0; DB `qnu_v1_test_768a0677e6a14509` tự dọn, sentinel giữ.
- DB nháp `qnu_v1_test_worker_fix` tạo thủ công trước khi dùng harness đã được xóa; DB ứng dụng không bị chạm.
- Full Pytest cô lập: **NOT RUN**. Baseline lịch sử **FAIL 4/1627** (phiên 928) giữ riêng, không chạy lại. Không E2E lại dịch vụ thật trong phiên này.

## Rủi ro còn lại

- Worker chết cứng giữa lượt soát: lượt cha `running` chỉ được đánh `uncertain`/`ocr_spelling_interrupted` khi có người đọc (`readable_check`), hạn `expires_at` 24 giờ theo timeout job. Chưa sửa; reconcile không tạo lượt mới khi đã có bản ghi cha.
- Index snapshot cũ vẫn `failed` — có chủ đích, không đổi.
- F13 và chất lượng OCR/chính tả trên dữ liệu thật vẫn mở.
- Chưa commit/push; mọi thay đổi nằm trong working tree cùng các thay đổi sẵn có của người dùng.

## E2E thật sau sửa (2026-11-11, collection `col_b4bb8dbc0dd5`)

- Khởi động lại ARQ worker lúc 20:47:57 để nạp mã mới: 27 hàm, có `spelling_reconcile` và `cron:spelling_reconcile`; health key TTL 3599.
- Upload PDF NQ57 9 trang vào collection mới trong workspace `ws_686011c2a0af`: source `src_ec30cbcef5d5`, revision `rev_6a21da91c4fd`, OCR `ocr_45a2c59c23cb` **completed 9/9 trang ~20 giây**; lượt soát tự động `spl_6dac4ed29cc1` được tạo ngay, `completed` version 0 với **7 gợi ý + 2 cần dò**, đúng một lượt soát (không trùng).
- Duyệt chính tả: áp dụng 6 đoạn sửa từ 7 gợi ý, bỏ qua 2 cần dò bằng disposition, lưu kèm `review_check_id` → văn bản version 1 `txt_e9d256c761df` (sha `6d968bcd...ab258c`), check ghi `reviewed_version=1`.
- Chuẩn bị source-first `cmp_86fc0c1f4acd` completed 5 giây; đăng ký `cdoc_dee25eebd787`/`cver_f3f35da2f42b` (bundle `bf1f0ef8...95a4ce`); duyệt `pdec_b7dbc770c22d`; xuất bản `pdec_f326eaaf3a58`.
- Index tự động: chỉ một run `idx_5fbf138c7625` generation 1, dispatch sau publish ~2 giây, **completed + active sau ~20 giây**, **119 chunk**, `attempt_count=1`, không lỗi, manifest `3e9837cf...92a83c1`; readiness `ready` revision 1.
- Kiểm tra vector: search dense trả 5 hit, tất cả mang `cver_f3f35da2f42b` (đúng phiên bản đã xuất bản), top hit chứa chỉ tiêu 5800/1600. Tổng thời gian pipeline 70,1 giây + verify 0,9 giây; báo cáo `%TEMP%\qnu_e2e_936_report.json`.
- Lỗi trong lần chạy đầu là assertion của chính script E2E (so `version_id` của hit với mã bản văn OCR `txt_...` thay vì mã phiên bản đã đăng ký `cver_...`), không phải lỗi sản phẩm; đã sửa assertion và chạy lại bước verify PASS.
- Chất lượng: top hit vẫn còn lỗi OCR chưa được gợi ý (`TUYỄN SINH`), nên E2E chứng minh đường ống, không chứng minh văn bản sạch toàn văn; F13 không đổi.
