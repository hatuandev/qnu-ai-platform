# Phiên 523 — Sửa bốn lỗi DOCX → QNU RAG Markdown v1.0

## Yêu cầu và phạm vi

Batch code cho bốn lỗi do review độc lập chỉ ra trên đường DOCX → chuẩn
Markdown v1.0 (tiếp [phiên 522](./2026-10-17_phien_522_trien_khai_chuan_markdown_docx.md)
và [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md)):

1. Artifact MD cũ vẫn được trả về sau khi sửa revision (ưu tiên cao nhất).
2. Heading cùng cấp bị gán sai quan hệ cha–con.
3. Bảng/list nhiều trang bị gán toàn bộ về trang đầu.
4. Validator bỏ lọt field và origin không tồn tại.

Ràng buộc đã tuân thủ: chỉ fixture DOCX + storage/DB giả lập; không gọi
LLM/OCR/cloud; không reset/migration, không reparse dữ liệu thật, không reindex,
không xuất bản, không restart/deploy, không commit/push; MD chuẩn **vẫn là dẫn
xuất song song**, chưa chuyển RAG sang đọc; không sửa nguồn, không đoán trang,
không sửa test để hợp thức hóa dữ liệu sai; không chạy full suite mặc định hoặc
benchmark 82 câu (ngoại lệ do người dùng giao trong phiên, ghi ở mục Kiểm chứng).

## Nguyên nhân và cách sửa

### 1. Artifact MD cũ trả về sau hiệu đính revision

- Nguyên nhân: `update_revision_content` tạo revision mới bằng cách copy toàn bộ
  cột của revision cũ, nên `snapshot_metadata["qnu_markdown"]` và
  `parse_provenance["qnu_markdown"]` được thừa kế nguyên vẹn — vẫn `status: ready`,
  vẫn `revision_id` của bản cũ, vẫn trỏ file `.qnu-rag-v1.md` của bản cũ.
  `get_qnu_markdown_artifact` chỉ đọc key và router chỉ chặn khi status khác
  `ready`, nên endpoint tải phục vụ đúng nội dung bản cũ cho danh tính bản mới.
- Sửa (`services/qnu_docx_artifacts.py`, `services/source_ingestion_service.py`,
  `services/native_table_review.py`):
  - `superseded_qnu_markdown_artifact(prior, revision_id)` ghi marker
    `status: unavailable`, `reason: superseded_revision_content`, giữ tham chiếu
    nguồn gốc `superseded_revision_id`/`superseded_sha256` và **không** chứa
    `path`/`structured_path`.
  - `update_revision_content` dựng dict mới cho cả `snapshot_metadata` và
    `parse_provenance` (không mutate revision gốc, không để nhánh fallback
    `or parse_provenance` lấy lại artifact cũ).
  - `get_qnu_markdown_artifact` kiểm tra tương thích danh tính
    `artifact.revision_id == rev.id` và `artifact.document_id == binding.id`
    trước khi trả; lệch danh tính → `AppException`
    `QNU_MARKDOWN_REVISION_MISMATCH` (409). Router giữ cơ chế lỗi hiện có:
    marker `unavailable` → `QNU_MARKDOWN_NOT_READY` (404).
  - Nhánh reuse DOCX không copy metadata nữa mà gọi
    `rebuild_qnu_markdown_for_revision()`: đọc `.qnu-doc-v1.json` đã lưu của bản
    dùng chung, render lại với `revision_id` của chính revision mới, validate và
    lưu file mới. Chia sẻ dữ liệu bất biến là hợp lệ vì `artifact_key` đã ghim
    hash nguồn + parser profile + OCR config + version; nhưng frontmatter MD
    chứa `revision_id` nên phải dựng lại, không dán nhãn.
  - Không dựng lại từ DOCX gốc và tuyên bố đó là nội dung đã hiệu đính; không ghi
    đè hoặc xóa artifact lịch sử (hash cũ vẫn còn trong metadata marker).
  - `native_table_review` cũng gắn marker khi ô bảng được sửa làm nội dung đổi,
    để cùng một quy tắc áp dụng cho mọi đường tạo revision mới.

### 2. Heading cùng cấp bị gán sai cha–con

- Nguyên nhân: nhánh heading lấy `parent_id = builder.parent_id()` **trước khi**
  `push_heading(...)`, nên ngăn xếp vẫn chứa anh/em cùng cấp ngay trước đó →
  A2 nhận A1 làm cha, B nhận A2 làm cha.
- Sửa (`parsers/docling_structure.py`): `open_section(level, text, block_id)`
  pop mọi heading cùng cấp hoặc sâu hơn trước, rồi cha là phần còn lại của ngăn
  xếp. Stack giữ `level` thô của Docling (không clamp) nên tài liệu nhảy cấp vẫn
  nest đúng; clamp `depth` chỉ còn tác dụng với số `#` khi render. Không tạo cha
  giả. Đoạn, list và bảng nằm sau heading vẫn lấy `parent_id`/`section_path` từ
  heading đang mở.

### 3. Bảng/list nhiều trang bị gán chung trang đầu

- Nguyên nhân: `_add_table` tính **một** `table_page` từ toàn bộ text bảng rồi
  `_add_table_rows` dùng lại cho mọi dòng và ghi chú; nhánh list cũng map một lần
  cho cả run.
- Sửa: `map_unit_to_page()` ánh xạ **từng đơn vị** (dòng dữ liệu, ghi chú, item
  list), anchor của bảng là dòng header. Căn cứ là token boundary của projection
  render: chỉ nhận trang khi toàn bộ token của đơn vị khớp liên tục, tìm tiến về
  phía trước theo `cursor`; một đơn vị xuất hiện ở **nhiều trang khác nhau** là
  mơ hồ → `page: null`, không vòng về đầu tài liệu để đoán. Đơn vị không có trong
  projection hoặc vượt quá vùng đã ánh xạ cũng giữ `null`.
- `page: null` kèm locator ổn định `docx:block:{index}#row{N}` và
  `QnuQualityFlag(code="page_unresolved", related_block_ids=…)` trên khối bảng;
  list dùng cờ tương tự với số thứ tự item.
- Stats đổi `mapped_blocks`/`unmapped_blocks` → `mapped_units`/`unmapped_units`
  + `unit_states` (matched/absent/ambiguous/out_of_order), nên
  `page_mapping.status` chỉ `aligned` khi mọi đơn vị được ánh xạ tin cậy; còn
  đơn vị chưa chắc chắn là `partial`. Trang vẫn là trang bản PDF render xem trước,
  không phải phân trang nguyên bản DOCX (note trong frontmatter giữ nguyên).

### 4. Validator bỏ lọt field và origin không tồn tại

- Nguyên nhân: `columns` bị đọc từ `attributes` của chính khối `table_row`, nơi
  nó không tồn tại, nên `column_ids` rỗng và `if column_ids and …` bỏ qua mọi
  field lạ; origin chỉ được so tên `basis`, không kiểm tra block/column đích.
- Sửa (`normalization/qnu_markdown.py`): dựng `index` block trong
  `_validate_blocks`, rồi chạy `_validate_table_relations(parsed, report, index,
  columns_by_table)` sau vòng parse:
  - `table_row` phải có parent là khối `table` biểu diễn `records`
    (`table_row_parent_invalid`);
  - key của `fields` phải thuộc `columns` của **bảng cha**
    (`table_field_unknown_column`);
  - `field_origins` chỉ được mang key của field hợp lệ, origin là mapping,
    `basis` ∈ {`merged_cell`, `explicit_reference`}, `block_id` tồn tại và trong
    phạm vi bảng (chính bảng cha hoặc `table_row`/`note` cùng cha), `column_id`
    ∈ columns (`table_field_origin_invalid`);
  - bảng `records` không khai báo `columns` → `table_column_invalid`;
  - metadata sai kiểu đi qua `_mapping_value`/guard `isinstance` → lỗi có cấu trúc,
    không `AttributeError`.
  Ô gộp hợp lệ vẫn được nhận (fixture merged-cell, ô trống, số 0, mã có số 0 đầu,
  ghi chú full-width đều còn PASS).

## File thay đổi

- `backend/app/modules/knowledge/normalization/qnu_markdown.py`
- `backend/app/modules/knowledge/parsers/docling_structure.py`
- `backend/app/modules/knowledge/services/qnu_docx_artifacts.py`
- `backend/app/modules/knowledge/services/source_ingestion_service.py`
- `backend/app/modules/knowledge/services/native_table_review.py`
- `backend/tests/test_qnu_docx_markdown.py` (10 → 28 test)
- `backend/tests/test_native_table_review.py` (thêm assertion, không nới guard)
- Docs: nhật ký 523, README index, WORK_LOG, PROJECT_CONTEXT, snapshot,
  [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md) mục 11.

## Regression đã bổ sung

- `TestQnuArtifactRevisionIdentity` (6): hiệu đính không kế thừa tệp cũ và không
  giữ `path`; metadata lịch sử của bản cũ nguyên vẹn; nhánh fallback
  `parse_provenance` không làm artifact stale hợp lệ trở lại (`QNU_MARKDOWN_REVISION_MISMATCH`);
  artifact khớp danh tính vẫn resolve; marker `unavailable` được báo hết hiệu lực;
  reuse dựng lại dưới danh tính riêng (`derived_from_revision_id`, file mới chứa
  `revision_id` mới), reuse thiếu bằng chứng JSON → `unavailable`.
- `TestQnuHeadingHierarchy` (2): A1/A2 là anh-em của A (không cha–con), A2a là con
  của A2, B quay về cấp A, B7 nhảy cấp vẫn nest trong B; body/list/đoạn theo đúng
  section đang mở; `section_path` và số `#` nhất quán; render + validate đạt.
- `TestQnuMultiPageUnits` (3): 10 dòng bảng records trải hai trang render nhận
  đúng trang của chính dòng (mã `MTxx` chỉ xuất hiện trong trang được gán, không
  phải `[1] * 10`); hai bullet list map `[1, 2]`; khi căn cứ chỉ phủ một phần
  projection thì `page: null` + `page_unresolved` + status `partial`, locator vẫn
  có.
- `TestQnuTableRelationValidation` (7 test, 8 subtest): field ngoài columns, origin
  trỏ block/column không tồn tại, origin ngoài phạm vi bảng, origin thiếu field,
  origin `basis` lạ, row không có parent table, metadata sai kiểu — đều bị từ chối
  có cấu trúc; bảng gộp/ô trống/số 0/mã 0 đầu/ghi chú vẫn hợp lệ.

## Kiểm chứng

Lệnh thật, cwd `backend`:

- `./.venv/Scripts/python.exe -m ruff check` trên 5 file app + 2 file test đã sửa
  → **All checks passed!** (exit 0).
- `PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe -m pytest tests/test_qnu_docx_markdown.py -q --basetemp=storage/pytest-basetemp-505`
  → **28 passed, 8 subtests passed** (exit 0).
- Nhóm trọng tâm 11 file (`test_qnu_docx_markdown`, `test_clean_content_510`,
  `test_knowledge_source_ingestion`, `test_native_table_review`,
  `test_source_context_review`, `test_source_layout_extraction`,
  `test_source_page_provenance`, `test_source_pause`,
  `test_studio_nullable_reading_order`, `test_studio_revision_safety`,
  `test_workers`) → **144 passed, 8 subtests passed** trong 48.93s (exit 0).
- Negative control cho lỗi 4 (chứng minh đúng lỗ hổng cũ, không chỉ màu xanh):
  cùng một tệp MD đã giả mạo (`fields.c99` ngoài columns, origin
  `block_id: "zz9"`, `column_id: "c77"`) chạy với `_validate_table_relations` bị
  vô hiệu hóa (mô phỏng mã trước sửa) → `ok = True`, 0 lỗi; chạy bình thường sau
  sửa → `ok = False`, `['table_field_origin_invalid', 'table_field_unknown_column']`;
  fixture bảng gộp hợp lệ vẫn `ok = True`.
- **PASS**: bốn hành vi trên, ở phạm vi fixture + storage/DB giả lập, và các test
  DOCX/Markdown/ingestion liên quan.
- **FAIL**: không có test FAIL trong phạm vi đã chạy.
- **NOT RUN**: full backend suite (người dùng yêu cầu không chạy mặc định cho batch
  này; chỉ chạy lại khi có lý do cụ thể), benchmark 82 câu, đường chat/RAG thật,
  PDF/OCR áp chuẩn, UI tải tệp có đăng nhập, reparse DOCX thật, reindex/xuất bản.
  Trạng thái RED trước sửa của lỗi 1–3 **NOT RUN** trên mã cũ (các file chưa được
  commit nên không tái chạy phiên bản cũ); chỉ lỗi 4 có negative control nêu trên.
  Test mock/chỉ fixture chứng minh contract nội bộ, không chứng minh dữ liệu thật
  hay dịch vụ Docling ngoài pipeline đã đạt.

## Rủi ro còn lại và bước tiếp theo

- Revision hiệu đính chưa có đường dựng MD chuẩn từ chính nội dung đã hiệu đính;
  hiện nó ở trạng thái `unavailable` có chủ đích. Khi nào RAG đọc artifact chuẩn
  thì cần bước "render từ canonical đã duyệt" rồi mới nghiệm thu.
- `native_table_review` gắn id revision mới thủ công (`ks_rev_…`) để marker mang
  đúng danh tính; nếu sau này đổi quy ước id phải sửa cả hai nơi.
- Mapping trang vẫn phụ thuộc bản PDF render xem trước; bảng/list bị cắt giữa dòng
  hoặc lặp nội dung sẽ ở `partial` với cờ `page_unresolved`, không phải `aligned`.
- Chưa đo tác động lên chất lượng trả lời; đạt test parser/validator không chứng
  minh chatbot tốt hơn.
- Việc còn treo từ phiên 482: rule quy đổi điểm vẫn `draft` (tool OFF) vì thiếu
  định danh người duyệt kích hoạt; chưa commit/push bất kỳ thay đổi nào.
