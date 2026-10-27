# Nhật ký phiên 665 — Giao diện OCR và kiểm tra hậu OCR trong frontendV1

- **Thời gian**: 2026-10-27T11:45:00+07:00
- **Phạm vi**: `frontendV1`
- **Mục tiêu**: Triển khai giao diện OCR và kiểm tra hậu OCR kết nối API thật `backendV1` tại `/platform/v1alpha1`, tích hợp vào trang chi tiết nguồn tài liệu (`SourceDetailPage`), hoàn thành chức năng và kiểm chứng.

---

## 1. Bối cảnh & Căn cứ kỹ thuật

- **Backend V1 OCR API**:
  - Base $R$: `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/processing-runs`
    - `POST R`: Yêu cầu xử lý (`provider_id: null | string`, `force: false | true`). 200 Reused (tái sử dụng lượt cùng fingerprint), 201 Created (tạo lượt mới khi `force=true`). Không dùng `Idempotency-Key`.
    - `GET R`: Danh sách lượt xử lý theo `Page` (`items`, `meta: { page, page_size, total }`).
    - `GET R/{run_id}`: Chi tiết lượt và danh sách trạng thái từng trang (`PageStatusResponse[]`).
    - `POST R/{run_id}/dispatch`: Gửi lại lượt xử lý đang chờ (`dispatch_pending`).
    - `GET R/{run_id}/document`: Tải Canonical JSON (`qnu.ocr.document/v1`).
    - `GET R/{run_id}/markdown`: Tải Derivative Markdown.
    - `GET R/{run_id}/manifest`: Xem/tải Processing Manifest (hash/toàn vẹn).
    - `GET R/{run_id}/evidence`: Xem/tải Evidence Snapshot ghim nguồn cho Compiler.
    - `GET R/{run_id}/pages/{page_number}/image`: Tải ảnh PNG trang đã render.
    - `GET R/{run_id}/pages/{page_number}/raw`: Tải raw response JSON/bytes của trang.
  - Base $T$: $R$`/{run_id}/text-review`
    - `GET T`: Lấy tài liệu review (`version` query param: 0 = OCR gốc, null = bản mới nhất).
    - `POST T`: Lưu sửa đổi (yêu cầu header `Idempotency-Key`, body: `{ expected_version, expected_sha256, changes }`).
    - `GET T/document?version=n`: Tải Canonical JSON theo phiên bản cụ thể.
    - `GET T/markdown?version=n`: Tải Markdown theo phiên bản cụ thể.
    - `POST T/checks`: Kiểm tra chính tả AI (yêu cầu header `Idempotency-Key`, body: `{ expected_version, expected_sha256, evidence_ids: [1..100], provider_id, max_output_tokens }`).
    - `GET T/checks/{check_id}`: Kiểm tra trạng thái/kết quả gợi ý chính tả.

---

## 2. Các thành phần đã triển khai

1. **Kiểu dữ liệu & Schemas** (`src/features/knowledge/ocr-types.ts`, `ocr-schemas.ts`):
   - Đầy đủ type contract cho ProcessingRun, PageStatusResponse, TextReviewUnit, ReviewDocument, TextChange, SaveReviewInput, DetectRequest, DetectionResponse, Suggestion.
   - Hàm tách/cắt span theo **Unicode code point** (`getCodePoints`, `getCodePointLength`, `sliceByCodePoints`, `replaceSpanByCodePoints`) đảm bảo tương thích 1:1 với Python offset (đặc biệt khi có emoji hoặc ký tự ngoài BMP, không bị lỗi lệch chỉ số UTF-16 của JS).
   - Hàm kiểm tra tính hợp lệ của gợi ý (`validateSuggestionSpan`) và áp dụng nhiều gợi ý theo thứ tự offset giảm dần (`applySuggestionsToText`) chống chồng lấn và từ chối gợi ý stale khi văn bản đã đổi.
   - Formatters hiển thị trung thực: `formatRunStatus`, `formatPageStatus` (giữ nguyên nghĩa `blank` là trang trắng không có mực, không quy đổi thành lỗi), `formatOcrError` (giải thích mã lỗi RFC 7807).

2. **Transport & Scoped Queries** (`ocr-requests.ts`, `ocr-queries.ts`):
   - Endpoint paths chuẩn hóa tại `ocrPaths`.
   - Các API request sử dụng `v1Client.get`, `post`, và `requestBlob` phân giải filename an toàn.
   - TanStack Query hooks có namespace gắn với `sessionId`, `workspaceId`, `collectionId`, `sourceId`, `revisionId`, `runId` chống lẫn dữ liệu giữa các phiên/workspace.
   - Polling có giới hạn cho lượt đang `queued`/`running`, dừng ngay khi chuyển trang, đổi tab, unmount hoặc gặp trạng thái terminal.
   - Thu hồi Blob Object URL an toàn khi unmount hoặc đổi ảnh/trang/phiên bản.

3. **Giao diện & Thành phần UI**:
   - `OcrRequestDialog`: Dialog yêu cầu xử lý OCR, chọn model từ ModelOps catalog capability `ocr` (hoặc mặc định workspace với `provider_id = null`), cờ `force` tách biệt giải thích rõ việc tiêu tốn token model và chỉ gửi `force: true` khi người dùng chủ động chọn.
   - `OcrRunsList`: Bảng danh sách các lượt xử lý, hiển thị generation, revision_no, trạng thái badge, thanh tiến độ trang `pages_done / pages_total` (chờ xác định khi null, không sinh phần trăm giả), attempt count, usage tokens (không đổi null thành 0), và nút Dispatch khi `dispatch_pending`.
   - `OcrComparisonView`: Màn hình đối chiếu side-by-side trên desktop (trái: ảnh PNG trang có zoom/pan, nút xem Raw JSON, cảnh báo layout renderer đối với file DOCX; phải: danh sách khối văn bản và bảng tái dựng với row_span, col_span, header). Hỗ trợ responsive chuyển tab dọc trên mobile.
   - `OcrTextReviewPanel`: Rà soát văn bản hậu OCR với bộ chọn phiên bản (v0 OCR gốc, v1, v2...), cho phép chỉnh sửa nội dung đoạn hoặc ô bảng vào draft cục bộ, modal đối chiếu trước/sau, lưu sửa đổi với `Idempotency-Key`. Giữ nguyên draft khi gặp xung đột phiên bản `409 ocr_text_version_conflict`. Tích hợp công cụ Kiểm tra chính tả AI (capability `chat`, phạm vi 1-100 đoạn), duyệt từng gợi ý và áp dụng vào draft cục bộ (không tự động áp dụng toàn bộ, không autosave). Hỗ trợ tải Canonical JSON và Markdown theo đúng version đã chọn.
   - `OcrArtifactsPanel`: Xem và tải các technical artifacts (Canonical Document JSON, Markdown dẫn xuất, Processing Manifest toàn vẹn, Evidence Snapshot).
   - `OcrTabContainer`: Điều phối các tab con (`runs`, `comparison`, `review`, `artifacts`), đồng bộ trạng thái qua URL Search Params (`revisionId`, `runId`, `page`, `subTab`).
   - Tích hợp vào `SourceDetailPage` thông qua hai Tab chính: *"Tệp gốc & Xem trước"* và *"Xử lý OCR & Rà soát văn bản"*. Cập nhật `validateSearch` tại route `$sourceId.tsx`.

---

## 3. Kết quả kiểm chứng

- **Unit & Contract Tests** (`tests/v1-ocr.test.ts`):
  - 11 test cases bao quát:
    1. Xử lý chính xác Unicode code points ngoài BMP và tương thích Python offset.
    2. Áp dụng nhiều gợi ý AI theo thứ tự giảm dần và chặn gợi ý chồng lấn/stale.
    3. Validate schema Zod cho SaveReview và DetectRequest.
    4. Format trung thực các trạng thái (không giả 0 khi null, giữ nguyên ý nghĩa blank page).
    5. Định dạng chính xác các mã lỗi RFC 7807 (`processing_run_active`, `ocr_text_version_conflict`, `ocr_provider_timeout`, v.v.).
    6. Cô lập scoped query keys theo `sessionId`, `workspaceId`, `revisionId`.
  - Kết quả: **76/76 tests PASS** trên toàn bộ 8 tệp test frontendV1 (0 fail).
- **TypeScript**: `tsc --noEmit` hoàn tất với **0 lỗi**.
- **Biome Linter & Formatter**: Toàn bộ 15 tệp liên quan đạt **0 errors / 0 warnings**.

---

## 4. Giới hạn & Bước tiếp theo

- Đợt này chưa triển khai Compiler, duyệt xuất bản (Publication Gate), chunk/embedding/index, và các hành động lifecycle pause/cancel/delete/restore.
- Không thêm bất kỳ thư viện sửa lỗi chính tả tự động nào; toàn bộ gợi ý AI hoàn toàn do người dùng chủ động yêu cầu và lựa chọn áp dụng vào bản nháp.
- Sẵn sàng chuyển tiếp dữ liệu Evidence Snapshot và Canonical Document cho đợt triển khai Compiler tiếp theo.
