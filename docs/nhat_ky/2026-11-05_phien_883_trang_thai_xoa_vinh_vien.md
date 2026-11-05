# Phiên 883 — Trạng thái xóa vĩnh viễn

## Yêu cầu và nguyên nhân

Người dùng phản ánh xóa vĩnh viễn chuyển qua nhiều bước giao diện. Kiểm tra mã cho thấy thao tác đã có một lần xác nhận, backend xử lý purge nền. Tuy nhiên, `useLifecycleAction` nhận nguyên trạng kết quả GET: một phản hồi preview cũ sau POST accept có thể ghi đè pending, hiện nút “Thử lại cùng thao tác” và làm dừng polling. Accept cũng invalidate cả biên nhận vừa ghi, tạo lượt đọc lại không cần thiết. Nhãn nút chuyển từ “Đang xác nhận…” sang “Đang xóa…” làm tăng cảm giác nhiều bước.

Hai regression mô phỏng phản hồi chậm/stale đã FAIL đúng nguyên nhân trước sửa (14 pass / 2 fail, exit 1). Đây là bằng chứng tái hiện qua client và component, không phải log của lần xóa thật của người dùng.

## Thay đổi có phạm vi

- `frontendV1/src/features/lifecycle/queries.ts`: sau GET, đọc cache của đúng session/workspace/action; không cho preview cũ thay thế biên nhận đã chuyển trạng thái. Giữ pending để polling tiếp và vẫn nhận completed/error thật. Lỗi HTTP không bị đổi thành thành công.
- `frontendV1/src/features/lifecycle/action-dialog.tsx`: không invalidate các lifecycle receipt sau accept. Nút nguồn giữ “Đang xóa…” ngay từ khi gửi xác nhận đến khi backend hoàn tất. Microcopy nói rõ không cần xác nhận thêm.
- `frontendV1/tests/delete-confirmation-709.test.tsx`: kiểm tra stale read, accept chậm/khóa gửi trùng, polling đến hoàn tất và lỗi worker thật cho phép thử lại cùng idempotency key. Giữ các test quyền, logout, hết hạn, preview cũ và lỗi mạng.

Không đổi contract/API/backend, quyền, preview hash hay cơ chế xóa dữ liệu. Không xóa tài liệu thật, reset, restart, reindex hoặc push; giữ thay đổi chưa commit có trước.

## Kiểm chứng

Cwd `D:/DuAnPhanMem/qnu-ai-platform/frontendV1`:

- `npm exec -- vitest run tests/delete-confirmation-709.test.tsx tests/lifecycle-operations-ui-678.test.tsx tests/legacy-source-deletions-718.test.tsx tests/v1-lifecycle-678.test.ts tests/knowledge-actions-708.test.tsx --reporter=dot`: **PASS**, exit 0, **66/66** ca ở 5 file. Log `tmp/fix-883-tests.log`.
- `npm run build`: **PASS**, exit 0, gồm TypeScript; vẫn có cảnh báo config native/chunk lớn. Log `tmp/fix-883-build.log`.
- `npm exec -- biome check src/features/lifecycle/action-dialog.tsx src/features/lifecycle/queries.ts tests/delete-confirmation-709.test.tsx`: **PASS**, exit 0, không lỗi/cảnh báo.
- Cwd root, `git diff --check`: **PASS**, exit 0. File sửa UTF-8 không BOM/LF.

Full frontend/backend và xóa dữ liệu ứng dụng thật: **NOT RUN**. Kết quả trên không tuyên bố nghiệm thu purge storage/vector thật. Sáu failure OCR806 của phiên882 nằm ngoài bộ test này và chưa sửa.

## Cách dùng

Tải lại trang dev, chọn menu xóa, xác nhận một lần. Hộp thoại theo dõi cùng yêu cầu rồi đóng khi xác nhận purge hoàn tất. Backend vẫn cần thời gian dừng tác vụ/dọn dữ liệu; lỗi thật được báo và cho phép người dùng chủ động tiếp tục cùng thao tác.
