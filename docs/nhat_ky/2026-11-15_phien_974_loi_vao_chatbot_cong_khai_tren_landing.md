# Phiên 974 — Lối vào chatbot công khai trên trang chủ

Ngày 15/11/2026. Người dùng chỉ ra trang chủ hiện tại bắt đăng nhập SSO mới vào được trợ lý, trong khi trợ lý đã xuất bản có kênh công khai `/chatbot/{slug}`; yêu cầu đề xuất cải thiện và chốt làm **Phase A trước** (lối vào từ trang chủ), Phase B (endpoint danh sách công khai + mục "Trợ lý đang hoạt động") để sau.

## Thay đổi

- `frontendV2/src/routes/index.tsx`: đọc `VITE_PUBLIC_CHATBOT_SLUG`; khi có slug, ô hỏi nhanh, chip gợi ý, nút nổi và nút đầu trang điều hướng thẳng tới `/chatbot/{slug}` (kèm `?q=` khi có câu hỏi) thay vì ép đăng nhập. Slug trống giữ nguyên luồng SSO → `/chat` cũ.
- `frontendV2/src/routes/chatbot.$slug.tsx`: `validateSearch` nhận thêm `q` (tối đa 1000 ký tự); khi trợ lý sẵn sàng, tự gửi câu hỏi đúng một lần rồi xóa `q` khỏi URL bằng `replace` để tải lại trang bắt đầu sạch. Dùng ref giữ callback mới nhất để không phải bọc `handleSend` bằng `useCallback` chỉ nhằm thỏa Biome.
- `frontendV2/src/components/landing/landing-header.tsx`: prop tùy chọn `onOpenAssistant` và nút outline "Trợ lý tư vấn" (icon Lucide `Bot`), ẩn dưới breakpoint `sm`.
- `frontendV2/.env.example`: tài liệu hóa `VITE_PUBLIC_CHATBOT_SLUG`, nêu rõ để trống thì giữ luồng đăng nhập nội bộ.

Không thêm dependency, không đổi backend, không bật xuất bản, không commit/deploy.

## Kiểm chứng

Biome (4 tệp) **PASS**; `tsc --noEmit` **PASS**; `npm run build` **PASS** (chỉ còn cảnh báo chunk-size có sẵn). Live trên Vite tạm cổng 3003 với `VITE_PUBLIC_CHATBOT_SLUG=tuyen-sinh-2026`: nút "Trợ lý tư vấn" hiện ở header và điều hướng tới `/chatbot/tuyen-sinh-2026`; chip gợi ý điều hướng kèm `?q=` đã mã hóa; trang công khai báo trung thực "Liên kết không còn hoạt động" vì dev chưa có publication bật. Cổng 3002 mặc định (slug trống): không có nút mới, trang chủ giữ nguyên, không lỗi console. Server tạm đã dừng.

## Giới hạn và bước sau

Tự gửi câu hỏi từ `?q=` **NOT RUN** trên dữ liệu thật vì cần bật xuất bản một trợ lý — chưa được phép. Phase B (endpoint `GET /public/chatbots` + mục trợ lý đang hoạt động) **chưa bắt đầu**. Muốn dùng trong dev: bật xuất bản trợ lý ở tab Công khai, rồi đặt `VITE_PUBLIC_CHATBOT_SLUG=<slug>` trong `frontendV2/.env.local`; production đặt cùng biến ở môi trường build.
