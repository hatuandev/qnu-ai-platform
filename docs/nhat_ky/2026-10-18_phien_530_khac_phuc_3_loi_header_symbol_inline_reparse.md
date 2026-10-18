# Phiên 530 — Khắc phục 3 lỗi Header làm mất dòng dữ liệu, Chú thích ký hiệu vượt phạm vi, và Inline Job bị Worker tự nhận

## Bối cảnh và yêu cầu

Người dùng ủy quyền triển khai độc lập toàn bộ 3 lỗi tồn đọng sau phiên 529:
1. **Lỗi 1 (P1) — Header làm mất dòng dữ liệu**: `pdf_tables.native_table` tin `header.names == matrix[0]`, làm `table_blocks` bỏ các dòng đầu. Trên artifact thật: `ks_rev_7b9dc0ce1a6a` trang 6 dòng 42 Logistics/7510605; `ks_rev_4a8c28996473` trang 2 dòng 17 Quản trị kinh doanh/7340101 và trang 3 dòng 43 Ngôn ngữ Anh/7220201 bị làm header. `_propose_header` trong `pdf_structure.py` cũng suy dòng đầu thành header chỉ vì native text lặp lại (bảng synthetic `001/12, 002/15` mất `001`).
2. **Lỗi 2 (P2) — Chú thích ký hiệu vượt phạm vi**: `pdf_structure._symbol_legends` dùng `setdefault(symbol, first_definition)` toàn tài liệu, `table_blocks` resolve mọi ô theo định nghĩa đầu (ví dụ: trang 1 dấu "–" là "không xét tuyển", trang 2 là "chưa có dữ liệu" nhưng nhận nghĩa trang 1). Cần phạm vi trang/bảng, giữ candidate definitions, chỉ resolved khi có canonical block thật và context_refs đúng; giữ positive case bảng nhiều trang chia sẻ chú thích duy nhất.
3. **Lỗi 3 (P2) — Inline job bị worker tự nhận**: `queue_reparse(dispatch=False)` chỉ bỏ enqueue trực tiếp nhưng job vẫn queued/pending và commit trước inline acquisition. `JobsService.reconcile_pending_dispatches` tự quét và gửi lại broker, worker cũ có thể thắng lease. Cần trạng thái tối thiểu phân biệt inline reservation khỏi broker retry, cơ chế recovery tôn trọng, không thêm schema/worker.

## Thay đổi mã nguồn

### 1. Header và bảo toàn dòng dữ liệu (`pdf_tables.py`, `pdf_structure.py`)
- `pdf_tables.py`: Bổ sung hàm heuristic cấu trúc và ngôn ngữ tổng quát `is_likely_data_row(row, next_row)` và `is_verified_header(row, next_row)`.
  - Nhận diện dòng dữ liệu: không có ký tự chữ (toàn số/ký hiệu), số thứ tự tăng dần ở cột 0 ($N \to N+1$), số thứ tự $> 1$ không kèm nhãn, mẫu số thập phân/điểm số (`\d+[.,]\d+`), định dạng ngày tháng, mã định danh dài ($\ge 4$ số), hoặc mẫu cột đồng dạng với dòng tiếp theo.
  - Nhận diện header chuẩn: không phải data row, độ dài nhãn hợp lý, chứa ký tự chữ mô tả khái niệm ngữ nghĩa.
  - `native_table()`: Chỉ thiết lập `depth = 1` (hoặc `proposed_header_depth > 1`) khi dòng 0 được xác minh là header. Dòng chưa xác minh hoặc là data row được giữ nguyên với `depth = 0`, gắn cờ `table_header_unresolved`, bảo toàn 100% dòng dữ liệu và giá trị thô, leading zeros, số 0/trống.
- `pdf_structure.py`: Cập nhật `_propose_header()` kiểm tra `is_likely_data_row` và `is_verified_header` trước khi xét sự lặp lại lớp chữ gốc. Ngăn chặn việc nuốt dòng dữ liệu số (như `001/12`).

### 2. Định nghĩa ký hiệu theo phạm vi (`pdf_structure.py`, `pdf_tables.py`)
- `pdf_structure.py`:
  - `_symbol_legends()` trả về `(page_legends, all_legends)`: thu thập định nghĩa theo từng trang cụ thể và danh sách candidate toàn tài liệu.
  - Trong `build_pdf_document()`: Áp dụng định nghĩa cục bộ của trang trước. Đối với trang không có định nghĩa cục bộ, nếu toàn tài liệu chỉ có duy nhất 1 định nghĩa cho ký hiệu đó (positive case bảng nhiều trang nối tiếp), cho phép áp dụng; nếu có nhiều định nghĩa xung đột giữa các trang, không tự suy diễn mà để unresolved/ambiguous.
  - `_link_symbol_legends()`: Duyệt qua `symbol_definitions` của từng block. Chỉ đánh dấu `present` và `resolved` khi tìm thấy canonical block thực sự chứa định nghĩa trong tài liệu và bổ sung vào `context_refs` cùng `related_block_ids`. Nếu không tìm thấy canonical block, chuyển trạng thái ô sang `ambiguous` và gắn cờ `ambiguous_cell`.

### 3. Phân lập Inline Job (`source_reparse.py`, `workers/tasks.py`)
- `source_reparse.py`: Trong `queue_reparse()`, khi `dispatch=False`, thiết lập `job.dispatch_status = "inline"` và `job.phase = "inline_reserved"`.
- `jobs/service.py`: `reconcile_pending_dispatches` vốn lọc `dispatch_status == "pending"`, do đó tự động bỏ qua các inline reservation.
- `workers/tasks.py`: Trong `task_knowledge_source_reparse()`, kiểm tra nếu tác vụ được gọi từ ARQ worker (`"job_try" in ctx`) mà `job.dispatch_status in ("inline", "inline_running")`, worker sẽ bỏ qua (`status: "skipped"`). Nếu được gọi inline từ script/operator (`"job_try" not in ctx`), tác vụ chuyển `dispatch_status = "inline_running"` và thực thi an toàn.

## Kết quả kiểm chứng

1. **Regression ban đầu (TDD)**:
   - Viết 4 bài test tái hiện cả 3 lỗi trong `backend/tests/test_qnu_pdf_markdown.py`.
   - Chạy trước khi sửa: **4 FAILED / 29 PASSED** (Exit code: 1).
2. **Kiểm thử hồi quy trọng tâm sau khi sửa**:
   - `test_qnu_pdf_markdown.py`: **33 passed** (Exit code: 0).
   - Core focused suite (`test_qnu_pdf_markdown.py`, `test_studio_revision_safety.py`, `test_qnu_serving.py`): **63 passed** (Exit code: 0).
   - Extended parser/review suite (`test_qnu_docx_markdown.py`, `test_native_table_review.py`...): **118 passed + 23 subtests passed** (Exit code: 0).
   - Jobs & Workers suite (`test_jobs.py`, `test_workers.py`): **27 passed** (Exit code: 0).
3. **Đối soát artifact thực qua script read-only `check_real_header_rows.py`**:
   - Lệnh: `python .antigravity-bridge/validation/check_real_header_rows.py` (Exit code: 0).
   - Cả 3 dòng dữ liệu thật đều được bảo toàn thành `table_row`:
     - `ks_rev_7b9dc0ce1a6a`, trang 6, row_key "42": `data_row_matches: 1, passed: true`
     - `ks_rev_4a8c28996473`, trang 2, row_key "17": `data_row_matches: 1, passed: true`
     - `ks_rev_4a8c28996473`, trang 3, row_key "43": `data_row_matches: 1, passed: true`
4. **Kiểm tra cú pháp và linter**:
   - `ruff check`: Scoped 5 files thay đổi: **All checks passed!** (Exit code: 0).
5. **Full backend suite (chạy một lần cuối batch, môi trường cô lập)**:
   - Lệnh: `python.exe -m pytest -q --basetemp=storage/pytest-basetemp-529`
   - Kết quả: **13 failed / 2049 passed / 17 skipped / 23 subtests passed in 197.61s**.
   - Khớp chính xác 13 failed IDs của baseline phiên 529 và 528 (11 lỗi nền API/canary/reconciliation + 2 tool tests đọc fact cũ đã purge). Số lượng test passed tăng từ 2044 lên 2049 nhờ các regression test mới. Giữ trung thực trạng thái FAIL cho full suite.

## Điều chỉnh sau Independent Review (Guidance marker: attempt-d9035e32-2920-4e84-bb70-ff6da709829e)
- **P1**: Xóa bỏ hoàn toàn vá từ điển (`_HEADER_DESCRIPTORS`), chỉ dùng bằng chứng cấu trúc/hình học (`_has_structural_header_evidence`). Khi không chắc chắn giữ `header_depth = 0`, bảo toàn 100% dòng dữ liệu thô, ô trống/0, leading zeros và merged origins, gán cờ `table_header_unresolved`.
- **P2**: `_symbol_legends` thu thập theo từng trang và candidate toàn tài liệu; chuẩn hóa Unicode NFC; cùng trang duplicate cùng nghĩa giải quyết, khác nghĩa giữ `ambiguous`; bảng độc lập khác trang không liên quan không leak; chỉ bảng tiếp nối trang có bằng chứng hình học (`_is_table_continuation`) và tài liệu có nghĩa duy nhất mới kế thừa; `_link_symbol_legends` chỉ resolve khi tìm thấy canonical block thật.
- **Regression Gap**: Kiểm thử reconciliation bổ sung `QuerySensitiveFakeSession` xác thực trực tiếp mệnh đề SQL `JobRecord.dispatch_status == "pending"` và patch đúng `app.modules.jobs.service.enqueue_arq_job`, kiểm chứng retry thành công job broker-failed và không đụng vào inline job.
- **Kiểm chứng điều chỉnh**: Scoped Ruff all checks passed; 108 tests focused passed (test_qnu_pdf_markdown 39 passed, core 69 passed); `check_real_header_rows.py` 3/3 passed; báo cáo tại `.antigravity-bridge/validation/gemini-three-fixes-correction-result.md` và `.antigravity-bridge/validation/gemini-three-fixes-correction-completion.json`.

## Điều chỉnh sau Correction Review cuối cùng (Correction marker: attempt-6dfe4fdc-14ba-4015-9d3e-8c8a2539aa58)
- **P1 (Native Table)**: Khắc phục sự lặp lại bằng chứng vòng (circular evidence) ở `header.bbox` trong `_has_structural_header_evidence`. Loại bỏ kiểm tra bbox đơn thuần; yêu cầu phân tách tọa độ vật lý thực sự (`min(body_y_mins) - header_box[3] >= 2.0`), bất tương xứng cell span hoặc multi-level geometry. Bảng văn bản lưới liền kề (`Alpha, North` và `Beta, South`) không có bằng chứng độc lập trả về `header_depth = 0`, không nuốt dòng dữ liệu đầu. Thêm regression `test_native_table_engine_bbox_alone_does_not_prove_header_role_without_separation`.
- **P1 (OCR Table)**: Trong `_propose_header`, tách biệt bằng chứng đối chiếu văn bản gốc (transcription corroboration) khỏi vai trò ngữ nghĩa (header role). Đề xuất header được lưu trong `header_proposal` và gắn cờ `native_header_needs_review`, nhưng KHÔNG tự ý nâng `header_depth = 1` trừ khi dòng tiếp theo có bằng chứng dữ liệu thân bảng rõ ràng (`is_likely_data_row`). Dòng chưa xác minh được giữ nguyên làm `table_row`, gán cờ `table_header_unresolved`. Thêm regression end-to-end `test_ocr_native_agreement_preserves_unverified_row_end_to_end_in_builder`.
- **P2 (Table-level Scope & Nối trang)**:
  - Thiết lập phạm vi chú thích ký hiệu ở cấp bảng thông qua `_collect_page_legends` và `_find_table_legends`. Thẩm định quan hệ không gian kề cận bên dưới (`table_y1 - 2 <= legend_y0 <= table_y1 + 25`), giao thoa phương ngang, không có bảng xen giữa và gần nhất duy nhất. Hai bảng độc lập trên cùng trang: Bảng 1 có chú thích giải quyết thành công, Bảng 2 giữ nguyên `ambiguous` với cờ `ambiguous_cell`, không rò rỉ chú thích. Thêm regression `test_symbol_legends_two_independent_same_page_tables_do_not_leak_legend`.
  - Căn lề biên và số cột qua trang được giữ nguyên là ứng viên nối trang (`table_continuation_needs_review`, `continuation_candidate`), không tự động phê duyệt nghĩa chung. Các ô ký hiệu ở trang tiếp nối giữ nguyên `ambiguous` chờ con người duyệt. Cập nhật regression `test_symbol_legends_continuation_candidate_preserves_evidence_but_keeps_symbols_ambiguous`.
- **Kiểm chứng cuối cùng**: Scoped Ruff all checks passed (0 errors); Focused suite 117 tests passed (exit 0); `check_real_header_rows.py` 3/3 passed; báo cáo tại `.antigravity-bridge/validation/gemini-correction-final-result.md` và `.antigravity-bridge/validation/gemini-correction-final-completion.json`.

## Điều chỉnh sau Independent Review của Gemini Correction (Review marker: attempt-2d064146-f004-47cb-b520-b4d39f99227c)

- **P1 (Header Role — Loại bỏ triệt để đường tắt dòng tiếp theo là số)**:
  - Khắc phục shortcut trong `native_table` (`pdf_tables.py`) và `_propose_header` (`pdf_structure.py`) coi việc dòng 1 có số liệu (`is_likely_data_row(row1)`) là bằng chứng gián tiếp chứng minh dòng 0 là header.
  - Ma trận hỗn hợp dữ liệu `[['Alpha', 'North'], ['2', 'South']]` không có bằng chứng cấu trúc/hình học độc lập bắt buộc trả về `header_depth = 0`, bảo toàn 100% bản ghi dữ liệu (cả hai dòng đều tạo ra `table_row`).
  - Trong `_propose_header`, sự đối chiếu lặp lại với lớp text số hóa chỉ được lưu vào `table["header_proposal"]` (kèm cờ `native_header_needs_review`) để người dùng/hệ thống xem xét; tuyệt đối không tự nâng `header_depth = 1` cho bảng OCR HTML không có thẻ `<th>`.
  - Bổ sung 2 regression test: `test_native_table_mixed_numeric_row1_does_not_consume_row0_without_independent_evidence` và `test_ocr_table_mixed_numeric_row1_does_not_consume_row0_in_full_builder`.

- **P2 (Table Legend Scope — Abstain khi hòa khoảng cách giữa các bảng)**:
  - Trong `_find_table_legends` (`pdf_structure.py`), lọc các bảng thỏa mãn hình học (`_is_table_geometrically_applicable`: nằm phía trên legend, giao thoa phương ngang).
  - Yêu cầu chiến thắng duy nhất: đo khoảng cách thẳng đứng đến tất cả bảng phù hợp; nếu có hơn 1 bảng gần nhất bằng nhau (tie - ví dụ hai bảng nằm ngang cạnh nhau chia sẻ một legend toàn chiều rộng phía dưới), hàm từ chối gán (abstain), giữ cả 2 bảng ở trạng thái `ambiguous` với cờ `ambiguous_cell`.
  - Bảng ở cột khác (không giao thoa phương ngang) không làm nhiễu liên kết của bảng kề cận thực sự.
  - Bổ sung 3 regression test: `test_symbol_legends_side_by_side_tables_shared_legend_tie_abstains`, `test_symbol_legends_positive_uniquely_adjacent_table_resolves`, và `test_symbol_legends_nearby_table_in_another_column_does_not_interfere`.

- **Kiểm chứng cuối cùng**:
  - Scoped Ruff: All checks passed (0 errors).
  - Focused test suite: 122 passed, 23 subtests passed (exit 0).
  - `check_real_header_rows.py`: 3/3 passed (rows 42, 17, 43).
  - Báo cáo tại `.antigravity-bridge/validation/gemini-monitor-feedback-1-result.md` và `.antigravity-bridge/validation/gemini-monitor-feedback-1-completion.json`.

## Giới hạn và NOT RUN
- NOT RUN: Không commit, không push git, không sửa live DB/artifacts; không reparse toàn bộ kho, approve, index hay publish lên production; không benchmark 12/20/82 câu hỏi; không thay đổi model/prompt hay Top K.

- Code hoàn tất sẵn sàng bàn giao để Codex review.


