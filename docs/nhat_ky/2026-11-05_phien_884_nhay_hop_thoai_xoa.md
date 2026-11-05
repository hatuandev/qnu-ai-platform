# Phiên 884 — Hộp thoại xóa không nháy và lời xác nhận ngắn

## Phạm vi và nguyên nhân

Người dùng vẫn thấy hộp thoại xóa hiện hai lần thoáng qua, yêu cầu rút gọn lời xác nhận. Giữ các sửa đổi của phiên882/883 và thay đổi chưa commit của người dùng.

Hai vấn đề bổ sung đã tái hiện bằng regression trước sửa:

- Trong bước tự chuẩn bị preview, state `busy` dùng chung khiến nút hiện “Đang xóa…” dù người dùng chưa xác nhận, rồi đổi lại “Xóa vĩnh viễn”.
- `useIsMobile` luôn khởi tạo false rồi cập nhật theo media query trong effect. Trên viewport nhỏ, ResponsiveDialog chuyển từ Dialog sang Drawer sau lần render đầu, có thể tháo/lắp portal và chạy lại hiệu ứng mở.

Không khẳng định ảnh tĩnh chứng minh số lần yêu cầu xóa thật. Kiểm chứng thực hiện trong fixture cô lập, không xóa dữ liệu ứng dụng.

## Thay đổi

- `frontendV1/src/hooks/use-mobile.ts`: đọc media query ngay khi khởi tạo state trên browser; vẫn theo dõi resize và tháo listener. SSR giữ fallback false. Không đổi breakpoint.
- `frontendV1/src/features/lifecycle/action-dialog.tsx`: giữ nhãn xác nhận trong lúc chuẩn bị preview; chỉ báo đang xóa sau khi gửi accept. Giữ disabled/aria-busy, quyền, preview/hash, xác nhận người dùng và idempotency. Bỏ dòng trạng thái chuẩn bị ở xóa nguồn để tránh thay đổi chiều cao không cần thiết.
- Lời xác nhận giữ tên tài liệu và câu “Xóa tệp gốc, các phiên bản và dữ liệu liên quan. Không thể khôi phục.” Bỏ câu hỏi trùng ý và đoạn chính sách sao lưu. Cảnh báo phụ thuộc, dừng tác vụ và ngừng phục vụ vẫn hiện khi preview có tác động tương ứng, với câu ngắn hơn. Lỗi backend vẫn được hiển thị.
- Bổ sung regression trong `frontendV1/tests/delete-confirmation-709.test.tsx`, thêm `frontendV1/tests/use-mobile-884.test.tsx`.

## Kiểm chứng thực chạy

Cwd `D:/DuAnPhanMem/qnu-ai-platform/frontendV1`:

1. Trước sửa: `npm exec -- vitest run tests/delete-confirmation-709.test.tsx tests/use-mobile-884.test.tsx --reporter=dot`: **FAIL**, exit1, 17 pass / 2 fail, đúng hai nguyên nhân trên. Log `tmp/fix-884-before.log`.
2. Sau sửa: `npm exec -- vitest run tests/delete-confirmation-709.test.tsx tests/use-mobile-884.test.tsx tests/lifecycle-operations-ui-678.test.tsx tests/legacy-source-deletions-718.test.tsx tests/v1-lifecycle-678.test.ts tests/knowledge-actions-708.test.tsx --reporter=dot`: **PASS**, exit0, **68/68** ở6 file. Chỉ cập nhật assertion microcopy đã thay, giữ các kiểm chứng callback/request/quyền/idempotency. Log `tmp/fix-884-tests.log`.
3. `npm exec -- biome check src/hooks/use-mobile.ts src/features/lifecycle/action-dialog.tsx tests/delete-confirmation-709.test.tsx tests/use-mobile-884.test.tsx`: **PASS**, exit0, không lỗi/cảnh báo.
4. `npm run build`: **PASS**, exit0, gồm TypeScript. Cảnh báo config native/chunk lớn vẫn còn. Log `tmp/fix-884-build.log`.

Cwd root:

5. `node tmp/fix-884-browser.mjs`: **PASS**, exit0 sau khi sửa lỗi resolve dependency của harness lần khởi tạo đầu. Vite/Chromium cô lập dùng SourceActions, dropdown và LifecycleActionDialog thật; auth/API là synthetic. 390px touch và1280px desktop: mở menu → một dialog mount (đếm MutationObserver) → một POST accept → polling pending/completed → tự đóng. Không gọi API ứng dụng/model. Log `tmp/fix-884-browser.log`; đã xem hai ảnh `tmp/fix-884-confirm-390.png`, `tmp/fix-884-confirm-1280.png`.
6. `git diff --check`, UTF-8 không BOM/LF: **PASS**.

Full frontend/backend và xóa dữ liệu thật: **NOT RUN**. Sáu lỗi OCR806 đã ghi ở phiên882 vẫn ngoài phạm vi. Không restart app, reset, reindex, deploy hay push.
