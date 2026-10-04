# NHẬT KÝ LÀM VIỆC: PHIÊN #260 — TÍCH HỢP HÌNH ẢNH KHUÔN VIÊN TRƯỜNG ĐẠI HỌC QUY NHƠN, LOGO CHÍNH THỨC, HỌA TIẾT LƯỚI KIẾN TRÚC & KÍNH MỜ GLASSMORPHISM

- **Thời gian**: 2026-10-04 22:45 (UTC+7)
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên (Goals)**:
  1. Giải quyết triệt để nhận xét của người dùng về giao diện `/chat` còn bị "đơn giản, thiếu màu nền và thiếu nhận diện hình ảnh Trường Đại học Quy Nhơn".
  2. **Tích hợp Hình ảnh Khuôn viên Đại học Quy Nhơn (Cinematic Campus Hero)**:
     - Tạo tài nguyên hình ảnh nhiếp ảnh kiến trúc khuôn viên ĐH Quy Nhơn tuyệt đẹp bên bờ biển Quy Nhơn xanh biếc với tòa nhà giảng đường hiện đại, thảm cỏ nhiệt đới và sinh viên dạo bước (`/images/qnu-campus-hero.jpg`).
     - Tích hợp lớp phủ Gradient kép thông minh (`Dual Directional Gradient Overlay`) đảm bảo độ tương phản hoàn hảo và dễ đọc nội dung ở cả hai chế độ Sáng (Light) và Tối (Dark).
  3. **Tích hợp Logo Chính Thức Của Trường**:
     - Thay thế các khối chữ CSS thô sơ bằng tệp logo chính thức của Trường Đại học Quy Nhơn (`/logo.png`) trên Topbar, thẻ giới thiệu trường trong Hero và chân trang bản quyền.
  4. **Họa tiết Nền Lưới Kiến Trúc & Hào Quang Ambient Radial Glow**:
     - Bổ sung họa tiết lưới kiến trúc nhẹ nhàng (`linear-gradient` 32px) tạo cảm giác không gian công nghệ số cao cấp.
     - Luồng sáng tỏa mờ Academic Teal (`oklch(0.46 0.13 160)`) từ trên đỉnh trang.
  5. **Thanh Tìm Kiếm Nổi Kính Mờ (Glassmorphic AI Search Dock)**:
     - Khung tìm kiếm phủ lớp kính mờ mờ ảo (`bg-background/95 backdrop-blur-md border border-primary/30 shadow-md`), viền phát sáng khi focus.
     - Nút "Hỏi ngay" và các chip gợi ý nhanh bo tròn thanh thoát.

---

## 1. Chi Tiết Tệp Mã Nguồn Đã Thay Đổi
- **`frontend2/public/images/qnu-campus-hero.jpg`**: Hình ảnh khuôn viên trường được lưu trữ phục vụ CDN tĩnh.
- **`frontend2/src/features/chat/public-chat-portal.tsx`**:
  - Tích hợp ảnh nền khuôn viên trường kèm hiệu ứng zoom nhẹ (`group-hover:scale-[1.01]`).
  - Tích hợp logo trường `/logo.png` sắc nét.
  - Tinh chỉnh Glassmorphism và màu nền theo tiêu chuẩn OKLCH Academic Teal.

---

## 2. Kết Quả Kiểm Thử (Verification)
- **Biome Linter**: 0 lỗi, 0 cảnh báo.
- **TypeScript Typecheck**: 100% sạch lỗi biên dịch (Exit code 0).
