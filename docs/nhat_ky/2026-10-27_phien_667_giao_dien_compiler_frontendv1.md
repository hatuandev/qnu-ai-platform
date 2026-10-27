# Nhật ký phiên 667 — Triển khai Giao diện Compiler trong frontendV1

- **Thời gian**: 2026-10-27T15:05:00+07:00
- **Phạm vi**: `frontendV1`
- **Mục tiêu**: Triển khai toàn bộ giao diện Compiler hoàn chỉnh trong `frontendV1`, kết nối API thực của `backendV1` tại prefix `/platform/v1alpha1`, hỗ trợ luồng: chọn nguồn OCR completed + text version → tạo Compiler run → theo dõi tiến trình → xem bản biên soạn & dẫn chứng citations → xem bảng nguồn literal read-only → theo dõi auto-review & tạo review thủ công → xem báo cáo review hai chiều → chỉnh sửa có cấu trúc → xem trước diff trên máy chủ → xác nhận tạo bản sửa người dùng (`user_edit`). Hoàn thành chức năng và kiểm chứng đầy đủ.

---

## 1. Bối cảnh & Căn cứ kỹ thuật

- **Backend V1 Compilation API**:
  - Base $C$: `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs`
    - `POST C`: Tạo lượt biên soạn mới. Bắt buộc header `Idempotency-Key` (8-128 ký tự, không dùng tiền tố `edit:` hay `auto:`). Body: `topic` (1-2000 ký tự đã trim), `ocr_run_ids` (1-20 unique IDs thuộc cùng collection), `text_versions` (mapping run_id → version; version 0 hoặc không có mapping là OCR gốc), `provider_id` (`null` = default chat workspace), `max_output_tokens` (nullable hoặc số nguyên dương), `structured_output` (mặc định false), `auto_review` (mặc định true), `review_provider_id` (`null` = ghim provider của compiler), `review_max_output_tokens` (mặc định 8192), `review_structured_output` (mặc định false). Trả về 201 Created hoặc 200 Replay.
    - `GET C?limit=20`: Danh sách các lượt biên soạn gần nhất dạng mảng thuần, generation giảm dần, limit 1-100 (không có offset hay total, không fake server pagination).
    - `GET C/{run_id}`: Chi tiết lượt biên soạn (generation, origin, status, attempt_count, provider_id, usage_tokens, bundle_sha256, parent_run_id).
    - `GET C/{run_id}/draft`: Bản biên soạn hoàn chỉnh dạng JSON (`schema_version`, `title`, `sections`, `unknowns`, `citations`, `source_tables`, `sources`).
    - `GET C/{run_id}/markdown`: Tải Derivative Markdown trực tiếp dưới dạng `text/markdown`.
    - `GET C/{run_id}/raw`: Tải LLM raw response payload (chỉ tải chủ động; bản `origin="user_edit"` không có raw compiler).
  - Auto-review:
    - `GET C/{run_id}/auto-review`: Trạng thái lượt rà soát tự động. Trả 404 `compilation_auto_review_not_found` khi chưa có intent (run chưa tới bước schedule hoặc `auto_review=false`); không biến 404 này thành lỗi hay thành "review đạt".
  - Manual Review ($V = C$`/{run_id}/reviews`):
    - `POST V`: Tạo review thủ công (quyền admin/editor/reviewer). Bắt buộc `Idempotency-Key` (không được bắt đầu bằng `auto:`). Body: `{ provider_id: null, max_output_tokens: 8192, structured_output: false }`. `provider_id=null` dùng default chat hiện hành của workspace.
    - `GET V?limit=20&offset=0`: Danh sách các lượt review dạng mảng thuần.
    - `GET V/{review_id}`: Chi tiết một lượt review.
    - `GET V/{review_id}/report`: Báo cáo review hoàn chỉnh gồm `verdict`, `summary`, `findings`, `source_assessments`, `draft_assessments`, `limits`.
    - `GET V/{review_id}/markdown`: Tải Markdown báo cáo rà soát.
    - `GET V/{review_id}/raw`: Tải raw response của reviewer.
  - Chỉnh sửa bản biên soạn (Context → Preview → Accept):
    - `GET C/{run_id}/edit-context`: Lấy ngữ cảnh chỉnh sửa (chỉ gọi khi có quyền ghi: admin/editor). Trả `bundle_sha256`, `content`, `citations`.
    - `POST C/{run_id}/edit-previews`: Tạo bản xem trước thay đổi. Gửi `expected_bundle_sha256`, `reason` (1-2000 ký tự), `review_id` (tùy chọn), `content` (title, sections, paragraphs kèm citations, unknowns). Trả `preview_id`, `preview_sha256`, `expires_at`, `diff` từ máy chủ.
    - `POST C/{run_id}/edits`: Xác nhận áp dụng sửa đổi. Gửi `preview_id`, `preview_sha256` kèm header `Idempotency-Key`. Trả child run có `origin="user_edit"`, `parent_run_id` trỏ bản gốc, `status="completed"`.

---

## 2. Các thành phần đã triển khai

1. **API Endpoints & Transport Requests** (`frontendV1/src/app/api/v1/endpoints.ts`, `compilation-requests.ts`):
   - Đăng ký `compilationPaths` với 16 routes chuẩn mực.
   - Các hàm request typed với `V1Client`: `createCompilationRun`, `listCompilationRuns`, `getCompilationRun`, `getCompilationDraft`, `downloadCompilationMarkdownBlob`, `getCompilationRaw`, `getAutoReviewStatus`, `createCompilationReview`, `listCompilationReviews`, `getCompilationReview`, `getCompilationReviewReport`, `downloadCompilationReviewMarkdownBlob`, `getCompilationReviewRaw`, `getEditContext`, `createEditPreview`, `acceptEdit`.
   - `getAutoReviewStatus` tự động bắt 404 `compilation_auto_review_not_found` và trả `{ notScheduled: true }` trung thực.
   - `createCompilationReview` kiểm tra `validateReviewIdempotencyKey` chặn khóa bắt đầu bằng tiền tố `auto:`.

2. **Types, Validation Schemas & Permissions** (`compilation-types.ts`, `compilation-schemas.ts`, `permissions.ts`):
   - Zod schemas: `compilationRequestSchema` (topic trim 1-2000 ký tự; ocr_run_ids 1-20 không trùng; text_versions ràng buộc thuộc ocr_run_ids), `editPreviewRequestSchema`, `acceptEditSchema`, `manualReviewRequestSchema`.
   - Formatters hiển thị trung thực: `formatCompilationStatus`, `formatCompilationOrigin` (phân biệt bản AI Compiler vs Người dùng chỉnh sửa), `formatAutoReviewStatus`, `formatReviewStatus`, `formatReviewVerdict`, `formatSourceAssessmentStatus`, `formatDraftAssessmentStatus`, `formatCompilationError`.
   - Quyền hạn: `canCreateOrEditCompilation` (admin, editor), `canReviewCompilation` (admin, editor, reviewer), `canReadCompilation` (tất cả thành viên).

3. **TanStack Scoped Query Hooks** (`compilation-queries.ts`):
   - Scoped query keys ghim `sessionId`, `workspaceId`, `collectionId`, `runId`, `reviewId` chống rò rỉ session.
   - Polling an toàn với interval 3s chỉ kích hoạt khi `queued`/`running`, dừng khi terminal, đổi trang hoặc unmount.
   - Mutation hooks cấu hình `retry: 0` triệt để chống auto-retry lặp submit.

4. **Thành phần Giao diện UI**:
   - `CompilationDialog`: Form tạo lượt biên soạn với các bước chọn nguồn OCR completed theo source/revision, chọn text version (v0 OCR gốc hoặc v1, v2...), chọn model chat ModelOps hoặc default, cấu hình auto-review và reviewer.
   - `CompilationRunsList`: Bảng danh sách các lượt biên soạn gần nhất, hiển thị badge bản gốc/bản sửa người dùng, link parent run, status, tokens, và nút chuyển sang xem chi tiết.
   - `CitationDrawer`: Ngăn kéo xem chi tiết dẫn chứng với source ID, revision ID, OCR run ID, trang, block path, text review version, canonical & manifest hashes, và nút điều hướng sang màn hình đối chiếu OCR.
   - `SourceTablesView`: Bảng nguồn literal read-only bảo toàn `row_span`, `col_span`, header, ô trống, số 0, dấu gạch và liên kết dẫn chứng.
   - `CompilationReviewTab`: Quản lý rà soát đánh giá hai chiều: theo dõi auto-review, dialog tạo review thủ công, danh sách các lượt review, báo cáo chi tiết với verdict banner, số liệu tổng hợp, lọc findings, đối chiếu nguồn ↔ bản nháp kèm trích đoạn và suggested actions, disclaimer giới hạn, tải Markdown báo cáo.
   - `CompilationEditorTab`: Trình chỉnh sửa có cấu trúc (quyền admin/editor) tải edit-context, sửa title, thêm/xóa mục và đoạn văn, chọn citations từ server, sửa unknowns, nhập lý do chỉnh sửa; modal xem trước diff trước/sau từ server trả về, kiểm tra hạn `expires_at`, và xác nhận tạo bản mới `POST edits`.
   - `CompilationDetailPage`: Trang chi tiết lượt biên soạn độc lập với breadcrumbs, summary header card, alert trạng thái khi đang xử lý, tabs điều hướng, tải Markdown/JSON và xem raw LLM.
   - Tích hợp vào `CollectionDetailPage`: Tab "Tài liệu nguồn" vs "Biên soạn tri thức", gắn kết dialog tạo biên soạn.
   - Nút "Dùng để biên soạn": Tích hợp trên `OcrRunsList` (lượt completed) và `OcrTextReviewPanel` (truyền chính xác text version v0 hoặc v1..vN đang xem).

5. **Routes**:
   - `/workspaces/:workspaceId/collections/:collectionId/compilations`: Danh sách các lượt biên soạn gần nhất và trigger dialog tạo.
   - `/workspaces/:workspaceId/collections/:collectionId/compilations/:runId`: Trang chi tiết lượt biên soạn độc lập.

---

## 3. Kết quả kiểm chứng

- **Unit & Contract Tests** (`frontendV1/tests/v1-compilation.test.ts`):
  - Chạy bằng `node --experimental-strip-types --test`:
  - **23/23 tests PASS (0 fail, 0 skipped, 281ms)**:
    - 4 tests Zod request schema (topic trim, ocr_run_ids bounds, text_versions mapping subset).
    - 3 tests Edit Preview, Accept Edit và Manual Review schemas.
    - 2 tests Idempotency key generation & validation (chặn `auto:`, `edit:`).
    - 7 tests Formatters cho trạng thái, nguồn gốc, verdict, assessments hai chiều, và mã lỗi RFC 7807.
    - 3 tests Role permissions (`canCreateOrEditCompilation`, `canReviewCompilation`, `canReadCompilation`).
    - 4 tests Mock HTTP transport requests (header Idempotency-Key, Bearer auth, query limit, bắt 404 auto-review).
- **TypeScript Typecheck**:
  - `tsc --noEmit` hoàn tất với **0 lỗi**.
- **Linter & Formatter**:
  - `npx biome check` trên toàn bộ 19 tệp nguồn hoàn tất với **0 lỗi** (Checked 19 files, 0 errors).
- **Production Build**:
  - `npm run build` (`vite build && tsc --noEmit`) hoàn tất thành công (**exit code 0**).

---

## 4. Ranh giới bàn giao

- **Đã hoàn thành**:
  - Luồng biên soạn tri thức hoàn chỉnh từ chọn nguồn OCR → tạo Compiler → theo dõi → xem bản biên soạn & dẫn chứng → bảng nguồn read-only → xem auto-review & review thủ công → chỉnh sửa có cấu trúc → xem trước diff server → xác nhận tạo bản sửa `user_edit`.
- **Chưa thực hiện (đúng theo phạm vi yêu cầu)**:
  - Đăng ký compiled document.
  - Phê duyệt / xuất bản tài liệu biên soạn.
  - Embedding / index / search tài liệu biên soạn.
  - Tự cập nhật nội dung đang phục vụ Chat.
  - Xóa, hủy hoặc các thao tác lifecycle khác trên compilation run.
