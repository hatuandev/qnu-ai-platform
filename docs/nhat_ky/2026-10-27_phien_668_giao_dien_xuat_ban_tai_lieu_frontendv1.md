# Nhật ký phiên 668 — Triển khai Giao diện Quản lý Phiên bản và Xuất bản Tài liệu Biên soạn trong frontendV1

- **Thời gian**: 2026-10-27T15:45:00+07:00
- **Phạm vi**: `frontendV1`
- **Mục tiêu**: Triển khai toàn bộ giao diện quản lý phiên bản và xuất bản tài liệu biên soạn (`compiled-documents`) trong `frontendV1`, kết nối API thực của `backendV1` tại prefix `/platform/v1alpha1`, hỗ trợ luồng: Compiler completed → đăng ký tài liệu/phiên bản → đọc báo cáo review và giải trình findings qua cổng rà soát (Review Gate) → xem trước quyết định duyệt (Decision Preview) → xác nhận duyệt → xem trước xuất bản → xác nhận xuất bản → xem bản xuất bản hiện hành và lịch sử quyết định → xem trước & xác nhận thu hồi phiên bản (Withdraw). Hoàn thành chức năng và kiểm chứng đầy đủ.

---

## 1. Bối cảnh & Căn cứ kỹ thuật

- **Backend V1 Publication API**:
  - Tiền tố $P$: `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/compiled-documents`
    - `POST P`: Tạo tài liệu và phiên bản đầu tiên. Bắt buộc header `Idempotency-Key`. Body: `document_key` (regex `^[a-z0-9][a-z0-9_.-]*$`, 1-120 ký tự), `title` (trim 1-255 ký tự), `compilation_run_id` (1-64 ký tự). Trả về 201 Created hoặc 200 Replay.
    - `GET P?limit=20&offset=0`: Danh sách tài liệu dạng mảng thuần, sắp xếp theo `created_at`/`id` tăng dần.
    - `GET P/{document_id}`: Metadata chi tiết tài liệu.
    - `POST P/{document_id}/versions`: Thêm phiên bản mới vào tài liệu có sẵn từ một Compiler run completed. Bắt buộc header `Idempotency-Key`. Body: `{ compilation_run_id: string }`.
    - `GET P/{document_id}/versions?limit=20&offset=0`: Danh sách phiên bản dạng mảng thuần, sắp xếp theo `version_no` giảm dần.
    - `GET P/{document_id}/versions/{version_id}`: Metadata chi tiết phiên bản (status: `draft`, `approved`, `published`, `superseded`, `withdrawn`).
    - `GET P/{document_id}/versions/{version_id}/draft`: Nội dung draft bất biến (sections, paragraphs, citations, source_tables, unknowns).
    - `GET P/{document_id}/versions/{version_id}/review-gate`: Lấy dữ liệu rà soát do máy chủ chọn cho phiên bản mục tiêu (`review_id`, `report_sha256`, `bundle_sha256`, `verdict`, `findings`).
    - `POST P/{document_id}/versions/{version_id}/decision-preview`: Tạo bản xem trước quyết định hành chính (`action`: `"approve"` | `"publish"` | `"withdraw"`, `reason`: 1-1000 ký tự; với `approve`, bắt buộc gửi `review_ack` gồm `review_id`, `report_sha256`, `confirmed_reviewed: true`, và `resolutions` giải trình đủ 100% findings). Trả về `preview_id` (thuộc tính `id`), `preview_sha256`, `expires_at`, các kỳ vọng sequence.
    - `POST P/{document_id}/versions/{version_id}/decisions`: Ghi nhận quyết định chính thức. Bắt buộc header `Idempotency-Key`. Body: `{ preview_id: string, preview_sha256: string }`.
    - `GET P/{document_id}/history?limit=50&offset=0`: Lịch sử quyết định dạng mảng thuần, sắp xếp theo `document_sequence` tăng dần.
    - `GET P/{document_id}/published`: Bản đang xuất bản hiện hành (`document`, `version`, `decision`, `content`). Trả 404 `published_compilation_not_found` nếu chưa có bản xuất bản.
- **Ranh giới & Quy tắc nghiệp vụ**:
  - Không nhầm lẫn các cấp định danh: KB source ID, OCR run ID, Compiler run ID, Compiled document ID, Compiled version ID.
  - Phân quyền theo ranh giới workspace của v1:
    - Đọc (`canReadCompiledDocuments`): admin, editor, reviewer, member.
    - Đăng ký tài liệu / phiên bản (`canRegisterCompiledDocument`): admin, editor.
    - Duyệt phiên bản (`canApproveCompiledVersion`): admin, reviewer.
    - Xuất bản phiên bản (`canPublishCompiledVersion`): admin.
    - Thu hồi phiên bản (`canWithdrawCompiledVersion`): admin.
    - Platform admin: bypass toàn bộ.
  - Cổng rà soát (Review Gate):
    - Máy chủ chọn review completed khớp đúng `bundle_sha256`, `input_sha256`, `draft_sha256`.
    - Checkbox "Tôi đã đọc và xem xét đầy đủ báo cáo rà soát" mặc định chưa tick (`false`), bắt buộc tick để tiếp tục.
    - Bắt buộc giải trình 100% findings từ máy chủ (chọn `accepted_risk` | `not_an_issue`, nhập lý do 10-2000 ký tự). Không cho thiếu, thừa hay trùng finding ID; không có tùy chọn "Đã sửa".
  - Thu hồi (Withdraw):
    - Áp dụng cho phiên bản `approved` hoặc `published`.
    - Không bắt buộc qua review gate (vẫn thao tác được ngay cả khi draft/review gặp lỗi).
    - Không tự động khôi phục bản cũ; muốn xuất bản lại bản cũ phải thực hiện quy trình duyệt và xuất bản lại.
  - Quản lý xung đột và Idempotency:
    - Xử lý mã RFC 7807: `compiled_document_key_exists`, `compiled_run_registered`, `publication_review_required`, `publication_approval_required`, `publication_transition_invalid`, `publication_preview_expired`, `published_compilation_not_found`, `idempotency_conflict`.

---

## 2. Các thành phần đã triển khai

1. **API Endpoints & Transport Requests** (`frontendV1/src/app/api/v1/endpoints.ts`, `publication-requests.ts`):
   - Đăng ký `compiledDocumentPaths` với 10 endpoint paths chuẩn: `documents`, `document`, `versions`, `version`, `versionDraft`, `versionReviewGate`, `decisionPreview`, `decisions`, `history`, `published`.
   - Các hàm request typed với `V1Client`: `createCompiledDocument`, `listCompiledDocuments`, `getCompiledDocument`, `createCompiledVersion`, `listCompiledVersions`, `getCompiledVersion`, `getCompiledVersionDraft`, `getCompiledVersionReviewGate`, `createDecisionPreview`, `commitDecision`, `getCompiledDocumentHistory`, `getPublishedCompiledDocument`.
   - `getPublishedCompiledDocument` tự động bắt 404 `published_compilation_not_found` và trả `null` an toàn.

2. **Types, Validation Schemas & Permissions** (`publication-types.ts`, `publication-schemas.ts`, `permissions.ts`):
   - Types: `CompiledDocumentStatus`, `DecisionAction`, `DocumentResponse`, `VersionResponse`, `RegistrationResponse`, `FindingResolutionInput`, `ReviewAckInput`, `ReviewGateFinding`, `ReviewGateResponse`, `DecisionPreviewRequest`, `DecisionPreviewResponse`, `DecisionCommitRequest`, `DecisionResponse`, `PublishedResponse`.
   - Zod schemas: `createDocumentSchema` (validate key regex `^[a-z0-9][a-z0-9_.-]*$`, trim title 1-255), `registerVersionSchema`, `findingResolutionSchema`, `reviewAckSchema` (ràng buộc `confirmed_reviewed: true`), `decisionPreviewSchema`, `decisionCommitSchema`.
   - Tiện ích: `slugifyKey` tự động tạo key chuẩn URL từ tiêu đề tiếng Việt (bỏ dấu, chuyển ký tự đặc biệt, gọt sạch dấu gạch đầu cuối).
   - Formatters hiển thị trung thực: `formatPublicationStatus`, `formatDecisionAction`, `formatPublicationError`.
   - Quyền hạn: `canRegisterCompiledDocument`, `canApproveCompiledVersion`, `canPublishCompiledVersion`, `canWithdrawCompiledVersion`, `canReadCompiledDocuments`.

3. **TanStack Scoped Query & Mutation Hooks** (`publication-queries.ts`):
   - Scoped query keys ghim `sessionId`, `workspaceId`, `collectionId`, `documentId`, `versionId` chống rò rỉ session.
   - Query hooks: `useCompiledDocumentsQuery`, `useCompiledDocumentQuery`, `useCompiledVersionsQuery`, `useCompiledVersionQuery`, `useCompiledVersionDraftQuery`, `useCompiledVersionReviewGateQuery`, `usePublishedCompiledDocumentQuery`, `useCompiledDocumentHistoryQuery`.
   - Mutation hooks: `useCreateCompiledDocumentMutation`, `useCreateCompiledVersionMutation`, `useDecisionPreviewMutation`, `useCommitDecisionMutation` (cấu hình `retry: 0` triệt để chống double-submit).

4. **Thành phần Giao diện UI**:
   - `RegisterDocumentDialog`: Form mở từ Compiler completed run hoặc chi tiết tài liệu, hỗ trợ 2 chế độ:
     - "Tạo tài liệu mới": nhập tiêu đề, document_key (có nút gợi ý tự động từ tiêu đề).
     - "Thêm phiên bản mới vào tài liệu có sẵn": danh sách dropdown tài liệu trong kho.
     - Khóa submit với `Idempotency-Key`, hiển thị thông điệp RFC 7807 rõ ràng khi key trùng hoặc run đã đăng ký.
   - `CompiledDocumentsList`: Danh sách tài liệu biên soạn trong collection, hiển thị tiêu đề, key, sequence thay đổi, ngày tạo và nút điều hướng chi tiết.
   - `CompiledDocumentDetailPage`: Trang chi tiết tài liệu biên soạn với breadcrumbs, card metadata tài liệu, hero card hiển thị phiên bản đang xuất bản hiện hành (hoặc thông báo chưa có bản xuất bản), tabs điều hướng giữa "Danh sách phiên bản" và "Lịch sử quyết định".
   - `CompiledVersionDetailPage`: Trang chi tiết phiên bản độc lập với thông tin version_no, status badge, liên kết ngược tới Compiler run gốc, các mã hash SHA-256 (`bundle_sha256`, `draft_sha256`), toolbar hành động theo quyền (Approve / Publish / Withdraw), và trình hiển thị nội dung draft bất biến kèm dẫn chứng citation drawer và bảng số liệu gốc literal tables.
   - `ReviewGateDialog`: Modal Cổng rà soát duyệt phiên bản tải dữ liệu từ máy chủ, hiển thị verdict mô hình (kèm chú thích chỉ mang tính tham khảo), checkbox xác nhận đã xem bắt buộc, bảng giải trình từng finding với 2 lựa chọn (`accepted_risk` | `not_an_issue`) kèm lý do tối thiểu 10 ký tự, lý do duyệt chung, và nút xem trước quyết định duyệt.
   - `DecisionConfirmDialog`: Modal xác nhận quyết định hiển thị preview chính xác từ máy chủ (`preview_id`, `preview_sha256`, `action`, `reason`, `expires_at`, các sequence kỳ vọng), cảnh báo tác động xuất bản/thu hồi, và nút xác nhận thực hiện gửi `POST decisions` kèm `Idempotency-Key`.
   - Tích hợp vào `CollectionDetailPage`: Bổ sung Tab thứ 3 "Tài liệu biên soạn" bên cạnh "Tài liệu nguồn" và "Biên soạn tri thức".
   - Tích hợp vào `CompilationDetailPage`: Bổ sung nút "Đăng ký thành tài liệu biên soạn" khi lượt compiler ở trạng thái `completed`.

5. **Routes**:
   - `/workspaces/:workspaceId/collections/:collectionId/documents`: Danh sách tài liệu biên soạn trong kho.
   - `/workspaces/:workspaceId/collections/:collectionId/documents/:documentId`: Chi tiết tài liệu biên soạn, phiên bản hiện hành, danh sách versions và lịch sử quyết định.
   - `/workspaces/:workspaceId/collections/:collectionId/documents/:documentId/versions/:versionId`: Chi tiết phiên bản, draft viewer, review-gate / preview / commit action dialogs.

---

## 3. Kết quả kiểm chứng

- **Unit & Contract Tests** (`frontendV1/tests/v1-publication.test.ts`):
  - 24/24 tests PASS:
    - Validation `createDocumentSchema`, regex key, empty/whitespace title.
    - Validation `registerVersionSchema`.
    - Chuyển đổi slug tiếng Việt qua `slugifyKey`.
    - Ràng buộc độ dài và enum của `findingResolutionSchema`.
    - Bắt buộc `confirmed_reviewed: true` trong `reviewAckSchema`.
    - Validation các action hợp lệ trong `decisionPreviewSchema` và từ chối action lạ (như reject).
    - Validation mã hash trong `decisionCommitSchema`.
    - Formatters status, action, RFC 7807 errors.
    - Kiểm tra phân quyền chính xác cho 5 helper quyền theo đúng ranh giới workspace backendV1.
    - Kiểm tra HTTP transport gửi `Idempotency-Key`, URL paths, query parameters và bắt 404 published document trả `null`.
- **Hồi quy toàn bộ Test Suite** (`v1-publication.test.ts` + `v1-compilation.test.ts`):
  - 47/47 tests PASS 100%.
- **Biome Linter & Formatter**:
  - Kiểm tra 20 file: 0 errors, 0 warnings, formatting sạch 100%.
- **TypeScript Typecheck** (`npm run typecheck` / `tsc --noEmit`):
  - 0 lỗi TypeScript strict.
- **Production Build** (`npm run build` / `vite build && tsc --noEmit`):
  - Vite build thành công, plugin TanStack Router tự động quét sinh lại `routeTree.gen.ts`, chunk bundle `workspaces._workspaceId.collections._collectionId.documents.*` được đóng gói hoàn chỉnh.
