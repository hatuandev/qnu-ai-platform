# Phiên 895 — Đóng bảng biên soạn

- Yêu cầu: thêm nút tắt bảng tiến độ. Thêm nút × ở đầu bảng, riêng với nút thu gọn để không lồng button; dùng Button/Lucide và tên truy cập rõ ràng.
- `compilation-activity.tsx`: `dismissAll` bỏ danh sách theo dõi trong phiên; không gọi API dừng, xóa hoặc tạo lại job. Lượt mới vẫn tự mở bảng. `compilation-activity-panel.tsx` gắn nút cả khi mở và thu gọn.
- Kiểm chứng từ `frontendV1`: Biome 3 file exit0; Vitest activity894/dialog809/tabs849 **26 PASS**, exit0 (hai ca mới: đóng nhiều lượt đang chạy rồi mở lượt mới; đóng khi thu gọn/hoàn tất). `npm run build` gồm TypeScript **PASS**, exit0; còn cảnh báo chunk lớn/config native cũ.
- Chromium cô lập3095, API giả lập trong fixture: **PASS** ở390/1280px; đã xem ảnh, nút luôn trong màn hình, đóng cả mở/thu gọn và mở lại bảng. Receipt `tmp/check-895-browser-receipt.json`, ảnh `tmp/check-895-close-{390,1280}.png`. Đã dừng server cô lập và gỡ fixture.
- Không đổi backend/DB/model/dịch vụ app hoặc push. Không chạy full FE/BE lại cho thay đổi này; full FE ở phiên894 vẫn có10 failure ngoài phạm vi, không coi gate toàn repo PASS. Giữ mọi sửa đổi sẵn có.
