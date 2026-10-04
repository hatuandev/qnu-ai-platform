# NHẬT KÝ LÀM VIỆC — PHIÊN #261: TRIỂN KHAI PHONG CÁCH LINEAR BENTO GRID & ASYMMETRIC 2-COLUMN HERO CHO CỔNG TRỢ LÝ AI HUB (/chat)

- **Thời gian**: 2026-10-04 23:05
- **Vai trò**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Tập tin thay đổi**:
  - `frontend2/src/features/chat/public-chat-portal.tsx`
  - `docs/ke_hoach_trien_khai_qnu_ai_hub_linear_bento_style.md`
  - `docs/nhat_ky/2026-10-04_phien_261_trien_khai_linear_bento_grid_va_asymmetric_hero_qnu_ai_hub.md`
  - `docs/nhat_ky/README.md`
  - `docs/memory/PROJECT_CONTEXT.md`
  - `docs/WORK_LOG.md`

---

## 🎯 1. Mục Tiêu Phiên Làm Việc
1. **Phân tích phong cách thiết kế của 9router.com**: Xác định rõ trường phái **"Linear-Style / Modern Technical Bento Grid"** theo yêu cầu của người dùng.
2. **Lên Kế Hoạch Triển Khai Chuyên Sâu**: Xây dựng tài liệu kế hoạch `ke_hoach_trien_khai_qnu_ai_hub_linear_bento_style.md` hòa quyện phong cách Linear Bento Grid với bản sắc học thuật của Trường Đại học Quy Nhơn.
3. **Triển Khai Bố Cục Hero 2 Cột Bất Đối Xứng (Asymmetric 2-Column Hero)**:
   - *Cột trái*: Pill badge phát sáng, tiêu đề H1 lớn với gradient Academic Teal, mô tả giá trị, Smart AI Prompt Dock kính mờ, 1-Click Trending Hot Queries, và dải 4 chỉ số KPI uy tín (`45+ Ngành`, `05 Trợ lý`, `1.300+ Facts`, `24/7 Trực tuyến`).
   - *Cột phải*: **Interactive Live Preview Card 3D** với hình ảnh thực cảnh khuôn viên trường biển Quy Nhơn (`/images/qnu-campus-hero.jpg`) và mô phỏng hội thoại thực tế có trích dẫn văn bản chính thức `[QĐ số 2139/QĐ-ĐHQN]`.
4. **Bố Cục Bento Grid Trợ Lý AI Chuyên Trách**:
   - Thẻ Spotlight Tuyển sinh 2026 nổi bật.
   - Thẻ các Trợ lý chuyên trách (Văn bản, Khảo thí, Thư viện số, Quy chế học vụ) với hộp icon trắng tương phản cao (`bg-white rounded-md p-2 shadow-xs border border-border/50`), hiệu ứng nhấc nhẹ `hover:-translate-y-1` và vầng sáng phát quang.
5. **Nền Khí Quyển & Vignette**: Lớp lưới kỹ thuật 40px (`linear-gradient`) kết hợp Radial Vignette tập trung thị giác vào trung tâm.
6. **Tuân thủ UI Rules**: 100% Radix UI Primitives, 0 raw buttons, 0 emoji, Biome check 0 lỗi.

---

## 🔬 2. Chi Tiết Thực Hiện

### 2.1. Lớp Nền Khí Quyển Tinh Tế & Mask Radial Fade
- **Khử bỏ lưới đậm kép**: Loại bỏ tình trạng lưới đè nhau quá đậm (0.25) giống bảng Excel. Chuyển sang 1 lớp lưới tuyến tính duy nhất siêu mảnh với độ mờ chỉ `0.08` (`rgba(26, 115, 101, 0.08)`).
- **Mask Fade Hào Quang**: Sử dụng `radial-gradient(ellipse 85% 55% at 50% 12%, black 35%, transparent 85%)` giúp lưới chỉ hiển thị nhẹ nhàng tại khu vực Hero phía trên để tạo chiều sâu công nghệ, sau đó tan biến mềm mại xuống dưới. Nền phần danh mục và footer bên dưới hoàn toàn sạch sẽ, thoáng mắt và bảo đảm độ tương phản chữ 100%.

### 2.2. Bố Cục Hero 2 Cột & Tối Ưu Typography
- **Tiêu đề H1 gọn gàng (No Orphan Word)**: Khắc phục lỗi rớt từ "Nhơn." sang một dòng lẻ loi bằng cách chuẩn hóa:
  *"Một Điểm Chạm.* <br /> *Mọi Thông Tin ĐH Quy Nhơn."*
- **Thanh AI Prompt Dock & Trending Queries**: Tối ưu khoảng cách và kích thước nút.
- **Thẻ Visual Showcase Phía Phải**: Mở rộng padding (`p-5 sm:p-6`), tăng kích thước chữ câu trả lời và trích dẫn chuẩn RAG lên `text-xs` (12px), loại bỏ cảm giác chật chội.

### 2.3. Tách Dòng Thanh Lọc Danh Mục & Bento Grid Chuẩn
- **Tách dòng thanh lọc danh mục**: Đưa bộ lọc danh mục xuống 1 hàng riêng biệt bên dưới tiêu đề phân khu với `flex-wrap gap-2`, triệt tiêu hoàn toàn lỗi cắt cụt chữ ("Quy chế & Họ...") và loại bỏ thanh cuộn ngang xám xấu xí.
- **Đồng bộ màu sắc Academic Teal**: Chuyển toàn bộ các nhãn danh mục về tông màu nhận diện ĐH Quy Nhơn (`text-primary bg-primary/10 border-primary/20`), xóa bỏ sự lộn xộn của 4-5 màu cầu vồng.
- **Bento Cards Tinh Gọn**:
  - Thẻ Tuyển sinh 2026 mở rộng làm thẻ Bento trọng tâm.
  - Các thẻ trợ lý còn lại: Mỗi thẻ chỉ giữ 1 câu hỏi mẫu tiêu biểu nhất với nút mũi tên 1-click trực diện, xóa bỏ nhãn "Chính thức" lặp lại thừa thãi.

---

## ✅ 3. Kết Quả Kiểm Thử
- **Biome Linter**: Kiểm tra `biome check src/features/chat/public-chat-portal.tsx` đạt **0 lỗi, 0 cảnh báo** (24ms).
- **Quy tắc AGENTS.md**: Tuân thủ 100% Rule 1.8/4.9 (Zero Raw Buttons), Rule 4.3 (Radius 6px/8px/16px), Rule 4.8 (Zero Emoji), Rule 1.10 (Sync Documentation).
