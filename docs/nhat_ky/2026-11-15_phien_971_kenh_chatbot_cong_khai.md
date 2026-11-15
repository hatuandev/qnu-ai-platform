# Phiên 971 — Kênh chatbot công khai và chuẩn bị triển khai

Ngày: 2026-11-14 → 2026-11-15. Nhánh `feat/v1-user-workflow`, không commit/push, không deploy.

## 1. Yêu cầu và quyết định

- Người dùng bỏ "Hộp thư duyệt" khỏi giao diện V2 (sidebar + route `/inbox`), giữ API inbox nhưng
  không dùng; không để lại mã thừa.
- Làm lại chức năng chatbot công khai để mỗi đơn vị tự bật, với các quyết định đã chốt:
  admin đơn vị tự bật (không cần duyệt cấp hệ thống, có công tắc tổng), khách ẩn danh hoàn toàn,
  giao diện tối giản theme QNU, URL `/chatbot/{slug}`, chỉ chia sẻ link + nhúng iframe, và tùy chọn
  hạn mức ngày "Không giới hạn" (`daily_token_budget = null`).
- Chia việc: **nhóm 2 trước** (vá OpenAPI, test hồi quy publications, UX lỗi lượt hỏi), **sau đó
  song song nhóm 1** (chuẩn bị container production + kế hoạch test iframe thật); **không deploy**.

## 2. Việc đã làm

### GĐ1–GĐ3 — kênh công khai (trong phiên)

- Backend domain mới `backendV1/qnu/domains/publications/` (models, schemas, service, router quản
  trị, public_router, public_service) + `identity/service_actor.py` (actor chỉ đọc cho khách) +
  wiring `api/routes.py`, `platform/ownership.py`, `platform/schema.py`, `alembic/env.py`.
- Migration `0029_assistant_publications.py`, `0030_publication_stats.py`; dev DB đã ở 0028, hai
  migration này áp khi deploy (bootstrap) hoặc khi chạy dev mới.
- API quản trị theo quyền đơn vị: slug chuẩn hóa chữ thường, revision-safe (`expected_revision`),
  chỉ `admin` của workspace được ghi, người ngoài nhận 404, vai trò thấp nhận 403; bật công khai chỉ
  khi trợ lý `ready` (409 `publication_not_ready`).
- API công khai không token: info/sessions/turns; guard theo thứ tự: kill-switch → phiên → trần
  lượt → rate limit theo IP băm (60 lượt/giờ, 12 phiên/giờ) → hạn mức token ngày (bỏ qua khi
  `null`) → readiness → pipeline trả lời; lỗi pipeline trả 502 kèm mã kỹ thuật, không giả câu trả lời.
- Thống kê: bảng `assistant_publication_stats`, sổ theo dõi 7/30 ngày zero-fill, ngân sách ngày
  theo Asia/Ho_Chi_Minh, top câu hỏi.
- Frontend V2: tab **Công khai** trong chi tiết trợ lý (cấu hình, bật/tắt, thẻ "Nhúng vào website",
  thẻ "Sổ theo dõi kênh công khai"), trang công khai thật `frontendV2/src/routes/chatbot.$slug.tsx`
  (thay route cũ `p.$slug.tsx`), chế độ `?embed=1`; sidebar/breadcrumb/routeTree cập nhật; bỏ
  `src/api/inbox/*` và route `/inbox`.
- E2E live trên dev đã chạy trong phiên (task #299/#302/#307): trang công khai, nhúng, thống kê.
  Publication cuối cùng để **tắt** (revision 11) — kênh chưa mở.

### Nhóm 2 — việc khuyến nghị trước deploy

1. **Vá OpenAPI artifact** `backendV1/docs/openapi-v1.json`: thêm 5 path và 11 schema publications,
   chỉ thêm (additive) so với `git show HEAD:`. Hiện 110 path / 137 schema; spec live vẫn mới hơn
   (174 path) nên artifact tiếp tục trễ có chủ đích, không regenerate toàn bộ.
2. **Test hồi quy domain publications** `backendV1/tests/integration/test_publication_channel.py`
   (mới) + cập nhật TRUNCATE list trong `conftest.py`:
   - 9/9 PASS trên DB dùng-một-lần `qnu_v1_test_591507b9e18e4e39`, 37,72 s, `db_dropped: true`,
     `legacy_sentinel_preserved: true`.
   - Bao phủ: slug chuẩn hóa/duy nhất, 403 editor vs 404 người ngoài, bật khi chưa ready
     (`publication_not_ready`), xung đột revision, info/session/kill-switch bằng monkeypatch,
     các guard phiên/rate/budget, "Không giới hạn" bỏ qua guard ngân sách, stats zero-fill và tham
     số `days`, và đường ready → bật → phục vụ với pipeline embedding giả lập.
   - Phải seed model mặc định hệ thống (`ensure_chat_default`) vì tạo trợ lý trả 409
     `model_not_configured` khi DB test trống; thêm ADMIN vào workspace của `published_input`.
3. **UX lỗi lượt hỏi trang công khai** `chatbot.$slug.tsx`: ẩn từ ngữ nội bộ ("backendV1 … cổng
   8002") khỏi khách ẩn danh; map lỗi thành thông báo thân thiện (`public_chatbot_unavailable`,
   lỗi mạng, 5xx); với lỗi tạm thời (status 0 hoặc ≥500) trả câu hỏi về ô nhập để gửi lại một chạm,
   không tạo bong bóng trùng.

### Nhóm 1 — chuẩn bị container production (không deploy)

- `frontendV2/Dockerfile`: build `node:24-alpine` (`npm ci` + `npm run build`) → `nginx:1.29-alpine`;
  healthcheck `/healthz`.
- `frontendV2/deploy/nginx.conf`: SPA fallback; proxy `/platform/` → `http://backend:8002`
  (timeout 300 s, `client_max_body_size 64m` khớp trần upload 60 MiB); `/assets/` cache immutable
  1 năm; `/healthz`; `/chatbot/` phục vụ qua **named location** (xem lỗi đã sửa bên dưới) với
  **không** `X-Frame-Options` + `Content-Security-Policy: frame-ancestors *`; mọi route khác giữ
  `SAMEORIGIN` + `frame-ancestors 'self'`.
- `frontendV2/.dockerignore`: loại `node_modules`, `dist`, `tests`, `*.log`; **giữ `dev/`** vì
  `vite.config.ts` import `dev/dev-auto-login.ts` lúc build.
- `docker-compose.yml`: service `frontend` (image `qnu-ai-platform-frontend-v2:${APP_IMAGE_TAG}`,
  build `./frontendV2`, `expose: 80`, `depends_on backend healthy`) đặt sau `profiles: ["frontend"]`
  để lần deploy hiện hành không đổi.
- `docs/trien_khai/06_kenh_chatbot_cong_khai.md` (mới): điều kiện tiên quyết (SSO cho quản trị,
  vì trang công khai không cần token nhưng bật publication cần giao diện/API có token), kiến trúc
  domain → frontend → proxy, các bước deploy có `--profile frontend`, bảng kiểm chứng sau deploy,
  kịch bản test iframe khác origin + kiểm tra âm (không nhúng được trang quản trị), rollback/công
  tắc an toàn, hạn chế đã biết.
- Đồng bộ tài liệu đang nói "chưa có service frontend": `docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md`,
  `docs/trien_khai/README.md`, `docs/deployment.md`; thêm `PUBLIC_CHATBOTS_ENABLED=true` vào
  `.env.dokploy.example`.
- Nối công tắc tổng vào compose: `x-runtime` thêm
  `PUBLIC_CHATBOTS_ENABLED: ${PUBLIC_CHATBOTS_ENABLED:-true}` — trước đó biến chỉ nằm trong mẫu env,
  container không nhận nên đặt `false` trên server sẽ không có tác dụng.

## 3. Lệnh thật đã chạy và kết quả

- Test hồi quy (harness DB dùng một lần, chạy từ root):
  `uv run --project backendV1 python backendV1/scripts/test_database.py tests/integration/test_publication_channel.py -q`
  → 9 passed, 37,72 s, DB đã drop.
- Ruff check + format các tệp backend mới → PASS; Biome check + `tsc --noEmit` frontendV2 → PASS
  (sau khi format lại dòng dài).
- Build image: `docker build -t qnu-ai-platform-frontend-v2:local frontendV2` → PASS.
- Smoke container: `docker run -d --name qnu-fe-smoke --add-host backend:host-gateway -p 18080:80 …`
  rồi curl:
  - `/healthz` → 200 `ok`;
  - `/` → index.html, `X-Frame-Options: SAMEORIGIN`, `frame-ancestors 'self'`;
  - `/chatbot/tuyen-sinh-2026` → index.html, **không** `X-Frame-Options`, `frame-ancestors *`;
  - `/assets/*.js` → `Cache-Control: public, max-age=31536000, immutable`;
  - `/platform/v1alpha1/public/chatbots/khong-ton-tai` → 404 `application/problem+json`
    (`public_chatbot_not_found`) từ backend dev trên host, chứng minh proxy same-origin hoạt động.
- `SSO_AUTHORITY=https://sso.example.test docker compose --profile frontend config --quiet` → PASS;
  danh sách service có profile: backend, bootstrap, frontend, storage-init, worker. (Thiếu biến
  deploy là hành vi có sẵn của compose production, không do thay đổi phiên này.)
- Kiểm phân giải công tắc tổng: `docker compose --profile frontend config` với env triển khai giả đủ
  biến bắt buộc và `PUBLIC_CHATBOTS_ENABLED=false` (chỉ grep dòng biến) → `"false"` có trong
  environment của backend và worker; đổi giá trị chỉ cần restart, không cần build lại.
- Dọn container smoke sau kiểm chứng; giữ image local.

## 4. Lỗi gặp và cách sửa

1. **`/chatbot/` vẫn trả `X-Frame-Options: SAMEORIGIN`** dù location riêng không đặt header:
   `try_files $uri /index.html` gây internal redirect vào `location /`, kế thừa bộ header của block
   đó (nginx thay toàn bộ `add_header` của location cha bằng của location đích). Sửa bằng named
   location `@chatbot_spa` trả `/index.html` trực tiếp kèm bộ header cho phép nhúng; build lại và
   curl xác nhận đúng. Đây là bài học cần giữ nếu sửa nginx sau này.
2. **Test publications 403 hàng loạt**: ghi publication cần role `admin` của workspace (EDITOR chỉ
   là `editor`); thêm actor ADMIN và assert riêng ca EDITOR → 403.
3. **409 `model_not_configured` khi tạo trợ lý trong DB test**: thêm `ensure_chat_default()` tạo
   provider + key + `PUT /modelops/defaults` trước mỗi ca.
4. **404 `workspace_not_found` ở ca cuối**: workspace của `published_input` chưa có ADMIN; thêm
   membership admin trước khi gọi API quản trị.
5. **Biome fail do dòng quá dài** sau khi thêm mapping lỗi; chạy `npx biome check --write`, sau đó
   Biome + tsc sạch.

## 5. PASS / FAIL / NOT RUN

- **PASS:** 9/9 test publications; Ruff; Biome; `tsc --noEmit`; `docker build`; smoke container
  (healthz, header `/` vs `/chatbot/`, cache asset, proxy 404 JSON); `docker compose --profile
  frontend config --quiet` với biến giả; E2E live GĐ1–GĐ3 đã chạy trong phiên (task #299/#302/#307).
- **FAIL (đã sửa trong phiên):** header nhúng `/chatbot/` bị SAMEORIGIN do internal redirect; đã
  sửa và kiểm lại PASS.
- **NOT RUN:** full pytest (theo yêu cầu người dùng — `NOT RUN ≠ PASS`); deploy production; SSO
  production cho frontendV2; test iframe thật trên domain thật (mới có kịch bản); bật cache C2.

## 6. Rủi ro và giới hạn

- Chưa thể quản trị kênh công khai trên production trước khi có đường đăng nhập (SSO V2 hoặc API
  token hợp lệ); trang công khai thì chạy được không token.
- Lớp lỗi guard RAG (~12% lượt ở câu bảng phức tạp, đã có từ baseline) vẫn có thể xuất hiện; trang
  công khai xử lý trung thực và cho gửi lại, không trả lời giả.
- Publication đang tắt; bật là thao tác riêng sau khi deploy và kiểm chứng.
- Artifact OpenAPI vẫn trễ so với spec live; chỉ vá thêm, không regenerate toàn bộ.

## 7. Bước tiếp

1. Người dùng duyệt thời điểm deploy; chạy mục 3–5 của checklist `06` trên server thật.
2. Bổ sung SSO production cho frontendV2 trước khi dùng giao diện quản trị trên production.
3. Chạy test nhúng iframe khác origin thật và kiểm tra âm trang quản trị.
4. Theo dõi sổ thống kê, rate limit và ngân sách sau khi mở kênh.
