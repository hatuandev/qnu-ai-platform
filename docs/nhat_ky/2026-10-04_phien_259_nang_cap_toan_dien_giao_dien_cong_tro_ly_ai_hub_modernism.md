# NHẬT KÝ LÀM VIỆC: PHIÊN #259 — NÂNG CẤP TOÀN DIỆN GIAO DIỆN CỔNG TRỢ LÝ AI (PUBLIC CHAT PORTAL) CHUẨN "ACADEMIC MODERNISM", SPOTLIGHT TUYỂN SINH & AI PROMPT DOCK

- **Thời gian**: 2026-10-04 22:30 (UTC+7)
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên (Goals)**:
  1. Tái thiết kế toàn diện trang Cổng Trợ Lý Công Khai (`/chat` - `public-chat-portal.tsx`) thoát khỏi phong cách "danh mục quản trị phẳng đơn điệu", nâng cấp thành **QNU AI Hub — Academic Modernism** đạt chuẩn thiết kế đẳng cấp quốc tế.
  2. **Hero Section & AI Prompt Search Bar**:
     - Hiệu ứng ánh sáng tỏa mờ (Ambient Radial Glow) bằng màu QNU Academic Teal tạo chiều sâu không gian công nghệ.
     - Thanh tìm kiếm dạng AI Prompt Dock nổi với nút gửi "Hỏi ngay" và nút xóa nhanh (`X`).
     - Thanh điều hướng câu hỏi nóng 1-Click (Trending Hot Queries): *"Điểm chuẩn Sư phạm & CNTT"*, *"Xét tuyển học bạ 2026"*, *"Học bổng khuyến khích"*, *"Mượn sách thư viện số"*. Nhấp vào là hệ thống tự động chuyển thẳng vào phòng chat với câu hỏi đó được gửi ngay lập tức.
  3. **Bộ Lọc Danh Mục Thuần Việt Kèm Icon Lucide**:
     - Thay thế toàn bộ các slug tiếng Anh thô (`Administration`, `Examination`, `Academic`) bằng danh mục tiếng Việt trang nhã kèm biểu tượng chuyên biệt:
       - `Sparkles`: Tất cả Trợ lý
       - `GraduationCap`: Tuyển sinh Đại học
       - `BookOpen`: Quy chế & Học vụ
       - `Library`: Thư viện & Học liệu
       - `FileText`: Soạn thảo Văn bản
       - `HelpCircle`: Khảo thí & Đề thi
  4. **Triệt Tiêu Lỗi Cắt Cụt Tên Trợ Lý (Smart Display Name Formatting)**:
     - Khắc phục triệt để lỗi 100% thẻ đều bị cắt cụt `Mô-đun trợ lý ảo...` do tên gốc quá dài.
     - Hàm `formatAssistantDisplayName` tự động chuẩn hóa thành các tiêu đề súc tích:
       - *Trợ lý Tư vấn Tuyển sinh 2026*
       - *Trợ lý Quy chế & Học vụ*
       - *Trợ lý Thư viện & Học liệu Số*
       - *Trợ lý Soạn thảo Văn bản*
       - *Trợ lý Ngân hàng Đề & Khảo thí*
  5. **Spotlight Hero Banner Cho Trợ Lý Tuyển Sinh**:
     - Tôn vinh Trợ lý Tuyển sinh (nhu cầu số 1 của cộng đồng) thành một thẻ Featured Hero Banner nổi bật ở vị trí danh dự:
       - Huy hiệu "Trọng điểm tuyển sinh 2026".
       - Các chỉ số nổi bật: 45 Ngành đào tạo • 05 Phương thức xét tuyển • Đối soát 100% văn bản gốc.
       - 2 gợi ý câu hỏi nhanh kèm nút CTA *"Bắt đầu tư vấn tuyển sinh ngay &rarr;"*.
  6. **Lưới Thẻ Trợ Lý Chuyên Trách & Dải Bảo Chứng**:
     - Các thẻ còn lại bố trí lưới 2 cột thông thoáng, bo góc `rounded-lg` (8px), viền phát sáng khi hover, câu hỏi gợi ý dạng interactive chips.
     - Dải Cam kết & Bảo chứng 3 cột (Trust & Guarantee Bar):
       - `100% Căn cứ chính thức`: Đối soát từ văn bản, quy chế ĐH Quy Nhơn.
       - `Hybrid RAG & Fact Layer`: Tra cứu bảng số liệu số hóa chống ảo giác.
       - `Phản hồi trực tuyến 24/7`: Phục vụ người học mọi lúc, mọi nơi.

---

## 1. Chi Tiết Tệp Mã Nguồn Đã Thay Đổi
- **`frontend2/src/features/chat/public-chat-portal.tsx`**:
  - Viết lại toàn bộ component với cấu trúc phân tầng: Ambient Glow -> Header -> Hero AI Search -> Trending Chips -> Vietnamese Category Pills -> Featured Admissions Spotlight -> 2x2 Specialized Grid -> Trust Bar -> Footer.
  - Tuân thủ 100% Rule 1.8 & 4.9: Dùng `Button`, `Badge`, `Card`, `Input` Radix UI.
  - Tuân thủ 100% Rule 4.3: Bán kính `rounded-md` cho nút/input, `rounded-lg` cho thẻ/bề mặt, `rounded-micro` cho tags.
  - Tuân thủ 100% Rule 4.8: Toàn bộ icon từ `lucide-react`, 0 emoji ký tự.

---

## 2. Kết Quả Kiểm Thử (Verification)
- **Biome Linter**: 0 lỗi, 0 cảnh báo.
- **TypeScript Typecheck**: Đạt 100% sạch lỗi biên dịch.
