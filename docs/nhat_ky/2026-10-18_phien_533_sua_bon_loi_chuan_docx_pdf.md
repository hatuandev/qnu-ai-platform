# Phiên 533 — Sửa bốn lỗi tuân thủ chuẩn DOCX/PDF

Ngày: 2026-10-18. Người dùng giao sửa bốn finding của [review532](./2026-10-18_phien_532_review_chuan_docx_pdf.md). Giữ nguyên phần sửa đang có; không thay đổi dữ liệu nguồn hay phê duyệt các PDF cũ.

## Thay đổi

1. **F1 — Mapping trang DOCX:** `docling_structure.py` dùng matcher toàn đơn vị, tiến một chiều, cho cả heading/đoạn/code/công thức/chú thích thay đường 12 token đầu. Đơn vị trải trang giữ đủ locations; trùng ở nhiều trang, khoảng hở hoặc nội dung không thể ghim giữ page null và cờ `page_unresolved`. Trạng thái mapping không còn aligned khi còn đơn vị chưa định vị. Mỗi hàng bảng được map đúng một lần; GFM chỉ chia sẻ vị trí khi mọi hàng cùng một trang đã biết. Bảng qua trang/không chắc chuyển sang records để mỗi hàng giữ trang và locator riêng. Không có preview thì vẫn giữ locator DOCX và trạng thái pagination unavailable.
2. **F2 — Vai trò hàng:** bỏ suy mọi ô phủ ngang là note. Bảng một cột giữ các hàng/field, kể cả 0. Ô gộp toàn hàng của bảng nhiều cột vẫn là table_row, giữ field_origins và raw cells, gắn `spanning_row_unclassified`/`spanning_row_needs_review`. Không dùng từ khóa “Ghi chú” để tự xác nhận vai trò.
3. **F3 — Phạm vi chú thích:** `qnu_projection.py` chỉ lấy refs khai báo rõ trên row hoặc table; không tự mở rộng mọi note con sang mọi row. Note không có liên kết phạm vi vẫn là unit riêng và sinh issue `table_note_scope_unresolved`; không bị xóa hay biến thành một hàng được đếm. Refs rõ ở row/table và chiều phụ thuộc được giữ.
4. **F4 — Gate cấu trúc:** `qnu_markdown.py` kiểm representation, GFM header/separator/width và header khớp columns, kiểu header_path, quality-flag status/detail, yêu cầu cảnh báo khi không có vị trí nguồn thực (cả `[]` và location rỗng). Page boolean bị từ chối. Validator và projection dùng chung `parse_qnu_gfm_table`, giữ escaped pipe, ô 0/trống và header nhiều tầng. GFM hỏng bị chặn trước StorageDriver writes; vị trí chưa biết có cảnh báo hợp lệ vẫn được lưu để đối soát. Derived index giữ ngoại lệ không có nguồn trực tiếp theo chuẩn.

File ứng dụng sửa: `backend/app/modules/knowledge/parsers/docling_structure.py`, `backend/app/modules/knowledge/normalization/qnu_markdown.py`, `backend/app/modules/knowledge/normalization/qnu_projection.py`.

Test mới `backend/tests/test_qnu_standard_regressions.py` có 26 ca cuối cùng. Một assertion cũ trong `test_qnu_docx_markdown.py` được đổi từ tự phân loại ô gộp thành note sang giữ đủ bốn field/role chưa xác định/cờ đối soát; vẫn kiểm số 0, mã có 0 đầu, ô trống và quan hệ bảng.

## Kiểm chứng thực chạy

Lệnh Python/Ruff dùng cwd `backend`, môi trường `.venv` hiện có; không cài gói hay đổi cấu hình.

| Kiểm tra | Kết quả |
|---|---|
| TDD trước sửa | `.venv/Scripts/python.exe -m pytest -q tests/test_qnu_standard_regressions.py --basetemp=storage/fix533-red` → **15 failed, 4 passed**, exit 1; đúng bốn nguyên nhân đã review |
| Focused cuối | `.venv/Scripts/python.exe -m pytest -q tests/test_qnu_standard_regressions.py tests/test_qnu_docx_markdown.py tests/test_qnu_pdf_markdown.py tests/test_qnu_serving.py tests/test_qnu_standard_integration.py tests/test_pdf_review_regressions.py tests/test_studio_revision_safety.py tests/test_document_revisions_lifecycle.py --basetemp=storage/fix533-focus-complete --junitxml=storage/fix533-focus-complete.xml` → **164 passed, 23 subtests passed**, exit 0, 11.40 giây |
| Ruff | `.venv/Scripts/ruff.exe check app/modules/knowledge/parsers/docling_structure.py app/modules/knowledge/normalization/qnu_markdown.py app/modules/knowledge/normalization/qnu_projection.py tests/test_qnu_standard_regressions.py tests/test_qnu_docx_markdown.py` → **PASS**, exit 0 |
| Tương thích tệp lưu sẵn | Chạy `.antigravity-bridge/validation/review-standard-532-stored.py` bằng Python backend từ root, transaction **READ ONLY** → **6/6 latest pairs valid**, exit 0; năm PDF vẫn review_required, không active. Hash raw và ba dòng PDF42/17/43 rebuild trong RAM vẫn đạt, không ghi nguồn |
| Full backend cuối | `.venv/Scripts/python.exe -m pytest -q --basetemp=storage/fix533-full-final --junitxml=storage/fix533-full-final.xml` → **FAIL: 13 failed, 2100 passed, 17 skipped, 23 subtests passed**, exit 1, 203.06 giây |

Log focused: `backend/storage/fix533-focus-complete.log`; log đọc tệp: `backend/storage/fix533-stored-final.log`. Full dùng `--basetemp=storage/fix533-full-final --junitxml=storage/fix533-full-final.xml`, stdout/stderr ở `backend/storage/fix533-full-final.log`. Một lượt full ban đầu đã **INTERRUPTED** bằng Ctrl+C để bổ sung biến thể location rỗng; không dùng lượt chưa hoàn thành đó làm kết quả nghiệm thu.

Đối chiếu tự động exact test IDs từ XML với baseline phiên529: **13/13 khớp**, `new_failures=[]`, `missing_baseline=[]`, exit 0. Bộ backend tổng thể vẫn FAIL; không đổi assertion hay chèn fact để che lỗi nền. Các ID còn lỗi:

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

Tự review diff, scoped Ruff, UTF-8 không BOM/LF và diff whitespace đã đạt cho mã/test. Không có finding còn mở trong bốn hành vi được giao sau kiểm thử; giới hạn dữ liệu thật bên dưới vẫn áp dụng.

## Giới hạn

Bốn hành vi có regression đạt; chưa chứng nhận mọi nội dung DOCX/PDF hoặc mọi nhánh của chuẩn đều đúng. Mapping được kiểm qua DOCX thật tạo trong RAM/Docling và projection có page ranges biết trước; chưa render Word mới hay nghiệm thu OCR provider thật. Đọc pair/checksum chỉ chứng minh toàn vẹn/danh tính, không xác nhận nội dung OCR.

Các revision cũ không tự được thay bằng code mới. Năm PDF vẫn cần xử lý/đối soát và duyệt riêng; chưa reparse, ghi artifact nguồn, index, publish hoặc chuyển active. Không commit/push/stage/reset/dọn tracked files, restart/deploy, sửa config/model/provider. Monitor Gemini vẫn paused.
