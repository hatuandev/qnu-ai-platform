# Context640 — Luồng xử lý tài liệu PDF/DOCX (backendV1)

Ngày 2026-10-26. Mục tiêu: biến một revision đã lưu thành **bằng chứng OCR có thể kiểm
chứng**, không chỉ dừng ở kế hoạch:

```
upload PDF/DOCX → revision gốc bất biến → yêu cầu xử lý bền vững → render trang
→ OCR Nemotron qua ModelOps runtime → raw + canonical JSON + Markdown + manifest
→ đọc lại qua API có kiểm quyền
```

Đã chạy hết luồng trên PostgreSQL thật và provider HTTP thật (loopback). **Live Nemotron
NOT RUN** — không có endpoint/credential thật; provider trong test là mock và được ghi rõ.

## 1. Đã triển khai

### Dữ liệu — migration `0006_ocr_processing`

Ba bảng mới: `ocr_processing_runs`, `ocr_run_pages`, `ocr_run_artifacts`.

- Composite FK `(revision_id, source_id, collection_id, workspace_id)` → `kb_source_revisions`:
  cách ly workspace do PostgreSQL bảo đảm. Cần unique key `uq_kb_revision_scope`, thêm bằng
  0006 — **không sửa** 0005 đã áp dụng.
- Partial unique index `uq_ocr_run_active` trên `revision_id` với
  `status IN ('queued','running')`: mỗi revision chỉ một lượt hoạt động, kể cả khi hai
  request tới cùng lúc.
- `CHECK` trên status/generation/bộ đếm/sha256; `downgrade()` từ chối chạy.
- Trạng thái xử lý **không** ghi vào `kb_sources`: nguồn vẫn `stored`, metadata tệp không đổi.

### Render

| Định dạng | Đường đi | Artifact |
|---|---|---|
| `.pdf` | PyMuPDF rasterize từng trang | `page_image` |
| `.docx` | `word/document.xml` → HTML → `pymupdf.Story` → PDF fixed-layout → rasterize | `render_pdf` + `page_image` |

- Giữ heading, bold/italic, tab/break, bảng có `gridSpan`/`vMerge`/`tblHeader`, footnote,
  ảnh nhúng (data URI, ≤4 MB). Nested table tới độ sâu 2.
- Ghi lại `converter`, `dpi`, phiên bản PyMuPDF và sha256 của cả hai loại artifact.
- Bản PDF trung gian của DOCX **được lưu** vì đó là thứ OCR thực sự nhìn.
- Phát hiện trang trắng bằng phép đo: quét **toàn bộ pixel trên các dòng mẫu**, đếm pixel
  tối; trắng khi < 24 pixel tối. Ngưỡng theo *tỷ lệ* đã bị loại bỏ vì một trang chỉ có
  dòng tiêu đề (tỷ lệ 0,0002) từng bị coi là trắng và bị bỏ OCR — đây là lỗi thật đã gặp
  và đã sửa, có test riêng.

### ModelOps runtime

- `resolve_workspace_provider` (không cần actor HTTP) + `resolve_ocr_runtime` trả
  `OcrRuntime`: provider/model/endpoint/credential đã giải mã, `repr=False`, có
  `public_dict()` để ghi vào artifact mà **không** lộ key hay URL.
- Kiểm tra theo thứ tự: capability hợp lệ → default của workspace → grant → provider active
  → capability `ocr` → key còn hiệu lực → quota. Sai ở bất kỳ bước nào → mã lỗi riêng và
  **0 request HTTP** (có test đếm số request).
- Không có API key trong `.env`, không hardcode endpoint/model/credential.
- Log chỉ có `model`, `status`, `duration_ms`, `image_bytes`.

### Job bền vững

- Yêu cầu xử lý ghi **trong cùng transaction** với upload; dispatch sau commit.
- Redis chết → run vẫn `queued` với `dispatch_pending=true`; có API dispatch lại và cron
  `ocr_reconcile_queued` (5 phút) nhặt lại run chưa dispatch.
- Claim nguyên tử `UPDATE ... WHERE queued OR (running AND lease hết hạn) RETURNING`;
  lease `OCR_LEASE_SECONDS`. Hai worker không xử lý cùng một run.
- Trang được commit `in_flight` **trước** khi gọi provider → worker chết giữa chừng thì
  trang thành `uncertain`, không thành lần gọi trùng.
- `job_id = qnu:v1:ocr:{run_id}:{attempt}`: dispatch lặp là no-op; ARQ `retry_jobs=False`,
  `max_tries=1` — retry thuộc bản ghi run, không hai lớp.
- Chỉ retry lỗi hạ tầng (`storage_unavailable`, `queue_unavailable`,
  `dependency_unavailable`), tối đa `OCR_RUN_MAX_ATTEMPTS`; trang `completed` không gọi lại.
- Worker kiểm lại quyền (`resolve_workspace_access` với `WRITE_ROLES`, actor dựng từ
  `requested_by`), trạng thái provider và hash revision tại thời điểm chạy.

### Bằng chứng

Artifact content-addressed: `v1/workspaces/{ws}/ocr/{run_id}/{kind}/p{page:04d}-{sha256}.{ext}`,
`kind ∈ {render_pdf, page_image, raw_response, canonical_json, markdown, manifest}`.
`_store_artifact` từ chối ghi đè bytes khác cho cùng `(run, kind, page)`.

Canonical `qnu.ocr.document/v1` gồm `identity`, `processing`, `pages[]` (status, image hash,
ink_ratio, blocks), `blocks[]` (evidence_id, order, type, text, bbox `normalized_0_1`,
requires_review, table), `table` (status, column_count, row_count, rows với row_span/
col_span/header/evidence_id), `evidence` map, `limits`, `unknowns`.

Evidence ID tất định: `ev_p{page:03d}_b{order:03d}` và `..._c{row:02d}_{col:02d}`.

Validation phân biệt rõ: `page_ocr_failed`, `page_ocr_uncertain`, `page_without_content`,
`page_count_mismatch`, `page_order_invalid`, `evidence_missing/duplicate/unmapped`,
`block_bbox_invalid`, `table_grid_inconsistent` (lỗi) và `blank_page_has_text`,
`table_unreconstructable` (cảnh báo). Trang trắng hợp lệ **không** phải lỗi; trang có mực
mà không có chữ **là** lỗi.

`usage_tokens = null` khi không quan sát được, không bao giờ 0 giả.

### API (8 route mới)

`POST/GET .../revisions/{revision_id}/processing-runs`, `GET /{run_id}`,
`POST /{run_id}/dispatch`, `GET /{run_id}/document|markdown|manifest|evidence`,
`GET /{run_id}/pages/{n}/image`.

- Mọi route qua `resolve_workspace_access` **và** `resolve_revision_scope` (đủ chuỗi
  workspace → collection → source → revision); không nhận đường dẫn storage từ client.
- `document`/`image` trả `ETag` = sha256 nội dung; `image` thêm `nosniff`.
- `POST` trả 201 khi tạo mới, 200 khi tái sử dụng kết quả hoàn tất tương thích
  (cùng revision + fingerprint + provider). `{"force": true}` tạo thế hệ mới.
- `document`/`markdown`/`evidence` trên run chưa hoàn tất → 409 `run_not_completed`
  (không phục vụ kết quả nửa vời).

## 2. Port từ backend cũ — chọn lọc

| Nguồn legacy | Đã lấy | Viết lại / bỏ |
|---|---|---|
| `modules/ocr/adapters/nemotron_layout.py` | ý tưởng parse `<x_><y_>text<x_><y_><class_>`, `\thead`, `\multicolumn`, `\multirow` | viết lại thành `domains/ocr/layout.py` thuần, không phụ thuộc app cũ; thêm kiểm bbox, giới hạn cột/dòng, `unsupported` thay vì đoán |
| `modules/ocr/adapters/nemotron_adapter.py` | payload OpenAI-compatible, prompt, data URI | viết lại thành `adapters/providers/nemotron.py` + port `ports/ocr_engine.py`; thêm mapping lỗi phân biệt, chặn endpoint, không log secret |
| `modules/ocr/adapters/nemotron_runtime.py` | cách chọn runtime theo provider | bỏ; thay bằng `modelops.resolve_ocr_runtime` đọc DB + grant + quota |
| `knowledge/services/source_extraction.py` | luồng trích xuất theo trang | bỏ phần Word→text cũ; thay bằng render→ảnh→OCR, không dùng text native để ghi đè OCR |
| `knowledge/services/source_ingestion_service.py` | thứ tự job/trạng thái | viết lại trên ARQ + claim/lease + bảng run riêng |
| `knowledge/services/qnu_docx_artifacts.py` | ý tưởng tách artifact theo loại | viết lại content-addressed, có manifest + hash |
| `knowledge/services/compilation_catalog.py` | — | **không port** (thuộc Compiler, batch sau) |

Không import module ứng dụng legacy; không mang Repository, không mang cơ chế quyền cũ;
`backend/app` giữ nguyên 475 file.

Quyết định thiết kế đáng ghi:

1. **PyMuPDF là dependency duy nhất** cho render. Không LibreOffice/Gotenberg, không
   python-docx/Pillow/reportlab. DOCX đi qua HTML → `Story` để có layout cố định thật.
2. **Bảng không tái dựng được thì giữ raw**, `status="unsupported"` + cảnh báo, không
   "đoán" lại lưới. Không thêm thư viện sửa chính tả hậu OCR, không từ điển thay từ,
   không heuristic riêng cho một tài liệu hay câu test.
3. **Một revision một lượt hoạt động** bằng partial unique index, không bằng kiểm tra
   trong code (kiểm tra code luôn thua race).
4. **`uncertain` là trạng thái thật**, không phải `failed`: timeout nghĩa là *không biết*
   provider đã xử lý chưa, và gọi lại có thể tính phí hai lần.
5. **Trang trắng đo bằng số pixel tối tuyệt đối**, không bằng tỷ lệ — xem mục 1.

## 3. Kiểm chứng

Cwd `backendV1`, venv `uv` đã khóa, `DATABASE_URL` dựng trong bộ nhớ từ `.env` (không in
ra), harness tạo DB `qnu_v1_test_*` riêng rồi drop.

| Lượt | Kết quả |
|---|---|
| 14 ca OCR integration, lần đầu | **11 FAIL** / 3 PASS — config thiếu `max_pages`, trang có chữ bị coi là trắng |
| sau khi sửa config + đo mực | 7 FAIL / 7 PASS |
| sau khi sửa quota/generation/snapshot | 1 FAIL / 13 PASS |
| 14 ca OCR integration, cuối | **14 PASS / 0 FAIL** |
| Full integration (kèm knowledge) | 86 PASS / **1 FAIL** — regression downgrade639 |
| sau khi sửa regression639 | 8 PASS (file 639) |
| **Full v1 cuối** | **249 PASS / 0 FAIL / 0 SKIP**, 83,39 s, exit 0 |
| Ruff toàn `backendV1/` | PASS (`All checks passed!`) |
| OpenAPI export | PASS — **39 path / 54 operation** (+8 path) |
| Migration ↔ ORM parity (0006) | PASS trong full run |
| Live Nemotron | **NOT RUN** |

DB test `qnu_v1_test_73051dbf42c4467a`, `db_dropped=true`,
`legacy_sentinel_preserved=true`, `pytest_exit=0`.

Ca mới: **95** (81 unit + 14 integration). Baseline trước batch: 154 (152 PASS + 2 FAIL
của Context641) → 249.

Lệnh chính:

```bash
cd backendV1
export DATABASE_URL=$(./.venv/Scripts/python.exe -c "...quote(POSTGRES_PASSWORD)...")
./.venv/Scripts/python.exe -X utf8 scripts/run_isolated_tests.py tests -q --tb=line
./.venv/Scripts/python.exe -m ruff check .
./.venv/Scripts/python.exe -X utf8 scripts/export_openapi.py
```

### Hai lỗi còn mở của Context641 — đã đóng

1. **Regression downgrade639.** Ca test ghim chuỗi `"knowledge evidence"` và version
   `0005`, nên FAIL khi 0006 trở thành head. Sửa **đúng bản chất**: vẫn yêu cầu
   downgrade trả mã lỗi khác 0 và vẫn yêu cầu thông báo của guard, nhưng kiểm **bất biến**
   "version không đổi sau khi hạ cấp thất bại" (lấy head trước đó) thay vì một chuỗi của
   riêng migration 0005. Guard không bị nới; assertion mới **mạnh hơn** vì còn chứng minh
   history không bị ghi dở.
2. **`PermissionError` của local writer.** Chỉ tái hiện khi chạy pytest ngoài harness:
   `tmp_path` trỏ vào `%TEMP%` không truy cập được. Trong harness (`--basetemp` riêng) 9 ca
   `test_local_blob_store.py` PASS. Không sửa code vì không có lỗi code.

## 4. Giới hạn

- **Live OCR NOT RUN**: chưa có endpoint/credential Nemotron thật, chưa có dữ liệu được
  phép gửi ra ngoài. Provider loopback chứng minh đường HTTP, header, timeout, parse —
  **không** chứng minh chất lượng nhận dạng.
- Chưa có Compiler, chunk, embedding, index, publication, RAG, frontend.
- Chưa migrate DB đang phục vụ; chưa restart/deploy; không sửa code legacy.
- `.xlsx`/`.txt`/`.md` vẫn được lưu nhưng OCR trả 415 rõ ràng.
- Chưa backfill tự động: revision cũ phải gọi API.
- Không có `ruff format` toàn repo: 25 file (gồm file có sẵn từ trước) chưa theo
  `ruff format`. Gate của repo là `ruff check`; reformat toàn bộ sẽ tạo nhiễu diff ngoài
  phạm vi batch.

## 5. Cần làm trước khi mở Compiler

1. **Chạy live một mẫu nhỏ** với provider/credential thật và dữ liệu được phép, ghi lại
   model, ảnh, raw response, chất lượng bảng — nếu không, Compiler sẽ được xây trên bằng
   chứng chưa từng kiểm chứng ngoài đời.
2. **Xác nhận `uncertain` bằng tay**: một lần timeout thật phải để lại trang `uncertain`
   và không bị cron gọi lại.
3. **Đo tải render**: 300 trang ở 144 dpi là ~300 × 1,5 s; cần biết có chấp nhận được với
   `job_timeout=1800` hay phải chia lô theo trang.
4. **Chốt schema Compiler đọc**: hiện đọc `evidence` snapshot; nếu Compiler cần thêm
   trường (ví dụ section/heading tree) thì phải thêm vào canonical **có version mới**, không
   sửa `qnu.ocr.document/v1`.
5. **Quyết định chính sách bảng `unsupported`**: hiện giữ raw + cảnh báo; cần nói rõ
   Compiler có được dùng bảng đó hay phải chờ người duyệt.
6. **Migration DB phục vụ** vẫn là thao tác chủ động riêng, chưa làm trong batch này.

Xem [thiết kế luồng](../../../backendV1/docs/ocr-processing.md) ·
[nhật ký phiên 640](../../nhat_ky/2026-10-26_phien_640_luong_xu_ly_pdf_docx_backendv1.md).
Seal file/hash của batch: `backendV1/storage/context640/final-seal.json` (44 file, kèm
receipt full suite; thư mục `storage/` bị Git ignore).
