# Phiên 976 — Thiết kế lại toàn bộ landing page theo hướng chat-first

Ngày 15/11/2026. Người dùng không hài lòng với hai vòng chỉnh trước (card to/mô tả thừa, rồi dải card gọn nhưng vẫn trên nền marketing cũ) và yêu cầu: "lên ý tưởng thiết lại toàn bộ landing page này, lên ý tưởng xong thì triển khai luôn". Giữ các ràng buộc đã chốt: thẻ trợ lý gọn, không mô tả thừa, click là sang thẳng trang chat; phần trò chuyện phải nằm đầu trang, là trọng tâm nhìn thấy ngay khi vào.

## Ý tưởng thiết kế

**"Bàn trò chuyện QNU"** — trang chủ mở đầu bằng chính trải nghiệm trò chuyện, không phải trang marketing:

- Màn hình đầu tiên = dải trợ lý công khai (chip gọn: icon + tên + chấm trạng thái) đặt ngay trên cùng, bên dưới là **khung trò chuyện** dùng đúng ngôn ngữ giao diện của trang `/chatbot/{slug}`: bong bóng chào của trợ lý, câu hỏi gợi ý thật, ô soạn câu hỏi (Enter gửi, Shift+Enter xuống dòng).
- Toàn bộ landing chuyển từ bảng màu marketing slate/emerald hardcode sang **semantic tokens** của app (teal học thuật OKLCH), nên light/dark đồng nhất với trang chat và phần quản trị; dark mode là công dân hạng nhất.
- Nền lưới token-driven + ba dải sáng ambient (primary/info/warning) trôi chậm; entrance theo tầng (rail → khung chat → ghi chú); tôn trọng `prefers-reduced-motion`; scrollbar trang nhuộm màu primary.
- Phần marketing cũ (headline khổng lồ, stats, campus card, 3 bước, nút nổi) bị gỡ. Dưới nếp gấp chỉ còn: 6 chủ đề thường hỏi dạng hàng gọn (icon + nhãn, bấm là gửi thẳng câu hỏi vào trợ lý) và băng liên hệ Ban Tuyển sinh (ảnh khuôn viên mờ + hotline + nút cuộn lên khung chat).
- Dữ liệu thật: danh sách trợ lý từ `GET /public/chatbots`; lời chào + câu hỏi gợi ý của trợ lý đang chọn từ `GET /public/chatbots/{slug}` (starter_prompts). Không mock, không TODO; trạng thái tải/lỗi/rỗng trung thực (skeleton chip, hàng lỗi có "Thử lại", danh sách rỗng ẩn rail).

## Thay đổi mã

- `frontendV2/src/components/landing/landing-assistants.tsx`: viết lại thành `AssistantRail` (chip `Button` bo tròn, `aria-pressed` cho trợ lý đang chọn, chấm `success`/`warning`, skeleton + hàng lỗi thử lại); giữ `PUBLIC_ASSISTANTS_SECTION_ID` và `scrollToPublicAssistants()`.
- `frontendV2/src/components/landing/landing-hero.tsx`: viết lại thành khung trò chuyện: header trợ lý (avatar + tên + trạng thái), bong bóng welcome thật, starter prompts thật (tối đa 4, fallback 3 câu gợi ý chung khi không có trợ lý công khai), composer `Textarea` + `Button` gửi; khóa gửi khi trợ lý tạm ngưng hoặc lỗi info (kèm hàng lỗi + thử lại); click chip chuyển câu hỏi đang gõ sang trợ lý được chọn qua `?q=`.
- `frontendV2/src/components/landing/landing-showcase.tsx`: viết lại gọn — 6 chủ đề dạng hàng `Button` (tint theo token primary/info/warning/success) + băng liên hệ; bỏ stats/3 bước/campus card lớn.
- `frontendV2/src/components/landing/landing-header.tsx`: restyle sang semantic tokens, theme toggle và các nút dùng `Button` primitive; hotline ẩn dưới `md`.
- `frontendV2/src/routes/index.tsx`: `activeSlug = env slug || trợ lý sẵn sàng đầu tiên || trợ lý đầu tiên`; composer/gợi ý/chủ đề gửi thẳng vào `activeSlug` kèm `?q=`; hết trợ lý công khai giữ luồng cũ (token → `/chat`, SSO, dev bridge); bỏ nút nổi và state `pendingQuestion`; footer semantic tokens.
- `frontendV2/src/styles/globals.css`: `.landing-grid` đổi sang token (color-mix primary), scrollbar trang theo primary, keyframes `landing-rise`/`landing-drift` + delay utilities, tắt animation khi reduced-motion.

Không thêm dependency, không đổi backend, không bật xuất bản, không commit/deploy.

## Kiểm chứng

- Biome (6 tệp) **PASS**; `npm run build` (gồm `tsc --noEmit`) **PASS** (chỉ còn cảnh báo chunk-size có sẵn).
- Live `localhost:3002` (viewport 672×785): rail nằm đầu `<main>` (top 206px, ngay dưới header 94px + heading), chip cao 36px; toàn bộ khung chat lọt màn hình đầu (bottom 610px < 785px); không tràn ngang.
- Click chip trợ lý → `/chatbot/tu-van-tuyen-sinh-2026` ngay lập tức.
- Composer: gõ câu hỏi → nút gửi được bật → submit → trang chat tự gửi `?q=` → trả lời học phí kèm trích dẫn `[1] Tài liệu nguồn · tr. 11`, lượt 14/15.
- Câu hỏi gợi ý thật bấm một lần → `?q=` mã hóa → tự gửi → trả lời đủ 5 phương thức kèm 15 trích dẫn; URL tự xóa `?q=` sau gửi.
- Đổi dark ↔ light: token nền đổi đúng (`oklch(0.145…)` ↔ `oklch(1…)`), không tràn ngang, khung chat vẫn trong màn hình đầu.
- Console trình duyệt sạch (chỉ log vite/React DevTools).
- **NOT RUN**: ảnh chụp màn hình (tool không khả dụng), viewport điện thoại thật ≤375px và desktop rộng ≥1280px, trạng thái nhiều trợ lý/kill-switch/rỗng/lỗi danh sách trên landing mới, pytest.

## Giới hạn và bước sau

- Nhiều trợ lý: composer nhắm trợ lý sẵn sàng đầu tiên (hoặc env slug); chip vẫn điều hướng thẳng từng trợ lý — hành vi nhiều trợ lý chưa kiểm live.
- Khi không còn trợ lý công khai nào, landing giữ luồng nội bộ cũ (SSO/`/chat`) với lời chào chung và 3 gợi ý chung.
- Chưa commit/deploy; publication giữ nguyên trạng thái người dùng đã bật cho dev.