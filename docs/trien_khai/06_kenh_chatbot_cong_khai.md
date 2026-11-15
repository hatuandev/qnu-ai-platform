# Đưa kênh chatbot công khai lên production

Trạng thái: **đã chuẩn bị, chưa triển khai**. Tài liệu này là checklist cho lần deploy đầu tiên của
kênh công khai (`/chatbot/{slug}`) gồm image frontendV2, domain, các bước bật và kiểm chứng.

## 1. Điều kiện tiên quyết

1. **Đường đăng nhập cho quản trị viên.** Bản production của `frontendV2` chưa có SSO (cầu nối dev
   tự tắt trong build). Trang công khai chạy không cần token, nhưng **bật/tắt công khai, sửa hạn mức
   và xem thống kê nằm trong tab Công khai của giao diện quản trị**, nên trước khi vận hành cần một
   trong hai:
   - frontendV2 có luồng đăng nhập production; hoặc
   - chủ động tạo/cập nhật publication bằng lệnh API với token SSO hợp lệ (platform/workspace admin).
2. **Máy chủ đã chạy backendV1 theo [quy trình Dokploy](02_quy_trinh_trien_khai_dokploy.md)**, gồm
   bootstrap chạy `alembic upgrade head`. Migration `0029` và `0030` (bảng publication + thống kê)
   được áp tự động trong lần deploy này, không cần chạy tay.
3. **Model chat mặc định của hệ thống đã cấu hình trong ModelOps** (provider + khóa + default).
   Thiếu default, tạo/sửa trợ lý trả 409 `model_not_configured`.
4. **Trợ lý đã sẵn sàng**: có kho tri thức đã xuất bản và index xong. Publication chỉ bật được khi
   readiness là `ready`; nếu chưa, API trả 409 `publication_not_ready`.
5. **Quyết định hạn mức token/ngày cho từng publication.** Để trống (`null`) là “Không giới hạn”.
   Khi đặt hạn mức, Redis giữ trước ngân sách ước tính cho từng lần gọi ModelOps theo ngày nghiệp vụ
   Asia/Ho_Chi_Minh. Khi provider báo số token thực, backend ghi số đó và giải phóng phần đã giữ.
   Nếu chưa biết số token thực, phần giữ tiếp tục tính vào ngân sách của ngày đó. Hạn mức cần đủ
   cho ngữ cảnh và đầu ra ước tính của ít nhất một lượt với cấu hình đang dùng.
6. **Cache câu trả lời vẫn tắt** (`ANSWER_CACHE_TTL_SECONDS=0`). Bật cache là quyết định riêng,
   không thuộc lần deploy này.
7. **Cấu hình IP proxy trước khi dùng giới hạn theo IP trên Dokploy.** Đặt `FORWARDED_ALLOW_IPS`
   bằng IP của Traefik/nginx thực sự tham gia chuỗi chuyển tiếp hoặc subnet dành riêng cho các
   proxy đó. Proxy biên cần chuẩn hóa header chuyển tiếp. Compose mặc định chỉ tin loopback.
   Nếu chưa đặt trên hệ thống sau proxy, backend dùng IP của proxy làm địa chỉ của khách.

## 2. Kiến trúc đường đi

```text
Browser khách ẩn danh
  → https://<domain-fe>/chatbot/<slug>          (nginx trong container frontend, cổng 80)
  → https://<domain-fe>/platform/v1alpha1/public/chatbots/...  (proxy same-origin tới backend:8002)
Trang của đơn vị (origin khác)
  → <iframe src="https://<domain-fe>/chatbot/<slug>?embed=1">
```

- Chỉ `/chatbot/*` được phép nhúng: nginx bỏ `X-Frame-Options` và đặt
  `Content-Security-Policy: frame-ancestors *`. Mọi route khác giữ `SAMEORIGIN` +
  `frame-ancestors 'self'`.
- API đi qua proxy same-origin nên không cần nới CORS riêng; nhưng `ALLOWED_ORIGINS` phía backend
  phải chứa origin của domain frontend, và `PUBLIC_BASE_URL` trỏ về domain đó.
- Danh sách ở `GET /platform/v1alpha1/public/chatbots` đối chiếu dữ liệu phát hành với thế hệ chỉ mục đang phục vụ trong PostgreSQL. Đây là trạng thái sơ bộ của thẻ ở trang chủ. Luồng trả lời kiểm tra lại phiên bản và nội dung đã ghim trước khi dùng làm căn cứ.
- Container frontend chỉ `expose` cổng 80 (không publish ra host); Dokploy/Traefik gắn domain HTTPS
  vào cổng 80 của service `frontend`.

## 3. Các bước triển khai (khi được duyệt)

Chạy trên server, dùng file secret thật `.env.production`; không in toàn bộ `compose config` ra log.

1. Backup PostgreSQL, object store, Qdrant và giữ khóa `PROVIDER_ENCRYPTION_KEY` hiện tại.
2. Trong `.env.production`, kiểm và đặt:
   - `PUBLIC_CHATBOTS_ENABLED=true` (công tắc tổng; `false` để ẩn toàn bộ kênh công khai; bỏ trống
     thì mặc định `true`),
   - `PUBLIC_BASE_URL=https://<domain-fe>`,
   - `ALLOWED_ORIGINS` có `https://<domain-fe>` (chuỗi ngăn cách bằng dấu phẩy, không phải JSON).
3. Build thử image trước khi deploy:
   ```bash
   docker compose --env-file .env.production --profile frontend config --quiet
   docker compose --env-file .env.production --profile frontend build backend frontend
   ```
4. Triển khai có kèm service frontend:
   ```bash
   docker compose --env-file .env.production --profile frontend up -d
   docker compose --env-file .env.production ps
   docker compose --env-file .env.production logs --tail=100 bootstrap backend frontend
   ```
5. Dokploy: gắn domain HTTPS của kênh công khai vào service `frontend`, cổng **80**, bật Let's
   Encrypt. Không trỏ domain này trực tiếp vào backend 8002 vì header cho phép nhúng nằm ở nginx của
   frontend.
6. Trên giao diện quản trị: mở trợ lý → tab **Công khai** → nhập slug/tiêu đề/lời chào/câu hỏi gợi
   ý/hạn mức → Lưu (bản nháp) → **Bật công khai**. Slug được chuẩn hóa chữ thường dạng
   `tuyen-sinh-2026` và phải khác nhau giữa các trợ lý. Cần quyền `admin` của đơn vị; vai trò thấp
   hơn nhận 403, người ngoài đơn vị nhận 404.
7. Chạy mục 4 (kiểm chứng sau deploy) và mục 5 (test nhúng thật) trước khi chia sẻ link.

## 4. Kiểm chứng sau deploy

Thay `<domain-fe>` và `<slug>` bằng giá trị thật.

| Kiểm tra | Lệnh / cách xem | Kỳ vọng |
| --- | --- | --- |
| Sức khỏe frontend | `curl -s https://<domain-fe>/healthz` | `ok` |
| Trang quản trị không bị nhúng | `curl -sI https://<domain-fe>/` | có `X-Frame-Options: SAMEORIGIN`, `frame-ancestors 'self'` |
| Trang công khai được nhúng | `curl -sI https://<domain-fe>/chatbot/<slug>` | **không** có `X-Frame-Options`, có `frame-ancestors *` |
| Asset đệm dài hạn | `curl -sI https://<domain-fe>/assets/<file>.js` | `Cache-Control: public, max-age=31536000, immutable` |
| API thông suốt qua proxy | `curl -s https://<domain-fe>/platform/v1alpha1/public/chatbots/<slug>` | 200 JSON `available: true`; slug sai trả 404 `public_chatbot_not_found` |
| Bắt đầu phiên ẩn danh | `POST .../public/chatbots/<slug>/sessions` | 201, `turns_remaining = max_turns` |
| Hội thoại thật | hỏi một câu có đáp án trong kho đã xuất bản | trả lời có trích dẫn; lỗi tạm thời hiển thị thông báo thân thiện và trả câu hỏi về ô nhập để gửi lại một chạm |
| Giới hạn ẩn danh | quá 60 lượt/giờ hoặc 12 phiên/giờ từ một IP | 429 `public_chat_rate_limited`; quá `max_turns` của phiên: 429 `public_chat_session_limit` |
| Tạm dừng trợ lý | tạm dừng trong cấu hình trợ lý khi kênh công khai đang bật | thẻ hiện tạm ngưng sau khi làm mới. API tạo phiên và gửi câu hỏi trả 409 `public_chatbot_unavailable`. Bật lại cho phép tiếp tục phiên còn hạn |
| Hạn mức ngày | publication có budget và đã dùng hết | 429 `public_chat_budget_exhausted`; publication "Không giới hạn" thì bỏ qua guard này |
| Công tắc tổng | đặt `PUBLIC_CHATBOTS_ENABLED=false` rồi restart backend | mọi endpoint công khai trả 404 `public_chatbot_not_found`; bật lại thì phục hồi |
| Sổ theo dõi | tab Công khai → "Sổ theo dõi kênh công khai" | phiên/lượt/token của hôm nay tăng; ngày trống hiển thị 0, không bịa số |

Ghi chú: đổi biến môi trường cần restart backend (và worker nếu liên quan) mới có hiệu lực; dữ liệu
trong Sổ theo dõi là số liệu tổng hợp, không có thông tin định danh khách.

## 5. Kịch bản test nhúng iframe thật

Mục tiêu: chứng minh một website khác origin nhúng được, còn giao diện quản trị thì không.

1. Tạo một trang HTML tạm (để trong `%TEMP%`, không đưa vào Git):
   ```html
   <!doctype html>
   <html lang="vi">
     <body style="margin:0;font-family:sans-serif;background:#eef">
       <h3 style="margin:16px">Trang của đơn vị (origin khác)</h3>
       <iframe src="https://<domain-fe>/chatbot/<slug>?embed=1"
               title="Trợ lý tuyển sinh"
               style="width:420px;height:640px;border:0;border-radius:12px;background:#fff"></iframe>
     </body>
   </html>
   ```
2. Phục vụ trang này từ một origin/cổng khác với domain chatbot (ví dụ một máy khác, một domain
   staging, hoặc `python -m http.server 8899` trên máy cá nhân nếu domain chatbot truy cập được).
   Cùng origin không chứng minh được gì vì CSP chỉ chặn origin khác.
3. Trên trang test, xác nhận:
   - iframe hiển thị đúng giao diện rút gọn (`?embed=1`), không có thanh điều hướng quản trị;
   - gửi một câu có đáp án → hiển thị câu trả lời + trích dẫn; mở trích dẫn được;
   - thu nhỏ iframe về 375×640 (giả lập điện thoại) → không có cuộn ngang toàn trang;
   - console trình duyệt không có lỗi CSP/khung bị chặn.
4. Kiểm tra âm: đổi `src` thành `https://<domain-fe>/` (trang quản trị) → trình duyệt phải chặn
   nhúng (vi phạm `frame-ancestors 'self'` / `SAMEORIGIN`). Đây là bằng chứng hai nhóm route đang
   được phân quyền nhúng khác nhau.
5. Thử thêm: tắt publication (hoặc công tắc tổng) rồi tải lại iframe → trang hiển thị thông báo
   "Trợ lý đang tạm ngưng phục vụ", không lộ chi tiết kỹ thuật.

## 6. Rollback và công tắc an toàn

Thứ tự ưu tiên khi cần dừng kênh công khai:

1. **Tắt publication của trợ lý** trong tab Công khai — hiệu lực ngay, không cần restart; các trợ lý
   khác không ảnh hưởng.
2. **Công tắc tổng**: `PUBLIC_CHATBOTS_ENABLED=false` trong `.env.production` rồi
   `docker compose --env-file .env.production up -d backend` — ẩn mọi kênh công khai.
3. **Gỡ frontend khỏi stack**: deploy lại **không** kèm `--profile frontend` (backend/worker giữ
   nguyên), hoặc gỡ domain khỏi service `frontend` trong Dokploy.
4. **Quay image**: dùng `APP_IMAGE_TAG` của bản trước cho backend/worker và build lại frontend từ
   commit trước. Migration 0029/0030 chỉ thêm bảng mới, không sửa dữ liệu cũ, nên rollback image
   không cần downgrade schema.

Không dùng `down -v`, volume prune hoặc reset DB cho bất kỳ bước rollback nào.

## 7. Hạn chế đã biết

- Nhóm câu hỏi bảng phức tạp có thể gặp lỗi guard (~12% ở lần chạy đầu, một phần hồi phục khi gửi
  lại); trang công khai trả thông báo trung tính và giữ câu hỏi để khách gửi lại, không trả lời giả.
- Khách hoàn toàn ẩn danh, giới hạn theo IP đã băm; không có đăng nhập, không thu thập danh tính.
- Thống kê là số liệu tổng hợp; chưa có xuất CSV hay chính sách lưu trữ tự động (nhóm tùy chọn GĐ4).
- Sổ theo dõi cộng token provider báo cho các bước ModelOps trong lượt hỏi, gồm embedding, rerank,
  sinh câu trả lời, sửa, kiểm chứng và thông báo thiếu căn cứ khi có gọi model. Số đang giữ được dùng
  để xét nhận lượt gọi. Báo cáo hiển thị số token quan sát được.
