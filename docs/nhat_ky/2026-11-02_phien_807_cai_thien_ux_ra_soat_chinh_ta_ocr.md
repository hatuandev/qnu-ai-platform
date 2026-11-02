# Nhật Ký Phiên 807 — Cải Thiện UI/UX Luồng Người Dùng Rà Soát và Sửa Chính Tả Sau OCR (`frontendV1`)

- **Ngày thực hiện:** 2026-11-02
- **Phạm vi:** `frontendV1/src/features/knowledge/`, `frontendV1/tests/`, `docs/`
- **Mục tiêu:** Cải thiện toàn diện UI/UX luồng cán bộ xử lý tài liệu rà soát văn bản sau OCR, chọn phạm vi/model kiểm tra chính tả AI, đối chiếu ảnh gốc có đánh dấu vùng `bbox` thật, áp dụng hoặc bỏ qua gợi ý vào bản nháp, lưu phiên bản hiệu đính với preview trước/sau và tiếp tục biên soạn (`Compiler`).

---

## 1. Khảo Sát Route Thực Tế & Điểm Nghẽn Trước Khi Sửa

Qua truy vết toàn bộ cây route trong `frontendV1/src/app/routes/`:
1. **Luồng chính từ Kho tri thức / Collection:**
   - `/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId` và `/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr` → render `OcrReviewPage` → ủy quyền trực tiếp cho `SourceDetailPage`.
   - Trước khi sửa, `SourceDetailPage` gặp các vấn đề UX/hợp đồng nghiêm trọng:
     - Bấm `"Kiểm tra chính tả"` gọi thẳng API với `.slice(0, 50)` âm thầm cắt bỏ các đoạn vượt quá 50, không cho cán bộ chọn phạm vi đoạn hay chọn model từ catalog ModelOps.
     - Không nối `SpellingResultPanel` vào `OcrComparisonView` và bỏ qua `search.checkId` trên URL, khiến mở lại `checkId` hoặc xem danh sách gợi ý cạnh ảnh nguồn không hoạt động.
     - Hộp thoại xác nhận lưu hiển thị mã kỹ thuật `evidence_id` thô (`ev_p015_b007`), tạo `Idempotency-Key` mới ở mỗi lần bấm làm mất tính idempotent khi thử lại, và thiếu kiểm tra xung đột `baseMovedOn` / `ocr_text_version_conflict`.
     - Thiếu `useActionScope` ngăn phản hồi bất đồng bộ của phiên/tài liệu cũ ghi đè màn hình hiện tại, và thiếu `useBlocker` cảnh báo khi rời trang đang có nháp chưa lưu.
2. **Luồng từ chi tiết Kho tri thức (`StageOcrPanel`):**
   - `/workspaces/$workspaceId/knowledge/$knowledgeId/ocr` → `StageOcrPanel` → `OcrTabContainer` → `OcrComparisonView` / `OcrTextReviewPanel`.
   - `OcrComparisonView` trước đó nhân đôi 2 cây DOM (Desktop `hidden lg:grid` và Mobile `lg:hidden`) gây trùng lặp phần tử, chưa hiển thị khung đánh dấu `bbox` trên ảnh gốc khi đối chiếu gợi ý, dùng màu cứng `amber-500`, và chưa cho chọn từng đoạn trên trang.

---

## 2. Các Thay Đổi Đã Triển Khai

1. **Hợp đồng dữ liệu, định vị đoạn thân thiện & xác thực `bbox` (`ocr-types.ts`, `ocr-schemas.ts`):**
   - Bổ sung `MAX_SPELL_CHECK_UNITS = 100` khớp giới hạn `1..100` đoạn của schema backend (`SpellingDetectionRequest`).
   - Bổ sung `extractNormalizedBbox(bbox)`: chỉ trả về tọa độ chuẩn hóa khi có đủ `x0, y0, x1, y1` hợp lệ trong khoảng `0 <= x0 < x1 <= 1` và `0 <= y0 < y1 <= 1`; trả về `null` khi thiếu hoặc không hợp lệ (tuyệt đối không ước đoán hay bịa vị trí).
   - Bổ sung `formatUnitKindLabel` và `formatUnitLocator` chuyển đổi `unit` thành nhãn nghiệp vụ dễ hiểu cho cán bộ: `Trang X · Đoạn văn Y` hoặc `Trang X · Ô bảng (Hàng R, Cột C)`.
   - Mở rộng `formatOcrError` bao phủ đầy đủ các mã lỗi kiểm tra chính tả và xung đột phiên bản (`ocr_spelling_invalid`, `ocr_spelling_interrupted`, `ocr_spelling_expired`, `ocr_spelling_not_found`, `ocr_text_conflict`, `chat_provider_changed`, `chat_output_truncated`).

2. **Hộp thoại cấu hình kiểm tra chính tả & xác nhận lưu hiệu đính (`ocr-review-dialogs.tsx`):**
   - `OcrSpellCheckDialog`:
     - Hiển thị rõ phạm vi kiểm tra (`Trang hiện tại` hoặc `Các đoạn/ô được chọn`), danh sách tích chọn từng đoạn/ô có chữ kèm số lượng thực tế.
     - Kiểm tra nghiêm ngặt giới hạn `1..100` đoạn; khi vượt quá 100 đoạn sẽ hiển thị cảnh báo yêu cầu thu hẹp lựa chọn và khóa nút gửi, không âm thầm dùng `.slice()`.
     - Khi có bản nháp chưa lưu (`pendingDraftCount > 0`), hiển thị cảnh báo rõ ràng rằng AI chỉ kiểm tra phiên bản đã lưu trên máy chủ (`Phiên bản vX`), không kiểm tra nội dung nháp chưa lưu.
     - Tích hợp `useCatalogQuery(workspaceId)` và `ConsumerModelBudgetNotice` để chọn model Chat từ danh mục được cấp cho workspace; không hardcode Luna làm model bắt buộc, không tự đổi model mặc định, và hướng dẫn liên hệ quản trị viên cấp quyền qua **ModelOps** nếu chưa có model mong muốn.
     - Trong lúc đang gửi: khóa nút gửi trùng, đo và hiển thị thời gian thực tế đã trôi qua (`Đã trôi qua: Xs`), không tạo phần trăm tiến độ giả.
   - `OcrSaveConfirmDialog`:
     - Hiển thị preview trước/sau (`Bản đang lưu` vs `Bản hiệu đính mới`) với vị trí đoạn/ô thân thiện (`Trang X · Đoạn văn Y`), ẩn hoàn toàn `evidence_id` và `canonical_sha256` khỏi giao diện nghiệp vụ chính.

3. **Bảng kết quả gợi ý chính tả & đối chiếu ảnh gốc (`spelling-result-panel.tsx`):**
   - Phân loại rõ 4 trạng thái từng gợi ý bằng nhãn chữ + biểu tượng: `Chờ xem xét`, `Đã áp dụng vào nháp`, `Đã bỏ qua`, `Không còn khớp`.
   - Hiển thị vị trí `Trang X · Đoạn văn Y`, cụm từ `Chữ gốc → Đề xuất sửa`, ngữ cảnh trước/sau đánh dấu phần thay đổi, và lý do ngắn gọn.
   - Hỗ trợ đầy đủ thao tác: `Áp dụng vào nháp`, `Bỏ qua`, `Đối chiếu trên trang`, `Sửa tay`, và `Hoàn tác nháp đoạn này`.
   - Tách riêng nhóm **“Cần đối chiếu ảnh gốc”** (`withheld_suggestions`, `role="note" aria-label="Cần đối chiếu ảnh gốc"`): không có nút áp dụng trực tiếp, chỉ cung cấp nút `Đối chiếu trên trang` và `Sửa tay sau khi đối chiếu`, không tự gắn nhãn đã xác minh.
   - Ẩn mã phiên kiểm tra (`check.id`) và mã lỗi kỹ thuật (`error_code`) vào thẻ `<details>` thu gọn.
   - Thông báo rõ khi có 0 gợi ý: *"Không có đề xuất trong lần kiểm tra này. Điều này không xác nhận OCR đã chính xác."*

4. **Bố cục đối chiếu song song Desktop & chuyển vùng Mobile/Tablet (`ocr-comparison-view.tsx`):**
   - Hợp nhất về **một cây DOM đáp ứng duy nhất** (xóa bỏ cây DOM nhân đôi trước đây):
     - **Desktop (`lg:grid-cols-2`)**: Cột trái hiển thị `Ảnh gốc trang X` (zoom, vừa ngang/vừa trang, chọn trang, mở toàn màn hình); cột phải hiển thị đồng thời `Kết quả kiểm tra chính tả` và `Văn bản trang X` để cán bộ vừa xem gợi ý vừa đối chiếu ảnh.
     - **Mobile/Tablet (`< lg`)**: Thanh chuyển đổi 3 vùng rõ ràng (`Ảnh trang X` | `Văn bản` | `Gợi ý`) giữ nguyên trang đang xem, bản nháp và đoạn đang chọn, không tràn ngang hoặc che nút lưu.
   - Khi bấm vào một gợi ý hoặc nút `Đối chiếu trên trang`, tự động chuyển tới đúng trang, cuộn tới đoạn/ô văn bản và hiển thị khung đánh dấu `data-testid="ocr-bbox-highlight"` trên ảnh nguồn **chỉ khi đoạn đó có `bbox` chuẩn hóa hợp lệ**; nếu đoạn không có `bbox`, hiển thị nhãn trung thực `(không có tọa độ vùng ảnh)`.
   - Thay thế toàn bộ màu cứng `amber-500` bằng semantic token `warning`.

5. **Kết nối hoàn chỉnh trên `SourceDetailPage`, `OcrTabContainer` và `OcrTextReviewPanel`:**
   - Nối đầy đủ `OcrSpellCheckDialog`, `OcrSaveConfirmDialog`, `SpellingResultPanel`, bộ chọn phiên bản văn bản (`selectedVersion`), thanh trạng thái bản nháp, cảnh báo xung đột phiên bản (`baseMovedOn` / `ocr_text_version_conflict`), `useBlocker` khi rời trang có nháp, và `useActionScope` chống phản hồi bất đồng bộ cũ.
   - Giữ ổn định `activeSaveKey` và `activeSpellKey` (`Idempotency-Key`) khi thử lại cùng một yêu cầu; chỉ sinh khóa mới khi nội dung nháp hoặc phạm vi kiểm tra thay đổi.
   - Nút `"Dùng để biên soạn"` kiểm tra nếu còn nháp chưa lưu sẽ cảnh báo cán bộ lưu trước, và truyền đúng `textVersion` đã lưu sang `CompilationDialog`.

6. **Tích hợp bộ 3 thư viện nâng cao trải nghiệm đối chiếu (theo xác nhận của người dùng trong phiên):**
   - **`react-resizable-panels` (`^4.16.1`)**: Bổ sung thanh kéo chia cột (`Group` / `Panel` / `Separator` với `id="ocr-panel-separator"`) kèm 3 nút chọn nhanh tỷ lệ trên Desktop (`50:50`, `Rộng ảnh`, `Rộng chữ`), đồng thời bảo toàn chế độ chuyển đổi 3 vùng trên Mobile/Tablet (`< lg`) trên cùng một cây DOM.
   - **`react-zoom-pan-pinch` (`^4.2.0`)**: Bọc vùng ảnh gốc trong `TransformWrapper` + `TransformComponent` hỗ trợ lăn chuột phóng to/thu nhỏ mượt, kéo giữ chuột (pan) soi chữ nhỏ, nhấp đúp để đặt lại, và nút `"Phóng vào vùng này"` (`zoomToElement`) tự động phóng trực tiếp vào khung `ocr-bbox-highlight` đang đối chiếu.
   - **`diff` (`^9.0.0` + `@types/diff`)**: Triển khai component `OcrWordDiffView` (`diffWordsWithSpace`) render trực tiếp bằng các thẻ React `<del>` (đỏ gạch ngang) và `<ins>` (xanh lá đậm) an toàn (không dùng `innerHTML`), hiển thị ở hộp thoại xác nhận lưu (`OcrSaveConfirmDialog`), hộp thoại sửa đoạn văn và ngay dưới đoạn văn đang có nháp chưa lưu.
   - **Phím tắt điều hướng trang (`[` / `]`)**: Hỗ trợ bấm `[` (Trang trước) và `]` (Trang sau) khi không đặt con trỏ trong ô nhập liệu hoặc hộp thoại.

---

## 3. Kết Quả Kiểm Chứng Thực Tế

Đã chạy các lệnh kiểm tra tại `frontendV1/`:

1. **Bộ kiểm thử hành vi mới + các bộ kiểm thử hồi quy OCR hiện hữu (Vitest):**
   - Lệnh:
     `Set-Location d:\DuAnPhanMem\qnu-ai-platform\frontendV1; npm test -- ocr`
   - Kết quả: **PASS** — 9/9 test files, **47/47 tests PASS** (trong đó `tests/ocr-review-ux-806.test.tsx` đạt **13/13 tests PASS**, bao gồm kiểm thử word-level diff `<del>`/`<ins>`, thanh kéo `role="separator"`, và phím tắt `[` / `]`).

2. **Kiểm tra Biome (Lint & Format):**
   - Lệnh:
     `Set-Location d:\DuAnPhanMem\qnu-ai-platform\frontendV1; npx @biomejs/biome check --write src/features/knowledge/ocr-types.ts src/features/knowledge/ocr-schemas.ts src/features/knowledge/ocr-review-dialogs.tsx src/features/knowledge/spelling-result-panel.tsx src/features/knowledge/ocr-comparison-view.tsx src/features/knowledge/ocr-text-review-panel.tsx src/features/knowledge/ocr-tab-container.tsx src/features/knowledge/source-detail-page.tsx tests/ocr-review-ux-806.test.tsx package.json`
   - Kết quả: **PASS** — `Checked 10 files in 157ms. No fixes applied.` (0 errors, 0 warnings).

3. **Kiểm tra kiểu TypeScript (`tsc --noEmit`) & Production Build (`vite build`):**
   - Lệnh:
     `Set-Location d:\DuAnPhanMem\qnu-ai-platform\frontendV1; npm run typecheck; npm run build`
   - Kết quả: **PASS** (exit code 0).

---

## 4. Ranh Giới & Bảo Toàn Trạng Thái

- Không sửa bất kỳ file nào trong `backendV1/` hay `backend/`.
- Không gọi model thật, không sửa dữ liệu nguồn hay chạy lại OCR/Compiler trên DB đang chạy.
- Giữ nguyên toàn bộ thay đổi chưa commit của người dùng trong worktree.
