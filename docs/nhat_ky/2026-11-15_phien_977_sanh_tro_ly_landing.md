# Phiên 977 — Thiết kế lại landing dạng "Sảnh trợ lý" (lưới thẻ chọn bot)

Ngày 15/11/2026. Người dùng bác bản chat-first của phiên 976 (ảnh chụp kèm theo): "giao diện này cũng ko được, tôi không thích nó hiện khối chat ở giữa, tôi muốn nó hiện ra các thẻ chatbot để người dùng lựa chọn... tôi đã làm chatbot tuyển sinh thì theo lý nó sẽ hiện ra thẻ chatbot tuyển sinh, hãy sửa lại đi với 1 ý tưởng mới, tìm hiểu xem các nền tảng khác làm như thế nào rồi thiết kế lại landing page này". Giữ các ràng buộc đã chốt từ những vòng trước: thẻ gọn, không mô tả thừa, click là sang thẳng trang chat; phần chọn trợ lý là trọng tâm nhìn thấy ngay khi vào.

## Khảo sát nền tảng khác

Tham khảo cách Poe, Coze Store và GPT Store tổ chức trang khám phá trợ lý: đều mở đầu bằng một **lưới thẻ bot** (avatar + tên + trạng thái/mô tả ngắn), phía trên có **ô tìm kiếm** và **chip lọc theo phân loại/trạng thái**; bấm thẻ mở thẳng phiên trò chuyện với bot đó. Không nhúng khung chat vào giữa trang khám phá. Áp dụng mô hình này nhưng giữ thẻ QNU tối giản (bỏ mô tả dài theo đúng yêu cầu người dùng).

## Ý tưởng thiết kế

**"Sảnh trợ lý QNU"** — trang chủ là một thư viện trợ lý công khai để khách chọn, không phải khung chat:

- Màn hình đầu tiên = tiêu đề gọn ("Chọn trợ lý, bắt đầu trò chuyện") + **lưới thẻ trợ lý** ngay bên dưới, là trọng tâm. Mỗi thẻ: avatar gradient theo token ngữ nghĩa, chấm + nhãn trạng thái (Sẵn sàng/Tạm ngưng), tên trợ lý, hàng chân "Trò chuyện ngay"/"Xem trợ lý" + mũi tên. **Không có mô tả dài.** Click thẻ → `/chatbot/{slug}` ngay (không mang `?q=`).
- Trên lưới có **ô tìm kiếm** (icon kính lúp, bỏ dấu tiếng Việt khi so khớp) và **chip lọc "Tất cả"/"Sẵn sàng"** (aria-pressed) + bộ đếm thật (`n/m trợ lý` khi lọc, `m trợ lý` khi không).
- **Không còn khung trò chuyện/composer ở giữa trang.** Câu hỏi vẫn gửi được qua mục "Chủ đề thường hỏi" bên dưới (bấm là gửi thẳng `?q=` vào trợ lý đang hoạt động).
- Nền aurora primary/info/warning + entrance theo tầng (tái dùng CSS đã có từ 976, tôn trọng reduced-motion), scrollbar nhuộm primary. Container rộng `max-w-5xl` cho desktop; lưới `1 → 2 (sm) → 3 (lg)` cột.
- Dữ liệu thật từ `GET /public/chatbots`; trạng thái trung thực: skeleton 3 thẻ khi tải, hàng lỗi có "Thử lại", danh sách rỗng có panel "Chưa có trợ lý công khai nào được bật" + nút "Trò chuyện nội bộ" (giữ luồng `/chat`/SSO), không kết quả tìm có "Xóa bộ lọc".
- Dưới nếp gấp: 6 chủ đề thường hỏi (giữ nguyên) + băng liên hệ Ban Tuyển sinh; nút "Trò chuyện cùng AI" và "Trợ lý tư vấn" trên header cuộn tới lưới thẻ.

## Thay đổi mã

- `frontendV2/src/components/landing/landing-assistants.tsx`: viết lại thành `AssistantDirectory` (ô tìm kiếm + chip lọc + đếm + lưới `AssistantCard`); `foldText` bỏ dấu NFD + đ/Đ→d/D + lowercase để tìm không dấu; giữ `PUBLIC_ASSISTANTS_SECTION_ID` và `scrollToPublicAssistants()`. Thẻ dùng `Button` primitive, tint gradient theo index (primary/info/warning/success), hover nhấc/nổi viền/mũi tên.
- `frontendV2/src/components/landing/landing-hero.tsx`: rút thành intro gọn (eyebrow + h1 + meta) bọc `AssistantDirectory`; bỏ hẳn console/composer/info-query của 976.
- `frontendV2/src/routes/index.tsx`: `handleSelectPublicBot(slug)` điều hướng thẳng `/chatbot/{slug}` (search rỗng); `handleOpenAssistant` cuộn tới lưới; `handleAsk`/`activeSlug` giữ nguyên cho chủ đề và luồng nội bộ; header luôn có `onOpenAssistant`.
- `frontendV2/src/components/landing/landing-showcase.tsx`: container `max-w-3xl → max-w-5xl`, lưới chủ đề `sm:grid-cols-2 → lg:grid-cols-3`; nội dung 6 chủ đề + băng liên hệ giữ nguyên.

Không thêm dependency, không đổi backend, không bật/tắt xuất bản, không commit/deploy.

## Kiểm chứng

- Biome (4 tệp) **PASS** (Fixed 2 formatting); `npm run build` (gồm `tsc --noEmit`) **PASS** (chỉ còn cảnh báo chunk-size có sẵn).
- Live `localhost:3002` (viewport 515×570): lưới thẻ nằm đầu `<main>`, thẻ "Tư vấn tuyển sinh QNU 2026" hiện trong màn hình đầu (top 257 / bottom 417 < 570); **không có composer** trên landing; không tràn ngang.
- Tìm kiếm bỏ dấu: gõ "tuyen sinh" → khớp thẻ, đếm "1/1 trợ lý"; gõ chuỗi không tồn tại → 0 thẻ + "Không tìm thấy trợ lý phù hợp." + nút "Xóa bộ lọc"; bấm xóa → thẻ trở lại, ô tìm trống.
- Chip "Sẵn sàng" → aria-pressed=true, thẻ available vẫn hiện; "Tất cả" trở lại bình thường.
- Click thẻ → `/chatbot/tu-van-tuyen-sinh-2026` tải đúng trang chat công khai (composer + welcome).
- Click chủ đề "Phương thức xét tuyển 2026" → `?q=` tự gửi một lần → trả lời kèm 13 trích dẫn "Tài liệu nguồn · tr. …", phiên còn 14/15, URL tự xóa `?q=`.
- Dark ↔ light: token nền đổi đúng (`oklch(0.145…)` ↔ nền sáng), thẻ tương phản tốt (chữ `oklch(0.985…)` trên nền tối), không tràn ngang; khôi phục light sau kiểm tra.
- Console trình duyệt sạch (không error/warn).
- **NOT RUN**: ảnh chụp màn hình (tool không khả dụng), viewport điện thoại thật ≤375px và desktop rộng ≥1280px (chỉ kiểm ở 515px), trạng thái nhiều trợ lý/kill-switch/rỗng/lỗi danh sách trên landing mới (các nhánh này rà qua mã, không kích live vì publication phải giữ nguyên), pytest.

## Giới hạn và bước sau

- Nhiều trợ lý: lưới render nhiều thẻ và lọc/tìm hoạt động, nhưng chưa kiểm live với >1 bot công khai (dev hiện có 1).
- Trạng thái rỗng/lỗi/skeleton đã cài đặt trung thực trong mã nhưng chưa kích live (không tắt publication để thử).
- Chưa commit/deploy; publication giữ nguyên trạng thái người dùng đã bật cho dev.