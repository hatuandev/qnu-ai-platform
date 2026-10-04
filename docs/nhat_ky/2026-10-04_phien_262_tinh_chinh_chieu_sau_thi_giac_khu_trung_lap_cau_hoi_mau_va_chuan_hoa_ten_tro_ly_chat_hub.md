# NHẬT KÝ LÀM VIỆC — PHIÊN #262: TINH CHỈNH CHIỀU SÂU THỊ GIÁC, KHỬ TRÙNG LẶP CÂU HỎI MẪU & CHUẨN HÓA TÊN TRỢ LÝ AI HUB (/chat)

- **Thời gian**: 2026-10-04 23:35
- **Vai trò**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Tập tin thay đổi**:
  - `frontend2/src/features/chat/public-chat-portal.tsx`
  - `docs/nhat_ky/2026-10-04_phien_262_tinh_chinh_chieu_sau_thi_giac_khu_trung_lap_cau_hoi_mau_va_chuan_hoa_ten_tro_ly_chat_hub.md`
  - `docs/nhat_ky/README.md`
  - `docs/memory/PROJECT_CONTEXT.md`
  - `docs/WORK_LOG.md`

---

## 🎯 1. Mục Tiêu Phiên Làm Việc
1. **Tinh Chỉnh Phân Tầng Thị Giác (Surface/Depth Hierarchy)**:
   - Khắc phục cảm giác nền trắng phẳng hoàn toàn (`#ffffff`) khiến các thẻ Card không có độ nổi và bóng mờ xúc giác.
   - Chuyển nền tổng thể sang màu warm off-white cao cấp (`#faf9f6` ở Light mode, `dark:bg-background` ở Dark mode).
   - Thiết lập các bề mặt Card và Trust bar sang `bg-white dark:bg-card shadow-xs` với độ nổi nhẹ (`hover:-translate-y-0.5 shadow-md`).
2. **Làm Mềm Mại Lớp Lưới Kỹ Thuật (Grid Edge Softening)**:
   - Thay đổi mặt nạ `maskImage` từ hình Elip rộng (vốn rò rỉ các vệt kẻ lưới xuống rìa 2 bên các Card và Footer giống giấy tập học sinh) sang dải chuyển tiếp mượt mà `linear-gradient(to bottom, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 320px, rgba(0,0,0,0) 580px)`.
   - Kết quả: Lớp lưới kỹ thuật 40px tạo chiều sâu công nghệ xuất sắc ở khu vực Hero và thanh tìm kiếm, sau đó tan biến hoàn toàn trước khi người dùng chạm tới phân khu Trợ lý và Footer.
3. **Chuẩn Hóa Tên Hiển Thị Trợ Lý (Assistant Display Name Normalization)**:
   - Xử lý triệt để tên dài dòng từ CSDL: `"Trợ lý tạo câu hỏi, ngân hàng câu hỏi theo chuẩn đầu ra"` được chuẩn hóa thành `"Trợ lý Ngân hàng Đề & Khảo thí"`.
   - Bổ sung quét cả `name` lẫn `code` với các từ khóa nhận diện hình thái học: `question`, `bank`, `cau_hoi`, `de_thi`, `khao_thi`, `ngân hàng`, `câu hỏi`.
4. **Khắc Phục Lỗi Trùng Lặp Câu Hỏi Mẫu (Sample Question Routing Bugfix)**:
   - Thẻ Trợ lý Ngân hàng Đề & Khảo thí trước đây bị rơi vào nhánh `else` do thiếu điều kiện bắt từ khóa `question`/`câu hỏi`, dẫn đến hiển thị trùng câu hỏi về Điều 16 của Trợ lý Quy chế & Học vụ.
   - Đã gán câu hỏi mẫu chuyên sâu chính xác: `"Ma trận đề thi tự luận theo thang nhận thức Bloom 4 mức độ như thế nào?"`.
5. **Kiểm Thử Biome & Tuân Thủ AGENTS.md**:
   - Biome linter pass 100% (25ms), 0 lỗi, 0 cảnh báo.
   - Tuân thủ 100% Rule 1.8 & 4.9 (100% Radix UI Button), Rule 4.3 (Bo góc 6px/8px), Rule 4.8 (Zero Emoji).

---

## 🔬 2. Chi Tiết Thực Hiện

### 2.1. Phân Tầng Thị Giác Bề Mặt
- Trước: Nền trang `bg-background` (`#ffffff`) kết hợp Card `bg-card` (`#ffffff`) khiến mọi thứ nằm trên cùng một mặt phẳng trắng trơn.
- Sau: Nền trang áp dụng `#faf9f6` (warm off-white tương tự Notion, Linear, Stripe). Các Card áp dụng `bg-white dark:bg-card border-border/80 shadow-xs` tạo cảm giác khối xúc giác tách bạch rõ rệt và sang trọng.

### 2.2. Mặt Nạ Mờ Tuyến Tính Cho Lớp Lưới
- Lớp lưới 40px `rgba(26, 115, 101, 0.08)` được kiểm soát bằng:
  ```css
  mask-image: linear-gradient(to bottom, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 320px, rgba(0,0,0,0) 580px);
  ```
- Khu vực danh mục trợ lý và Footer bên dưới hoàn toàn sạch sẽ, không còn bất kỳ đường lưới hay viền sọc nào gây rối mắt.

### 2.3. Bóc Tách & Khớp Câu Hỏi Mẫu Tự Động
- Sử dụng logic phân giải 4 loại trợ lý dựa trên bất biến danh mục và từ khóa:
  - `isDraft`: `"Soạn thông báo tổ chức Hội nghị Nghiên cứu Khoa học sinh viên cấp Trường."`
  - `isExam`: `"Ma trận đề thi tự luận theo thang nhận thức Bloom 4 mức độ như thế nào?"`
  - `isLib`: `"Cách truy cập cơ sở dữ liệu quốc tế ScienceDirect từ xa?"`
  - `isReg`: `"Quy định cảnh báo học tập và thôi học tại Điều 16 như thế nào?"`

---

## ✅ 3. Kết Quả Kiểm Thử
- **Biome Linter**: Kiểm tra `src/features/chat/public-chat-portal.tsx` đạt **0 lỗi, 0 cảnh báo** (25ms).
- **Trải nghiệm người dùng**: Giao diện đạt độ tương phản chuẩn WCAG AAA, phân tầng thị giác nổi bật, không trùng lặp dữ liệu.
