# Phiên 529 — Xử lý nguyên nhân khiến 5 PDF còn cảnh báo khi chuyển sang QNU RAG Markdown v1.0

## Quyền và phạm vi

Nhiệm vụ do người dùng giao: phân loại nguyên nhân theo bằng chứng thật, sửa parser
ở gốc theo ưu tiên 5 tài liệu đã liệt kê, chỉ reparse nguồn bị ảnh hưởng, tạo bản
sạch **chờ duyệt**, và chỉ nạp vector/xuất bản đúng revision được duyệt cụ thể.
Giữ nguyên mọi thay đổi chưa commit của các phiên trước; **không sửa và không xuất
bản lại DOCX** `ks_rev_0c1e98ac424b` (đã duyệt, đã publish `idx_rev_c482a9e11451`).
Không restart worker, không migration, không đổi config/prompt/model/Top K, không
commit/push, không xóa kho, không benchmark 12/20/82 câu.

## Nguyên nhân phân loại theo bằng chứng

Đọc MD/JSON chuẩn đã lưu qua StorageDriver, raw PDF evidence, ảnh trang gốc và so
sánh với bytes PDF; không dump raw OCR vào log/docs.

| Nhóm | Bằng chứng | Kết luận |
|---|---|---|
| Nền bảng bị coi là "vùng hình chưa phiên âm" | `ks_rev_c041d878ae7e` 420 figure blocks, `ks_rev_faf36025f7ab` 502, trong khi nguồn có 2467/1743 nét kẻ | **Lỗi parser**: `intersection_fraction(box, target)` chia cho diện tích đối số đầu, một nét kẻ mảnh hoặc chấm giao điểm bị coi là vùng nội dung |
| Ô gạch ngang bị gắn cờ `ambiguous` | 30 ô của điểm sàn nằm cạnh chú thích `Ký hiệu "–": Trường không xét tuyển theo phương thức tương ứng đối với ngành này.` | **Không phải lỗi OCR**: ký hiệu có nghĩa, parser thiếu liên kết ký hiệu–chú thích |
| Bảng native bị hàng OCR thay thế | scan ngành 2025: 665 `ambiguous` + 268 `blank`, chỉ 164 `present`, facts 0 | **Lỗi parser**: `_select_items` chọn theo số lượng item, không so độ đầy đủ ô nên mất lưới column |
| Tiêu đề nhiều tầng / bảng nối trang | 7 `native_header_needs_review`, 6 `table_continuation_needs_review`, 173 `MISSING_COLUMN_HEADER` ở điểm sàn | **Cần người duyệt**: parser không được tự đoán header; chỉ thêm căn cứ để reviewer quyết |
| Xung đột native/OCR thật | Poster ghi native `TUYỂN`, OCR `TUYỀN` | **Giữ cờ**, không sửa số/tên theo suy đoán |
| Vùng hình thật | 24 panel nền/khung ảnh/icon trên trang đồ họa 1644×4648.5pt, seal/photo/QR | **Giữ lại hợp lệ**, không phải lỗi |

Số trường bị gắn cờ của phiên 528 là số cờ, **không phải số lỗi số liệu**; con số
sau khi sửa cũng không tự chứng minh mọi header đã đúng.

## Thay đổi mã trong phiên

- `pdf_structure.py` (F1): `_is_grid_furniture` phân biệt nét kẻ/chấm giao điểm bằng
  hình học tổng quát (bề dày, tỉ lệ dài–rộng, ngưỡng `_HAIRLINE_POINT = 2.0` cho
  hình lấp đầy không có stroke width). Không hardcode theo tên tài liệu hay trang.
- `pdf_structure.py` (F2): `_native_spans`, `_overlap_ratio`, `_completeness` và
  nhánh so tài native-table — bảng thắng khi IoU ≥ 0.3 **và** độ đầy đủ ô cao hơn,
  không tính theo số item.
- `pdf_structure.py` (F3): `_symbol_legends` + `_link_symbol_legends` dựng điển
  ký hiệu từ chú thích in trong bảng và gắn `context_refs` cho ô dùng ký hiệu đó.
- `pdf_structure.py` + `pdf_tables.py` (F4): `_propose_header` và cờ
  `native_header_needs_review` mang theo căn cứ (đề mục native, đơn vị, phạm vi
  trang) cho reviewer; `UNRESOLVED_CELL_SYMBOLS` chỉ là dấu hiệu chờ điển ký hiệu,
  `cell_symbol_defined` chuyển ô sang `present` khi có chú thích xác nhận.
- `pdf_structure.py`: `document_meta["visual_classification"]` ghi ba số kiểm đếm
  được (`ruling_strokes_in_source`, `visual_regions_retained`,
  `symbol_legend_definitions`) để tái hiện quyết định mà không cần raw dump.
- `source_reparse.py`: `queue_reparse(..., *, dispatch: bool = True)`. Worker ARQ
  đang sống (j_complete=2035) chứa mã parser trước khi sửa; reparse phiên này dùng
  `dispatch=False` rồi gọi `task_knowledge_source_reparse` inline theo tập quán
  operator đã có ở `source_purge.py`. `PDF_STRUCTURE_VERSION` giữ nguyên vì nó đặt
  tên schema bằng chứng, không phải ngưỡng phân loại.
- Test: `test_qnu_pdf_markdown.py` thêm fixture nét kẻ lấp đầy (29 passed),
  `test_studio_revision_safety.py` thêm `test_operator_can_reserve_reparse_without_broker_dispatch` (9 passed).

## Kết quả tái sinh (chỉ nguồn bị ảnh hưởng)

Chạy qua `queue_reparse` + `execute_reparse` thật, artifact mới đặt tên theo hash;
revision cũ giữ nguyên bytes và vẫn `review_required` (không có cơ chế đánh dấu
superseded cho bản chưa từng publish). `verify_reparse_529.py` xác minh
pair/checksum/snapshot/origin hash cho cả 5 cặp: **pair_valid true cả 5**.

| Nguồn | Revision cũ → mới | Kết quả đo |
|---|---|---|
| Cac nganh Tuyen sinh 2025_moi.pdf | ks_rev_a6a7a50d2bb0 → **ks_rev_1ba8a04f5ee4** | 152→83 blocks, 1 bảng 52 dòng; states {ambiguous 665, blank 268, present 164} → {present 156}; unresolved cells 0; facts 0→52; giữ 51/51 mã ngành 7 chữ số; khác biệt token số duy nhất là "2025" từng bị in đôi |
| TB điểm sàn 26.pdf | ks_rev_faf36025f7ab → **ks_rev_7b9dc0ce1a6a** | 586→87 blocks, figure 502→3; 30 ô "–" → `present` với `cell_symbol_defined` (resolved) và `context_refs=["p0008_b0005"]`; facts 49→57; còn 173 MISSING_COLUMN_HEADER, 7 native_header, 6 continuation, 1 TABLE_HEADER_UNRESOLVED, 1 AMBIGUOUS_COLUMN_CONTEXT, 1 header_rescue |
| Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed.pdf | ks_rev_c041d878ae7e → ks_rev_8e5732f6fdf5 → **ks_rev_8db62cd3f358** | 528→115→114 blocks, figure 420→7→6 sau sửa nét kẻ lấp đầy; present 706 và facts 534 **không đổi**; ruling_strokes_in_source 2467 |
| TB học phí K49.pdf | ks_rev_bfe4b12cbf72 → **ks_rev_4a8c28996473** | 102→89 blocks, figure 16→3; present 540 và facts 128 **không đổi**; 502 nét kẻ |
| Hương dan thi Nang khieu GDTC 2026.pdf | **ks_rev_5ffe3662aee1** (giữ nguyên) | Không reparse: 43 blocks, 3 figure thật, 1 header_rescue, 0 facts — không có defect parser nào giải thích được cờ còn lại |

Bốn revision mới đều `review_required` theo `prepare_standard_revision`; **không có
index row nào, collection epoch vẫn 50**, nên chưa bản nào tới được RAG. Snapshot
`snapshots/migration-inventory` chưa thay đổi so với phiên 528.

## Còn chờ người duyệt

Cờ `unresolved` đọc lại từ artifact đã lưu của chính revision mới (định dạng
JSON chuẩn, không suy từ log):

| Revision | `unresolved` còn lại |
|---|---|
| ks_rev_1ba8a04f5ee4 (poster) | `visual_content_untranscribed` 24 (panel nền/khung ảnh/icon thật), `native_ocr_conflict` 2, `native_header_needs_review` 1 |
| ks_rev_7b9dc0ce1a6a (điểm sàn) | `visual_content_untranscribed` 3, `native_header_needs_review` 7, `table_continuation_needs_review` 6, `header_rescue_needs_review` 1; ở tầng canonical hoá: `MISSING_COLUMN_HEADER` 173, `TABLE_HEADER_UNRESOLVED` 1, `AMBIGUOUS_COLUMN_CONTEXT` 1 |
| ks_rev_8db62cd3f358 (quy đổi) | `visual_content_untranscribed` 6, `native_header_needs_review` 3, `heading_inferred_typography` 3, `table_continuation_needs_review` 1, `header_rescue_needs_review` 1 |
| ks_rev_4a8c28996473 (học phí) | `visual_content_untranscribed` 3, `native_header_needs_review` 3, `table_continuation_needs_review` 2, `heading_inferred_typography` 1, `header_rescue_needs_review` 1 |
| ks_rev_5ffe3662aee1 (GDTC, không reparse) | `visual_content_untranscribed` 3, `header_rescue_needs_review` 1 |

30 ô "–" của điểm sàn giờ mang cờ `cell_symbol_defined` trạng thái **resolved** —
giải thích bằng chú thích in trong nguồn, không phải gỡ cờ.

Một danh sách nhóm được gửi kèm báo cáo cuối phiên; không giả danh người duyệt và
không hỏi lại từng bước. Nội dung cần quyết: xung đột tiêu đề `TUYỀN/TUYỂN` trên
poster, **4** đề mục `header_rescue` do OCR vùng đầu (`Số: 121/TB-HDTS` + "Gia Lai,
ngày 09 tháng 7 năm 2026" ở điểm sàn; "ngày 11 tháng 7 năm 2026" ở quy đổi;
`Số: 2404/TB-ĐHQN` + "ngày 10 tháng 8 năm 2026" ở học phí K49; "ngày 16 tháng 6
năm 2026" ở GDTC), 7 `native_header` + 6 `table_continuation` + 173
`MISSING_COLUMN_HEADER` của điểm sàn, 4 cờ `heading_inferred_typography` (3 quy đổi,
1 học phí), và các
vùng hình đã giữ thật (seal, ảnh, QR, logo, panel nền). Đường dẫn hiệu đính được
hỗ trợ: `native_table_review.create_native_table_draft`.

## Kiểm chứng

- Ruff scoped 7 file thay đổi: **PASS**.
- Regression focused 11 file (`test_qnu_pdf_markdown`, `test_qnu_docx_markdown`,
  `test_pdf_*`, `test_studio_revision_safety`, `test_source_*` liên quan): **161
  passed + 23 subtests**, 21.70s. File mới: 29 passed / 9 passed.
- Full backend suite chạy **một lần** sau khi mã ổn định: cwd `backend`,
  `PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -m pytest -q
  --basetemp=storage/pytest-basetemp-529`, log `backend/storage/qnu529/full-suite-529.log`.
  **FAIL**, **13 failed / 2044 passed / 17 skipped / 23 subtests passed**, 204.16s.
  Exit code 0 chỉ do pipeline `| tee`; căn cứ là dòng tổng kết pytest.
- 13 ID khớp tập baseline phiên 528 (11 lỗi nền API/GC/canary/trust/reconciliation/
  dispatcher + 2 test fact-layer CNTT đọc fact thật của corpus đã purge):

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

Hai test fact-layer **không sửa** và **không chèn fact giả**; khuyến nghị bước sau
chuyển sang fixture cô lập kiểu `test_evidence_postgres.py` (`QNU_TEST_EVIDENCE_DB=1`),
vì sửa lúc này buộc chạy full suite lần hai ngoài phạm vi đã thỏa thuận.

## Giới hạn và NOT RUN

NOT RUN: 5 kiểm tra retrieval có đích (chờ duyệt), DB/Qdrant parity sau publish,
chat/UI, benchmark 12/20/82, Docker build, backup/restore. MD hợp lệ và pair hash
đạt **không** phải bằng chứng toàn RAG ổn định. Parser mới đã chạy trên toàn bộ 4
nguồn bị ảnh hưởng qua đường service, nhưng worker ARQ sống vẫn mang mã cũ; tiến
trình sau này phải inline hoặc chờ người dùng restart.

Script vận hành giữ lại để tái hiện (không phải mã production, theo thông lệ
`probe_*`/`standard_migration_*` của các phiên trước): `scripts/reparse_pdf_529.py`
(giữ revision với `dispatch=False` rồi chạy `task_knowledge_source_reparse` inline),
`scripts/verify_reparse_529.py` (đối soát read-only cặp revision, token số, field
state, unresolved), `scripts/list_revisions_529.py`, `scripts/inspect_pdf_flags_529.py`,
`scripts/analyze_figures_529.py`, `scripts/render_pdf_pages_529.py`,
`scripts/rebuild_from_evidence_529.py` (bê-ta thí điểm, không phải đường ghi chính
thức). Bêtạm: `backend/storage/qnu529/` và `backend/storage/pytest-basetemp-529*`.
