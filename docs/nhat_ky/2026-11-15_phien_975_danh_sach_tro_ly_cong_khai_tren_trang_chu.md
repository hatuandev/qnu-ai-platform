# Phiên 975 — Danh sách trợ lý công khai trên trang chủ (Phase B)

Ngày 15/11/2026. Tiếp sau Phase A (lối vào chatbot công khai từ trang chủ), người dùng yêu cầu trang chủ hiện **card các chatbot đã xuất bản** để khách chọn rồi chat, thay vì chỉ một lối vào cố định.

## Thay đổi

Backend (`backendV1/qnu/domains/publications`):

- `schemas.py`: `PublicChatbotSummary` (slug, display_name, welcome_message, available, unavailable_reason) và `PublicChatbotListResponse { chatbots: [...] }` — chỉ trường trình bày, không lộ workspace/collection/assistant id.
- `public_router.py`: `GET /platform/v1alpha1/public/chatbots` (response model, `Cache-Control: no-store`), đặt trước route `/{slug}`.
- `public_service.py`: `listing()` — kill-switch tắt trả danh sách rỗng (không 404); sắp xếp ổn định theo `display_name, slug`, giới hạn 50; mỗi trợ lý lấy `available` từ `assistant_readiness`; cache Redis 30 giây theo fingerprint `slug:revision`, danh sách rỗng không cache để trợ lý mới xuất bản hiện ngay.

Frontend (`frontendV2`):

- `src/api/publications/{types,endpoints,requests,queries}.ts`: type + `getPublicChatbotList` qua `v1PublicClient` (ẩn danh) + hook `usePublicChatbotListQuery`.
- `src/components/landing/landing-assistants.tsx`: mục "Trợ Lý Đang Hoạt Động" — card tên, lời chào (3 dòng), badge "Sẵn sàng"/"Tạm ngưng", nút mở chat; skeleton khi tải, card lỗi có "Thử lại", tự ẩn khi danh sách rỗng.
- `src/routes/index.tsx`: `featuredSlug` = slug từ `VITE_PUBLIC_CHATBOT_SLUG` hoặc trợ lý duy nhất; nhiều trợ lý thì CTA/ô hỏi/chip cuộn tới mục card và giữ câu hỏi, card được chọn nhận `?q=`; không có trợ lý giữ luồng SSO cũ.

Phụ trợ: vá bổ sung `backendV1/docs/openapi-v1.json` (+1 path, +2 schema; không tái tạo toàn bộ). API dev cổng 8002 chạy không `--reload` nên được khởi động lại đúng lệnh cũ (`uvicorn qnu.main:app --host 127.0.0.1 --port 8002 --env-file ../.env`) để nạp route.

Không thêm dependency, không bật/tắt xuất bản, không đổi dữ liệu, không commit/deploy.

## Kiểm chứng

- Ruff 3 tệp backend **PASS**; Biome 6 tệp frontend **PASS**; `tsc --noEmit` và `npm run build` **PASS** (chỉ còn cảnh báo chunk-size có sẵn).
- `GET /platform/v1alpha1/public/chatbots` live **200** với `cache-control: no-store`, trả đúng 1 trợ lý đang bật sẵn trong dev (`tu-van-tuyen-sinh-2026`, `available: true`); `openapi.json` runtime có route mới.
- Landing 3002 (DOM, ảnh chụp trình duyệt trong app **NOT RUN** vì surface ẩn): mục "Trợ Lý Đang Hoạt Động" hiện đúng 1 card "Tư vấn tuyển sinh QNU 2026" kèm badge "Sẵn sàng"; bấm card → `/chatbot/tu-van-tuyen-sinh-2026`; gõ câu hỏi ở ô hero rồi gửi → mở đúng chatbot và **tự gửi** câu hỏi, trả lời kèm 6 trích dẫn; mạng 200/201, console không lỗi.
- **NOT RUN:** kill-switch tắt (cần đổi env/restart), trạng thái rỗng (cần tắt xuất bản), nhiều trợ lý + cuộn/giữ câu hỏi (dev chỉ có 1), pytest (theo quy định không chạy nếu không được yêu cầu).

## Giới hạn và bước sau

Trạng thái "Tạm ngưng" và hành vi nhiều trợ lý mới chỉ được kiểm bằng mã/type, chưa có dữ liệu live. Cache danh sách 30 giây: trạng thái sẵn sàng có thể trễ tối đa 30 giây (cùng chính sách endpoint thông tin). Muốn thấy thay đổi ngay trên dev: bật/tắt xuất bản ở tab Công khai của trợ lý; không cần đặt `VITE_PUBLIC_CHATBOT_SLUG` khi có nhiều trợ lý (trang chủ tự liệt kê và cuộn tới card).

## Tinh chỉnh theo phản hồi (cùng phiên)

Người dùng yêu cầu card **nhỏ gọn, bỏ mô tả thừa, bấm là vào chat**, và đưa mục trợ lý lên **đầu trang** vì là trọng tâm. Đã sửa:

- `landing-assistants.tsx`: card dạng thanh gọn (icon + tên + chấm trạng thái + mũi tên, cao ~54px), **bỏ lời chào/mô tả**; tiêu đề mục thu nhỏ còn một dòng; skeleton và khối lỗi cũng gọn theo.
- `routes/index.tsx`: render `LandingAssistants` **trước** `LandingHero` — vào trang là thấy danh sách trợ lý ngay dưới header.

Kiểm chứng lại: Biome + build **PASS**; live 3002: mục trợ lý là phần tử đầu của `<main>` (sát dưới header), card chỉ còn tên + "Sẵn sàng" (không còn lời chào), bấm card → `/chatbot/{slug}`, không tràn ngang, console sạch. Ảnh chụp trình duyệt vẫn **NOT RUN** (surface ẩn).

