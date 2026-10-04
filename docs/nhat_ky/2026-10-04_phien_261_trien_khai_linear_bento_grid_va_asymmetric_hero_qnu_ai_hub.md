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

### 2.1. Lớp Nền Khí Quyển (Atmospheric Backdrop)
- Tạo lớp nền lưới kỹ thuật 40px:
  `bg-[linear-gradient(to_right,oklch(0.46_0.13_160/0.06)_1px,transparent_1px),linear-gradient(to_bottom,oklch(0.46_0.13_160/0.06)_1px,transparent_1px)] bg-[size:40px_40px]`
- Tạo lớp Radial Vignette mờ dần về 4 góc:
  `bg-[radial-gradient(ellipse_at_center,transparent_45%,rgba(0,0,0,0.03)_100%)] dark:bg-[radial-gradient(ellipse_at_center,transparent_35%,rgba(0,0,0,0.45)_100%)]`
- Vầng sáng Academic Teal tỏa mờ:
  `bg-gradient-to-b from-primary/15 via-teal-500/8 to-transparent blur-3xl opacity-75`

### 2.2. Bố Cục Hero 2 Cột Bất Đối Xứng
- **Cột Trái (Col Span 7)**:
  - Badge phát sáng: `<Sparkles className="size-3.5 text-primary" /> Hệ sinh thái Trợ lý AI · ĐH Quy Nhơn`
  - H1 Typography: "Một Điểm Chạm. Mọi Thông Tin Đại Học Quy Nhơn."
  - AI Prompt Dock nổi: `bg-card/95 dark:bg-card/85 p-1.5 shadow-md backdrop-blur-md`
  - Gợi ý câu hỏi nóng 1-click: *Điểm chuẩn Sư phạm & CNTT*, *Xét tuyển học bạ 2026*, *Học bổng khuyến khích*, *Mượn sách thư viện số*.
  - Metric counters: 45+ Ngành đào tạo, 05 Trợ lý AI, 1.300+ Facts số hóa, 24/7 Hỗ trợ tức thì.
- **Cột Phải (Col Span 5)**:
  - 3D Interactive Live Card với hiệu ứng ánh sáng nền mờ `bg-gradient-to-r from-primary/30 via-teal-500/20 to-emerald-500/30 blur-xl`.
  - Ảnh thực cảnh khuôn viên trường bên bờ biển Quy Nhơn kèm tag trạng thái thực tế "Trực tuyến · Tư vấn 2026".
  - Đoạn chat đối thoại mô phỏng thực tế với trích dẫn văn bản minh chứng chuẩn RAG.

### 2.3. Lưới Bento Grid & Thẻ Tương Tác
- Bố cục Bento Box đa kích thước phân cấp rõ ràng.
- Khung icon chuẩn mực: `size-10 rounded-md bg-white dark:bg-muted/40 p-2 shadow-xs border border-border/50` giúp icon luôn nổi bật và sắc nét.

---

## ✅ 3. Kết Quả Kiểm Thử
- **Biome Linter**: Kiểm tra `biome check src/features/chat/public-chat-portal.tsx` đạt **0 lỗi, 0 cảnh báo**.
- **Quy tắc AGENTS.md**: Tuân thủ 100% Rule 1.8/4.9 (Zero Raw Buttons), Rule 4.3 (Radius 6px/8px/16px), Rule 4.8 (Zero Emoji), Rule 1.10 (Sync Documentation).
