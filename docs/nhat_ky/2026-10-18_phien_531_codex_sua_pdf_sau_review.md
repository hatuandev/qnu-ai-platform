# Phiên 531 — Codex trực tiếp sửa các lỗi PDF còn lại

Ngày: 2026-10-18. Theo yêu cầu mới, dừng monitor Gemini mỗi 5 phút và chuyển việc sửa mã cho Codex. Ngoại lệ này thay thế giới hạn trước đó chỉ review/giao Gemini sửa. Automation `review-khi-gemini-s-a-pdf-xong` đã PAUSED; phiên Gemini được xác minh và dừng, lúc kiểm tra không còn chạy.

## Nguyên nhân và cách sửa

- `backend/app/modules/knowledge/parsers/pdf_tables.py`: bỏ suy vai trò header từ nội dung hàng, ô gộp ở body, khoảng cách bbox hoặc `proposed_header_depth`. Các dữ kiện đó là đề xuất của engine, không chứng minh hàng đầu là header. Giữ toàn bộ matrix ở `header_depth=0`, lưu `header_proposal` và cờ unresolved. Header external không lấy hàng dữ liệu khỏi matrix; header HTML `<th>` nhiều tầng/năm và separator Markdown vẫn hoạt động. Không dùng từ điển header viết tay.
- `backend/app/modules/knowledge/parsers/pdf_structure.py`: native text trùng OCR chỉ đề xuất transcription, không loại hàng. Giữ chú thích trùng chữ ở những locator khác nhau; nối `context_refs` và `related_block_ids` bằng page + locator của candidate đã chọn, bắt buộc có đúng một block canonical phù hợp. Thiếu/trùng/sai nguồn giữ ô ambiguous và lưu candidate. Bảng ở cột khác không chặn hành lang liên kết table–legend.
- Giữ sửa inline job có sẵn ở `source_reparse.py` và `workers/tasks.py`: inline reservation khác pending, reconciler không enqueue inline, ARQ bỏ qua reservation. Đã đọc và kiểm thử lại; không thêm sửa ứng dụng ở hai file này trong lượt Codex.
- Thêm `backend/tests/test_pdf_review_regressions.py`: 11 ca regression qua builder và bước nối canonical; chỉnh ba test cũ đang coi engine proposal là bằng chứng header hoặc phụ thuộc vị trí hàng đã bị loại. Vẫn kiểm giá trị, origin, bbox và raw matrix.

## Kiểm chứng thực chạy

Cwd cho lệnh Python/Ruff bên dưới: `backend`; dùng môi trường `.venv` hiện có (Python 3.12.13), không cài dependency hay đổi cấu hình.

| Kiểm tra | Lệnh / kết quả |
|---|---|
| Tái hiện trước sửa | `.venv/Scripts/python.exe -m pytest -q tests/test_pdf_review_regressions.py --basetemp=storage/fix531-red` → **6 failed, 1 passed**, exit 1; đúng lỗi nuốt hàng/liên kết chú thích |
| Sau sửa, vòng đầu | PDF + regression mới → **3 failed, 51 passed**, exit 1; ba test cũ còn đòi engine proposal trở thành header, được đổi theo hợp đồng bảo toàn hàng nêu trên |
| Focused cuối | `.venv/Scripts/python.exe -m pytest -q tests/test_pdf_review_regressions.py tests/test_qnu_pdf_markdown.py tests/test_studio_revision_safety.py tests/test_qnu_serving.py tests/test_jobs.py tests/test_workers.py --basetemp=storage/fix531-focused2` → **115 passed**, exit 0 |
| Scoped Ruff | `.venv/Scripts/ruff.exe check app/modules/knowledge/parsers/pdf_tables.py app/modules/knowledge/parsers/pdf_structure.py app/modules/knowledge/services/source_reparse.py app/workers/tasks.py tests/test_qnu_pdf_markdown.py tests/test_pdf_review_regressions.py` → **PASS**, exit 0 |
| Dữ liệu lưu sẵn, chỉ đọc | `.venv/Scripts/python.exe ../.antigravity-bridge/validation/check_real_header_rows.py` → **3/3 PASS**, exit 0; kiểm hash raw, dựng trong RAM, các dòng 42/17/43 xuất hiện đúng một lần; transaction READ ONLY |
| Full backend một lần | `.venv/Scripts/python.exe -m pytest -q --basetemp=storage/fix531-full --junitxml=storage/fix531-full-results.xml` → **FAIL: 13 failed, 2074 passed, 17 skipped, 23 subtests passed**, exit 1, 226.46 giây |

Full log: `backend/storage/fix531-full.log`; XML: `backend/storage/fix531-full-results.xml` (artifact local bị ignore). Đối chiếu tự động tập exact test IDs trong XML với baseline phiên529: 13/13 khớp, `new_failures=[]`, `missing_baseline=[]`, exit 0. Không coi suite có lỗi nền là PASS.

13 test còn lỗi:

```text
tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export
tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export
tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint
tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit
tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback
tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies
tests/test_tools.py::test_fact_layer_lookup_tool_found
tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims
tests/test_universal_tools.py::test_fact_layer_lookup_tool
tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts
```

## Giới hạn bàn giao

Các regression trong phạm vi đã đạt. Cách xử lý native header cố ý bảo thủ: giữ cả hàng có thể là header và yêu cầu đối soát thay vì đoán rồi mất dữ liệu. Không chứng minh OCR provider thật hoặc mọi tài liệu đều chính xác. Không reparse/ghi artifact nguồn/duyệt PDF cũ, không index/publish/restart/deploy/config/model changes. Không commit/push/stage/reset, không bỏ theo dõi hay dọn các artifact tracked. Giữ nguyên phần sửa chưa commit của người dùng/Gemini ngoài phạm vi trực tiếp.

NOT RUN: reparse thực, duyệt/xuất bản năm PDF cũ, retrieval/chat/UI/live OCR sau sửa. Chưa có kết luận bộ backend hoàn toàn xanh; 13 lỗi nền ở trên còn tồn tại.
