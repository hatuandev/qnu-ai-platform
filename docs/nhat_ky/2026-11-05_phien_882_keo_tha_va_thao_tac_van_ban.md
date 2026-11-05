# Phiên 882 — Kéo/thả và thao tác văn bản

## Phạm vi

Người dùng yêu cầu sửa hai điểm P2 sau khi pull mã mới. Giữ các thay đổi chưa commit đang tồn tại; chỉ sửa frontend, không đổi API, dữ liệu hoặc dịch vụ ứng dụng.

## Thay đổi

- `frontendV1/src/features/knowledge/knowledge-detail-page.tsx`: chỉ nhận thao tác kéo tài liệu được khởi tạo tại trang hiện hành. Bỏ fallback từ `text/plain`; kiểm tra quyền quản lý, mutation đang chạy, session, workspace, collection, tài liệu còn trong danh sách và đích thư mục hợp lệ. Kết thúc drag trước gọi mutation để không gửi trùng. Guard frontend không thay thế quyền server.
- `frontendV1/src/features/knowledge/document-sheet-canvas.tsx`: nút sửa và checkbox luôn hiện, không phụ thuộc hover. Thanh thao tác nằm trong luồng bố cục để không che văn bản; checkbox có khoảng trống trên màn hình nhỏ. Giữ callback và quyền sửa cũ.
- Mở rộng `frontendV1/tests/knowledge-drag-and-drop.test.tsx` đang có của người dùng; thêm `frontendV1/tests/document-sheet-canvas-accessibility-882.test.tsx`.

## Kiểm chứng thực chạy

Cwd frontend: `D:/DuAnPhanMem/qnu-ai-platform/frontendV1`.

1. Trước sửa: chạy Vitest kéo/thả, **FAIL**, exit 1: 3 pass / 3 fail. Tái hiện nhận drag bên ngoài (plain text/custom MIME) và vẫn gọi mutation khi chỉ có quyền xem.
2. Sau sửa: `npm exec -- vitest run tests/knowledge-actions-708.test.tsx tests/knowledge-drag-and-drop.test.tsx tests/ocr-original-preview.test.tsx tests/document-sheet-canvas-accessibility-882.test.tsx tests/ocr-review-ux-806.test.tsx --reporter=dot`: **FAIL**, exit 1, **52 pass / 6 fail**. Riêng kéo/thả 16/16 và canvas 2/2 đạt. Log `tmp/fix-882-tests.log`.
3. Sáu failure trùng exact test IDs với baseline `tmp/pull-review-tests.log`, đều trong `tests/ocr-review-ux-806.test.tsx`: zoom scan; case 3 integration; case 5 apply suggestion; case 7 save dialog; case 8 mobile draft; case 12 word diff/split/page navigation. Assertion cũ chờ nhãn/control đã đổi (Phóng to ảnh, microcopy quy trình/bản nháp và 50:50). Không sửa assertion, bỏ test hay retry model để làm xanh.
4. `npm run build`: **PASS**, exit 0, gồm Vite production build và TypeScript. Cảnh báo chunk lớn/native config vẫn tồn tại. Log `tmp/fix-882-build.log`.
5. `npm exec -- biome check` trên bốn file source/test trong phạm vi: **PASS**, exit 0, 0 error / 5 warning có sẵn (optional chain và non-null assertions). Chỉ format/organize imports bốn file này. Log `tmp/fix-882-biome.log`.
6. Cwd root: `node tmp/fix-882-visual.mjs`: **PASS**, exit 0. Chromium cô lập render component thật cùng CSS build: 390px có touch và 1280px desktop; nút/checkbox có opacity hiển thị, click được, Tab tới checkbox, không cuộn ngang. Đã xem ảnh `tmp/fix-882-canvas-390.png` và `tmp/fix-882-canvas-1280.png`. Không khởi động lại app hoặc kết nối backend.
7. `git diff --check`: **PASS**, exit 0.

## Giới hạn và bàn giao

Không chạy full frontend/backend hay model thật; thay đổi không chạm hợp đồng backend. Bộ test mở rộng vẫn FAIL vì sáu lỗi baseline kể trên. Dữ liệu và thay đổi ngoài phạm vi của người dùng được giữ lại. Không restart, reset, reindex hoặc push. Có thể tải lại trình duyệt trong phiên dev hiện có để dùng giao diện mới.
