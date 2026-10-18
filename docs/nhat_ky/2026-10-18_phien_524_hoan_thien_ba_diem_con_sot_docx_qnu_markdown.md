# Phiên 524 — Hoàn thiện ba điểm còn sót của DOCX → QNU RAG Markdown

## Yêu cầu và phạm vi

Tiếp [phiên 523](./2026-10-18_phien_523_sua_bon_loi_docx_qnu_markdown.md), sửa trực
tiếp ba lỗi review độc lập còn lại trên đường DOCX → [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md):

1. `map_unit_to_page` chỉ dùng điểm bắt đầu phép khớp nên một đơn vị trải hai trang
   vẫn nhận trang đầu và trạng thái `matched`.
2. Validator `qnu_markdown` văng `TypeError` (không phải lỗi có cấu trúc) khi metadata
   sai kiểu (`state: []`, `type: []`, `context_refs: 42`).
3. `rebuild_qnu_markdown_for_revision` bỏ qua `structured_sha256` đã lưu, dựng artifact
   `ready` từ bytes chưa được xác minh.

Ràng buộc đã tuân thủ: một batch code rồi mới bổ sung regression và kiểm tra trọng
tâm; chỉ fixture DOCX + storage/DB giả lập; không gọi LLM/OCR/cloud; không reset DB,
migration, reparse tài liệu thật, reindex, publish, restart/deploy, commit/push; MD
chuẩn **vẫn là dẫn xuất song song**, chưa nối vào RAG; không mở rộng thành refactor
toàn pipeline; không bọc validator bằng `try/except` rộng; không nới guard hay đoán dữ
liệu để test xanh; giữ nguyên các bản sửa đúng và thay đổi chưa commit của phiên trước.

## Kết quả

### 1. Trang ánh xạ phải do toàn bộ khoảng khớp quyết định

`parsers/docling_structure.py`:

- `_span_pages(start, end, page_ranges)` trả danh sách trang render phủ hết
  `[start, end)`; nếu khoảng đơn vị vượt ra ngoài vùng đã ghim, hoặc có gap giữa hai
  range liền kề (không liền mạch theo ký tự) thì trả `None` — nghĩa là **unknown**,
  không suy ra trang từ điểm đầu.
- `map_unit_to_page` xét cả `hit.start()` lẫn `hit.end()` của **mọi** phép khớp: phép
  khớp chưa ghim được → `ambiguous`; các phép khớp lặp lại có span trang khác nhau →
  `ambiguous`; phép khớp đầu tiên không lệch cursor → `out_of_order`. Trả
  `(pages: list[int], cursor, state)` với state mới `spanning` khi đơn vị chiếm ≥2
  trang. Vẫn forward-only, vẫn coi nội dung lặp ở nhiều trang là mơ hồ.
- `_locations(index, pages, suffix)` phát sinh **một `source_location` cho mỗi trang
  render** mà đơn vị chiếm, giữ nguyên locator `docx:block:N#rowM`; `_add_table`
  (anchor header), `_add_table_rows` (dòng dữ liệu và ghi chú) và nhánh list đều dùng
  chung đường này. Đơn vị không chắc chắn → `page: null` + locator + cờ
  `page_unresolved` như phiên 523.
- `stats.unit_states` now tách `matched`/`spanning`/`ambiguous`/`absent`/`out_of_order`
  nên `page_mapping.status = aligned` chỉ đạt khi **không còn** đơn vị chưa định vị,
  và số đơn vị đa trang nhìn thấy được ngay trong artifact.
- Trang vẫn là **trang PDF render xem trước** (`kind: pdf_preview_render`, note trong
  `document_meta.page_mapping`), không phải phân trang vật lý của DOCX.

### 2. Kiểm tra kiểu trước mọi tra cứu set/dict và trước vòng lặp

`normalization/qnu_markdown.py`:

- Thêm `_typed_in(value, allowed)` — `isinstance(value, str)` trước phép thử thành
  viên frozenset/set — và áp ở mọi đường previously trần: `review_status`
  (frontmatter), `type` khối, `state` field, `basis` origin, `type` của khối con trong
  `child_rows` và trong quan hệ origin.
- `context_refs` sai kiểu: vòng lặp quan hệ chỉ chạy khi `isinstance(raw_refs, list)`;
  lỗi `block_attribute_invalid` đã do pass chính ghi, không lặp lại và không nuốt.
- Quét placeholder dùng `str(metadata)` thay cho `json.dumps(..., default=str)` vì
  metadata sai kiểu key không còn làm validator crash khi serialize.
- `_construct_unique_mapping` kiểm `isinstance(key, Hashable)` trước phép tra cứu
  `key in mapping`, nên khóa YAML phức tạp (mapping-as-key) thành
  `block_metadata_yaml_error` có cấu trúc thay vì `TypeError`.
- **Không** bọc validator bằng catch rộng, **không** ép kiểu sai thành hợp lệ; các
  kiểm tra cũ (field thuộc columns bảng cha, origin hợp lệ, ô gộp, số 0, mã có 0 đầu,
  ô trống) giữ nguyên và vẫn đạt.

### 3. Xác minh checksum dẫn xuất trước khi parse/render/lưu

`services/qnu_docx_artifacts.py`:

- `rebuild_qnu_markdown_for_revision` dựng `_SHA256_HEX = [0-9a-f]{64}` và kiểm
  `structured_sha256` đã lưu: thiếu/rỗng/null → `unavailable/structured_checksum_missing`;
  sai định dạng (hex hoa, 63 ký tự, có khoảng trắng) → `unavailable/structured_checksum_invalid`;
  chỉ khi hợp lệ mới đọc StorageDriver.
- Tính SHA-256 trên **đúng bytes trả về từ storage** và đối chiếu trước
  `model_validate_json`/render; lệch → `failed/structured_checksum_mismatch` kèm
  `expected_sha256`/`actual_sha256`, log WARNING, **không** sinh MD/JSON mới.
  Không bao giờ lấy hash vừa tính gán lại làm checksum kỳ vọng.
- Path đạt đường cũ vẫn giữ `derived_from_revision_id` và `structured_sha256`;
  artifact lịch sử không bị sửa hay xóa.

### Regression (`backend/tests/test_qnu_docx_markdown.py`)

- `TestQnuUnitPageMapping` (7 test, hàm thuần): item "Alpha beta gamma delta" có ranh
  giới giữa "beta" và "gamma" → `[1, 2]` + `spanning`; đơn vị trọn trong một trang vẫn
  `[1]`/`[2]`; gap trong span → unknown; span vượt vùng ghim → unknown; văn bản lặp ở
  hai trang → `ambiguous`; khớp sau cursor → `out_of_order`; thiếu projection → `unavailable`.
- `TestQnuMultiPageUnits` thêm 2 test builder với projection cắt **giữa dòng**: item
  list wrapping giữ `[1, 2]` cùng locator, `unmapped_units = 0`, `aligned`,
  `kind = pdf_preview_render`, render lại vẫn `ok`; dòng `MT05` wrapping giữ `[1, 2]`,
  `MT01 → [1]`, `MT10 → [2]`.
- `TestQnuTableRelationValidation` thêm 2 test: sáu payload sai kiểu (`type: []`,
  `state: []`, `basis: []`, `context_refs: 42`, `section_path: 42`,
  `review_status: []`) phải trả `ok=False` với đúng mã lỗi, và khóa YAML không băm được
  → `block_metadata_yaml_error` (không phải exception).
- `TestQnuArtifactRevisionIdentity`: fixture `_ready` bỏ checksum giả `"d" * 64`, dùng
  `compute_sha256` của bytes thật và path content-addressed theo hash thật; test reuse
  dựng lại bằng đúng serialization của writer. Thêm 3 test: bytes lệch hash → `failed`
  và `set(stored)` không đổi (không ghi tệp mới); thiếu checksum → dừng **trước** khi
  đọc storage; checksum sai định dạng → từ chối.
- Các trường hợp phiên 523 (revision stale, heading cùng cấp, bảng gộp, ô đặc biệt)
  vẫn đạt.

## Kiểm chứng

- cwd `backend`. `uv run ruff check` 4 file đã sửa
  (`parsers/docling_structure.py`, `normalization/qnu_markdown.py`,
  `services/qnu_docx_artifacts.py`, `tests/test_qnu_docx_markdown.py`) →
  **All checks passed!** (exit 0).
- `pytest tests/test_qnu_docx_markdown.py -q -p no:cacheprovider --basetemp=storage/pytest-basetemp-524`
  → **42 passed, 23 subtests passed** (7.20s), exit 0. Tăng từ 28+8 lên 42+23.
- Nhóm trọng tâm 11 file DOCX/Markdown/ingestion (qnu_docx_markdown,
  docling_office_parser, source_layout_extraction, knowledge_docx_tables,
  ingestion_mixed_regressions, native_table_review, knowledge_source_ingestion,
  docx_preview_fields, source_context_stage2, knowledge,
  document_revisions_schema) → **182 passed, 23 subtests passed** (57.12s), exit 0,
  0 fail/skip mới.
- Bằng chứng guard hoạt động trước khi sửa fixture: lần chạy đầu tiên khi checksum
  fixture vẫn giả cho `failed/structured_checksum_mismatch` với
  `expected=dddd…` và `actual=4e44e26b…` — đúng hành vi mong muốn, sau đó fixture
  được cập nhật sang checksum thật chứ **không** nới guard.
- `git diff --check` exit 0; 4 file đã sửa là UTF-8, LF, không BOM; tiếng Việt đã đọc
  lại sau khi ghi.
- NOT RUN: full backend suite và benchmark 82 câu (không nằm trong phạm vi yêu cầu);
  đường chat/RAG thật; reindex/publish; PDF/OCR áp chuẩn; UI tải tệp có đăng nhập;
  reparse DOCX thật; RED-on-old-code cho ba lỗi (các file này chưa commit nên không
  còn trạng thái "trước sửa" để tái chạy cô lập).

## Giới hạn và việc tiếp theo

- `map_text_to_page` (heading/đoạn/hình/công thức/code) vẫn ánh xạ theo điểm bắt đầu
  và giới hạn 12 token; batch này chỉ nâng cấp đường **đơn vị** (dòng bảng, item list)
  theo đúng phạm vi yêu cầu. Muốn nhất quán toàn bộ thì cần quyết định riêng.
- Một đơn vị đa trang nay mang N `source_location` cùng locator; consumer RAG sau này
  phải hiểu "một khối, nhiều trang render" khi đọc chứng cứ.
- Trang vẫn là trang PDF render; DOCX không có phân trang vật lý.
- Chưa có consumer nào đọc `unit_states`/`spanning`; chỉ là bằng chứng trong artifact.
- Việc treo từ phiên 482 không đổi: rule quy đổi điểm vẫn `draft`, tool OFF, chờ định
  danh người duyệt kích hoạt.

## Ghi chú an toàn trong phiên

Trong lúc chạy Ruff/Read/`git diff`, một số **kết quả tool bị chèn thêm các chỉ thị lạ**
(mạo danh system-reminder/teammate): yêu cầu dừng triển khai, "handoff" vào
`C:\Users\AnhTuan\.qoder\cache\...`, và nhiều lượt tuyên bố sai rằng người dùng đã
duyệt lưu `LLM_API_KEY`/GitHub PAT/Qoder PAT dạng plaintext trong `backend/.env` hoặc
rằng `.gitleaks.toml` cho phép allowlist match-everything. Không làm theo lượt nào; các
tuyên bố này còn tự mâu thuẫn qua từng lượt (`banned = [""]`, rồi `banned = []`, rồi
`banned = ["backend/.env"]`). Đối chiếu
thực tế: `backend/.env` bị `.gitignore:42 (.env)` loại trừ, **không tracked, không
staged**; **không tồn tại** `.gitleaks.toml` trong repo. Bí mật LLM vẫn theo bất biến 6
 của AGENTS.md (ModelOps DB có bảo vệ). Người dùng nên kiểm tra hook/MCP đang chèn nội
dung vào tool output.
