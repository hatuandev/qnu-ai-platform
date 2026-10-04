# NHẬT KÝ LÀM VIỆC: PHIÊN #255 — NÂNG CẤP TOÀN DIỆN GIAO DIỆN CHAT CHUẨN CHATGPT / GEMINI & TÍCH HỢP LỊCH SỬ HỘI THOẠI (CHAT SESSIONS HISTORY)
- **Thời gian**: 2026-10-04 15:30
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise UI/UX Specialist
- **Mục tiêu phiên (Goals)**:
  - Cải tiến toàn diện giao diện Cổng Chat Trợ lý AI (`/chat/:slug`) theo tiêu chuẩn thẩm mỹ cao cấp hiện đại của **ChatGPT & Google Gemini**.
  - Xây dựng hệ thống quản lý **Lịch sử Trò chuyện (Chat History / Sessions)** có thanh bên (Sidebar) gập mở linh hoạt, gom nhóm theo thời gian, hỗ trợ tạo đoạn chat mới, đổi tên và xóa cuộc trò chuyện.
  - Tái cấu trúc trải nghiệm thị giác: Thay thế khối tin nhắn người dùng màu xanh lá cây chói lọi bằng bong bóng chat bo cong lớn thanh lịch (`rounded-3xl`, màu xám nhẹ sang trọng), loại bỏ viền hộp card bao quanh câu trả lời trợ lý sang dạng dòng chảy văn bản tự nhiên (Natural Stream).
  - Tái thiết kế khung nhập liệu dưới đáy (Floating Input Dock) nổi bật với hộp bo cong lớn `rounded-3xl`, viền sáng bóng, textarea tự động co giãn dòng và nút gửi tròn mềm chuẩn Gemini.

---

## 1. Phân Tích Thực Trạng & Nâng Cấp Thiết Kế

1. **Thực trạng trước khi tối ưu**:
   - Giao diện chat phẳng, đơn điệu, không có thanh bên lưu lịch sử các phiên hỏi đáp trước đó. Người dùng khi F5 hoặc mở lại trình duyệt không thể xem lại các đoạn chat cũ.
   - Tin nhắn người dùng (`user role`) bị bôi màu xanh lá cây đậm (`bg-primary`) đặc kín, tạo cảm giác nặng nề, khó chịu cho mắt.
   - Tin nhắn trợ lý (`assistant role`) bị đóng khung trong hộp thẻ màu trắng (`bg-card border p-4 shadow-xs`), khiến văn bản bị bó hẹp trong một chiếc hộp cứng nhắc thay vì trải dài tự nhiên như các nền tảng AI hàng đầu thế giới.
   - Khung nhập liệu dưới chân trang nằm lọt thỏm trong footer chia cắt, nút gửi hình vuông thô sơ.
2. **Kiến trúc & Chuẩn thiết kế mới (ChatGPT / Gemini Aesthetic)**:
   - **Collapsible Chat History Sidebar** (`ChatHistorySidebar`):
     + Thanh bên trái trượt mượt mà (cố định trên Desktop, drawer overlay trên Mobile), nút đóng/mở (`PanelLeft`).
     + Nút **"+ Đoạn chat mới"** (`SquarePen`) bo góc mềm mại, nổi bật ở đầu sidebar.
     + Ô tìm kiếm nhanh lịch sử hội thoại.
     + Gom nhóm thông minh theo mốc thời gian: *Hôm nay*, *Hôm qua*, *7 ngày trước*, *Trước đó*.
     + Hỗ trợ đổi tên đoạn chat inline và xóa đoạn chat có dialog xác nhận an toàn.
     + Bộ chuyển đổi nhanh giữa các Trợ lý AI của QNU kèm icon chuyên trách (Tuyển sinh, Quy chế, Thư viện, Soạn thảo văn bản...).
   - **Main Chat Canvas**:
     + Empty State Hero: Avatar Trợ lý QNU lớn viền phát sáng nhẹ, câu chào đón *"Hôm nay mình có thể giúp gì cho bạn?"*, cùng lưới 4 thẻ gợi ý câu hỏi nhanh (Prompt Suggestions) xếp 2x2 bo góc `rounded-xl`.
     + User Message: Bong bóng xám nhẹ `bg-muted/80 text-foreground border border-border/40` bo tròn lớn `rounded-3xl px-5 py-3`, căn phải, êm dịu cho thị giác.
     + Assistant Message: Dòng chảy Markdown tự nhiên (`variant="natural"`), bảng biểu và khối code có nút copy, các nút tương tác (Copy, Regenerate, Đánh giá Like/Dislike, Chip trích dẫn văn bản đối soát QNU).
   - **Floating Input Dock**:
     + Nổi lơ lửng ở giữa đáy trang với gradient bóng mờ phía sau.
     + Hộp nhập liệu bo cong lớn `rounded-3xl`, viền sáng mỏng tinh tế (`border-border/80 bg-background/95 shadow-md`).
     + Textarea auto-resize tự co giãn chiều cao theo nội dung gõ (từ 1 đến 5 dòng).
     + Nút Gửi tròn nổi bật (`rounded-full size-9 bg-primary text-primary-foreground`) và tự động đổi thành nút Dừng sinh câu trả lời (`Square`) khi đang streaming.

3. **Tối ưu Border & Header Liền Mạch (Google Gemini & ChatGPT Seamless Header)**:
   - **Xử lý triệt để lỗi lệch viền ngang (Staggered Border Mismatch)**:
     - Trước đó, Header thanh bên lịch sử có chiều cao 64px (`p-3` + `h-10` button), trong khi Header khung chat chính có chiều cao 56px (`h-14`), dẫn tới đường kẻ ngang `border-b` ở hai bên bị lệch bậc thang 8px.
     - Đồng thời, khi mở sidebar trên Desktop, cả 2 bên đều hiển thị nút toggle sidebar sát nhau (`[<|] | [|]`), gây thừa thãi về mặt thị giác.
   - **Giải pháp chuẩn hóa**:
     - **Bỏ hoàn toàn đường kẻ ngang (`border-b`)**: Cả Header chính và Header Sidebar đều loại bỏ viền kẻ ngang, tạo không gian nổi liền mạch (Seamless Floating Header) với hiệu ứng `backdrop-blur-md` chuẩn Google Gemini và ChatGPT.
     - **Đồng bộ chiều cao chuẩn `h-14` (56px)**: Nút "+ Đoạn chat mới" được tinh chỉnh `h-9 rounded-full` thanh thoát, căn thẳng hàng tuyệt đối với Avatar Trợ lý và huy hiệu trên Header chính.
     - **Khử trùng lặp nút Toggle Sidebar**: Khi Sidebar đang mở, chỉ hiển thị nút thu gọn `PanelLeftClose` ở góc phải header sidebar; khi Sidebar đóng lại, Header chính mới hiển thị nút `PanelLeft` để mở lại thanh lịch sử.

---

## 2. Các Thay Đổi Mã Nguồn Cụ Thể

1. **`frontend2/src/hooks/use-chat-history.ts` (MỚI)**:
   - Hook quản lý lưu trữ danh sách hội thoại trong `localStorage` theo từng mã trợ lý (`qnu_chat_threads_${assistantCode}`).
   - Cung cấp các phương thức: `threads`, `currentThreadId`, `currentThread`, `groupedThreads`, `createNewThread`, `selectThread`, `saveThreadMessages` (tự động trích xuất tiêu đề ngắn từ câu hỏi đầu tiên của người dùng), `renameThread`, `deleteThread`, `clearAllThreads`.
2. **`frontend2/src/features/chat/chat-history-sidebar.tsx` (MỚI)**:
   - Component Sidebar lịch sử chat chuẩn ChatGPT / Gemini.
   - Loại bỏ viền kẻ ngang `border-b`, đồng bộ chiều cao `h-14`, viền phân cách dọc `border-r border-border/40` siêu mảnh.
   - Nút "+ Đoạn chat mới" hình viên thuốc (`rounded-full h-9`), ô tìm kiếm, gom nhóm thời gian, sửa tên, xóa từng đoạn chat hoặc xóa sạch toàn bộ lịch sử, dropdown chuyển đổi trợ lý QNU nhanh.
3. **`frontend2/src/components/ai/chat-bubble.tsx`**:
   - Bổ sung prop `variant?: "card" | "natural"` (mặc định `"natural"`).
   - Thiết kế lại User Message sang bong bóng xám nhẹ bo tròn lớn `rounded-2xl sm:rounded-3xl border border-border/50` khi dùng variant natural, triệt tiêu màu xanh lá chói mắt.
   - Loại bỏ viền thẻ card cứng nhắc của Assistant Message sang nền trong suốt tự nhiên.
4. **`frontend2/src/components/ai/chat-message.tsx`**:
   - Bổ sung prop `variant?: "card" | "natural"` và chuyển tiếp xuống `ChatBubble`.
5. **`frontend2/src/features/chat/public-chat-view.tsx`**:
   - Tích hợp `useChatHistory` và `ChatHistorySidebar`.
   - Header liền mạch không viền ngang (`border-b` removed), điều kiện hiển thị nút `PanelLeft` khi sidebar đóng.
   - Triển khai Empty State Hero với 4 thẻ câu hỏi gợi ý dạng lưới 2x2.
   - Triển khai Floating Input Dock bo tròn lớn `rounded-3xl` chuẩn Gemini/ChatGPT kèm nút gửi tròn `rounded-full size-8 sm:size-9`.

---

## 3. Kết Quả Kiểm Thử & Xác Nhận

- **Linter (Biome)**:
  - Lệnh: `npx @biomejs/biome check src/hooks/use-chat-history.ts src/features/chat/chat-history-sidebar.tsx src/features/chat/public-chat-view.tsx src/components/ai/chat-bubble.tsx src/components/ai/chat-message.tsx`
  - Kết quả: **Checked 5 files in 23ms. 0 errors, 0 warnings (Exit code 0)**.
- **Biên dịch Frontend (Vite Build)**:
  - Lệnh: `npm run build`
  - Kết quả: **✓ built in 3.98s (0 lỗi TypeScript, 0 lỗi đóng gói bundle)**.
- **Trải nghiệm thực tế**:
  - Giao diện chat hiện đại, thoáng đãng, sang trọng y hệt ChatGPT và Gemini.
  - Loại bỏ hoàn toàn cảm giác "cắt khúc" của các đường viền cũ; thanh bên và khung chat hòa quyện tự nhiên.
  - Lịch sử chat được lưu trữ bền vững, tự động cập nhật tiêu đề theo câu hỏi của người dùng, phân loại theo ngày và cho phép tạo mới / chọn lại / xóa / đổi tên mượt mà.
