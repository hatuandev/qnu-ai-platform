# Nhật ký phiên 657 — Triển khai Giao diện Kho Tri Thức Giai đoạn Đầu (frontendV1)

- **Thời gian**: 2026-10-27
- **Mục tiêu**: Triển khai toàn diện giao diện Kho tri thức giai đoạn đầu trong `frontendV1`, kết nối API `backendV1` hiện có qua ranh giới transport an toàn (`/platform/v1alpha1`); hỗ trợ quản lý bộ sưu tập, tải lên nguồn tài liệu PDF/DOCX (multipart/form-data giữ nguyên bytes), quản lý lịch sử revision bất biến, tải tệp gốc qua client xác thực và xem trước PDF an toàn (Zero persistence token, Idempotency-Key 8-128 chars, scoped queries).
- **Trạng thái**: Hoàn tất triển khai và kiểm chứng 100%. Toàn bộ test suite frontend 43/43 PASS (0 fail), Biome 0 error / 0 warning, TypeScript compiler typecheck PASS.

---

## 1. Khảo sát & Đối chiếu Contract BackendV1

1. **Bộ sưu tập (`KBCollection`)**:
   - `GET /workspaces/{ws}/collections`: Danh sách phân trang (`Page[CollectionResponse]`).
   - `POST /workspaces/{ws}/collections`: Tạo mới (`name` 1-255 ký tự không rỗng, `description` tối đa 2000 ký tự).
   - `GET /workspaces/{ws}/collections/{col}`: Chi tiết bộ sưu tập.
   - `PATCH /workspaces/{ws}/collections/{col}`: Cập nhật metadata (chỉ gửi trường thay đổi; bỏ qua description để giữ nguyên, gửi `null` tường minh để xóa description).
   - Không có trường `status` và chưa có endpoint `DELETE`.
2. **Nguồn tài liệu (`KBSource`) & Revision (`KBRevision`)**:
   - `GET /workspaces/{ws}/collections/{col}/sources`: Danh sách nguồn phân trang (`Page[SourceResponse]`).
   - `POST /workspaces/{ws}/collections/{col}/sources`: Tải lên nguồn mới (`file` bắt buộc, `title` tùy chọn tối đa 255 ký tự; `multipart/form-data`).
   - `GET /workspaces/{ws}/collections/{col}/sources/{src}`: Chi tiết nguồn tài liệu.
   - `GET /workspaces/{ws}/collections/{col}/sources/{src}/revisions`: Danh sách phiên bản (mảng `KBRevision[]`, mới nhất trước).
   - `POST /workspaces/{ws}/collections/{col}/sources/{src}/revisions`: Tải lên phiên bản mới (`file` bắt buộc; **từ chối title**, không gửi trường title vào FormData; mã lỗi 422 `revision_title_not_supported` nếu có title).
   - `GET /workspaces/{ws}/collections/{col}/sources/{src}/revisions/{rev}/content`: Tải lại đúng tệp gốc dạng binary (dùng `revision_id`, không dùng `revision_no`), trả về kèm header `Content-Disposition`, `ETag`, `Content-Type`.
   - Trạng thái nguồn: `status === "stored"` hiển thị "Đã lưu tệp" (không tự gắn nhãn OCR hay indexed).

---

## 2. Các Thành Phần Đã Triển Khai

### A. Mở rộng Transport & Client v1 (`client.ts`, `endpoints.ts`, `index.ts`)
- **FormData Upload**:
  - Khi `body instanceof FormData`, client không tự gán `Content-Type: application/json` để trình duyệt tự động tạo `multipart/form-data` kèm boundary string hợp lệ.
  - Bổ sung phương thức `v1Client.upload<T>(path, formData, options)`.
- **Header `Idempotency-Key`**:
  - Hỗ trợ truyền tùy chọn `idempotencyKey` trong `V1RequestOptions`, gán header `Idempotency-Key` (8–128 ký tự).
  - Tự động giữ nguyên key khi người dùng bấm thử lại trên cùng một thao tác tải lên sau lỗi mạng; tạo key mới khi đổi tệp hoặc đổi đối tượng.
- **Binary & Blob Responses**:
  - Hỗ trợ `responseType: "blob"`. Khi thành công, đọc `response.blob()`, phân giải filename từ `Content-Disposition` (hỗ trợ cả chuẩn RFC 5987 `filename*=UTF-8''...` và `filename="..."`), lấy `contentType` và `etag`.
  - Bổ sung phương thức `v1Client.requestBlob(path, options)`.
  - **Bảo vệ lỗi HTTP**: Nếu API trả về mã lỗi (400, 401, 403, 404, 409, 413, 415, 422, 5xx), response luôn được parse `application/problem+json` và ném `ApiProblemError`, tuyệt đối không xử lý payload lỗi như là một tệp tải xuống thành công.

### B. Module Kho Tri Thức (`src/features/knowledge/`)
- `types.ts`: Định nghĩa TypeScript interfaces chuẩn cho `KBCollection`, `KBSource`, `KBRevision`, `SourceUploadResult`, `PageParams`, `PageResponse`.
- `schemas.ts`: Zod schemas cho tạo/sửa bộ sưu tập, upload nguồn, upload revision; các hàm tiện ích `formatBytes`, `formatSourceStatus`, `isPdf`, `isDocx`, `validateUploadFile` (giới hạn 60 MiB, chỉ nhận `.pdf`, `.docx`), `generateIdempotencyKey`.
- `requests.ts`: Tầng gọi API chuẩn cho tất cả các thao tác nghiệp vụ.
- `queries.ts`: TanStack Query hooks với query keys được cô lập theo `['v1', sessionId, 'workspaces', workspaceId, 'knowledge', ...]`. Hỗ trợ invalidate chính xác phạm vi sau khi tạo bộ sưu tập, sửa bộ sưu tập, tải lên nguồn mới và thêm phiên bản mới.
- `permissions.ts`: Hàm kiểm tra quyền `canManageKnowledge(role)`: chỉ cho phép `admin` và `editor` (hoặc platform workspace admin) thực hiện tạo/sửa/tải lên.
- `collection-form-dialog.tsx`: Dialog tạo và sửa bộ sưu tập, tuân thủ `ResponsiveDialogContent` `p-0 gap-0`, form native submit (hỗ trợ cả click nút và phím Enter), cơ chế so sánh gửi `null` để xóa mô tả và bỏ qua trường không đổi.
- `collections-panel.tsx`: Bảng danh sách bộ sưu tập, thanh công cụ tìm kiếm gọn, phân trang URL, chế độ hiển thị card trên mobile và table trên desktop, `EmptyState` khi chưa có dữ liệu.
- `source-upload-dialog.tsx`: Dialog tải lên nguồn tài liệu mới, tích hợp `FileUpload`, ô nhập tiêu đề tùy chọn, sinh và giữ `Idempotency-Key`, hiển thị trạng thái "Đang tải lên tệp..." trung thực (không chạy timer % giả).
- `revision-upload-dialog.tsx`: Dialog tải lên phiên bản mới, chỉ nhận tệp (không có tiêu đề), sinh và giữ `Idempotency-Key`, cập nhật lịch sử revision.
- `collection-detail-page.tsx`: Màn hình chi tiết bộ sưu tập, breadcrumb điều hướng, thẻ tổng quan, danh sách nguồn tài liệu với phân trang và tìm kiếm.
- `source-detail-page.tsx`: Màn hình chi tiết nguồn tài liệu, hiển thị SHA-256 (có nút copy hash), thông tin người tạo/ngày tạo, bảng lịch sử revision đầy đủ, và khung xem tệp:
  - **Tệp PDF**: Tải binary qua `v1Client.requestBlob` với token xác thực, sinh Object URL hiển thị inline `<iframe />`, tự động thu hồi `URL.revokeObjectURL` khi unmount hoặc đổi revision/nguồn, kèm nút tải xuống dự phòng.
  - **Tệp DOCX**: Hiển thị thông báo rõ ràng rằng trình duyệt không hỗ trợ xem DOCX trực tiếp, cung cấp nút tải tệp DOCX gốc về máy; tuyệt đối không gửi tệp ra ngoài và không giả lập scan mẫu.

### C. Điều hướng & Routing
- Thêm tab "Kho tri thức" vào `TABS` trong `workspace-detail-layout.tsx`.
- Tạo 3 route TanStack Router file-based:
  - `workspaces.$workspaceId.collections.index.tsx` -> `/workspaces/$workspaceId/collections`
  - `workspaces.$workspaceId.collections.$collectionId.index.tsx` -> `/workspaces/$workspaceId/collections/$collectionId`
  - `workspaces.$workspaceId.collections.$collectionId.sources.$sourceId.tsx` -> `/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId`
- Sinh lại `routeTree.gen.ts` sạch sẽ thông qua `@tanstack/router-generator`.
- Cập nhật ranh giới `V1_DIRECTORIES` trong `tests/template-boundary.test.ts` bổ sung `"features/knowledge/"`.

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Unit & Regression Suite (`bun test`)**:
   - `tests/v1-knowledge.test.ts` (MỚI): 7/7 test cases PASS.
     - Kiểm tra khế ước danh sách, tạo, đọc chi tiết, và PATCH description (`null` vs omission).
     - Kiểm tra upload nguồn gửi `multipart/form-data`, không có JSON header, giữ nguyên File bytes và gửi `Idempotency-Key`.
     - Kiểm tra upload revision từ chối gửi `title`.
     - Kiểm tra download binary trả về Blob kèm phân giải filename RFC 5987; kiểm tra lỗi HTTP trả về `ApiProblemError` thay vì blob.
     - Kiểm tra quy tắc validation file rỗng, dung lượng > 60 MiB, định dạng không hỗ trợ.
     - Kiểm tra phân quyền: admin/editor được ghi, member/reviewer chỉ đọc, platform admin được ghi.
     - Kiểm tra cô lập query keys theo `sessionId` và `workspaceId`.
     - Kiểm tra các endpoint đọc chi tiết (`getCollection`, `getSource`, `listSources`, `listRevisions`).
   - `tests/template-boundary.test.ts`: 5/5 PASS (KTX boundary giữ nguyên 100%).
   - `tests/v1-contract.test.ts`: 14/14 PASS.
   - `tests/v1-session-secret-regression.test.ts`: 7/7 PASS.
   - `tests/v1-sso.test.ts`: 10/10 PASS.
   - **Tổng cộng: 43 passed, 0 failed (100% PASS)**.
2. **TypeScript Typecheck (`tsc --noEmit`)**:
   - 0 errors (PASS hoàn toàn).
3. **Biome Linter & Formatter (`biome check`)**:
   - 21 files checked: 0 errors, 0 warnings (PASS hoàn toàn).

---

## 4. Các Giới Hạn Cần Lưu Ý
- **OCR, Compiler, Indexing & Chat**: Chưa triển khai trong đợt này theo yêu cầu; trạng thái hiển thị "Đã lưu tệp" (`stored`), không tự động kích hoạt background worker hay pipeline xử lý.
- **Xóa / Archive tài nguyên**: Hiện tại backendV1 chưa cung cấp endpoint `DELETE` cho Collection, Source hoặc Revision; UI không cung cấp nút xóa giả.
- **Sửa tiêu đề nguồn**: BackendV1 chưa hỗ trợ endpoint PATCH đổi title của KBSource; do đó tiêu đề được gán khi upload lần đầu.
- **Xem trước DOCX**: Không thể xem inline trực tiếp trên trình duyệt; cung cấp nút tải tệp gốc có xác thực để người dùng xem bằng Word.
