# Phiên 886 — Gọn thao tác bóc tách

## Yêu cầu và thay đổi

Bỏ nút Bóc tách cấp kho vì upload đã tự bóc tách. Menu duy nhất của từng tài liệu có “Xem kết quả bóc tách” và “Bóc tách lại”; áp dụng cho cả lưới và bảng.

- `frontendV1/src/features/knowledge/knowledge-detail-page.tsx`: bỏ nút/state/dialog chọn nguồn toàn kho; gắn xác nhận bóc tách lại đúng tài liệu. Bỏ hai wrapper chặn click thừa quanh SourceActions vì trigger và menu đã chặn lan truyền.
- `frontendV1/src/features/knowledge/source-actions.tsx`: đổi nhãn xem kết quả; chỉ người có quyền quản lý mới có bóc tách lại. Khóa mục này khi queued/running/dispatch_pending.
- Thêm `source-reextract-dialog.tsx`: lấy đúng revision_no hiện tại từ danh sách revision, không lấy mặc định lượt OCR cũ hoặc revision đầu tiên; xác nhận trước POST auto/force, chặn bấm lặp, giữ lịch sử và mở lượt mới. Không tự gửi lại khi lỗi; kiểm scope trước/sau bất đồng bộ.
- Xóa `extract-document-dialog.tsx` không còn được dùng; không đổi API, provider, parser hoặc cấu hình chạy. Giữ các sửa đổi khác đang có.

## Kiểm chứng thực chạy

Cwd `frontendV1`:

- `npm exec -- vitest run tests/knowledge-actions-708.test.tsx tests/knowledge-drag-and-drop.test.tsx --reporter=dot`: **PASS**, exit 0, 36/36 ca. Kiểm nút đầu trang đã bỏ, xem không POST, xác nhận một lần, đúng source/revision, queued/running/dispatch bị chặn, quyền đọc, revision thiếu/lỗi và menu bảng.
- `npm run build`: **PASS**, exit 0, gồm Vite và TypeScript. Còn cảnh báo bundle >500kB.
- `npm exec -- biome check --write src/features/knowledge/knowledge-detail-page.tsx src/features/knowledge/source-actions.tsx src/features/knowledge/source-reextract-dialog.tsx tests/knowledge-actions-708.test.tsx`: lần cuối exit 0, 0 lỗi, 1 warning optional-chain ở parentFolder đã có trước. Lượt đầu phát hiện bốn lỗi accessibility ở hai wrapper thừa; đã bỏ wrapper và kiểm lại đạt.

Cwd root:

- `node tmp/fix-886-browser.mjs`: **PASS**, exit 0, Chromium cô lập 390px touch/1280px; xem kết quả không POST, mở xác nhận không POST, xác nhận gửi đúng một POST đến revision hiện tại và tự đóng. Đã kiểm ảnh hai kích thước; ảnh mobile sau khi đợi animation cho thấy đầy đủ nút.
- `git diff --check`: **PASS**. Log/ảnh trong `tmp/check-886-*`, `tmp/fix-886-confirm-*` không đưa vào Git.

Backend/full suite **NOT RUN** vì chỉ đổi UI dùng contract hiện có. Kiểm trình duyệt dùng API tổng hợp; không bóc tách lại tài liệu thật, không gọi model hoặc thay dữ liệu ứng dụng. Không restart/reset/reindex/push. Người dùng tải lại trang để thấy menu mới.
