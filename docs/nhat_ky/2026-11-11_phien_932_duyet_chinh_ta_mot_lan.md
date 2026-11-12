# Phiên 932 — Duyệt chính tả một lần sau upload, ẩn phiên bản khỏi giao diện

## Phạm vi và quyết định sản phẩm

Tiếp nối chuỗi P0–P3 của phiên 930/931. Người dùng chốt lại quy trình: sau khi up
tài liệu, OCR → chuẩn bị nội dung → soát chính tả → **phê duyệt một lần**; không
bắt người dùng hiểu hoặc thao tác lại theo `v0`, `v1`. Version vẫn tồn tại cho DB,
audit, biên nhận và truy vết RAG nhưng không xuất hiện trong luồng làm việc.

Quy tắc duyệt được chọn: **"Bắt xử lý hết"** — mọi gợi ý và gợi ý bị withheld phải
được áp dụng, tự sửa hoặc bỏ qua trước khi hoàn tất. Để giữ tốc độ, thêm
**"Bỏ qua tất cả còn lại"** ghi nhận hàng loạt.

Không reset/seed/reindex, không sửa migration `0020_reverse_flow`. F13 (chất lượng
RAG) nằm ngoài phạm vi. Sau khi người dùng duyệt kế hoạch, phiên áp migration
`0024` lên DB dev, restart API/worker và chạy E2E duyệt trên nguồn dev có sẵn.

## Thay đổi

### Backend

- Migration `0024_spelling_reviews` (`down_revision = 0023_spelling_dispositions`)
  và model `SpellingReview` — mỗi lượt soát chỉ có tối đa một bản ghi duyệt:
  - Cột ghim `check_id`, `reviewed_version`, `reviewed_sha256`,
    `reviewed_version_id`, `change_count`, `reviewed_by`, `idempotency_key`,
    `request_hash`, `reviewed_at`.
  - FK scope tới `ocr_processing_runs` (run/workspace/collection, RESTRICT), FK
    `check_id` tới `ocr_spelling_runs`, FK `reviewed_version_id` tới
    `ocr_text_versions` (nullable); unique `check_id`; unique
    `(workspace_id, reviewed_by, idempotency_key)`; check `reviewed_version >= 0`.
  - Bảng nằm trong `purge_graph`, ownership `V1_TABLES` và danh sách TRUNCATE của
    test harness.
- `SaveReview.review_check_id` (tùy chọn): lưu kèm id này là thao tác duyệt.
  `review_target` kiểm tra lượt thuộc đúng run/workspace/collection, không phải lô
  con tự động (`automatic_parent`), phải `completed`, chưa được duyệt
  (`ocr_spelling_review_exists`) và `(version, canonical_sha256)` trùng nội dung
  hiện tại (`ocr_spelling_check_stale`); thứ tự kiểm tra ưu tiên "đã duyệt" trước
  "stale" để trả đúng mã lỗi.
- `require_all_handled`: mọi gợi ý trong `suggestions` + `trace.withheld_suggestions`
  phải có disposition bỏ qua theo đúng tọa độ hoặc evidence tương ứng nằm trong
  `changes`; còn lại trả `409 ocr_spelling_suggestions_pending` kèm số lượng.
- Lưu không có thay đổi nhưng có `review_check_id` (đã bỏ qua hết) chỉ tạo
  `SpellingReview`, không tạo `ocr_text_versions`; `reviewed_version` là bản hiện
  tại. Lưu có thay đổi tạo text version `N+1` như cũ và duyệt luôn bản `N+1`.
  Gửi lặp cùng Idempotency-Key/body trả lại bản đã tạo (text version hoặc bản ghi
  duyệt); key khác cho nội dung khác trả `idempotency_conflict`.
- Audit `ocr.spelling_reviewed` chỉ ghi run/check/version/change_count; không ghi
  văn bản hay output model.
- `DetectionResponse` trả thêm `reviewed_version`, `reviewed_sha256`,
  `reviewed_at`, `reviewed_by`; danh sách lượt soát ghép bản ghi duyệt và vẫn ẩn
  các lô con tự động.
- `POST /text-review/checks/{check_id}/dispositions/bulk` nhận
  `{suggestions: [...]}`: yêu cầu quyền ghi, lượt `completed`, mọi phần tử phải có
  trong lượt; insert `ON CONFLICT DO NOTHING` theo unique tọa độ; audit
  `ocr.spelling_ignored_bulk` với số lượng; không sửa văn bản/lượt soát.
- Tài liệu `backendV1/docs/ocr-text-review.md`: mô tả duyệt một lần, hợp đồng
  `review_check_id`, bảng `ocr_spelling_reviews`, bulk ignore và ranh giới
  Compiler/publication (chuẩn bị nội dung ghim `text_version`; duyệt không tự xuất
  bản hay tái tạo chỉ mục).

### Frontend V2

- Trang `knowledge.$sourceId_.review.tsx` viết lại theo luồng một lần:
  - Search schema chỉ còn `collectionId`, `revisionId`, `runId`; bỏ toàn bộ
    selector phiên bản, lịch sử phiên bản, chế độ xem bản cũ và các copy `vN`.
  - Luôn đọc bản văn bản mới nhất; `currentSpellingCheck(checks, reviewDoc.version)`
    chọn lượt khớp `version` hoặc `reviewed_version` (ưu tiên đã duyệt > completed >
    running > đầu tiên).
  - Nút **Hoàn tất duyệt** chỉ bật khi lượt `completed`, coverage đủ, lượt không
    phải lô con, khớp nội dung hiện tại, chưa duyệt và không còn gợi ý mở; hộp thoại
    xác nhận hiển thị số đã áp dụng/đã bỏ qua.
  - **Bỏ qua tất cả còn lại** gọi endpoint bulk, cập nhật state cục bộ theo đúng
    tọa độ và toast số vị trí.
  - Hoàn tất gửi `{expected_version, expected_sha256, changes, review_check_id}` với
    Idempotency-Key ổn định theo signature `[ocrRunId, body]`; chỉ gửi yêu cầu chuẩn
    bị nội dung khi server tạo text version mới (`version_id != null`), sau đó điều
    hướng về trang tài liệu.
  - Sau khi duyệt, mọi gợi ý chưa có disposition được hiển thị như đã xử lý
    (`viewDecisions`), thẻ gợi ý chuyển chế độ chỉ đọc và các phím A/X/E/U bị khóa;
    S mở hộp thoại hoàn tất khi đủ điều kiện.
  - Soát lại vẫn dùng `POST /checks/rerun` với `{version, retry}` nhưng copy không
    nhắc số phiên bản.
- `spelling-status-strip.tsx` viết lại: thêm trạng thái **đã duyệt** (kèm số vị trí
  bỏ qua, thời điểm, thời gian tương đối), phân biệt chưa có lượt/đang chạy/lỗi/
  gián đoạn/thiếu coverage; nhãn hành động theo thứ tự đã duyệt → còn chờ → chưa có
  lượt → đủ điều kiện duyệt → xem chi tiết; link chỉ truyền ba tham số
  `collectionId/revisionId/runId`.
- `lib/spelling-review.ts`: thêm `formatSpellingMoment`; xóa các helper chỉ phục vụ
  selector phiên bản (`preferredSpellingCheck`, `spellingChecksForVersion`,
  `latestSpellingCheckVersion`); `currentSpellingCheck` và `spellingScope` giữ
  nguyên hợp đồng nội bộ.
- `knowledge.$sourceId.tsx`: link "Rà soát chính tả" truyền tường minh
  `revisionId`/`runId` thay vì spread `reviewScope` (không còn đẩy `textVersion`
  vào search). `reviewScope.textVersion` vẫn được dùng nội bộ cho input chuẩn bị
  nội dung.
- API client/query: thêm type `SpellingDispositionBatch` và hook
  `useBulkIgnoreTextReviewSuggestionsMutation`, ghi kết quả mới vào cache lượt soát
  và các danh sách đã cache.

## Kiểm chứng thực chạy

- Backend, DB cô lập (từ `backendV1`):
  `uv run --env-file ../.env python -m scripts.test_database tests/integration/test_ocr_text_review_651.py -q`
  → **41 ca PASS**, exit 0; DB test đã dọn; DB ứng dụng không bị chạm. Nhóm này
  gồm các ca duyệt: ghi nhận và replay, duyệt khi bỏ qua hết giữ nguyên văn bản,
  chặn gợi ý còn chờ/lượt cũ/lượt lạ/chưa xong, bulk ignore, purge nguồn có
  disposition.
- Frontend V2 (từ `frontendV2`):
  - `npx biome check .` → **177 tệp, không có lỗi/không sửa gì**, exit 0.
  - `npx tsc --noEmit` → PASS.
  - `npm run build` (Vite build + `tsc --noEmit`) → PASS, bundle tạo trong 2,43 giây.
- Loại trừ tĩnh các tham chiếu phiên bản còn sót: grep không còn
  `textVersion` trong search params hay identifier của thời kỳ selector.
- Migration dev: `.venv/Scripts/python.exe scripts/run_v1.py v1-migrate` áp
  `0023_spelling_dispositions -> 0024_spelling_reviews`, exit 0; bảng
  `ocr_spelling_reviews` tồn tại, revision khớp.
- Restart dev (`run_v1.py dev`): API 8002 health 200, Vite 3002 200; OpenAPI mới có
  `dispositions/bulk`, `review_check_id` và `reviewed_at` nên không còn phục vụ code
  cũ. Worker ARQ khởi động lại.
- E2E trình duyệt trên nguồn `src_a07e29184b04` (run `ocr_d16b33fd30e6`, check
  `spl_53d5a06b4a4f`, bản hiện hành 0):
  - Trang rà soát không còn selector phiên bản; hiển thị 35 vị trí chưa xử lý
    (25 gợi ý + 10 cần dò), nút **Hoàn tất duyệt** bị khóa.
  - Bấm **Bỏ qua tất cả còn lại (35)** → toast "Đã bỏ qua 35 vị trí còn lại.";
    các tab về `Chờ duyệt (0) · Đã nhận (0) · Bỏ qua (35) · Cần dò (0)`, hiện
    "Tất cả gợi ý đã được xử lý xong!" và nút duyệt bật.
  - Hộp thoại xác nhận hiển thị đúng: nội dung giữ nguyên, 35 vị trí bỏ qua không
    thay đổi văn bản, lượt soát sẽ được đánh dấu đã duyệt. Xác nhận → toast
    "Đã duyệt chính tả cho văn bản.", điều hướng về trang tài liệu.
  - Trang tài liệu: dải trạng thái "Đã duyệt chính tả · 35 vị trí bỏ qua lúc 16:26
    11-11" với hành động "Xem kết quả"; lịch sử có "Lượt #1 — Đã duyệt chính tả ·
    35 vị trí bỏ qua".
  - Tải lại trang rà soát: banner "Đã duyệt", "Đã duyệt chính tả lúc 16:26 11-11",
    tab giữ `0/0/35/0`, gợi ý chỉ đọc ("Văn bản đã được duyệt chính tả. Mọi thay
    đổi tiếp theo cần một lượt soát mới."), không còn nút duyệt/bỏ qua hàng loạt.
- DB dev sau E2E (chỉ đọc): đúng một bản ghi `ocr_spelling_reviews`
  (`splrev_bbb947ab33fc`, `reviewed_version=0`, `reviewed_version_id=NULL`,
  `change_count=0`, `reviewed_by=act_dev_admin`), 35 `ocr_spelling_dispositions`,
  **không** có `ocr_text_versions` mới cho run, audit `ocr.spelling_ignored_bulk`
  (count 35) và `ocr.spelling_reviewed` (version 0, change_count 0). Người dùng đã
  duyệt một lần chỉ với bỏ qua, không gọi model/token provider; preparation intent
  duy nhất của nguồn có từ 2026-11-10 nên thao tác duyệt không tạo intent mới.
- Full Pytest cô lập: **NOT RUN**. Baseline lịch sử **FAIL 4/1627** của phiên 928
  giữ riêng, không chạy lại để làm xanh.

## Giới hạn và bước sau

- E2E đã chạy nhánh "bỏ qua hết" (không tạo text version). Nhánh áp dụng một phần
  gợi ý tạo `N+1` và kèm yêu cầu chuẩn bị nội dung chưa được thao tác E2E trong
  phiên này; backend có test cô lập cho cả hai nhánh.
- Duyệt một lần không tự xuất bản; muốn bản sửa vào phục vụ phải chạy luồng chuẩn
  bị nội dung → xuất bản hiện có.
- E2E chất lượng OCR/chính tả (CER/WER, đối chiếu ảnh gốc) vẫn chưa nghiệm thu; F13
  và baseline lỗi nền RAG giữ nguyên.
- Working tree chưa commit; không push/deploy.
