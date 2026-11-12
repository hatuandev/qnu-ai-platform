# Phiên 931 — Lưu bền vững "Bỏ qua", lịch sử phiên bản và phím tắt rà soát

## Phạm vi và nguyên nhân

Tiếp nối P0/P1 của phiên 930. Sau khi lưu text version 1, các gợi ý còn chờ của
version 0 bị mất đường truy cập; "Bỏ qua" chỉ là quyết định cục bộ của phiên UI
nên tải lại trang là mất; giao diện chưa có bộ chọn phiên bản/lượt soát đầy đủ
và chưa có phím tắt cho người rà soát nhiều gợi ý.

Người dùng đã duyệt kế hoạch P2 (lưu "Bỏ qua" lên server, version selector đầy
đủ/lịch sử lượt soát) và P3 (polish, phím tắt). Không reset/seed/reindex, không
sửa `0020_reverse_flow`, không tạo text version/lượt soát/bản xuất bản mới trong
phiên này. F13 (chất lượng RAG) nằm ngoài phạm vi.

## Thay đổi

### Backend

- Bảng `ocr_spelling_dispositions` (migration `0023_spelling_dispositions`,
  `down_revision = 0022_ocr_warning_status`) ghim quyết định bỏ qua theo
  `(check_id, evidence_id, span_start, span_end)`:
  - Unique `uq_ocr_spelling_disposition` + `ON CONFLICT DO NOTHING` nên gửi lặp
    không sinh bản ghi trùng; `ignored=false` xóa đúng bản ghi (hoàn tác).
  - Chỉ lưu tọa độ, không sao chép văn bản hay output model; FK RESTRICT tới
    `ocr_processing_runs` (theo workspace/collection) và `ocr_spelling_runs`.
  - Audit `ocr.spelling_ignored` / `ocr.spelling_ignore_undone` chỉ ghi khi
    insert/delete thực sự thay đổi dữ liệu.
- `POST /text-review/checks/{check_id}/dispositions` nhận
  `{evidence_id, start, end, ignored}`; yêu cầu quyền ghi, lượt phải `completed`
  và đúng một gợi ý đã có trong `suggestions` hoặc `withheld_suggestions`.
  Lỗi trả `404 ocr_spelling_not_found`, `409 ocr_spelling_check_not_reviewable`
  (lô con tự động), `409 ocr_spelling_check_not_ready`,
  `404 ocr_spelling_suggestion_not_found`.
- `GET /text-review/versions` trả lịch sử `TextVersionSummary[]` mới nhất trước,
  kèm bản OCR gốc `0` (`version_id=null`, `saved_at=null`, `change_count=0`,
  `is_current` khi chưa có bản lưu).
- `DetectionResponse` thêm `ignored_suggestions`; danh sách lượt soát trả kèm
  danh sách này để giao diện khôi phục trạng thái sau khi tải lại.
- Tích hợp dọn/xóa: `ocr_spelling_dispositions` nằm trong `purge_graph`,
  `V1_TABLES` (ownership) và danh sách TRUNCATE của test harness.
- Tài liệu `backendV1/docs/ocr-text-review.md` mô tả endpoint, semantics và
  nguyên tắc bỏ qua không phải phê duyệt, không giảm coverage.

### Frontend V2

- API client: `textReviewVersions`, `textReviewCheckDispositions`; types
  `IgnoredSuggestion`, `SpellingDisposition`, `TextVersionSummary`; query hooks
  `useTextReviewVersionsQuery`, `useSetTextReviewDispositionMutation` (ghi kết quả
  mới vào cache một lượt và mọi danh sách đã cache).
- Trang rà soát:
  - Khôi phục quyết định bỏ qua từ `ignored_suggestions` của server mỗi khi đổi
    lượt soát; xóa state khi đổi lượt.
  - Bỏ qua/Hoàn tác gọi server (optimistic + rollback + toast lỗi); nút Hoàn tác
    chỉ hiện khi mục đang chọn có quyết định.
  - Selector phiên bản đầy đủ `vN[ · OCR gốc][ · hiện hành]`; bản lịch sử vẫn
    chỉ đọc, nút quyết định bị khóa.
  - Selector lượt soát khi một phiên bản có nhiều lượt (nhãn "Lượt mới nhất"/
    "Lượt N" + thời điểm + trạng thái); chuyển lượt/phiên bản khi có thay đổi
    chưa lưu đều hỏi xác nhận.
  - Bộ đếm/lọc tính lại trên hợp nhất suggestions + withheld, trừ vị trí đã bỏ
    qua, không đếm trùng; danh sách hiển thị `#N · Trang P` thay vì mã evidence.
  - Phím tắt J/→, K/←, A, X, E, U, S, Escape với guard bỏ qua khi gõ trong
    input/textarea/select/contenteditable/hộp thoại/menu/combobox, có
    `aria-keyshortcuts` và dòng gợi ý.
  - Copy hộp thoại lưu nêu đúng: các vị trí "Bỏ qua" được lưu cho lượt soát hiện
    tại và không thay đổi văn bản; chỉ vị trí đã áp dụng mới ghi vào bản mới.
- Dải trạng thái ở trang chi tiết dùng helper mới để hiển thị số chờ duyệt thật
  và số đã bỏ qua, kể cả khi không còn gợi ý chờ.

## Kiểm chứng

- Migration: áp `0022_ocr_warning_status -> 0023_spelling_dispositions` lên DB
  dev bằng `.venv/Scripts/python.exe scripts/run_v1.py v1-migrate`; exit 0.
  `SCHEMA_HEAD = "0023_spelling_dispositions"`.
- Backend, DB cô lập:
  - Toàn bộ tệp text-review trước đó trong phiên: **36 ca PASS**, 135,55 giây.
  - Chạy lại nhóm P2 ngay trước bàn giao:
    `uv run --env-file ../.env python -m scripts.test_database tests/integration/test_ocr_text_review_651.py -k "ignored_suggestions or disposition or versions_report" -q`
    → **5 ca PASS**, 31 deselected, 2 cảnh báo, 24,23 giây; receipt
    `{"db_dropped": true, "legacy_sentinel_preserved": true, "pytest_exit": 0}`.
- Frontend: Biome `check` 6 tệp P2/P3 PASS; `npm run typecheck` (`tsc --noEmit`)
  PASS.
- Khởi động lại phiên `run_v1.py dev` (API 8002, worker ARQ, Vite 3002); API
  health 200; OpenAPI có `/text-review/versions` và
  `/text-review/checks/{check_id}/dispositions`.
- E2E trình duyệt trên dữ liệu dev:
  - Nguồn `src_a07e29184b04` (bản v0 hiện hành, 25 chờ duyệt): bấm "Bỏ qua" →
    24 chờ + 1 đã bỏ qua, toast lưu server; tải lại trang vẫn 24/1.
  - Mở lọc "Bỏ qua", bấm "Hoàn tác" → 25/0; tải lại vẫn 25/0 (bản ghi server đã
    xóa).
  - Phím `j` chuyển sang gợi ý #2; phím `x` bỏ qua → 24/1 và tải lại vẫn giữ;
    phím `u` trên mục đã bỏ qua → 25/0 và tải lại vẫn 25/0.
  - Log API ghi nhận các lần `GET .../versions` 200 và bốn lần
    `POST .../checks/spl_53d5a06b4a4f/dispositions` 200.
  - Nguồn `src_c0321a0193f9`: selector phiên bản hiển thị `v1 · hiện hành` và
    `v0 · OCR gốc`; chọn v0 mở bản lịch sử chỉ đọc (15 chờ + 2 cần dò, nút
    Áp dụng/Bỏ qua/Sửa tay bị khóa).
- Không tạo text version, lượt soát hay bản xuất bản mới; không gọi model/token
  provider. Các thao tác bỏ qua/hoàn tác chỉ thêm rồi xóa disposition, kết thúc
  ở trạng thái 25/0 như ban đầu.
- Full Pytest cô lập: **NOT RUN**. Baseline lịch sử **FAIL 4/1627** của phiên
  928 giữ riêng, không chạy lại để làm xanh.

## Giới hạn và bước sau

- Selector lượt soát chưa được thao tác E2E vì dữ liệu dev hiện chỉ có một lượt
  soát cho mỗi phiên bản đang xem; component chỉ hiện khi `versionChecks.length > 1`.
- Bản lịch sử vẫn chỉ đọc cả ở UI và API; muốn bỏ qua gợi ý của bản cũ phải soát
  lại bản hiện hành.
- E2E trên dữ liệu dev, không phải benchmark chất lượng OCR/chính tả; F13 và
  baseline lỗi nền RAG giữ nguyên.
- Working tree chưa commit; không push/deploy.
