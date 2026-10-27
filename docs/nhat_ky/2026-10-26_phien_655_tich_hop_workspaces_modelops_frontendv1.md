# Nhật ký phiên 655 — Tích hợp Workspaces & ModelOps frontendV1

- **Thời gian**: 2026-10-26
- **Mục tiêu**: Hoàn thiện tích hợp Workspaces và ModelOps trong frontendV1, giải quyết triệt để rò rỉ secret trong mutation cache, cô lập phiên (session isolation), bảo toàn draft, cấu trúc form submit, đối chiếu contract quota, và dọn sạch linter Biome.
- **Trạng thái**: Hoàn tất phần mã nguồn, test suite 26/26 PASS, Biome 0 errors / 0 warnings, TypeScript typecheck PASS.

## 1. Các vấn đề cốt lõi đã giải quyết

### A. Triệt tiêu Secret trong MutationCache
- **Hiện tượng**: TanStack Query lưu payload gửi vào `mutateAsync(variables)` tại `mutation.state.variables`. Khi tạo hoặc rotate key, secret bị lưu trong MutationCache kể cả sau khi đóng dialog.
- **Giải pháp**:
  - Tại `useCreateProviderKey` và `useRotateProviderKey` (`src/features/modelops/queries.ts`), trích xuất `secret` rồi xóa thuộc tính `secret` trực tiếp trên đối tượng đầu vào (`delete input.secret` / `delete args.input.secret`) trước khi gọi API.
  - Thêm `onSettled` dọn dẹp dự phòng trên mutation state.
  - Đảm bảo secret không xuất hiện trong URL, query key, localStorage, toast hay log.
- **Kiểm chứng**: Unit test `tests/v1-session-secret-regression.test.ts` kiểm tra trực tiếp trên `queryClient.getMutationCache().getAll()` sau cả hai trường hợp success và failure. Kết quả: `variables.secret === undefined`.

### B. Cô lập phiên làm việc (Session Isolation & Pinning)
- **Hiện tượng**: Callback 401 của client gọi `clearAccessToken` mà không gắn phiên; request từ phiên cũ trả về 401 sẽ làm xóa token của phiên mới vừa đăng nhập. Response chậm từ phiên cũ có thể đẩy dữ liệu cũ vào cache phiên mới.
- **Giải pháp**:
  - `session-token.ts`: Thêm `sessionId` tăng đơn điệu; `clearAccessToken` nhận `{ sessionId?: number; expired?: boolean }`. Nếu `sessionId` không khớp phiên hiện tại, thao tác xóa bị bỏ qua.
  - `client.ts`: Ghim `startingSessionId` khi bắt đầu request. Khi response trả về, nếu `getSessionId() !== startingSessionId`, request lập tức bị hủy với lỗi `ApiProblemError({ code: "session_aborted" })`, ngăn chặn dữ liệu cũ rò rỉ vào phiên mới.
  - Scoped Query Keys: Mọi query key của Workspaces và ModelOps được gắn `sessionId` (`["v1", sessionId, ...]` thay vì `token`).
  - `V1AuthProvider` (`src/app/auth/v1/provider.tsx`): Khi đăng nhập/đăng xuất/chuyển phiên, tự động hủy và xóa sạch query cache v1 (`cancelQueries`, `removeQueries`) và dọn sạch `MutationCache`. Hàm `isValidActor` xác thực danh tính từ `/auth/me` (yêu cầu `actor_id`, `username`, `authenticated === true`).

### C. Cấu trúc Dialog & Form Submit thực tế
- **Hiện tượng**: Trong `key-dialogs.tsx`, thẻ `<form>` bọc ngoài `DialogShell`, trong khi `ResponsiveDialogContent` của Radix render qua Portal ra `document.body`. Điều này làm các input và button nằm ngoài `<form>` trong DOM thực tế, khiến click submit và phím Enter không kích hoạt form submit.
- **Giải pháp**:
  - Cấu trúc lại `DialogShell` để thẻ `<form>` nằm bên trong `<ResponsiveDialogContent>`.
  - Input và Submit Button là con trực tiếp của `<form>`, hỗ trợ cả Dialog (desktop) và Drawer (mobile).
  - Thêm `handleClose()` reset toàn bộ form, mutation state và server error khi đóng dialog.
  - Bổ sung `form.reset(...)` khi mở lại dialog trong `workspace-form-dialog.tsx`, `member-form-dialog.tsx`, và `provider-form-dialog.tsx`, tránh giữ lại dữ liệu cũ hoặc server error của lần mở trước.

### D. Đối chiếu Contract Quota & Workspace State
- **Quota**:
  - Phân biệt rõ `quota.configured === false` (chưa cấu hình hạn mức) với `quota.configured === true && monthly_token_limit === null` (đã cấu hình nhưng không giới hạn token) và `monthly_token_limit !== null` (giới hạn cụ thể).
  - Thêm validate số nguyên không âm và giới hạn tối đa `10^15` (1.000.000.000.000.000) theo schema backendV1 (`ge=0, le=10**15`).
  - Xóa cụm từ "trong kỳ này" ở mô tả usage rỗng vì endpoint `GET /usage` không lọc theo kỳ.
  - Reset `limitDraft` và `blockedDraft` khi `workspaceId` thay đổi.
- **Model Allowlist & Defaults**:
  - Reset draft và confirmation dialog khi `workspaceId` thay đổi.
  - Dùng `dirtyRef` và `draftRef` để bảo vệ draft: background refetch không ghi đè draft đang sửa của người dùng.
  - Loại bỏ các provider đang tắt (`is_active: false`) hoặc thiếu capability khỏi danh sách lựa chọn model mặc định.

### E. Linter & Documentation Hygiene
- **Biome**: Khắc phục 3 lỗi ban đầu (`v1-live-notice.tsx`, `navigation/utils.ts`, `routes/__root.tsx`), loại bỏ khai báo trùng lặp `baseline`/`dirty`, bổ sung dependencies cho hooks. Kết quả: 18 file v1 kiểm tra đạt 0 errors, 0 warnings.
- **README.md & AGENTS.md**: Cập nhật làm rõ ranh giới:
  - Workspaces (`/workspaces`), ModelOps (`/modelops`), v1 API (`/platform/v1alpha1`) là các module đã tích hợp thực tế với backendV1.
  - Các màn hình KTX còn lại tiếp tục là bản mẫu UI (bị `backend-fetch.ts` chặn egress).

## 2. Kết quả kiểm chứng (Quality Gates)

| Gate | Lệnh / Công cụ | Kết quả | Ghi chú |
|---|---|---|---|
| Unit / Regression Tests | `bun test` | **PASS** (26/26 tests across 3 files, 0 fail) | Bao gồm 7 test hồi quy mới cho session isolation, 401 race condition, secret purging, actor validation, quota bounds, inactive provider filter, workspace draft reset. |
| Linter | `bun ./node_modules/@biomejs/biome/bin/biome check <v1 files>` | **PASS** (0 errors, 0 warnings) | Kiểm tra 18 tệp thuộc phạm vi v1 và tích hợp. |
| TypeScript Typecheck | `bun ./node_modules/typescript/bin/tsc --noEmit` | **PASS** (exited with code 0) | Không có lỗi kiểu dữ liệu. |
| Browser / API Thật | Manual / Network | **NOT RUN** | Do backendV1 chưa khởi chạy dịch vụ local tại thời điểm kiểm tra; tất cả contract được kiểm chứng thông qua mock fetch sát với contract backendV1. |
