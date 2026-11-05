# Xử lý tài liệu PDF/DOCX (OCR) — backendV1

Context710 bổ sung upload tự bóc tách, native-first và ZIP MD/JSON/ảnh. Luồng OCR
toàn trang thủ công bên dưới vẫn giữ tương thích. Xem [quy trình43](../../docs/quy_trinh/43_boc_tach_tu_dong_backend_v1.md)
cho mode auto, migration0007, quyền và giới hạn; native không tạo raw provider giả.

Native v2 (phiên870) bổ sung giữ thứ tự ký tự trong cell và OCR ảnh nhúng qua
MinerU theo vùng có tọa độ nguồn. Xem mục “Chữ bên trong ảnh nhúng với MinerU”
ở quy trình43. Dữ liệu cũ giữ nguyên; muốn áp dụng cần lượt bóc tách mới.

PDF tự động mới dùng PDF Inspector đọc lớp chữ và phân loại từng trang. PyMuPDF
đo vùng dẫn chứng, dựng lưới bảng và kết xuất ảnh xem trước. Nếu chữ trong một
vùng khác với lớp chữ tại vị trí đo được, giữ chữ nguồn của vùng đó và ghi số
vùng phục hồi trong cảnh báo trang. MinerU nhận riêng các trang cần OCR hoặc
ảnh raster nhúng và trả kết quả về tọa độ gốc.

DOCX mới dùng Docling đọc trực tiếp gói Word. Văn bản, bảng, giá trị trường đã lưu
và vị trí nguồn lấy từ DOCX. MinerU xử lý ảnh raster nhúng. Các artifact từ
luồng DOCX chuyển PDF trước đây vẫn đọc được.

Luồng biến một revision đã lưu thành bằng chứng OCR có thể kiểm chứng:

```
upload PDF/DOCX → revision gốc bất biến → yêu cầu xử lý (cùng transaction)
→ dispatch sau commit → worker claim → Docling cho DOCX hoặc PDF Inspector cho PDF tự động
→ raw response + canonical JSON + Markdown + manifest → đọc qua API
```

Phạm vi batch này dừng ở **bằng chứng kỹ thuật**. Chưa có Compiler, chunk, embedding,
index, publication, RAG hay frontend. Nguồn vẫn ở trạng thái `stored`: trạng thái xử lý
nằm ở bảng riêng, không ghi đè metadata tệp.

Theo dõi từng bước, API raw và cách xuất báo cáo nghiệm thu được mô tả trong
[kiểm chứng OCR](ocr-acceptance.md). Báo cáo kỹ thuật tách riêng chất lượng Nemotron
thật và đối soát ảnh nguồn, không dùng provider giả lập để tự duyệt nội dung.

## 1. Mô hình dữ liệu

Baseline `0001_initial_schema` đã bao gồm ba bảng OCR; xem [migration](migrations.md).

| Bảng | Vai trò |
|---|---|
| `ocr_processing_runs` | một lượt xử lý gắn với một revision bất biến, có generation, config ghim, lease và bộ đếm |
| `ocr_run_pages` | trạng thái từng trang: ảnh, hash, text, số block, cờ bảng, token, mã lỗi |
| `ocr_run_artifacts` | mọi artifact content-addressed kèm sha256, kích thước, content-type, blob key |

Ràng buộc đáng chú ý:

- `FOREIGN KEY (revision_id, source_id, collection_id, workspace_id)` → `kb_source_revisions`.
  Cách ly theo workspace được PostgreSQL bảo đảm, không chỉ bằng code. Khóa này cần
  unique key `uq_kb_revision_scope` trên bảng revision, đã nằm trong baseline.
- `UNIQUE (revision_id, generation)` — số thế hệ tăng đơn điệu.
- Partial unique index `uq_ocr_run_active ON ocr_processing_runs(revision_id)
  WHERE status IN ('queued','running')` — mỗi revision chỉ có một lượt đang hoạt động.
- `CHECK` trên `status`, `generation`, bộ đếm trang và định dạng sha256.
- `downgrade()` **từ chối chạy**: xóa bằng chứng OCR phải là quyết định có kế hoạch.

`ocr_processing_runs.config` là JSONB đã ghim: `renderer`, `ocr`, `provider`. Cùng với
`config_fingerprint` (sha256 của cấu hình chuẩn hóa), nó bảo đảm một lượt chạy cũ luôn
được đọc lại bằng đúng tham số đã tạo ra bytes.

## 2. Trạng thái

| Đối tượng | Giá trị |
|---|---|
| run | `queued` → `running` → `completed` \| `failed` \| `uncertain` |
| trang | `pending`, `in_flight`, `completed`, `blank`, `failed`, `uncertain` |

- `blank`: đo được trang không có mực (< 24 pixel tối trên mẫu dòng) — trang trắng hợp lệ,
  không gọi provider, không tính là lỗi.
- `uncertain`: đã gửi request nhưng không biết provider có xử lý hay không (timeout).
  Trang này **không bao giờ được gọi lại tự động**.
- `failed`: provider trả lỗi xác định hoặc phản hồi không dùng được.

`pages_done`/`pages_failed` là số đếm thật từ canonical, không phải phần trăm ước lượng.
Run chỉ `completed` khi không còn trang lỗi/không xác định.

## 3. Bóc tách và vị trí nguồn

| Định dạng | Cách làm | Artifact |
|---|---|---|
| `.pdf` | rasterize từng trang bằng PyMuPDF (`pdf-direct`) | `page_image` |
| `.docx` | Docling đọc gói Word trực tiếp, MinerU bổ sung chữ trong ảnh nhúng | `native_page` và `embedded_image` khi có ảnh |

DOCX có `pagination=document` và một đơn vị logic dùng chung contract với PDF.
`source_locator` ghi tham chiếu Docling và đường dẫn OOXML khi có. Bbox OCR trong
DOCX quy chiếu theo ảnh nhúng. Giao diện mở tệp Word gốc để đối chiếu. Bảng vượt
phạm vi cấu trúc hỗ trợ giữ văn bản và đánh dấu cần rà soát.

## 4. Artifact

Khóa content-addressed, nên retry ghi lại đúng một object:

```
v1/workspaces/{workspace_id}/ocr/{run_id}/{kind}/p{page:04d}-{sha256}.{ext}
```

| `kind` | Nội dung |
|---|---|
| `render_pdf` | PDF fixed-layout của các lượt DOCX cũ |
| `page_image` | PNG từng trang, đúng bytes đã gửi provider |
| `raw_response` | nguyên văn JSON provider trả về cho trang đó |
| `canonical_json` | tài liệu chuẩn `qnu.ocr.document/v1` |
| `markdown` | bản dẫn xuất `qnu.ocr.markdown/v1` |
| `manifest` | `qnu.ocr.manifest/v1`: hash, checks, validation |

`_store_artifact` từ chối ghi nếu cùng `(run, kind, page)` đã có bytes khác — nghĩa là
không thể âm thầm thay bằng chứng của một lượt đã chạy.

## 5. Hợp đồng bằng chứng cho Compiler

`GET .../processing-runs/{run_id}/evidence` trả snapshot chỉ đọc, ghim theo
`revision_id` + `generation` + `canonical_sha256` + `manifest_sha256`. Đọc một snapshot
cũ **không bao giờ** tự chuyển sang revision mới nhất.

Canonical JSON gồm:

- `identity`: workspace/collection/source/revision, `revision_no`, `source_sha256`,
  `run_id`, `generation`.
- `processing`: `processor_version`, `prompt_version`, `table_layout_version`,
  `config_fingerprint`, `renderer`, `provider` (id/model/capability, **không** credential),
  `started_at`, `finished_at`, `warnings`.
- `pages[]`: `page_number`, `status`, `image{sha256,width,height,ink_ratio}`, `blocks[]`.
- `blocks[]`: `evidence_id`, `order`, `type`, `label`, `text`, `bbox{x0,y0,x1,y1,units}`
  với `units="normalized_0_1"`, `requires_review`, `table`.
- `table`: `status`, `column_count`, `row_count`, `rows[][]` với `text`, `row_span`,
  `col_span`, `header`, `evidence_id`.
- `evidence`: map `evidence_id → {kind, page, block|cell, bbox|row/col}`.
- `limits`, `unknowns`.

Evidence ID tất định trong một generation: `ev_p{page:03d}_b{order:03d}` cho block và
`ev_p{page:03d}_b{order:03d}_c{row:02d}_{col:02d}` cho ô.

Nguyên tắc nội dung:

- Không suy ra năm, hiệu lực, vai trò trường từ tên tệp hay ngày ban hành.
- Giữ nguyên `0`, ô rỗng, `-`, `--`, đơn vị, điều kiện.
- Chuẩn hóa Unicode/định dạng luôn giữ raw + mapping, và **không** được coi là bằng chứng
  OCR đã đúng.
- `usage_tokens = null` khi không quan sát được, không bao giờ gán 0.

### Mã kiểm tra (`validation`)

Lỗi (run → `failed`): `page_count_mismatch`, `page_order_invalid`, `page_ocr_failed`,
`page_ocr_uncertain`, `page_without_content`, `evidence_missing`, `evidence_duplicate`,
`evidence_unmapped`, `block_bbox_invalid`, `table_grid_inconsistent`.

Cảnh báo (vẫn có thể `completed`): `blank_page_has_text`, `table_unreconstructable`.

Run hoàn thành chỉ xác nhận **xử lý kỹ thuật**; nó không phê duyệt nội dung và không
xuất bản gì.

## 6. API

Tiền tố:
`/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/processing-runs`

| Method | Path | Quyền | Ghi chú |
|---|---|---|---|
| POST | `` | admin/editor | 201 tạo mới, 200 khi tái sử dụng kết quả tương thích |
| GET | `` | đọc | danh sách, mới nhất trước |
| GET | `/{run_id}` | đọc | trạng thái + tiến độ từng trang |
| POST | `/{run_id}/dispatch` | admin/editor | 202, idempotent |
| GET | `/{run_id}/document` | đọc | canonical JSON, có `ETag` |
| GET | `/{run_id}/markdown` | đọc | Markdown dẫn xuất |
| GET | `/{run_id}/manifest` | đọc | hash + checks + validation |
| GET | `/{run_id}/evidence` | đọc | snapshot ghim cho Compiler |
| GET | `/{run_id}/pages/{page_number}/image` | đọc | PNG trang, có `ETag` |

Mọi route đi qua `resolve_workspace_access` **và** `resolve_revision_scope`, tức kiểm tra
cả chuỗi workspace → collection → source → revision. Không route nào nhận đường dẫn
storage từ client: `kind` là địa chỉ.

### Ví dụ (không kèm secret)

```bash
BASE=/platform/v1alpha1/workspaces/ws_1/collections/col_1/sources/src_1/revisions/rev_1

# 1. Yêu cầu xử lý (bỏ trống body cũng được: provider lấy theo cấu hình workspace)
curl -sS -X POST "$HOST$BASE/processing-runs" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"provider_id": "prv_ocr"}'

# 2. Tạo thế hệ mới dù đã có kết quả hoàn tất
curl -sS -X POST "$HOST$BASE/processing-runs" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"force": true}'

# 3. Theo dõi
curl -sS "$HOST$BASE/processing-runs/ocr_abc123" -H "Authorization: Bearer $TOKEN"

# 4. Đọc bằng chứng đã ghim
curl -sS "$HOST$BASE/processing-runs/ocr_abc123/document" -H "Authorization: Bearer $TOKEN"
curl -sS "$HOST$BASE/processing-runs/ocr_abc123/evidence" -H "Authorization: Bearer $TOKEN"
```

## 7. ModelOps và bảo mật

- Provider/model/endpoint lấy từ DB theo grant + default của workspace; credential giải mã
  từ ModelOps DB. Không có API key trong `.env`, không hardcode endpoint/model.
- Trước mỗi lần gọi: provider phải `active`, có capability `ocr`, được grant cho workspace,
  và còn quota. Provider bị tắt/thiếu capability/hết quota → lỗi riêng, **0 request HTTP**.
- Endpoint đi qua `assert_allowed_endpoint` (chặn mạng nội bộ ở production).
- Log chỉ có `model`, `status`, `duration_ms`, `image_bytes` — không có secret,
  `Authorization`, URL nhạy cảm, nội dung tài liệu hay Base64 ảnh.
- Worker kiểm tra lại quyền, trạng thái workspace và provider tại thời điểm chạy; quyền bị
  thu hồi sau khi enqueue thì lượt chạy thất bại thay vì tiếp tục.

## 8. Job bền vững

- ARQ với queue riêng của v1 (`QUEUE_NAME`), `retry_jobs=False`, `max_tries=1`: retry do
  bản ghi run quyết định, không có retry hai lớp.
- Yêu cầu xử lý được ghi **trong cùng transaction** với upload; dispatch sau commit. Redis
  chết → run vẫn `queued` với `dispatch_pending=true`, có API dispatch lại và cron
  `ocr_reconcile_queued` (5 phút/lần) nhặt lại.
- Claim nguyên tử `UPDATE ... WHERE status='queued' OR (running AND lease hết hạn) RETURNING`,
  nên hai worker không xử lý cùng một lượt.
- Trang được commit `in_flight` **trước** khi gọi provider: worker chết giữa chừng thì trang
  thành `uncertain`, không thành một lần gọi trùng.
- `job_id` = `qnu:v1:ocr:{run_id}:{attempt}` để dispatch lặp là no-op.
- Chỉ retry lỗi hạ tầng (`storage_unavailable`, `queue_unavailable`,
  `dependency_unavailable`), tối đa `OCR_RUN_MAX_ATTEMPTS`. Trang đã `completed` không bị gọi lại.

Từ Context643, startup nạp Settings trực tiếp từ nguồn cấu hình. Mỗi execution có
claim token riêng, heartbeat gia hạn lease và kiểm token/lease bằng row lock trước
commit hoặc bắt đầu request mới. Worker mất claim không được ghi đè kết quả. Cron
còn phục hồi run running hết lease và queued có delivery cũ; recovery dùng ticket
theo cửa sổ cron để không mắc kẹt vì Redis giữ kết quả job cũ. Trang in_flight của
worker đã mất được giữ uncertain, không tự gửi lại. Retry enqueue lỗi xóa dispatch
marker để cron nhặt được. Hết số lần thực thi thì dừng, không lặp vô hạn.

Raw bytes của mọi phản hồi provider đã nhận được lưu trước parse/validation, gồm
truncated, malformed và layout lỗi. Raw lỗi không được phục vụ như canonical hoàn tất.
Run ghim hash endpoint/model/capacity/prompt; thay target không được trộn vào cùng
generation. Kết quả hoàn tất chỉ reuse khi identity hiện tại vẫn tương thích.

Header, footer và footnote Word được đọc theo cấu trúc Docling. Các bản ghi cũ
giữ nguyên bằng chứng và trạng thái lỗi đã lưu.

## 9. Cấu hình

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `OCR_RENDER_DPI` | 144 | độ phân giải rasterize |
| `OCR_MAX_PAGES` | 300 | trần số trang |
| `OCR_MAX_PAGE_BYTES` | 8388608 | trần kích thước một ảnh trang |
| `OCR_MAX_OUTPUT_TOKENS` | null | Override OCR ảnh legacy; trống dùng ModelOps. MinerU không dùng token LLM |
| `OCR_PAGE_TOKEN_BUDGET` | 8192 | tương thích cấu hình cũ; runtime643 không dùng làm reserve |
| `OCR_RUN_MAX_ATTEMPTS` | 2 | số lần thử tối đa của một run |
| `OCR_LEASE_SECONDS` | 900 | hạn lease của worker |
| `OCR_DISPATCH_ENABLED` | true | tắt dispatch để chạy kiểm thử có kiểm soát |

Mọi thay đổi ở đây làm đổi `config_fingerprint`, nên kết quả cũ không bị tái sử dụng nhầm.

OCR còn yêu cầu token_limits và ocr_page_input trong ModelOps. Ngân sách là tổng
input bound có căn cứ + output đã kiểm; unknown bị chặn trước HTTP. Xem
[capacity và accounting ảnh](model-capacity.md).

## 10. Mã lỗi

| Mã | HTTP | Nguồn |
|---|---|---|
| `processing_unsupported_format` | 415 | định dạng không phải PDF/DOCX |
| `processing_run_active` | 409 | đã có lượt khác đang chạy với cấu hình khác |
| `processing_run_not_found` | 404 | run không thuộc revision |
| `processing_config_invalid` | 409 | config ghim hỏng |
| `provider_inactive` | 409 | provider bị tắt |
| `provider_capability_mismatch` | 409 | provider không có capability `ocr` |
| `provider_not_found` | 404 | provider chưa được cấp cho workspace |
| `model_not_configured` | 409 | workspace chưa chọn default cho `ocr` |
| `provider_changed` | 409 | provider đổi giữa hai lần chạy của cùng run |
| `quota_exceeded` / `quota_not_configured` | 409 | hết hoặc thiếu quota |
| `ocr_credentials_missing` / `ocr_credentials_unreadable` | 503 | thiếu/không giải mã được key |
| `ocr_provider_auth_failed` | 502 | provider từ chối credential |
| `ocr_provider_rate_limited` | 503 | provider giới hạn tần suất |
| `ocr_provider_unavailable` | 503 | provider lỗi 5xx |
| `ocr_provider_rejected` | 502 | provider từ chối yêu cầu |
| `ocr_provider_timeout` | 504 | **uncertain**, không retry |
| `ocr_provider_unreachable` | 502 | không kết nối được |
| `ocr_provider_endpoint_blocked` | 503 | endpoint bị chính sách mạng chặn |
| `ocr_response_invalid` | 502 | JSON/định dạng không đọc được |
| `ocr_response_empty` | 502 | provider trả trang rỗng |
| `ocr_response_incomplete` | 502 | `finish_reason` bất thường |
| `ocr_output_truncated` | 422 | đầu ra bị cắt, chưa đủ bằng chứng |
| `ocr_input_empty` | 422 | ảnh trang rỗng |
| `pdf_invalid`, `pdf_encrypted`, `pdf_no_pages`, `document_too_many_pages` | 422 | PDF không render được |
| `docx_source_invalid`, `docx_source_incomplete`, `docx_empty` | 422 | Docling không đọc được đầy đủ cấu trúc hoặc không có nội dung |
| `page_image_too_large` | 422 | ảnh trang vượt trần |
| `revision_content_mismatch` | 409 | bytes không còn khớp hash đã ghim |
| `render_mismatch` | 409 | số trang/ảnh khác lần chạy trước |
| `blob_missing` / `storage_unavailable` | 502 / 503 | lỗi storage |
| `run_not_completed` | 409 | run chưa/không hoàn tất, không phục vụ kết quả |
| `run_not_ready` | 409 | thiếu artifact được yêu cầu |

## 11. Kiểm thử

```bash
cd backendV1
# DATABASE_URL dựng trong bộ nhớ từ .env; harness tạo DB test riêng rồi drop
./.venv/Scripts/python.exe -X utf8 scripts/run_isolated_tests.py tests -q
```

- `tests/unit/test_ocr_*.py`: layout, DOCX→HTML, render/blank, canonical, validate,
  config fingerprint, adapter (URL, payload, mapping lỗi, không lộ secret).
- `tests/integration/test_ocr_processing_api.py`: 14 ca qua HTTP thật + PostgreSQL thật,
  provider là HTTP server loopback.
- Provider loopback là **mock**, không phải Nemotron thật. Trạng thái live OCR được ghi
  riêng trong báo cáo batch (hiện **NOT RUN**: không có endpoint/credential thật).

## 12. Giới hạn đã biết

- Chưa có Compiler, chunk, embedding, index, publication, RAG, frontend.
- Chưa hỗ trợ `.xlsx`, `.txt`, `.md` cho OCR — API trả 415 rõ ràng, tệp vẫn được lưu.
- Lượt DOCX mới ghim phiên bản luồng Docling. Lượt cũ chưa hoàn tất cần tạo lại
  từ revision Word gốc. Đồ họa Word chưa đọc được có cảnh báo để đối chiếu.
- Bảng không tái dựng được giữ raw + cảnh báo, không được tự "đoán" lại.
- Chưa có backfill tự động cho revision cũ: phải gọi API.
