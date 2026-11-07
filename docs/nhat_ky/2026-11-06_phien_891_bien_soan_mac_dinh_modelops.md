# Phiên 891 — Dùng cấu hình mặc định khi biên soạn tệp

Hộp thoại mở từ trang tài liệu dùng model mặc định của đơn vị và ngân sách token tự động. Công tắc Rà soát sau khi biên soạn nằm cùng các lựa chọn chế độ. Biên soạn AI bật rà soát theo mặc định. Chế độ nhanh dựng từ nguồn ẩn công tắc và gửi yêu cầu tắt rà soát. Chế độ nhanh có AI bổ sung hiển thị công tắc, mặc định tắt. Trang bộ sưu tập tiếp tục cung cấp cài đặt nâng cao.

- Trong `frontendV1`, `npm exec -- biome check src/features/knowledge/compilation-dialog.tsx tests/compilation-dialog-state-809.test.tsx` đạt, exit 0.
- Trong `frontendV1`, `npm exec -- vitest run tests/compilation-dialog-state-809.test.tsx tests/v1-compilation.test.ts --reporter=dot` đạt 32 ca, exit 0. Kiểm cấu hình mặc định, cờ rà soát và tùy chọn nâng cao ở trang bộ sưu tập.
- Trong `frontendV1`, `npm run build` đạt, exit 0, có cảnh báo kích thước gói của Vite.
- Từ root, `node tmp/check-891-browser.mjs` đạt ở 390 và 1280 px, exit 0. Đã xem ảnh và kiểm công tắc khi chuyển chế độ. Chưa gửi tác vụ biên soạn thật. Chưa chạy full suite và backend test.
